package endpoints

import (
	"encoding/json"
	"fmt"
	"html/template"
	"io"
	"net/http"
	"os"

	"github.com/jhillyerd/enmime"
	"github.com/wohnheim/stueble/database"
	"github.com/wohnheim/stueble/sessions"
	"github.com/wohnheim/stueble/utils"
)

/* Essential connections and data */

type SharedData struct {
	DB          *database.DatabasePool
	SMTPSender  *enmime.SMTPSender
	SMTPBase    enmime.MailBuilder
	Templates   *template.Template
	Sessions    *sessions.Sessions
	FrontendUrl string
}

var sd *SharedData

func InitializeSharedData(sharedData *SharedData) {
	sd = sharedData
}

/* Utility functions */

type ErrorMessage struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

func writeJSONError(w http.ResponseWriter, err error, code int, message string, data any, log bool) {
	if log {
		fmt.Fprintf(os.Stderr, "ERROR: %s: %v\n", message, err)
	}

	errMessage := ErrorMessage{
		Code:    code,
		Message: message,
		Data:    data,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(errMessage)
}

func parseJSONData[T any](w http.ResponseWriter, req *http.Request, v T, valid func(T) bool) bool {
	if req.Header.Get("Content-Type") != "application/json" {
		w.WriteHeader(http.StatusUnsupportedMediaType)
		return false
	}

	body, err := io.ReadAll((req.Body))
	if err != nil {
		writeJSONError(w, err, http.StatusBadRequest, "Failed to parse input data", nil, false)
		return false
	}

	if json.Unmarshal(body, v) != nil || (valid != nil && !valid(v)) {
		writeJSONError(w, err, http.StatusBadRequest, "Invalid JSON data", nil, false)
		return false
	}

	return true
}

/* Residence Enum */

type Residence int

const (
	ResidenceAltbau Residence = iota
	ResidenceNeubau
	ResidenceAnbau
	ResidenceHirte
)

var residenceName = map[Residence]string{
	ResidenceAltbau: "altbau",
	ResidenceNeubau: "neubau",
	ResidenceAnbau:  "anbau",
	ResidenceHirte:  "hirte",
}

var residenceNameReverse = utils.ReverseMap(residenceName)

func (r Residence) String() string {
	return residenceName[r]
}

/* UserRole Enum */

type UserRole int

const (
	UserRoleExtern UserRole = iota
	UserRoleUser
	UserRoleHost
	UserRoleTutor
	UserRoleAdmin
)

var userRoleName = map[UserRole]string{
	UserRoleExtern: "extern",
	UserRoleUser:   "user",
	UserRoleHost:   "host",
	UserRoleTutor:  "tutor",
	UserRoleAdmin:  "admin",
}

var userRoleNameReverse = utils.ReverseMap(userRoleName)

func (r UserRole) String() string {
	return userRoleName[r]
}
