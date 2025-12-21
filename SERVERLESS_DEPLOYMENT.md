# MarketPulse-X - Serverless Deployment Guide (Auto Scales to Zero)

## 🎯 Recommended Deployment Strategy

**Backend**: Google Cloud Run (serverless - only runs when active)
**Frontend**: Firebase Hosting (free, global CDN)

**Cost**: ~$2-5/month for actual usage (vs $170/month for always-on GKE)

---

## 📊 Cost Comparison

| Solution | Monthly Cost | Notes |
|----------|--------------|-------|
| **Cloud Run + Firebase** | **$2-5** | ✅ Recommended - Scales to 0 |
| GKE (Kubernetes) | $170 | ❌ Always running |
| AWS Lambda + S3 | $3-8 | Alternative option |
| Vercel + Railway | $5-10 | Good alternative |

---

## 🚀 Deployment Steps

### Part 1: Deploy Backend to Cloud Run (Serverless)

Cloud Run automatically:
- ✅ **Stops when idle** = $0 cost
- ✅ **Starts in <1 second** when visitor arrives
- ✅ **Auto-scales** 0 to 10 instances based on traffic

```bash
# 1. Install Google Cloud CLI
# Visit: https://cloud.google.com/sdk/docs/install

# 2. Login
gcloud auth login

# 3. Create project (or use existing)
gcloud projects create marketpulse-prod
gcloud config set project marketpulse-prod

# 4. Enable billing (required)
# Visit: https://console.cloud.google.com/billing

# 5. Enable Cloud Run API
gcloud services enable run.googleapis.com

# 6. Update API keys in .env
# Edit .env file with your production keys

# 7. Deploy backend
chmod +x scripts/deploy-backend-cloudrun.sh
./scripts/deploy-backend-cloudrun.sh

# Copy the backend URL (e.g., https://marketpulse-backend-xxx.run.app)
```

**Backend is now deployed!** It will:
- Sleep when no one is using it (0 cost)
- Wake up instantly when traffic arrives
- Auto-scale based on load

---

### Part 2: Deploy Frontend to Firebase Hosting (Free)

Firebase Hosting provides:
- ✅ **100% FREE** (unlimited bandwidth)
- ✅ **Global CDN** (fast worldwide)
- ✅ **Free SSL** certificate
- ✅ **Custom domain** support

```bash
# 1. Install Firebase CLI
npm install -g firebase-tools

# 2. Login to Firebase
firebase login

# 3. Initialize Firebase project
cd frontend
firebase init hosting

# When prompted:
# - Create new project or use existing
# - Public directory: dist
# - Single-page app: Yes
# - Automatic builds: No

# 4. Update API endpoint
# Edit frontend/.env.production:
echo "VITE_API_URL=https://YOUR-BACKEND-URL.run.app" > .env.production

# 5. Deploy frontend
chmod +x ../scripts/deploy-frontend-firebase.sh
../scripts/deploy-frontend-firebase.sh

# Your app is now live at: https://YOUR-PROJECT.web.app
```

---

## 🔒 Configure API Keys Securely

### For Cloud Run:

```bash
# Set secrets via command line (more secure than .env)
gcloud run services update marketpulse-backend \
    --region us-central1 \
    --set-env-vars GEMINI_API_KEY=YOUR_KEY \
    --set-env-vars NEWSAPI_KEY=YOUR_KEY

# Or use Google Secret Manager (best practice)
gcloud secrets create gemini-api-key --data-file=- < <(echo "YOUR_KEY")
```

---

## 💰 Cost Breakdown (Cloud Run + Firebase)

### Backend (Cloud Run):
- **Free tier**: 2 million requests/month
- **After free tier**: $0.00002400 per request
- **Example**:
  - 0 visitors = **$0**
  - 1,000 requests/month = **$1-2**
  - 10,000 requests/month = **$3-5**
  - 100,000 requests/month = **$15-20**

### Frontend (Firebase):
- **Hosting**: FREE (10 GB storage, 360 MB/day transfer)
- **Custom domain**: FREE
- **SSL**: FREE

### Total Monthly Cost:
- **Light usage** (few visitors): **$0-2**
- **Medium usage** (100-200 daily visitors): **$3-5**
- **Heavy usage** (1000+ daily visitors): **$15-25**

---

## 🎯 Alternative Deployment Options

### Option 2: Vercel (Frontend) + Railway (Backend)

**Frontend**: Vercel (free)
**Backend**: Railway (sleeps when idle)

```bash
# Deploy to Vercel
cd frontend
npm install -g vercel
vercel --prod

# Deploy to Railway
# Visit: https://railway.app
# Connect GitHub repo → Auto-deploy
```

**Cost**: $5/month (Railway starter)

### Option 3: AWS Lambda + S3

**Frontend**: S3 + CloudFront (cheap)
**Backend**: AWS Lambda (serverless)

```bash
# Use AWS Amplify for easy setup
npm install -g @aws-amplify/cli
amplify init
amplify add hosting
amplify publish
```

**Cost**: ~$3-8/month

---

## 🔧 Post-Deployment Configuration

### 1. Update Frontend Environment Variable

After deploying backend, update frontend:

```bash
# frontend/.env.production
VITE_API_URL=https://marketpulse-backend-xxx.run.app
```

Then redeploy frontend.

### 2. Configure CORS (if needed)

In `app/main.py`, update origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-url.web.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Set up Custom Domain (Optional)

**Firebase Hosting:**
```bash
firebase hosting:channel:deploy production
# Then map custom domain in Firebase Console
```

**Cloud Run:**
```bash
gcloud run domain-mappings create \
    --service marketpulse-backend \
    --domain api.yourdomain.com \
    --region us-central1
```

---

## 📊 Monitoring & Logs

### View Cloud Run Logs:
```bash
gcloud run services logs read marketpulse-backend \
    --region us-central1 \
    --limit 100
```

### View Firebase Hosting:
```bash
firebase hosting:channel:list
```

### Monitor Costs:
- Cloud Run: https://console.cloud.google.com/run
- Firebase: https://console.firebase.google.com

---

## 🚀 Quick Deploy Commands

```bash
# Deploy everything (after setup)
./scripts/deploy-backend-cloudrun.sh
./scripts/deploy-frontend-firebase.sh
```

---

## ✅ Benefits of This Setup

1. **💰 Cost Effective**: Only pay for actual usage
2. **⚡ Auto-Scaling**: Handles traffic spikes automatically  
3. **🛡️ Secure**: Managed by Google/Firebase
4. **🌍 Global**: CDN for fast access worldwide
5. **🔄 Zero Downtime**: Rolling deployments
6. **📊 Monitoring**: Built-in logs and metrics
7. **🔒 SSL**: Automatic HTTPS

---

## 🆘 Troubleshooting

**Backend not waking up:**
- Check Cloud Run logs for errors
- Verify billing is enabled

**Frontend can't reach backend:**
- Update VITE_API_URL in .env.production
- Check CORS configuration

**High costs:**
- Check Cloud Run instance count
- Reduce max-instances if needed

---

**You're all set!** 🎉 Your MarketPulse app will now:
- ✅ Scale to zero when idle (save money)
- ✅ Wake up instantly when visitors arrive  
- ✅ Handle traffic automatically
- ✅ Cost only $2-5/month for normal use
