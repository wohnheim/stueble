package main

import (
	"fmt"
	"log"
	"net/http"
	"net/smtp"
	"os"
	"strconv"

	"github.com/jhillyerd/enmime"
	"github.com/wohnheim/backend/database"
	"github.com/wohnheim/backend/endpoints"
	"github.com/wohnheim/backend/sessions"
	"github.com/wohnheim/backend/templates"
)

// Constants & Global variables

const envPrefix = "WOHNHEIMAPP_"

// Session Time-To-Live in days
const envSessionTTL = envPrefix + "SESSION_TTL"

// Verification Code Time-To-Live in minutes
const envVerificationCodeTTL = envPrefix + "VERIFICATION_CODE_TTL"

// Frontend URL used in email links
const envFrontendUrl = envPrefix + "FRONTEND_URL"

const envHost = envPrefix + "HOST"
const envHTTPPort = envPrefix + "HTTP_PORT"
const envWebSocketPort = envPrefix + "WEBSOCKET_PORT"
const envDatabaseUrl = envPrefix + "DATABASE_URL"

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

	frontendUrl := os.Getenv(envFrontendUrl)
	if len(frontendUrl) == 0 {
		log.Fatalf("Missing %s environment variable\n", envFrontendUrl)
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

	templates, err := templates.ParseTemplates()
	if err != nil {
		log.Fatalf("Failed to parse templates: %v\n", err)
	}

	endpoints.InitializeSharedData(&endpoints.SharedData{
		DB: databasePool,
		SMTPSender: enmime.NewSMTP(
			fmt.Sprintf("%s:%d", smtpHost, smtpPort),
			smtp.PlainAuth("", smtpUsername, smtpPassword, smtpHost)),
		SMTPBase:  enmime.Builder().From("Stüble-Team", smtpFrom),
		Templates: templates,
		Sessions: &sessions.Sessions{
			TTL: sessionTTL,
		},
		FrontendUrl: frontendUrl,
	})
	endpoints.RegisterAuthEndpoints()

	listenAddr := fmt.Sprintf("%s:%d", host, httpPort)

	log.Printf("Listening on %s", listenAddr)
	log.Fatalln(http.ListenAndServe(listenAddr, nil))
}
