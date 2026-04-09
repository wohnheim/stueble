package main

import (
	"fmt"
	"log"
	"net/http"
	"net/smtp"
	"os"
	"strconv"

	"github.com/jhillyerd/enmime"
	"github.com/wohnheim/stueble/database"
	"github.com/wohnheim/stueble/endpoints"
	"github.com/wohnheim/stueble/sessions"
	"github.com/wohnheim/stueble/templates"
)

// Constants & Global variables

const envPrefix = "WOHNHEIMAPP_"

// Session Time-To-Live in days
const envSessionTTL = envPrefix + "SESSION_TTL"

// Verification Code Time-To-Live in minutes
const envVerificationCodeTTL = envPrefix + "VERIFICATION_CODE_TTL"

const envHost = envPrefix + "HOST"
const envHTTPPort = envPrefix + "HTTP_PORT"
const envWebSocketPort = envPrefix + "WEBSOCKET_PORT"
const envDatabaseUrl = envPrefix + "DATABASE_URL"

const envRedisAddress = envPrefix + "REDIS_ADDR"
const envRedisUsername = envPrefix + "REDIS_USERNAME"
const envRedisPassword = envPrefix + "REDIS_PASSWORD"
const envRedisDatabase = envPrefix + "REDIS_DB"

const envSMTPHost = envPrefix + "SMTP_HOST"
const envSMTPPort = envPrefix + "SMTP_PORT"
const envSMTPFrom = envPrefix + "SMTP_FROM"
const envSMTPUsername = envPrefix + "SMTP_USERNAME"
const envSMTPPassword = envPrefix + "SMTP_PASSWORD"

// Function declarations

func main() {
	/* App specific configuration */

	sessionTTL, err := strconv.Atoi(os.Getenv(envSessionTTL))
	if err != nil {
		log.Fatalf("Missing %s environment variable\n", envSessionTTL)
	}

	verificationCodeTTL, err := strconv.Atoi(os.Getenv(envVerificationCodeTTL))
	if err != nil {
		log.Fatalf("Missing %s environment variable\n", envVerificationCodeTTL)
	}

	/* HTTP */
	httpPort, err := strconv.Atoi(os.Getenv(envHTTPPort))
	if err != nil {
		log.Fatalf("Missing %s environment variable\n", envHTTPPort)
	}

	host := os.Getenv(envHost)
	if len(host) == 0 {
		host = "127.0.0.1"
	}

	/* PostgreSQL */
	databaseUrl := os.Getenv(envDatabaseUrl)
	if len(databaseUrl) == 0 {
		log.Fatalf("Missing %s environment variable\n", envDatabaseUrl)
	}

	/* Redis */
	/* redisAddress := os.Getenv(envRedisAddress)
	if len(redisAddress) == 0 {
		log.Fatalf("Missing %s environment variable\n", envRedisAddress)
	}

	redisDatabase, err := strconv.Atoi(os.Getenv(envRedisDatabase))
	if err != nil {
		log.Fatalf("Missing %s environment variable\n", envRedisDatabase)
	}

	redisUsername := os.Getenv(envRedisUsername)
	redisPassword := os.Getenv(envRedisPassword) */

	/* SMTP */
	smtpHost := os.Getenv(envSMTPHost)
	if len(smtpHost) == 0 {
		log.Fatalf("Missing %s environment variable\n", envSMTPHost)
	}

	smtpPort, err := strconv.Atoi(os.Getenv(envSMTPPort))
	if err != nil {
		log.Fatalf("Missing %s environment variable\n", envSMTPPort)
	}

	smtpFrom := os.Getenv(envSMTPFrom)
	if len(smtpFrom) == 0 {
		log.Fatalf("Missing %s environment variable\n", envSMTPFrom)
	}

	smtpUsername := os.Getenv(envSMTPUsername)
	if len(smtpUsername) == 0 {
		log.Fatalf("Missing %s environment variable\n", envSMTPUsername)
	}

	smtpPassword := os.Getenv(envSMTPPassword)
	if len(smtpPassword) == 0 {
		log.Fatalf("Missing %s environment variable\n", envSMTPPassword)
	}

	/* Establish connections */
	databasePool, err := database.CreateDatabasePool(databaseUrl, verificationCodeTTL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v\n", err)
	}

	/* redisClient, err := cache.CreateRedisClient(redisAddress, redisUsername, redisPassword, redisDatabase)
	if err != nil {
		log.Fatalf("Failed to connect to redis: %v\n", err)
	} */

	templates, err := templates.ParseTemplates()
	if err != nil {
		log.Fatalf("Failed to parse templates: %v\n", err)
	}

	endpoints.InitializeSharedData(&endpoints.SharedData{
		DB: databasePool,
		// Redis:     redisClient,
		Templates: templates,
		SMTPSender: enmime.NewSMTP(
			fmt.Sprintf("%s:%d", smtpHost, smtpPort),
			smtp.PlainAuth("", smtpUsername, smtpPassword, smtpHost)),
		SMTPBase: enmime.Builder().From("Stüble-Team", smtpFrom),
		Sessions: &sessions.Sessions{
			TTL: sessionTTL,
		},
	})
	endpoints.RegisterAuthEndpoints()

	listenAddr := fmt.Sprintf("%s:%d", host, httpPort)

	log.Printf("Listening on %s", listenAddr)
	log.Fatalln(http.ListenAndServe(listenAddr, nil))
}
