# MarketPulse-X - Google Cloud GKE Deployment Guide

## 🚀 Complete Deployment Guide for Google Kubernetes Engine

### Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Google Cloud SDK** installed (`gcloud` CLI)
3. **Docker** installed locally
4. **kubectl** installed
5. **API Keys** ready:
   - Gemini API Key
   - News API Keys (NewsAPI, Finnhub, GNews, etc.)

### 📋 Step-by-Step Deployment

#### 1. Set Up Google Cloud Project

```bash
# Install gcloud CLI (if not installed)
# Visit: https://cloud.google.com/sdk/docs/install

# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create marketpulse-prod --name="MarketPulse Production"

# Set the project
gcloud config set project marketpulse-prod

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable compute.googleapis.com
```

#### 2. Configure API Keys

Edit `k8s/deployment.yaml` and update the `api-keys` Secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
  namespace: marketpulse
type: Opaque
stringData:
  GEMINI_API_KEY: "AIzaSy..."           # Your actual Gemini key
  GEMINI_API_KEYS: "key1,key2,key3"     # Multiple keys (comma-separated)
  NEWSAPI_KEY: "your_newsapi_key"
  FINNHUB_API_KEY: "your_finnhub_key"
  # ... other keys
```

#### 3. Build and Push Docker Images

```bash
# Make scripts executable
chmod +x scripts/build-and-push.sh
chmod +x scripts/deploy-gke.sh

# Update PROJECT_ID in the script
# Edit scripts/build-and-push.sh and replace YOUR_GCP_PROJECT_ID

# Build and push images
./scripts/build-and-push.sh
```

This will:
- Build backend Docker image
- Build frontend Docker image
- Push both to Google Container Registry (GCR)

#### 4. Deploy to GKE

```bash
# Update PROJECT_ID in deploy script
# Edit scripts/deploy-gke.sh and replace YOUR_GCP_PROJECT_ID

# Run deployment
./scripts/deploy-gke.sh
```

This will:
- Create a GKE cluster (3 nodes, e2-medium)
- Apply Kubernetes manifests
- Deploy backend and frontend
- Set up LoadBalancer
- Configure autoscaling

#### 5. Verify Deployment

```bash
# Check namespace
kubectl get namespaces

# Check pods
kubectl get pods -n marketpulse

# Check services
kubectl get svc -n marketpulse

# Get application URL
kubectl get svc frontend-service -n marketpulse

# Check logs
kubectl logs -f deployment/backend -n marketpulse
kubectl logs -f deployment/frontend -n marketpulse
```

### 🔧 Configuration Details

#### Kubernetes Resources Created:

1. **Namespace**: `marketpulse`
2. **Backend Deployment**: 
   - 2 replicas (auto-scales 2-10)
   - Persistent Volume for SQLite database
   - Health checks enabled
3. **Frontend Deployment**:
   - 2 replicas
   - Nginx serving React app
4. **Services**:
   - `backend-service` (ClusterIP)
   - `frontend-service` (LoadBalancer)
5. **HorizontalPodAutoscaler**: Auto-scale based on CPU/Memory

#### Resource Allocation:

**Backend:**
- Requests: 512Mi RAM, 0.25 CPU
- Limits: 1Gi RAM, 0.5 CPU

**Frontend:**
- Requests: 128Mi RAM, 0.1 CPU
- Limits: 256Mi RAM, 0.2 CPU

### 💰 Cost Estimation

**Monthly costs (approximate):**
- GKE Cluster Management: ~$74/month
- 3 × e2-medium nodes: ~$75/month
- LoadBalancer: ~$18/month
- Persistent Disk (10GB): ~$2/month
- **Total: ~$170/month**

### 🛠️ Useful Commands

```bash
# Scale backend manually
kubectl scale deployment backend -n marketpulse --replicas=5

# Update deployment (after code changes)
kubectl rollout restart deployment/backend -n marketpulse
kubectl rollout restart deployment/frontend -n marketpulse

# View resource usage
kubectl top pods -n marketpulse
kubectl top nodes

# Access pod shell
kubectl exec -it deployment/backend -n marketpulse -- /bin/bash

# Port forward for local testing
kubectl port-forward svc/backend-service 8000:8000 -n marketpulse

# Delete entire deployment
kubectl delete namespace marketpulse

# Delete GKE cluster
gcloud container clusters delete marketpulse-cluster --zone=us-central1-a
```

### 🔒 Production Best Practices

1. **Secrets Management**:
   - Use Google Secret Manager instead of Kubernetes Secrets
   - Never commit secrets to Git

2. **Database**:
   - Consider Cloud SQL instead of SQLite for production
   - Set up regular backups

3. **Monitoring**:
   - Enable GKE monitoring and logging
   - Set up alerting for downtime

4. **Domain & SSL**:
   - Configure custom domain
   - Use Google-managed SSL certificates

5. **CI/CD**:
   - Set up Cloud Build for automated deployments
   - Use GitHub Actions for continuous deployment

### 🌐 Custom Domain Setup (Optional)

```bash
# Reserve static IP
gcloud compute addresses create marketpulse-ip --global

# Get the IP
gcloud compute addresses describe marketpulse-ip --global

# Update DNS A record to point to this IP
# Then update k8s/deployment.yaml to use Ingress instead of LoadBalancer
```

### 📊 Monitoring & Logs

```bash
# View GKE dashboard
gcloud console

# Stream logs
kubectl logs -f deployment/backend -n marketpulse  --tail=100

# View events
kubectl get events -n marketpulse --sort-by='.lastTimestamp'
```

### 🚨 Troubleshooting

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n marketpulse
kubectl logs <pod-name> -n marketpulse
```

**Image pull errors:**
```bash
# Verify GCR authentication
gcloud auth configure-docker
docker pull gcr.io/YOUR_PROJECT_ID/marketpulse-backend:latest
```

**Database persistence issues:**
```bash
# Check PVC
kubectl get pvc -n marketpulse
kubectl describe pvc backend-data-pvc -n marketpulse
```

### 📞 Support

For deployment issues:
1. Check GKE logs in Google Cloud Console
2. Verify API keys are correct
3. Ensure billing is enabled on GCP project
4. Check resource quotas

---

**You're all set!** 🎉 Your MarketPulse-X application is now running on Google Cloud with Kubernetes!
