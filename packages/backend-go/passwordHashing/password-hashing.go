package passwordHashing

import (
	"bytes"
	"crypto/rand"
	"errors"

	"golang.org/x/crypto/argon2"
	"golang.org/x/crypto/bcrypt"
)

const HashAlgorithm = "argon2id"

type argon2idHash struct {
	Time uint32
	// computation cost
	Memory uint32
	// parallelism
	Threads uint8
	KeyLen  uint32
	SaltLen uint32
}

type HashSalt struct {
	Hash []byte
	Salt []byte
}

var argon2IdHash = argon2idHash{1, 64 * 1024, 4, 32, 16}

func randomSecret(length uint32) ([]byte, error) {
	secret := make([]byte, length)

	_, err := rand.Read(secret)
	if err != nil {
		return nil, err
	}

	return secret, nil
}

func (a *argon2idHash) generateHash(password, salt []byte) (*HashSalt, error) {
	if len(salt) == 0 {
		var err error

		salt, err = randomSecret(a.SaltLen)
		if err != nil {
			return nil, err
		}
	}

	hash := argon2.IDKey(password, salt, a.Time, a.Memory, a.Threads, a.KeyLen)

	return &HashSalt{Hash: hash, Salt: salt}, nil
}

func (a *argon2idHash) compare(hash, salt, password []byte) error {
	hashSalt, err := a.generateHash(password, salt)
	if err != nil {
		return err
	}

	if !bytes.Equal(hash, hashSalt.Hash) {
		return errors.New("Hashes don't match")
	}

	return nil
}

func Compare(hash, salt, password []byte, algorithm string) (bool, error) {
	switch algorithm {
	case HashAlgorithm:
		return false, argon2IdHash.compare(hash, salt, password)
	case "bcrypt":
		return true, bcrypt.CompareHashAndPassword(hash, password)
	default:
		return true, errors.New("Unknown hashing algorithm")
	}
}

func GenerateHash(password, salt []byte) (*HashSalt, error) {
	return argon2IdHash.generateHash(password, salt)
}
