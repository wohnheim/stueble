package templates

import (
	"embed"
	"html/template"
)

type ConfirmationTemplateData struct {
	FirstName         string
	LastName          string
	ContentId         string
	FrontendUrl       string
	VerificationToken string
}

type OverwrittenUserTemplateData struct {
	FirstName string
	LastName  string
	ContentId string
}

//go:embed assets/*
var AssetFiles embed.FS

func ParseTemplates() (*template.Template, error) {
	return template.New("").ParseFS(AssetFiles, "assets/*.html")
}
