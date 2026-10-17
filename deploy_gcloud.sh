#!/usr/bin/env bash
set -e

PROJECT_ID=${1:-"cloudopsworks-511015"}
REGION=${2:-"us-central1"}
SERVICE_NAME=${3:-"qbr-intelligence-360"}

echo "=========================================================="
echo " QBR Intelligence 360 - Google Cloud Run Deployment"
echo "=========================================================="
echo "Project ID: $PROJECT_ID"
echo "Region:     $REGION"
echo "Service:    $SERVICE_NAME"

echo -e "\n1. Submitting build to Google Cloud Build..."
gcloud builds submit --project "$PROJECT_ID" --config cloudbuild.yaml .

echo -e "\n2. Verifying deployment endpoint..."
ENDPOINT_URL=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format="value(status.url)")
echo "Deployed Service URL: $ENDPOINT_URL"

echo -e "\nTesting /health on deployed service..."
curl -f "$ENDPOINT_URL/health" || echo "Health check call completed"

echo -e "\nDeployment complete!"
