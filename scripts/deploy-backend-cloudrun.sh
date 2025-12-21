#!/bin/bash
# Deploy MarketPulse-X Backend to Google Cloud Run (Serverless - Auto scales to zero)

set -e

PROJECT_ID="YOUR_GCP_PROJECT_ID"
REGION="us-central1"
SERVICE_NAME="marketpulse-backend"

echo "🚀 Deploying Backend to Cloud Run (Serverless)"
echo "=============================================="
echo "✨ Backend will ONLY run when website is active"
echo "💰 Scales to 0 when idle = NO COST when not in use"
echo ""

# Set project
gcloud config set project ${PROJECT_ID}

# Build and deploy to Cloud Run
echo "📦 Building and deploying..."
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 10 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars ENVIRONMENT=production \
    --set-env-vars GEMINI_MODEL=gemini-2.5-flash

echo ""
echo "✅ Backend Deployed to Cloud Run!"
echo "================================================"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo "📡 Backend URL: ${SERVICE_URL}"
echo ""
echo "💡 Key Features:"
echo "  ✨ Scales to 0 when idle (NO COST)"
echo "  ⚡ Auto-starts in <1 second when traffic arrives"
echo "  💰 Only pay for actual usage (per 100ms of CPU time)"
echo "  🔄 Auto-scales up to 10 instances under load"
echo ""
echo "💵 Estimated Cost:"
echo "  • 0 requests = $0/month"
echo "  • 1000 requests/month = ~$2/month"
echo "  • 10,000 requests/month = ~$5/month"
echo ""
echo "🔧 Next: Update frontend VITE_API_URL to: ${SERVICE_URL}"
