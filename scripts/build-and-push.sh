#!/bin/bash
# Build and Push Docker Images to Google Container Registry

set -e

# Configuration
PROJECT_ID="YOUR_GCP_PROJECT_ID"
REGION="us-central1"
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/marketpulse-backend"
FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/marketpulse-frontend"
VERSION="latest"

echo "🚀 MarketPulse-X - Docker Build & Push Script"
echo "=============================================="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

# Authenticate with GCP
echo "📝 Step 1: Authenticating with Google Cloud..."
gcloud auth configure-docker

# Build Backend
echo "🔨 Step 2: Building Backend Docker Image..."
docker build -t ${BACKEND_IMAGE}:${VERSION} -f Dockerfile .
echo "✅ Backend image built successfully"

# Build Frontend
echo "🔨 Step 3: Building Frontend Docker Image..."
cd frontend
docker build -t ${FRONTEND_IMAGE}:${VERSION} -f Dockerfile .
cd ..
echo "✅ Frontend image built successfully"

# Push Backend
echo "📤 Step 4: Pushing Backend to GCR..."
docker push ${BACKEND_IMAGE}:${VERSION}
echo "✅ Backend pushed successfully"

# Push Frontend
echo "📤 Step 5: Pushing Frontend to GCR..."
docker push ${FRONTEND_IMAGE}:${VERSION}
echo "✅ Frontend pushed successfully"

echo ""
echo "✅ All images built and pushed successfully!"
echo "Backend: ${BACKEND_IMAGE}:${VERSION}"
echo "Frontend: ${FRONTEND_IMAGE}:${VERSION}"
