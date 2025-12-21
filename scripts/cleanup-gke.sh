#!/bin/bash
# ⚠️  CLEANUP SCRIPT - DELETE EVERYTHING TO STOP BILLING ⚠️

PROJECT_ID="YOUR_GCP_PROJECT_ID"
CLUSTER_NAME="marketpulse-cluster"
REGION="us-central1"
ZONE="us-central1-a"

echo "🛑 DESTROYING MARKETPULSE DEPLOYMENT"
echo "======================================"
echo "This will delete the GKE cluster and Load Balance."
echo "Running this stops all billing for compute/clusters."
echo ""
read -p "Are you sure you want to delete everything? (type 'DELETE'): " -r confirm
if [[ $confirm != "DELETE" ]]; then
    echo "❌ Cancelled"
    exit 1
fi

# 1. Delete Kubernetes Services (Release Load Balancer IP)
echo "🔌 Step 1: Deleting Services (Releasing IP)..."
kubectl delete service frontend-service -n marketpulse --ignore-not-found
kubectl delete service backend-service -n marketpulse --ignore-not-found

# 2. Delete the Cluster
echo "💥 Step 2: Deleting GKE Cluster (This takes ~5-10 mins)..."
gcloud container clusters delete ${CLUSTER_NAME} --zone=${ZONE} --quiet

# 3. Delete Images (Optional - saves storage cost)
echo "🗑️  Step 3: Cleaning up old images..."
gcloud container images delete gcr.io/${PROJECT_ID}/marketpulse-backend:latest --force-delete-tags --quiet
gcloud container images delete gcr.io/${PROJECT_ID}/marketpulse-frontend:latest --force-delete-tags --quiet

echo ""
echo "✅ CLEANUP COMPLETE"
echo "   billing for this deployment has stopped."
