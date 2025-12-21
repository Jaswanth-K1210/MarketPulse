#!/bin/bash
# Deploy MarketPulse-X to Google Kubernetes Engine (GKE)

set -e

# Configuration
PROJECT_ID="YOUR_GCP_PROJECT_ID"
CLUSTER_NAME="marketpulse-cluster"
REGION="us-central1"
ZONE="us-central1-a"

echo "🚀 MarketPulse-X - GKE Deployment Script"
echo "========================================="
echo "Project: ${PROJECT_ID}"
echo "Cluster: ${CLUSTER_NAME}"
echo "Region: ${REGION}"
echo ""

# Set project
echo "📝 Step 1: Setting GCP Project..."
gcloud config set project ${PROJECT_ID}

# Create GKE cluster (if it doesn't exist)
echo "🏗️  Step 2: Creating/Verifying GKE Cluster..."
if ! gcloud container clusters describe ${CLUSTER_NAME} --zone=${ZONE} &>/dev/null; then
    echo "Creating new GKE cluster..."
    gcloud container clusters create ${CLUSTER_NAME} \
        --zone=${ZONE} \
        --num-nodes=3 \
        --machine-type=e2-medium \
        --disk-size=20GB \
        --enable-autoscaling \
        --min-nodes=2 \
        --max-nodes=10 \
        --enable-autorepair \
        --enable-autoupgrade \
        --addons=HorizontalPodAutoscaling,HttpLoadBalancing
    echo "✅ Cluster created successfully"
else
    echo "✅ Cluster already exists"
fi

# Get credentials
echo "🔑 Step 3: Getting cluster credentials..."
gcloud container clusters get-credentials ${CLUSTER_NAME} --zone=${ZONE}

# Update API keys in the secret file
echo "⚙️  Step 4: Configuring Secrets..."
echo ""
echo "⚠️  IMPORTANT: Update k8s/deployment.yaml with your API keys before deploying!"
echo "   Edit the 'api-keys' Secret section with your actual API keys."
echo ""
read -p "Have you updated the API keys? (yes/no): " -n 3 -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]
then
    echo "❌ Please update API keys in k8s/deployment.yaml first"
    exit 1
fi

# Update image names in deployment.yaml
echo "🔄 Step 5: Updating image references..."
sed -i '' "s/YOUR_PROJECT_ID/${PROJECT_ID}/g" k8s/deployment.yaml

# Apply Kubernetes manifests
echo "📦 Step 6: Deploying to Kubernetes..."
kubectl apply -f k8s/deployment.yaml
echo "✅ Kubernetes resources deployed"

# Wait for deployments
echo "⏳ Step 7: Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/backend -n marketpulse
kubectl wait --for=condition=available --timeout=300s deployment/frontend -n marketpulse
echo "✅ All deployments are ready"

# Get external IP
echo "🌐 Step 8: Getting application URL..."
echo "Waiting for LoadBalancer IP..."
sleep 10
EXTERNAL_IP=$(kubectl get svc frontend-service -n marketpulse -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo ""
echo "✅ Deployment Complete!"
echo "========================"
echo "📊 Application URL: http://${EXTERNAL_IP}"
echo "📦 Backend URL: http://backend-service.marketpulse.svc.cluster.local:8000"
echo ""
echo "📋 Useful Commands:"
echo "  View pods: kubectl get pods -n marketpulse"
echo "  View logs: kubectl logs -f deployment/backend -n marketpulse"
echo "  View services: kubectl get svc -n marketpulse"
echo "  Delete deployment: kubectl delete namespace marketpulse"
