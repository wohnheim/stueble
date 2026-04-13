package endpoints

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/mail"
	"os"
	"strings"
	"time"

	"github.com/wohnheim/stueble/database"
	"github.com/wohnheim/stueble/passwordHashing"
	"github.com/wohnheim/stueble/templates"
	"github.com/wohnheim/stueble/utils"
)

type LoginRequest struct {
	User     string `json:"user"`
	Password string `json:"password"`
}

type SignupRequest struct {
	FirstName  string `json:"firstName"`
	LastName   string `json:"lastName"`
	RoomNumber int32  `json:"roomNumber"`
	Residence  string `json:"residence"`
	Username   string `json:"username"`
	Email      string `json:"email"`
	Password   string `json:"password"`
	Token      string `json:"token"`
	// Property to prevent manual registration without accepting the privacy policy
	PrivacyPolicy bool `json:"privacyPolicy"`
}

type VerifySignupRequest struct {
	Token string `json:"token"`
}

type ChangePasswordRequest struct {
	NewPassword string `json:"newPassword"`
}

type ChangeUsernameRequest struct {
	Username string `json:"username"`
}

type ResetPasswordRequest struct {
	User string `json:"user"`
}

type ResetPasswordConfirmRequest struct {
	Token    string `json:"token"`
	Password string `json:"password"`
}

type SignupTokenRequest struct {
	TokenTTL int `json:"token_ttl"`
}

type SignupTokenResponse struct {
	Token          string `json:"token"`
	ExpirationDate string `json:"expiration_date"`
}

func IsEmail(email string) bool {
	emailAddress, err := mail.ParseAddress(email)
	return err == nil && emailAddress.Address == email
}

func createSecureCookie(value string, expires time.Time) *http.Cookie {
	return &http.Cookie{
		Name:     "SID",
		Value:    value,
		Path:     "/",
		Expires:  expires,
		HttpOnly: true,
		Secure:   true,
		SameSite: http.SameSiteLaxMode,
	}
}

func login(w http.ResponseWriter, req *http.Request) {
	var l LoginRequest

	if req.Method != "POST" {
		http.NotFound(w, req)
		return
	}

	valid := func(l *LoginRequest) bool { return len(l.Password) != 0 }
	if !parseJSONData(w, req, &l, valid) {
		return
	}

	ctx := req.Context()

	var info *database.LoginInfo
	var err error
	l.User = strings.ToLower(l.User)
	if IsEmail(l.User) {
		info, err = sd.DB.GetLoginInfo(ctx, &l.User, nil)
	} else {
		info, err = sd.DB.GetLoginInfo(ctx, nil, &l.User)
	}

	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
		return
	} else if info == nil {
		writeJSONError(w, err, http.StatusUnauthorized, "Email address and password do not match.", nil, false)
		return
	}

	changePassword, err := passwordHashing.Compare([]byte(utils.OptionalDereference(info.PasswordHash, "")), []byte(utils.OptionalDereference(info.PasswordSalt, "")), []byte(l.Password), info.PasswordAlgorithm)
	if err != nil {
		message := "Email address and password do not match."
		if changePassword {
			message += " Try resetting your password."
		}

		writeJSONError(w, err, http.StatusUnauthorized, message, nil, false)
		return
	}

	if changePassword {
		hashSalt, err := passwordHashing.GenerateHash([]byte(l.Password), nil)
		if err != nil {
			fmt.Fprintf(os.Stderr, "WARN: Failed to update password hash from %s: %v\n", info.PasswordAlgorithm, err)
		} else {
			err = sd.DB.UpdatePassword(ctx, info.Id, hashSalt)
			if err != nil {
				fmt.Fprintf(os.Stderr, "WARN: Failed to query database: %v\n", err)
			}
		}
	}

	session, err := sd.Sessions.CreateSession(ctx, sd.DB, info.Id)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to create session", nil, true)
		return
	}

	cookie := createSecureCookie(session.SessionId, session.ExpirationDate)
	http.SetCookie(w, cookie)

	w.WriteHeader(http.StatusNoContent)
}

func logout(w http.ResponseWriter, req *http.Request) {
	if req.Method != "POST" {
		http.NotFound(w, req)
		return
	}

	cookie, err := req.Cookie("SID")
	if err != nil {
		writeJSONError(w, err, http.StatusUnauthorized, "Missing session identifier", nil, false)
		return
	}

	http.SetCookie(w, createSecureCookie("", time.Unix(0, 0)))

	removed, err := sd.Sessions.DeleteSession(req.Context(), sd.DB, cookie.Value)
	if err != nil || !removed {
		var message string
		if err != nil {
			message = err.Error()
		} else {
			message = "Invalid session identifier"
		}

		writeJSONError(w, err, http.StatusUnauthorized, message, nil, false)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func signup(w http.ResponseWriter, req *http.Request) {
	var s SignupRequest

	if req.Method != "POST" {
		http.NotFound(w, req)
		return
	}

	valid := func(s *SignupRequest) bool {
		return len(s.FirstName) != 0 && len(s.LastName) != 0 && len(s.Username) != 0 && IsEmail(s.Email) && len(s.Password) != 0 && len(s.Token) != 0 && utils.CheckMapKey(residenceNameReverse, s.Residence) && s.PrivacyPolicy
	}
	if !parseJSONData(w, req, &s, valid) {
		return
	}

	ctx := req.Context()

	var additionalData string
	found, err := sd.DB.GetAdditionalData(ctx, false, s.Token, &additionalData)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to validate verification token", nil, true)
		return
	} else if !found || len(additionalData) < 3 || additionalData[1:len(additionalData)-1] != "signup-token" {
		writeJSONError(w, err, http.StatusUnauthorized, "Invalid verification token", nil, false)
		return
	}

	conflictingUsers, err := sd.DB.GetConflictingUsers(ctx, &s.Email, &s.Username, &s.RoomNumber, &s.Residence)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
		return
	}

	lenConflictingUsers := len(conflictingUsers)
	if lenConflictingUsers != 0 {
		var conflicts []string
		var roomConflict *database.ConflictingUser

		roomConflict = nil
		emailConflict := false
		usernameConflict := false

		for i := range lenConflictingUsers {
			if roomConflict == nil && s.RoomNumber == conflictingUsers[i].Room && s.Residence == conflictingUsers[i].Residence {
				roomConflict = &conflictingUsers[i]
				continue
			}

			if !emailConflict && s.Email == conflictingUsers[i].Email {
				emailConflict = true
				conflicts = append(conflicts, "email")
			}

			if !usernameConflict && s.Username == conflictingUsers[i].Username {
				usernameConflict = true
				conflicts = append(conflicts, "username")
			}
		}

		if emailConflict || usernameConflict {
			writeJSONError(w, err, http.StatusBadRequest, "Failed to create account. Conflicting entries exist.", conflicts, false)
			return
		} else {
			err = sd.DB.DisableUser(ctx, roomConflict.Id)
			if err != nil {
				writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
				return
			}

			templateData := templates.OverwrittenUserTemplateData{
				FirstName: roomConflict.FirstName,
				LastName:  roomConflict.LastName,
				ContentId: "stueble_logo",
			}

			var buffer bytes.Buffer
			err = sd.Templates.ExecuteTemplate(&buffer, "overwritten-user-info.html", &templateData)
			if err != nil {
				writeJSONError(w, err, http.StatusInternalServerError, "Failed to execute template", nil, true)
				return
			}

			var icon []byte
			icon, err = templates.AssetFiles.ReadFile("assets/stueble_150.png")
			if err != nil {
				writeJSONError(w, err, http.StatusInternalServerError, "Failed to read image file", nil, true)
				return
			}

			msg := sd.SMTPBase.
				To(fmt.Sprintf("%s %s", roomConflict.FirstName, roomConflict.LastName), roomConflict.Email).
				Subject("Stüble-Benutzeraccount deaktiviert").
				AddInline(icon, "image/png", "image.png", templateData.ContentId).
				HTML(buffer.Bytes())

			err = msg.Send(sd.SMTPSender)
			if err != nil {
				writeJSONError(w, err, http.StatusInternalServerError, "Failed to send overwritten user info email", nil, true)
				return
			}
		}
	}

	hashSalt, err := passwordHashing.GenerateHash([]byte(s.Password), nil)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to generate password hash", nil, true)
		return
	}

	token, _, err := sd.DB.AddVerificationCode(ctx, -1, &database.SignupInfo{
		FirstName:         s.FirstName,
		LastName:          s.LastName,
		RoomNumber:        s.RoomNumber,
		Residence:         s.Residence,
		Username:          s.Username,
		Email:             s.Email,
		PasswordHash:      base64.StdEncoding.EncodeToString(hashSalt.Hash),
		PasswordSalt:      base64.StdEncoding.EncodeToString(hashSalt.Salt),
		PasswordAlgorithm: passwordHashing.HashAlgorithm,
	})
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to cache signup information", nil, true)
		return
	}

	templateData := templates.ConfirmationTemplateData{
		FirstName:         s.FirstName,
		LastName:          s.LastName,
		ContentId:         "stueble_logo",
		FrontendUrl:       sd.FrontendUrl,
		VerificationToken: *token,
	}

	var buffer bytes.Buffer
	err = sd.Templates.ExecuteTemplate(&buffer, "signup-confirmation.html", &templateData)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to execute template", nil, true)
		return
	}

	var icon []byte
	icon, err = templates.AssetFiles.ReadFile("assets/stueble_150.png")
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to read image file", nil, true)
		return
	}

	msg := sd.SMTPBase.
		To(fmt.Sprintf("%s %s", s.FirstName, s.LastName), s.Email).
		Subject("Neuer Benutzeraccount für das Stüble").
		AddInline(icon, "image/png", "image.png", templateData.ContentId).
		HTML(buffer.Bytes())

	err = msg.Send(sd.SMTPSender)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to send verification email", nil, true)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func verifySignup(w http.ResponseWriter, req *http.Request) {
	var v VerifySignupRequest

	if req.Method != "POST" {
		http.NotFound(w, req)
		return
	}

	valid := func(v *VerifySignupRequest) bool { return len(v.Token) != 0 }
	if !parseJSONData(w, req, &v, valid) {
		return
	}

	ctx := req.Context()

	var infos database.SignupInfo
	found, err := sd.DB.GetAdditionalData(ctx, true, v.Token, &infos)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to get cached signup information", nil, true)
		return
	} else if !found {
		writeJSONError(w, err, http.StatusUnauthorized, "Invalid verification token", nil, false)
		return
	}

	userId, err := sd.DB.CreateUser(ctx, &infos, UserRoleUser.String())
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
		return
	}

	session, err := sd.Sessions.CreateSession(ctx, sd.DB, userId)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to create session", nil, true)
		return
	}

	cookie := createSecureCookie(session.SessionId, session.ExpirationDate)
	http.SetCookie(w, cookie)

	w.WriteHeader(http.StatusNoContent)
}

func delete(w http.ResponseWriter, req *http.Request) {
	if req.Method != "DELETE" {
		http.NotFound(w, req)
		return
	}

	cookie, err := req.Cookie("SID")
	if err != nil {
		writeJSONError(w, err, http.StatusUnauthorized, "Missing session identifier", nil, false)
		return
	}

	http.SetCookie(w, createSecureCookie("", time.Unix(0, 0)))

	ctx := req.Context()

	session, err := sd.Sessions.GetSessionInfo(ctx, sd.DB, cookie.Value)
	if err != nil || session == nil {
		var message string
		if err != nil {
			message = err.Error()
		} else {
			message = "Invalid session identifier"
		}

		writeJSONError(w, err, http.StatusUnauthorized, message, nil, false)
		return
	}

	err = sd.Sessions.DeleteSessions(ctx, sd.DB, session.UserId)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to delete sessions", nil, true)
		return
	}

	err = sd.DB.DisableUser(ctx, session.UserId)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func changeLoginInfo(w http.ResponseWriter, req *http.Request) {
	if req.Method != "POST" {
		http.NotFound(w, req)
		return
	}

	cookie, err := req.Cookie("SID")
	if err != nil {
		writeJSONError(w, err, http.StatusUnauthorized, "Missing session identifier", nil, false)
		return
	}

	ctx := req.Context()

	session, err := sd.Sessions.GetSessionInfo(ctx, sd.DB, cookie.Value)
	if err != nil || session == nil {
		var message string
		if err != nil {
			message = err.Error()
		} else {
			message = "Invalid session identifier"
		}

		writeJSONError(w, err, http.StatusUnauthorized, message, nil, false)
		return
	}

	switch req.Pattern {
	case "/change_password":
		var c ChangePasswordRequest

		valid := func(c *ChangePasswordRequest) bool { return len(c.NewPassword) != 0 }
		if !parseJSONData(w, req, &c, valid) {
			return
		}

		hashSalt, err := passwordHashing.GenerateHash([]byte(c.NewPassword), nil)
		if err != nil {
			writeJSONError(w, err, http.StatusInternalServerError, "Failed to generate password hash", nil, true)
			return
		}

		err = sd.DB.UpdatePassword(ctx, session.UserId, hashSalt)
		if err != nil {
			writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
			return
		}
	case "/change_username":
		var c ChangeUsernameRequest

		valid := func(c *ChangeUsernameRequest) bool { return len(c.Username) != 0 }
		if !parseJSONData(w, req, &c, valid) {
			return
		}

		conflictingUsers, err := sd.DB.GetConflictingUsers(ctx, nil, &c.Username, nil, nil)
		if err != nil {
			writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
			return
		}

		if len(conflictingUsers) > 0 {
			writeJSONError(w, err, http.StatusBadRequest, "Failed to update username. Conflicting entries exist.", nil, false)
			return
		}

		err = sd.DB.UpdateUsername(ctx, session.UserId, strings.ToLower(c.Username))
		if err != nil {
			writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
			return
		}
	}

	w.WriteHeader(http.StatusNoContent)
}

func resetPassword(w http.ResponseWriter, req *http.Request) {
	var r ResetPasswordRequest

	if req.Method != "POST" {
		http.NotFound(w, req)
		return
	}

	valid := func(r *ResetPasswordRequest) bool { return len(r.User) != 0 }
	if !parseJSONData(w, req, &r, valid) {
		return
	}

	ctx := req.Context()

	var info *database.LoginInfo
	var err error
	r.User = strings.ToLower(r.User)
	if IsEmail(r.User) {
		info, err = sd.DB.GetLoginInfo(ctx, &r.User, nil)
	} else {
		info, err = sd.DB.GetLoginInfo(ctx, nil, &r.User)
	}

	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
		return
	} else if info == nil {
		w.WriteHeader(http.StatusNoContent)
		return
	}

	user, err := sd.DB.GetUser(ctx, info.Id)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
		return
	}

	token, _, err := sd.DB.AddVerificationCode(ctx, -1, info.Id)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to create verification code", nil, true)
		return
	}

	templateData := templates.ConfirmationTemplateData{
		FirstName:         user.FirstName,
		LastName:          user.LastName,
		ContentId:         "stueble_logo",
		FrontendUrl:       sd.FrontendUrl,
		VerificationToken: *token,
	}

	var buffer bytes.Buffer
	err = sd.Templates.ExecuteTemplate(&buffer, "reset-password-confirmation.html", &templateData)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to execute template", nil, true)
		return
	}

	var icon []byte
	icon, err = templates.AssetFiles.ReadFile("assets/stueble_150.png")
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to read image file", nil, true)
		return
	}

	msg := sd.SMTPBase.
		To(fmt.Sprintf("%s %s", user.FirstName, user.LastName), *user.Email).
		Subject("Passwort zurücksetzen").
		AddInline(icon, "image/png", "image.png", templateData.ContentId).
		HTML(buffer.Bytes())

	err = msg.Send(sd.SMTPSender)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to send password reset email", nil, true)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func resetPasswordConfirmation(w http.ResponseWriter, req *http.Request) {
	var r ResetPasswordConfirmRequest

	if req.Method != "POST" {
		http.NotFound(w, req)
		return
	}

	valid := func(r *ResetPasswordConfirmRequest) bool { return len(r.Token) != 0 && len(r.Password) != 0 }
	if !parseJSONData(w, req, &r, valid) {
		return
	}

	ctx := req.Context()

	var userId int
	found, err := sd.DB.GetAdditionalData(ctx, true, r.Token, &userId)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to get user identifier", nil, true)
		return
	} else if !found {
		writeJSONError(w, err, http.StatusUnauthorized, "Invalid password reset token", nil, false)
		return
	}

	hashSalt, err := passwordHashing.GenerateHash([]byte(r.Password), nil)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to generate password hash", nil, true)
		return
	}

	err = sd.DB.UpdatePassword(ctx, userId, hashSalt)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to query database", nil, true)
		return
	}

	err = sd.Sessions.DeleteSessions(ctx, sd.DB, userId)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to delete sessions", nil, true)
		return
	}

	session, err := sd.Sessions.CreateSession(ctx, sd.DB, userId)
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to create session", nil, true)
		return
	}

	cookie := createSecureCookie(session.SessionId, session.ExpirationDate)
	http.SetCookie(w, cookie)

	w.WriteHeader(http.StatusNoContent)
}

func signupToken(w http.ResponseWriter, req *http.Request) {
	var s SignupTokenRequest

	if req.Method != "PUT" {
		http.NotFound(w, req)
		return
	}

	cookie, err := req.Cookie("SID")
	if err != nil {
		writeJSONError(w, err, http.StatusUnauthorized, "Missing session identifier", nil, false)
		return
	}

	ctx := req.Context()

	session, err := sd.Sessions.GetSessionInfo(ctx, sd.DB, cookie.Value)
	if err != nil || session == nil {
		var message string
		if err != nil {
			message = err.Error()
		} else {
			message = "Invalid session identifier"
		}

		writeJSONError(w, err, http.StatusUnauthorized, message, nil, false)
		return
	}

	if session.UserRole != "admin" {
		writeJSONError(w, nil, http.StatusForbidden, "Admin permissions are required", nil, false)
		return
	}

	valid := func(s *SignupTokenRequest) bool { return s.TokenTTL > 0 }
	if !parseJSONData(w, req, &s, valid) {
		return
	}

	token, expirationDate, err := sd.DB.AddVerificationCode(ctx, s.TokenTTL, "signup-token")
	if err != nil {
		writeJSONError(w, err, http.StatusInternalServerError, "Failed to create verification code", nil, true)
		return
	}

	response := SignupTokenResponse{
		Token:          *token,
		ExpirationDate: expirationDate.Format(time.RFC3339),
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(response)
}

func RegisterAuthEndpoints() {
	const prefix = "/auth"

	http.HandleFunc(prefix+"/login", login)
	http.HandleFunc(prefix+"/logout", logout)
	http.HandleFunc(prefix+"/signup", signup)
	http.HandleFunc(prefix+"/verify_signup", verifySignup)
	http.HandleFunc(prefix+"/delete", delete)
	http.HandleFunc(prefix+"/change_password", changeLoginInfo)
	http.HandleFunc(prefix+"/change_username", changeLoginInfo)
	http.HandleFunc(prefix+"/reset_password", resetPassword)
	http.HandleFunc(prefix+"/reset_password_confirm", resetPasswordConfirmation)

	http.HandleFunc(prefix+"/signup_token", signupToken)
}
