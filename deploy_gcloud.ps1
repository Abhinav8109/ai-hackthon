# QBR Intelligence 360 - Google Cloud Run Deployment Script
param (
    [string]$ProjectId = "cloudopsworks-511015",
    [string]$Region = "us-central1",
    [string]$ServiceName = "qbr-intelligence-360"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " QBR Intelligence 360 - Google Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Project ID: $ProjectId"
Write-Host "Region:     $Region"
Write-Host "Service:    $ServiceName"

Write-Host "`n1. Submitting build to Google Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --project $ProjectId --config cloudbuild.yaml .

Write-Host "`n2. Verifying deployment endpoint..." -ForegroundColor Yellow
gcloud run services describe $ServiceName --project $ProjectId --region $Region --format="value(status.url)"

Write-Host "`nDeployment process completed!" -ForegroundColor Green
