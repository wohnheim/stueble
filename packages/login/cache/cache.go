package cache

import (
	"context"
	"sync"

	"github.com/redis/go-redis/v9"
)

type RedisClient struct {
	Client  *redis.Client
	Context context.Context
	mutex   sync.Mutex
}

func CreateRedisClient(address, username, password string, database int) (*RedisClient, error) {
	var err error
	var client RedisClient

	client.Client = redis.NewClient(&redis.Options{
		Addr:     address,
		Username: username,
		Password: password,
		DB:       database,
	})

	client.Context = context.Background()

	if err = client.Client.Ping(client.Context).Err(); err != nil {
		return nil, err
	}

	return &client, nil
}

func (c *RedisClient) ClosePool() {
	c.mutex.Lock()
	defer c.mutex.Unlock()

	if c.Client == nil {
		return
	}

	c.Client.Close()
	c.Client = nil
}
