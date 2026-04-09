package database

import (
	"context"
	"sync"

	"github.com/jackc/pgx/v5/pgxpool"
)

type DatabasePool struct {
	Pool  *pgxpool.Pool
	mutex sync.Mutex

	verificationCodeTTL int
}

func CreateDatabasePool(url string, verificationCodeTTL int) (*DatabasePool, error) {
	var err error
	var pool DatabasePool

	pool.verificationCodeTTL = verificationCodeTTL
	ctx := context.Background()

	pool.Pool, err = pgxpool.New(ctx, url)
	if err != nil {
		return nil, err
	}

	if err = pool.Pool.Ping(ctx); err != nil {
		return nil, err
	}

	return &pool, nil
}

func (p *DatabasePool) ClosePool() {
	p.mutex.Lock()
	defer p.mutex.Unlock()

	if p.Pool == nil {
		return
	}

	p.Pool.Close()
	p.Pool = nil
}
