---
description: Deploy MarketPulse-X to Vercel (Frontend) and Render (Backend)
---

# 🚀 Deployment Guide: Vercel & Render

This guide outlines the steps to deploy your **MarketPulse-X** application for free using **Render** (for the Python backend) and **Vercel** (for the React/Vite frontend).

---

## Part 1: Deploy Backend to Render

1.  **Sign Up/Log In**: Go to [render.com](https://render.com) and log in.
2.  **Create New Web Service**:
    *   Click the **"New +"** button and select **"Web Service"**.
3.  **Connect Repository**:
    *   Select "Build and deploy from a Git repository".
    *   Connect your GitHub account and select your `MarketPulse` repository.
4.  **Configure Service**:
    *   **Name**: `marketpulse-backend`
    *   **Region**: Choose the one closest to you (e.g., Singapore, Frankfurt).
    *   **Branch**: `JaswanthK-1210` (or your main working branch).
    *   **Root Directory**: `.` (Leave connection default or set to empty).
    *   **Runtime**: **Python 3**.
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `python run.py`
5.  **Environment Variables**:
    *   Scroll down to the "Environment Variables" section.
    *   Add the keys and values from your local `.env` file. **Crucial ones**:
        *   `GEMINI_API_KEY`: (Your Google Gemini Key)
        *   `NEWSAPI_KEY`: (Your NewsAPI Key)
        *   `FINNHUB_API_KEY`: (Your Finnhub Key)
        *   `ENVIRONMENT`: `production`
        *   `HOST`: `0.0.0.0`
        *   `PORT`: `10000` (Render's default port)
6.  **Deploy**:
    *   Click **"Create Web Service"**.
    *   Wait for the build to finish. Once successful, you will see a URL like `https://marketpulse-backend.onrender.com`.  
    *   **Copy this URL**. You will need it for the frontend.

---

## Part 2: Deploy Frontend to Vercel

1.  **Sign Up/Log In**: Go to [vercel.com](https://vercel.com) and log in.
2.  **Add New Project**:
    *   Click **"Add New..."** -> **"Project"**.
3.  **Import Git Repository**:
    *   Select your `MarketPulse` repository and click **"Import"**.
4.  **Configure Project**:
    *   **Project Name**: `marketpulse-frontend` (or similar).
    *   **Framework Preset**: **Vite** (should be auto-detected).
    *   **Root Directory**:
        *   Click "Edit" next to Root Directory.
        *   Select the `frontend` folder.
5.  **Build & Output Settings**:
    *   **Build Command**: `npm run build` (Default is usually correct).
    *   **Output Directory**: `dist` (Default is usually correct).
6.  **Environment Variables**:
    *   Expand the "Environment Variables" section.
    *   Add the following variable:
        *   **Key**: `VITE_API_URL`
        *   **Value**: The **Render Backend URL** you copied earlier (e.g., `https://marketpulse-backend.onrender.com`).  
        *   *Note: Do NOT add a trailing slash `/`.*
7.  **Deploy**:
    *   Click **"Deploy"**.
    *   Vercel will build your frontend. Once complete, you will get a live URL (e.g., `https://marketpulse-frontend.vercel.app`).

---

## Part 3: Final Verification

1.  Open your **Vercel Frontend URL**.
2.  The dashboard should load.
3.  Check the "Live" indicator. If the backend is waking up (Render free tier sleeps after inactivity), it might take 30-60 seconds for the first request to succeed.
4.  Try creating a user or searching for a company to verify the connection.

### Troubleshooting
*   **CORS Errors**: If you see CORS errors in the browser console, you may need to update `app/main.py` in the backend to explicitly allow your Vercel domain in `allow_origins`, although `allow_origins=["*"]` is currently set, which should work for everything.
*   **404 on Refresh**: If refreshing a page gives a 404, Vercel needs a rewrite rule for Single Page Apps (SPA).
    *   Create a file `vercel.json` inside the `frontend/` folder with this content:
        ```json
        {
          "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
        }
        ```
    *   Commit and push this change to trigger a redeploy.
