# MarketPulse - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Start the Backend
```bash
cd /Users/apple/Desktop/Marketpulse/MarketPulse
python run.py
```
✅ Backend will start on **http://localhost:8000**

### Step 2: Start the Frontend
```bash
cd frontend
npm install     # First time only
npm run dev
```
✅ Frontend will start on **http://localhost:5173**

### Step 3: Open in Browser
```
http://localhost:5173
```
✅ You should see the dashboard with live data!

---

## 📱 What You'll See

### Dashboard Features
- **Live Connection Indicator** - Shows if backend is connected
- **Real-time Alerts** - New alerts appear automatically
- **Portfolio Holdings** - Your current positions
- **Market Statistics** - Active alerts, events, impact scores
- **Alert Trend Chart** - 7-day alert activity

### Interactive Elements
- **⚡ Fetch News Button** (Header) - Manually fetch latest news
- **Run Pipeline Button** (Sidebar) - Process articles manually
- **Alert Cards** - Click to expand for details
- **Trigger Buttons** - Test positive/negative scenarios

---

## 🔧 Troubleshooting

### "Offline" indicator showing?
➜ Make sure backend is running: `python run.py`

### No data appearing?
➜ Backend database might be empty. Wait 5 minutes for first news fetch or click "Fetch News"

### Port already in use?
➜ Frontend: Kill process on port 5173
➜ Backend: Kill process on port 8000

---

## 📖 Documentation

- **FRONTEND_INTEGRATION_SUMMARY.md** - Complete integration overview
- **frontend/INTEGRATION_README.md** - Technical documentation
- **README.md** - Project overview

---

## ✨ Integration Highlights

✅ **Real Backend Data** - No more mock data when backend is running  
✅ **Live Updates** - WebSocket pushes new alerts automatically  
✅ **Error Handling** - Graceful fallback if backend is offline  
✅ **Manual Controls** - Fetch news and run pipeline on demand  
✅ **Production Ready** - Includes loading states and error messages  

---

**Happy Monitoring! 🎉**
