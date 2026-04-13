package sessions

import (
	"context"
	"errors"
	"log"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/wohnheim/backend/database"
)

type Sessions struct {
	TTL int
}

type Session struct {
	SessionId      string
	ExpirationDate time.Time
}

// TODO parse into UserRole Enum
type SessionInfo struct {
	Id       string `db:"session_id"`
	UserId   int    `db:"user_id"`
	UserRole string `db:"user_role"`
}

func (s *Sessions) CreateSession(ctx context.Context, pool *database.DatabasePool, id int) (*Session, error) {
	if pool == nil {
		log.Panic("Assertion failed: pool needs to be defined")
	}

	sql := `
		INSERT INTO sessions (user_id, expiration_date)
		VALUES ($1, NOW() + ($2 * INTERVAL '1 day'))
		RETURNING session_id, expiration_date
	`

	var session Session
	err := pool.Pool.QueryRow(ctx, sql, id, s.TTL).Scan(&session.SessionId, &session.ExpirationDate)
	if err != nil {
		return nil, err
	}

	return &session, nil
}

func (s *Sessions) GetSessionInfo(ctx context.Context, pool *database.DatabasePool, sessionId string) (*SessionInfo, error) {
	sql := `
		SELECT session_id, user_id, user_role
		FROM sessions
		JOIN users ON sessions.user_id = users.id
		WHERE session_id = $1
	`

	rows, _ := pool.Pool.Query(ctx, sql, sessionId)
	info, err := pgx.CollectExactlyOneRow(rows, pgx.RowToStructByName[SessionInfo])
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}

		return &info, err
	}

	return &info, nil
}

func (s *Sessions) DeleteSession(ctx context.Context, pool *database.DatabasePool, sessionId string) (bool, error) {
	sql := `
		DELETE FROM sessions
		WHERE session_id = $1
	`

	ct, err := pool.Pool.Exec(ctx, sql, sessionId)
	if err != nil {
		return false, err
	}

	return ct.RowsAffected() == 1, nil
}

func (s *Sessions) DeleteSessions(ctx context.Context, pool *database.DatabasePool, userId int) error {
	sql := `
		DELETE FROM sessions
		WHERE user_id = $1
	`

	_, err := pool.Pool.Exec(ctx, sql, userId)
	return err
}
