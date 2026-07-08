# MarketPulse-X — Deployment Guide

Deploy the backend on **Render** (free/$7/month) and the frontend on **Vercel** (free).

---

## Prerequisites

- GitHub account with this repo pushed
- [Render account](https://render.com) (free tier works)
- [Vercel account](https://vercel.com) (free tier works)
- [Upstash account](https://upstash.com) — free Redis (10K req/day)

---

## Step 1 — Push to GitHub

```bash
cd MarketPulse
git init            # if not already a git repo
git add .
git commit -m "feat: initial MarketPulse-X production build"
git remote add origin https://github.com/YOUR_USERNAME/marketpulse-x.git
git push -u origin main
```

---

## Step 2 — Create Upstash Redis (free)

1. Go to [console.upstash.com](https://console.upstash.com) → **Create Database**
2. Name it `marketpulse`, region: `us-east-1`, type: **Regional**
3. Copy the **UPSTASH_REDIS_REST_URL** and **UPSTASH_REDIS_REST_TOKEN** from the REST API tab

---

## Step 3 — Deploy Backend on Render

### 3a — Create the web service

1. Go to [render.com/dashboard](https://dashboard.render.com) → **New +** → **Web Service**
2. Connect your GitHub repo (`marketpulse-x`)
3. Set the **Root Directory** to `MarketPulse` (the folder containing `Procfile`)
4. Render auto-detects the `render.yaml` — confirm the settings:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
   - **Plan**: Free (or Starter $7/month for always-on)

### 3b — Add environment variables

In Render → your service → **Environment** tab, add each of these:

| Variable | Value |
|---|---|
| `SECRET_KEY` | any 32-char random string, e.g. `openssl rand -hex 32` |
| `LLM_MODE` | `groq` |
| `GROQ_API_KEY` | your Groq key |
| `OPENROUTER_API_KEY` | your OpenRouter key |
| `GOOGLE_API_KEY` | your Gemini API key |
| `UPSTASH_REDIS_REST_URL` | from Step 2 |
| `UPSTASH_REDIS_REST_TOKEN` | from Step 2 |
| `NEWS_API_KEY` | your NewsAPI key |
| `GNEWS_API_KEY` | your GNews key |
| `MEDIASTACK_API_KEY` | your MediaStack key |
| `FRED_API_KEY` | free from [fred.stlouisfed.org/docs/api](https://fred.stlouisfed.org/docs/api/api_key.html) |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `FRONTEND_URL` | your Vercel URL (add after Step 4, e.g. `https://marketpulse.vercel.app`) |

Optional conflict data (leave blank to use bootstrap seed):

| Variable | Value |
|---|---|
| `ACLED_API_KEY` | free from [acleddata.com](https://acleddata.com/acleddatanerd/) |
| `ACLED_EMAIL` | email you registered with ACLED |

### 3c — Deploy

Click **Save Changes** then **Manual Deploy → Deploy Latest Commit**.

Wait ~3 minutes. Your backend URL will be:
```
https://marketpulse-x.onrender.com
```

Verify it's working:
```bash
curl https://marketpulse-x.onrender.com/health
# → {"status": "healthy", ...}

curl https://marketpulse-x.onrender.com/api/intelligence/market-overview
# → {"regime": "sideways", "vix": ..., ...}
```

> **Note on free tier:** Render free services spin down after 15 min of inactivity and take ~30s to cold-start. Upgrade to Starter ($7/month) for always-on.

---

## Step 4 — Deploy Frontend on Vercel

### 4a — Import project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repo
3. Set **Root Directory** to `MarketPulse/frontend`
4. Vercel auto-detects Vite from `vercel.json`

### 4b — Add environment variable

In Vercel → your project → **Settings** → **Environment Variables**:

| Variable | Value |
|---|---|
| `VITE_API_URL` | your Render backend URL, e.g. `https://marketpulse-x.onrender.com` |

### 4c — Deploy

Click **Deploy**. After ~1 minute your frontend is live at:
```
https://marketpulse-x.vercel.app
```

Go back to Render and set `FRONTEND_URL` to this Vercel URL (for CORS).

---

## Step 5 — Set Up GitHub Actions Pipeline

The pipeline runs every 10 minutes for all users (shared global pipeline).

### 5a — Add GitHub Secrets

In your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret | Value |
|---|---|
| `GROQ_API_KEY` | your Groq key |
| `OPENROUTER_API_KEY` | your OpenRouter key |
| `GOOGLE_API_KEY` | your Gemini key |
| `NEWS_API_KEY` | your NewsAPI key |
| `GNEWS_API_KEY` | your GNews key |
| `MEDIASTACK_API_KEY` | your MediaStack key |
| `FRED_API_KEY` | your FRED key |
| `UPSTASH_REDIS_REST_URL` | from Step 2 |
| `UPSTASH_REDIS_REST_TOKEN` | from Step 2 |
| `RENDER_DEPLOY_HOOK_URL` | from Render → Settings → Deploy Hook (optional) |
| `VERCEL_TOKEN` | from Vercel → Account Settings → Tokens (optional, for auto-deploy) |

### 5b — Enable the workflow

The file `.github/workflows/pipeline.yml` already exists. Push to `main` to activate it.

Verify in GitHub → **Actions** tab → `MarketPulse Pipeline` is running on schedule.

---

## Step 6 — Verify End-to-End

1. Open your Vercel URL in a browser
2. Go to **Intelligence Hub** (Trends page)
3. You should see: Market Regime, VIX, Macro Indicators, Sector ETFs
4. If any panel shows "loading…" → check Render logs for errors
5. Open **Network tab** in browser DevTools → confirm calls to `https://marketpulse-x.onrender.com/api/intelligence/*` return 200

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| CORS error in browser | Set `FRONTEND_URL` in Render env vars to your exact Vercel URL |
| 500 on `/api/intelligence/macro` | `FRED_API_KEY` missing or FRED rate-limited — bootstrap data still serves |
| Frontend shows all dashes `—` | `VITE_API_URL` not set in Vercel, or Render cold-starting |
| LightGBM import error on Render | Add `lightgbm` to `requirements.txt` (it's already there) |
| FinBERT OOM on free Render | FinBERT falls back to keyword classification automatically |
| GitHub Action fails | Check secret names match exactly — they are case-sensitive |

---

## Cost Summary

| Service | Tier | Cost |
|---|---|---|
| Render backend | Free (spins down) / Starter | $0 / $7/month |
| Vercel frontend | Free | $0 |
| Upstash Redis | Free (10K req/day) | $0 |
| Groq LLM | Free (14,400 req/day) | $0 |
| Gemini API | Free (1M tokens/day) | $0 |
| GitHub Actions | Free (2000 min/month) | $0 |
| **Total** | | **$0–$7/month** |

---

## Re-deploying After Changes

```bash
git add .
git commit -m "your change"
git push origin main
# Render auto-deploys on push to main
# Vercel auto-deploys on push to main
```

Both Render and Vercel watch your `main` branch and redeploy automatically.
