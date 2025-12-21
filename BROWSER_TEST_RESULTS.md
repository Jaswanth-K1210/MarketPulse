# MarketPulse-X - Critical Issues Found by Browser Testing

## 🔴 **CRITICAL ISSUES TO FIX:**

### **1. News Feed - Raw HTML in Descriptions**
**Problem:** Articles showing escaped HTML tags instead of plain text
**Example:** `<a href="..." target="_blank">...</a>` visible in description
**Fix Needed:** Strip HTML tags from article content before displaying
**Location:** Backend - news_aggregator.py or Frontend - NewsCard.jsx

### **2. Portfolio - $0 Stock Prices**
**Problem:** AAPL showing $0.00 instead of actual price ($273.67)
**Result:** Performance showing +NaN%
**Fix Needed:** Ensure stock prices are properly passed from backend to frontend
**Location:** Frontend - Dashboard.jsx portfolio rendering

### **3. Watchlist - 405 Method Not Allowed**
**Problem:** POST /api/watchlist returns 405 error
**Result:** Cannot add tickers to watchlist
**Fix Needed:** Implement POST handler for /api/watchlist endpoint
**Location:** Backend - app/api/routes.py

### **4. JavaScript Error in Login**
**Problem:** `ReferenceError: apiUrl is not defined` at Login.jsx:88
**Fix Needed:** Define apiUrl or import from config
**Location:** Frontend - Login.jsx line 88

---

## ✅ **WHAT'S WORKING:**

1. **News Feed Links** - Articles open correctly in new tabs
2. **Backend API** - Fetching 45+ live articles from multiple sources
3. **Stock Price API** - Backend returning correct prices ($273.67 for AAPL)
4. **WebSocket** - Connecting successfully (after retry)
5. **Date Filtering** - Last 7 days filter working
6. **Portfolio Companies** - Affected companies badges showing correctly

---

## 🔧 **FIX PRIORITY:**

1. **HIGH**: Strip HTML from news descriptions
2. **HIGH**: Fix portfolio price display ($0 → actual prices)
3. **MEDIUM**: Implement POST /api/watchlist
4. **LOW**: Fix apiUrl reference error

---

**Testing Completed:** 2025-12-21 01:18 IST
**Browser Agent:** Antigravity Extension
**Recording:** dashboard_testing_1766260127951.webp
