---
description: Deploy MarketPulse-X to Google Kubernetes Engine (GKE)
---

This guide details the steps to deploy the MarketPulse-X application to Google Cloud GKE using the provided Kubernetes manifests.

## Prerequisites

Ensure you have the following installed:
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- [Kubernetes CLI](https://kubernetes.io/docs/tasks/tools/) (`kubectl`)
- Docker Desktop

## Step 1: Google Cloud Setup

1.  **Login to Google Cloud**:
    ```bash
    gcloud auth login
    ```

2.  **Create or Select a Project**:
    Replace `[YOUR_PROJECT_ID]` with your actual project ID (e.g., `marketpulse-prod`).
    ```bash
    gcloud config set project [YOUR_PROJECT_ID]
    ```

3.  **Enable Required APIs**:
    ```bash
    gcloud services enable container.googleapis.com \
                         artifactregistry.googleapis.com \
                         cloudbuild.googleapis.com
    ```

## Step 2: Build and Push Docker Images

We will use Google Container Registry (GCR) to store your Docker images.

1.  **Configure Docker Authentication**:
    ```bash
    gcloud auth configure-docker
    ```

2.  **Build and Push Backend**:
    Replace `[YOUR_PROJECT_ID]` with your project ID.
    ```bash
    # Build
    docker build -t gcr.io/[YOUR_PROJECT_ID]/marketpulse-backend:latest .
    
    # Push
    docker push gcr.io/[YOUR_PROJECT_ID]/marketpulse-backend:latest
    ```

3.  **Build and Push Frontend**:
    ```bash
    # Build
    docker build -t gcr.io/[YOUR_PROJECT_ID]/marketpulse-frontend:latest frontend
    
    # Push
    docker push gcr.io/[YOUR_PROJECT_ID]/marketpulse-frontend:latest
    ```

## Step 3: Create GKE Cluster

Create a small cluster for this demo.

```bash
gcloud container clusters create marketpulse-cluster \
    --num-nodes=1 \
    --machine-type=e2-standard-4 \
    --zone=us-central1-a
```

Get credentials to access the cluster:
```bash
gcloud container clusters get-credentials marketpulse-cluster --zone us-central1-a
```

## Step 4: Configure Credentials and Manifests

1.  **Edit `k8s/deployment.yaml`**:
    Open `k8s/deployment.yaml` in your editor.

    -   **Replace Image Names**: Find `image: gcr.io/YOUR_PROJECT_ID/...` and replace `YOUR_PROJECT_ID` with your actual Project ID.
    -   **Update Secrets**: Find the `Secret` section named `api-keys`. Replace the placeholder values (`YOUR_GEMINI_API_KEY_HERE`, etc.) with your actual API keys from your `.env` file.

    *Alternative (Secure)*: instead of editing the file, you can create the secret directly:
    ```bash
    # First, create the namespace
    kubectl create namespace marketpulse
    
    # Create secret from env file (if you have one locally)
    # kubectl create secret generic api-keys -n marketpulse --from-env-file=.env
    ```
    *If you verify `k8s/deployment.yaml` matches your keys, you can just apply the file.*

## Step 5: Deploy to Kubernetes

Apply the configuration to your cluster:

```bash
kubectl apply -f k8s/deployment.yaml
```

## Step 6: Verify Deployment

1.  **Check Pods**:
    Wait for all pods to be `Running`.
    ```bash
    kubectl get pods -n marketpulse
    ```

2.  **Get Public IP**:
    Find the external IP address assigned to the `frontend-service`.
    ```bash
    kubectl get services -n marketpulse
    ```
    Look for `frontend-service` and the `EXTERNAL-IP` column.

3.  **Access the App**:
    Open `http://[EXTERNAL-IP]` in your browser.

## Troubleshooting

-   **Pending External IP**: It may take a few minutes for Google Cloud to assign an IP.
-   **Pod Errors**: Use `kubectl logs [POD_NAME] -n marketpulse` to see logs.
-   **Database**: This architecture uses a PersistentVolumeClaim (`backend-data-pvc`) to store the SQLite database. If the pod restarts, data is preserved.
