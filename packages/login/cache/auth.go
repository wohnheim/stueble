package cache

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/gofrs/uuid/v5"
	"github.com/redis/go-redis/v9"
)

type SignupInfos struct {
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

func (r *RedisClient) AddSignupInfos(infos *SignupInfos) (*string, error) {
	infosJson, err := json.Marshal(infos)
	if err != nil {
		return nil, err
	}

	var uuidv7 uuid.UUID
	uuidv7, err = uuid.NewV7()
	if err != nil {
		return nil, err
	}

	uuidString := uuidv7.String()

	tx := r.Client.TxPipeline()

	tx.Set(r.Context, "signup-"+uuidString, infosJson, 30*time.Minute)
	tx.Set(r.Context, fmt.Sprintf("signup-map-%d-%s", infos.RoomNumber, infos.Residence), uuidString, 30*time.Minute)

	_, err = tx.Exec(r.Context)
	if err != nil {
		return nil, err
	}

	return &uuidString, nil
}

// This function can return a nil value without error.
func (r *RedisClient) GetSignupInfos(token string) (*SignupInfos, error) {
	var infos SignupInfos

	tx := r.Client.TxPipeline()
	key := fmt.Sprintf("signup-%s", token)

	infosCmd := tx.JSONGet(r.Context, key)
	tx.Del(r.Context, key)

	var err error
	_, err = tx.Exec(r.Context)
	if err != nil {
		if err == redis.Nil {
			return nil, nil
		} else {
			return nil, err
		}
	}

	err = json.Unmarshal([]byte(infosCmd.Val()), &infos)
	if err != nil {
		return nil, err
	}

	return &infos, nil
}
