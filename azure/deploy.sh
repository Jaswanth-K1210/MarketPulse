#!/usr/bin/env bash
# MarketPulse-X — Azure deployment script
# Usage: ./azure/deploy.sh [dev|staging|prod] [resource-group] [subscription-id]
set -euo pipefail

ENV="${1:-prod}"
RG="${2:-marketpulse-rg}"
SUB="${3:-}"
LOCATION="westeurope"

# ── Prerequisites check ────────────────────────────────────────────────────────
command -v az   >/dev/null 2>&1 || { echo "ERROR: Azure CLI not found. Install: https://docs.microsoft.com/cli/azure/install-azure-cli"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker not found."; exit 1; }

echo "▶ MarketPulse-X deployment — env=$ENV rg=$RG"

# ── Login & subscription ───────────────────────────────────────────────────────
az account show >/dev/null 2>&1 || az login

if [ -n "$SUB" ]; then
  az account set --subscription "$SUB"
fi

CURRENT_SUB=$(az account show --query id -o tsv)
echo "  Using subscription: $CURRENT_SUB"

# ── Resource group ─────────────────────────────────────────────────────────────
echo "▶ Ensuring resource group $RG in $LOCATION..."
az group create --name "$RG" --location "$LOCATION" --output none

# ── Container registry (create once) ──────────────────────────────────────────
ACR_NAME="mktpulse${ENV}acr"
echo "▶ Ensuring container registry $ACR_NAME..."
az acr create \
  --resource-group "$RG" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --output none 2>/dev/null || echo "  (ACR already exists)"

ACR_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_PASS=$(az acr credential show --name "$ACR_NAME" --query passwords[0].value -o tsv)
echo "  Registry: $ACR_SERVER"

# ── Build & push images ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "▶ Building Python backend image..."
docker build -t "$ACR_SERVER/marketpulse-backend:latest" -f "$ROOT_DIR/Dockerfile" "$ROOT_DIR"

echo "▶ Building .NET gateway image..."
docker build -t "$ACR_SERVER/marketpulse-gateway:latest" -f "$ROOT_DIR/dotnet-gateway/Dockerfile" "$ROOT_DIR/dotnet-gateway"

echo "▶ Pushing images to ACR..."
echo "$ACR_PASS" | docker login "$ACR_SERVER" -u "$ACR_NAME" --password-stdin
docker push "$ACR_SERVER/marketpulse-backend:latest"
docker push "$ACR_SERVER/marketpulse-gateway:latest"

# ── Bicep deployment ───────────────────────────────────────────────────────────
echo "▶ Deploying Bicep template..."
DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "$RG" \
  --template-file "$SCRIPT_DIR/main.bicep" \
  --parameters "@$SCRIPT_DIR/parameters.json" \
  --parameters env="$ENV" \
               backendImage="$ACR_SERVER/marketpulse-backend:latest" \
               gatewayImage="$ACR_SERVER/marketpulse-gateway:latest" \
  --output json)

GATEWAY_URL=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['gatewayUrl']['value'])")
STORAGE_NAME=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['storageAccountName']['value'])")

echo ""
echo "✅ Deployment complete!"
echo "   Gateway URL:    $GATEWAY_URL"
echo "   Storage:        $STORAGE_NAME"
echo "   App Insights:   mktpulse-${ENV}-ai (in $RG)"
echo ""
echo "   Update your frontend VITE_GATEWAY_URL=$GATEWAY_URL"
