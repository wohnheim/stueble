package database

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/wohnheim/backend/passwordHashing"
)

type LoginInfo struct {
	Id                int     `db:"id"`
	PasswordHash      *string `db:"password_hash"`
	PasswordSalt      *string `db:"password_salt"`
	PasswordAlgorithm string  `db:"password_algorithm"`
}

type User struct {
	Id        int     `db:"id" json:"id"`
	FirstName string  `db:"first_name" json:"firstName"`
	LastName  string  `db:"last_name" json:"lastName"`
	Room      int32   `db:"room" json:"roomNumber"`
	Residence string  `db:"residence" json:"residence"`
	Email     *string `db:"email" json:"email"`
	Username  string  `db:"user_name" json:"username"`
}

type ConflictingUser struct {
	Id           int     `db:"id"`
	FirstName    string  `db:"first_name" `
	LastName     string  `db:"last_name"`
	Email        string  `db:"email"`
	Username     string  `db:"user_name"`
	Room         int32   `db:"room"`
	Residence    string  `db:"residence"`
	PasswordHash *string `db:"password_hash"`
}

type SignupInfo struct {
	FirstName         string `json:"firstName"`
	LastName          string `json:"lastName"`
	RoomNumber        int32  `json:"roomNumber"`
	Residence         string `json:"residence"`
	Username          string `json:"username"`
	Email             string `json:"email"`
	PasswordHash      string `json:"passwordHash"`
	PasswordSalt      string `json:"passwordSalt"`
	PasswordAlgorithm string `json:"passwordAlgorithm"`
}

func (p *DatabasePool) GetLoginInfo(ctx context.Context, email *string, username *string) (*LoginInfo, error) {
	if email == nil && username == nil {
		log.Panic("Assertion failed: Either email or username needs to be defined")
	}

	sql := "SELECT id, password_hash, password_salt, password_algorithm FROM users WHERE deleted IS FALSE"
	var args []any
	argPos := 1

	if email != nil {
		sql += fmt.Sprintf(" AND email = $%d", argPos)
		args = append(args, *email)
		argPos++
	}

	if username != nil {
		sql += fmt.Sprintf(" AND user_name = $%d", argPos)
		args = append(args, *username)
		argPos++
	}

	rows, _ := p.Pool.Query(ctx, sql, args...)
	info, err := pgx.CollectExactlyOneRow(rows, pgx.RowToStructByName[LoginInfo])
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}

		return nil, err
	}

	// Legacy bcrypt hashed passwords are not base64 encoded
	if info.PasswordAlgorithm != "bcrypt" {
		decodedHash, err := base64.StdEncoding.DecodeString(*info.PasswordHash)
		if err != nil {
			return nil, err
		} else {
			str := string(decodedHash)
			info.PasswordHash = &str
		}

		if info.PasswordSalt != nil {
			decodedSalt, err := base64.StdEncoding.DecodeString(*info.PasswordSalt)
			if err != nil {
				return nil, err
			} else {
				str := string(decodedSalt)
				info.PasswordSalt = &str
			}
		}
	}

	return &info, nil
}

func (p *DatabasePool) GetUser(ctx context.Context, id int) (*User, error) {
	sql := `
		SELECT id, first_name, last_name, room, residence, email, user_name
		FROM users
		WHERE id = $1
	`

	rows, _ := p.Pool.Query(ctx, sql, id)
	user, err := pgx.CollectExactlyOneRow(rows, pgx.RowToStructByName[User])
	if err != nil {
		return nil, err
	}

	return &user, nil
}

func (p *DatabasePool) UpdateUsername(ctx context.Context, id int, username string) error {
	sql := `
		UPDATE users
		SET user_name = $1
		WHERE id = $2
	`

	_, err := p.Pool.Exec(ctx, sql, username, id)
	return err
}

func (p *DatabasePool) UpdatePassword(ctx context.Context, id int, hashSalt *passwordHashing.HashSalt) error {
	sql := `
		UPDATE users
		SET password_hash = $1, password_salt = $2, password_algorithm = $3
		WHERE id = $4
	`

	_, err := p.Pool.Exec(ctx, sql, base64.StdEncoding.EncodeToString(hashSalt.Hash), base64.StdEncoding.EncodeToString(hashSalt.Salt), passwordHashing.HashAlgorithm, id)
	return err
}

func (p *DatabasePool) GetConflictingUsers(ctx context.Context, email *string, username *string, room *int32, residence *string) ([]ConflictingUser, error) {
	if email == nil && username == nil && (room == nil || residence == nil) {
		log.Panic("Assertion failed: Only unique key combination needs to be defined")
	}

	sql := "SELECT id, first_name, last_name, email, user_name, room, residence, password_hash FROM users WHERE deleted IS FALSE AND (0=1"
	var args []any
	argPos := 1

	if email != nil {
		sql += fmt.Sprintf(" OR email = $%d", argPos)
		args = append(args, *email)
		argPos++
	}

	if username != nil {
		sql += fmt.Sprintf(" OR user_name = $%d", argPos)
		args = append(args, *username)
		argPos++
	}

	if room != nil && residence != nil {
		sql += fmt.Sprintf(" OR (room = $%d AND residence = $%d)", argPos, argPos+1)
		args = append(args, *room, *residence)
		argPos += 2
	}

	rows, _ := p.Pool.Query(ctx, sql+")", args...)
	return pgx.CollectRows(rows, pgx.RowToStructByName[ConflictingUser])
}

func (p *DatabasePool) CreateUser(ctx context.Context, signupInfos *SignupInfo, userRole string) (int, error) {
	sql := `
		INSERT INTO users (first_name, last_name, room, residence, user_name, email, password_hash, password_salt, password_algorithm, user_role)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		RETURNING id
	`

	var userId int
	row := p.Pool.QueryRow(ctx, sql, signupInfos.FirstName, signupInfos.LastName, signupInfos.RoomNumber, signupInfos.Residence, signupInfos.Username, signupInfos.Email, signupInfos.PasswordHash, signupInfos.PasswordSalt, signupInfos.PasswordAlgorithm, userRole)
	err := row.Scan(&userId)
	if err != nil {
		return -1, err
	}

	return userId, nil
}

func (p *DatabasePool) DisableUser(ctx context.Context, id int) error {
	sql := `
		UPDATE users
		SET deleted = TRUE
		WHERE id = $1
	`

	_, err := p.Pool.Exec(ctx, sql, id)
	return err
}

func (p *DatabasePool) DeleteUser(ctx context.Context, id int) error {
	sql := `
		DELETE FROM users
		WHERE id = $1
	`

	_, err := p.Pool.Exec(ctx, sql, id)
	return err
}

func (p *DatabasePool) AddVerificationCode(ctx context.Context, ttl int, v any) (*string, *time.Time, error) {
	if ttl < 0 {
		ttl = p.verificationCodeTTL
	}

	sql := `
		INSERT INTO verification_codes (additional_data, expiration_date)
		VALUES ($1, NOW() + ($2 * INTERVAL '1 minute'))
		RETURNING id, expiration_date
	`

	vJson, err := json.Marshal(v)
	if err != nil {
		return nil, nil, err
	}

	var code string
	var expirationDate time.Time
	row := p.Pool.QueryRow(ctx, sql, vJson, ttl)
	err = row.Scan(&code, &expirationDate)
	if err != nil {
		return nil, nil, err
	}

	return &code, &expirationDate, nil
}

// TODO: Split into Get and Delete functions
// TBC: Storing Multi-Use Column in DB
// This function can return a nil value without error.
func (p *DatabasePool) GetAdditionalData(ctx context.Context, delete bool, token string, dest any) (bool, error) {
	var sql string
	if delete {
		sql = `
			DELETE FROM verification_codes
			WHERE id = $1
			RETURNING additional_data
		`
	} else {
		sql = `
			SELECT additional_data
			FROM verification_codes
			WHERE id = $1
		`
	}

	err := p.Pool.QueryRow(ctx, sql, token).Scan(dest)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return false, nil
		}

		return false, err
	}

	return true, nil
}
