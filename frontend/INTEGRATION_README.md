# MarketPulse Frontend - Backend Integration

## Overview
This frontend is now integrated with the MarketPulse backend API. It fetches real-time data from your FastAPI backend and displays live alerts via WebSocket.

## Backend Integration Features

### ✅ Implemented
- **Real-time Data Loading**: Fetches alerts, portfolio, and stats from backend
- **WebSocket Connection**: Live updates for new alerts
- **API Service Layer**: Clean separation of concerns with `services/api.js`
- **Data Transformation**: Converts backend models to frontend format
- **Error Handling**: Graceful fallback to mock data if backend unavailable
- **Loading States**: Shows loading indicators while fetching data
- **Manual Triggers**: Buttons to fetch news and run pipeline manually

### 🔌 API Endpoints Used
- `GET /api/alerts` - Fetch all alerts
- `GET /api/portfolio` - Fetch portfolio holdings
- `GET /api/stats` - Fetch system statistics
- `POST /api/fetch-news` - Trigger manual news fetch
- `POST /api/run-pipeline` - Trigger manual pipeline run
- `WS /ws` - WebSocket for real-time alerts

## Setup Instructions

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment
The `.env` file is already configured with default backend URLs:
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

### 3. Start Backend (Required)
Make sure your backend is running first:
```bash
cd ..
python run.py
# Backend should start on http://localhost:8000
```

### 4. Start Frontend
```bash
npm run dev
# Frontend starts on http://localhost:5173
```

## Architecture

### Directory Structure
```
frontend/
├── src/
│   ├── services/
│   │   └── api.js              # Backend API integration
│   ├── hooks/
│   │   └── useWebSocket.js     # WebSocket connection hook
│   ├── utils/
│   │   ├── dataTransform.js    # Backend to frontend data transformation
│   │   ├── mockData.js         # Fallback mock data
│   │   └── triggerEvents.js    # Demo trigger events
│   ├── components/
│   │   ├── AlertCard.jsx       # Alert display
│   │   ├── PortfolioCard.jsx   # Portfolio holding display
│   │   └── ...
│   └── pages/
│       └── Dashboard.jsx       # Main dashboard (now with backend integration)
```

### Data Flow
```
Backend API → services/api.js → dataTransform.js → Dashboard.jsx → Components
                                      ↓
WebSocket → useWebSocket.js → Dashboard.jsx → Real-time alerts
```

## Key Changes Made

### 1. `services/api.js` (NEW)
- Centralized API calls to backend
- Error handling and retry logic
- Exports functions for all backend endpoints

### 2. `hooks/useWebSocket.js` (NEW)
- Custom React hook for WebSocket connection
- Auto-reconnection with exponential backoff
- Real-time alert streaming

### 3. `utils/dataTransform.js` (NEW)
- Transforms backend data models to frontend format
- Ensures compatibility between API responses and UI components
- Handles missing/null data gracefully

### 4. `pages/Dashboard.jsx` (UPDATED)
- Added `useEffect` to load data on mount
- Integrated WebSocket for live updates
- Added loading states and error handling
- Connected "Fetch News" and "Run Pipeline" buttons to backend
- Graceful fallback to mock data if backend unavailable

### 5. `vite.config.js` (UPDATED)
- Added proxy configuration for `/api` and `/ws` routes
- Ensures proper CORS handling

## Usage

### Live Connection Status
The dashboard header shows connection status:
- 🟢 **Live**: Connected to backend and receiving updates
- 🔴 **Offline**: Using demo data (backend not available)

### Manual Actions
- **⚡ Zap Icon** (Header): Fetch latest news from sources
- **Run Pipeline** (Right sidebar): Manually trigger pipeline processing

### Real-time Updates
When backend generates new alerts:
1. Alert sent via WebSocket
2. Frontend receives and transforms data
3. New alert appears at top of list
4. No page refresh needed

## Backend Data Models

### Alert Format (Backend)
```json
{
  "id": "alert_123",
  "title": "Supply chain disruption",
  "affected_companies": ["Apple Inc."],
  "affected_tickers": ["AAPL"],
  "severity": "critical",
  "portfolio_impact_percent": -2.4,
  "event_summary": "Description...",
  "created_at": "2025-12-13T10:30:00Z",
  "confidence": 0.92,
  "recommendation": "HOLD",
  "cascade_chain": [...],
  "source_urls": [...]
}
```

### Portfolio Format (Backend)
```json
{
  "user_name": "Jaswanth",
  "total_value": 150000,
  "holdings": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "quantity": 150,
      "purchase_price": 145.50,
      "current_price": 198.75
    }
  ]
}
```

## Troubleshooting

### Backend Not Connecting
- Check if backend is running: `curl http://localhost:8000/api/health`
- Verify VITE_API_URL in `.env` matches backend URL
- Check browser console for CORS errors

### WebSocket Not Connecting
- Ensure backend WebSocket endpoint is active
- Check VITE_WS_URL in `.env`
- Look for WebSocket errors in browser console

### Mock Data Showing Instead of Real Data
- This is expected behavior if backend is offline
- Check connection status indicator in dashboard header
- Start backend to see real data

## Development

### Testing with Backend
1. Start backend: `python run.py`
2. Wait for first news fetch cycle (5 minutes)
3. Start frontend: `npm run dev`
4. Watch real-time alerts appear

### Testing without Backend
- Frontend automatically falls back to mock data
- All UI features work with demo data
- Connection indicator shows offline status

## Next Steps

### Optional Enhancements
- [ ] Add authentication/login
- [ ] Implement search functionality
- [ ] Add filters for alerts (severity, company, date)
- [ ] Create detailed alert view page
- [ ] Add historical data charts
- [ ] Implement multi-agent Q&A integration (Phase 2)

## Notes
- **No backend code was modified** - All changes are frontend only
- **Backward compatible** - Works with mock data if backend unavailable
- **Production ready** - Includes error handling and loading states
