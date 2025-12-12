# 🚀 HOW TO USE CLAUDE CODE WITH MARKETPULSE-X PROMPT

## 📋 Step-by-Step Instructions

### **STEP 1: Access Claude Code**

There are 3 ways to use Claude Code:

#### **Option A: Web Interface (Easiest)**
1. Go to https://claude.ai
2. Start a new conversation
3. Click the `💻 Code` button (if available)
4. Claude Code interface opens

#### **Option B: Desktop App**
1. Download Claude desktop app
2. Open it
3. Start a conversation
4. Look for code execution options

#### **Option C: API (For Developers)**
1. Use Anthropic API
2. Pass the prompt via API
3. Claude executes code generation

### **STEP 2: Copy the Complete Prompt**

The prompt file is: `CLAUDE_CODE_COMPLETE_PROMPT.md`

1. Open the file
2. Copy EVERYTHING between the triple backticks (the large code block)
3. Should start with: `🤖 BUILD MARKETPULSE-X...`
4. Should end with: `YOU'RE ALL SET! 🚀`

### **STEP 3: Paste into Claude Code**

1. Open Claude Code interface
2. Paste the entire prompt
3. Press Enter or Send

### **STEP 4: Claude Code Execution**

Claude will understand and:
- Ask clarifying questions about setup
- Start building the backend system
- Create all 18 backend files
- Create all 9 frontend files
- Provide testing instructions

### **STEP 5: Guide Claude Through Build**

When Claude asks, tell it:

**For Backend Build:**
```
"Start with Phase 1: Build app/config.py first, then app/main.py, 
then the models, then services (gemini_client, news_aggregator, 
database, then pipeline), then API routes and websocket.
Follow the build order exactly."
```

**For Multi-Agent Build:**
```
"Now build Phase 2: Start with agents/base_agent.py, then 
agent_registry.py with all tool implementations, then each 
specialized agent (analyst, researcher, calculator, synthesizer), 
then orchestrator.py, then modify api/routes.py to add the 
/agent-question endpoint."
```

**For Frontend Build:**
```
"Now build Phase 3: Start with src/App.jsx setup, then Dashboard.jsx, 
then each component in order (PortfolioSummary, AlertCard, 
KnowledgeGraph, AgentChat enhanced version, new AgentWorkflow, 
new Agents page), then api.js client."
```

---

## 📂 WHAT CLAUDE CODE WILL DELIVER

### **Backend Files Created (18 total)**

**Layer 1-2 (Deterministic Pipeline)**:
```
app/
├── main.py               ✓ FastAPI setup
├── config.py            ✓ Configuration
├── api/
│   ├── routes.py        ✓ REST endpoints
│   └── websocket.py     ✓ WebSocket handler
├── services/
│   ├── gemini_client.py        ✓ Gemini wrapper
│   ├── news_aggregator.py      ✓ News fetching
│   ├── pipeline.py             ✓ 7-stage processing
│   └── database.py             ✓ Data storage
└── models/
    ├── article.py       ✓ Article model
    ├── alert.py         ✓ Alert model
    └── knowledge_graph.py ✓ Graph model
```

**Layer 3 (Multi-Agent System)**:
```
agents/
├── base_agent.py        ✓ Base class (Think-Act-Observe)
├── analyst_agent.py     ✓ Market analysis specialist
├── researcher_agent.py  ✓ Data gathering specialist
├── calculator_agent.py  ✓ Impact calculation specialist
├── synthesizer_agent.py ✓ Orchestrator & combiner
├── orchestrator.py      ✓ Routes queries to agents
└── agent_registry.py    ✓ Tool registry (20+ tools)
```

### **Frontend Files Created (9 total)**

```
src/
├── App.jsx                        ✓ Main app routing
├── pages/
│   ├── Dashboard.jsx              ✓ Main dashboard
│   └── Agents.jsx                 ✓ Agent capabilities (NEW)
├── components/
│   ├── PortfolioSummary.jsx       ✓ Portfolio display
│   ├── AlertCard.jsx              ✓ Alert display
│   ├── KnowledgeGraph.jsx         ✓ Graph visualization
│   ├── AgentChat.jsx              ✓ Enhanced chat (multi-agent)
│   └── AgentWorkflow.jsx          ✓ Workflow visualization (NEW)
└── services/
    └── api.js                     ✓ API client (multi-agent aware)
```

---

## ⚙️ TECH STACK SUMMARY

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend Runtime** | Python 3.10+ | Server runtime |
| **Web Framework** | FastAPI | REST API + async |
| **ASGI Server** | Uvicorn | Production server |
| **AI Model** | Google Gemini | Text generation |
| **Job Scheduling** | APScheduler | Background tasks (5 min) |
| **WebSocket** | python-socketio | Real-time alerts |
| **Data Validation** | Pydantic 2.5+ | Type safety |
| **News APIs** | NewsAPI, NewsData.io | Article fetching |
| **Web Scraping** | BeautifulSoup4 | Additional sources |
| **Database** | JSON or PostgreSQL | Data storage |
| **Frontend Runtime** | Node.js 16+ | JS runtime |
| **Framework** | React 18 | UI library |
| **Language** | TypeScript | Type safety |
| **Build Tool** | Vite | Fast bundling |
| **Styling** | Tailwind CSS | Utility CSS |
| **Components** | Shadcn UI | Pre-built components |
| **State Mgmt** | Zustand | Global state |
| **Routing** | React Router v6 | Page navigation |
| **HTTP Client** | Axios | API requests |
| **WebSocket** | Socket.io-client | Real-time updates |
| **Charting** | Recharts | Data visualization |
| **Graphs** | React Flow | Graph visualization |
| **Icons** | Lucide React | Icon library |

---

## 🔑 API KEYS NEEDED

**Get these BEFORE running Claude Code:**

### 1. Google Gemini API (Required)
- **URL**: https://makersuite.google.com/app/apikey
- **Cost**: Free
- **Limits**: 60 requests/min, 1500/day
- **Time**: 2 minutes to get
- **Instructions**:
  1. Go to link above
  2. Click "Create API Key"
  3. Copy the key
  4. Save for .env file

### 2. NewsAPI (Required)
- **URL**: https://newsapi.org
- **Cost**: Free tier available
- **Limits**: 100 requests/day
- **Time**: 5 minutes to get
- **Instructions**:
  1. Go to link above
  2. Click "Sign Up"
  3. Choose "Free" tier
  4. Verify email
  5. Get API key from dashboard
  6. Save for .env file

### 3. NewsData.io (Required)
- **URL**: https://newsdata.io
- **Cost**: Free tier available
- **Limits**: 200 requests/day
- **Time**: 5 minutes to get
- **Instructions**:
  1. Go to link above
  2. Click "Sign Up"
  3. Choose "Free" tier
  4. Verify email
  5. Get API key from dashboard
  6. Save for .env file

**Total time to get all keys: ~12 minutes**

---

## 📝 SAMPLE .env FILE

Create this file in the backend directory:

```
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
NEWSAPI_KEY=your_newsapi_key_here
NEWSDATA_IO_KEY=your_newsdata_io_key_here

# Environment
ENVIRONMENT=development
DEBUG=True

# Server
PORT=8000
HOST=0.0.0.0

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Logging
LOG_LEVEL=INFO

# Database (optional)
DATABASE_URL=sqlite:///./data.db
```

---

## 🎯 BUILDING PHASES

### **Phase 1: Backend Infrastructure (6-8 hours)**
1. Setup + config
2. Models (Article, Alert, KnowledgeGraph)
3. Services (Gemini client, News aggregator, Database)
4. Pipeline (7-stage processing)
5. API routes + WebSocket
6. **Test**: News monitoring and alert generation

### **Phase 2: Multi-Agent System (4-5 hours)**
1. Base agent class
2. Agent registry with tools
3. 4 specialized agents (Analyst, Researcher, Calculator, Synthesizer)
4. Orchestrator
5. Modify routes for /agent-question
6. **Test**: Multi-agent Q&A

### **Phase 3: Frontend (4-5 hours)**
1. App setup + routing
2. Dashboard page
3. Components (Portfolio, Alert, Graph, Chat)
4. Enhanced AgentChat for multi-agent
5. New AgentWorkflow component
6. New Agents page
7. API client
8. **Test**: UI + API integration

### **Phase 4: Integration & Testing (2-3 hours)**
1. End-to-end testing
2. WebSocket real-time testing
3. Multi-agent testing
4. UI/UX polish
5. Production readiness

---

## 🧪 TESTING AFTER BUILD

### **Test Backend Alone**
```bash
cd backend
python -m pytest
# or manually: python run.py
# Check endpoints in Postman/curl
```

### **Test Frontend Alone**
```bash
cd frontend
npm run dev
# Check components in browser
```

### **Test Integration**
1. Start backend: `python run.py`
2. Start frontend: `npm run dev`
3. Open http://localhost:3000
4. Check dashboard
5. Check alerts via WebSocket
6. Test multi-agent Q&A

### **Test Multi-Agent System**
1. Go to /explore page
2. Ask: "Will semiconductors be hit harder?"
3. Verify response shows:
   - Agent routing
   - Each agent's findings
   - Final synthesized answer
   - Confidence score
   - Evidence list

---

## 📊 EXAMPLE FLOW AFTER BUILD

**User asks:** "Will semiconductors be hit harder than others?"

**Expected Response:**
```
Query: "Will semiconductors be hit harder than others?"

Routing:
- Primary Agent: Analyst
- Supporting Agents: Researcher, Calculator

Agent Responses:
1. Analyst found: Semiconductor sector 3x more volatile
2. Researcher found: TSMC supplies 100% of Apple chips
3. Calculator found: 85% impact vs 35% other sectors

Final Answer:
"Yes, semiconductors will be hit harder (85% impact vs 35%).
 Reason: TSMC is critical supplier. Recovery: 3-4 weeks."

Confidence: 92%
Evidence: [3 facts], [sources]
```

---

## 🚨 COMMON ISSUES & FIXES

| Issue | Fix |
|-------|-----|
| **"API key invalid"** | Check .env file, ensure key is copied correctly |
| **"Port 8000 already in use"** | Kill process: `lsof -ti:8000 \| xargs kill -9` |
| **"Module not found"** | Run `pip install -r requirements.txt` |
| **"WebSocket connection failed"** | Ensure backend is running on port 8000 |
| **"CORS error"** | Check FRONTEND_URL in backend config |
| **"Node modules missing"** | Run `npm install` in frontend directory |
| **"Vite not found"** | Run `npm install` with correct node version |

---

## 📱 AFTER CLAUDE CODE BUILDS EVERYTHING

### **Run the Full System**

**Terminal 1 - Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows
pip install -r requirements.txt
python run.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Open in Browser:**
- Frontend: http://localhost:3000
- Backend Health: http://localhost:8000/health
- API Docs: http://localhost:8000/docs (Swagger)

---

## ✅ COMPLETION CHECKLIST

After Claude Code finishes:

### **Backend**
- [ ] All 18 files created
- [ ] `python run.py` starts without errors
- [ ] `/health` endpoint returns 200
- [ ] News aggregation runs every 5 minutes
- [ ] Pipeline processes articles correctly
- [ ] Alerts broadcast via WebSocket
- [ ] Multi-agent /agent-question endpoint works
- [ ] Gemini API calls succeed
- [ ] No missing imports or syntax errors

### **Frontend**
- [ ] All 9 files created
- [ ] `npm run dev` starts without errors
- [ ] http://localhost:3000 loads
- [ ] Dashboard shows portfolio
- [ ] Real-time alerts appear
- [ ] Agent chat sends/receives messages
- [ ] Agent workflow visualization works
- [ ] No missing imports or build errors
- [ ] Responsive design looks good

### **Integration**
- [ ] Backend + Frontend communicate
- [ ] WebSocket alerts appear in real-time
- [ ] Multi-agent responses display correctly
- [ ] No CORS errors
- [ ] No connection errors
- [ ] Entire flow works smoothly

---

## 🚀 YOU'RE READY!

1. **Get API keys** (12 min)
2. **Open Claude Code**
3. **Paste the prompt** from `CLAUDE_CODE_COMPLETE_PROMPT.md`
4. **Follow Claude's instructions**
5. **Test each phase**
6. **Deploy to production**

**Estimated total time: 14-18 hours to production-ready system** ⏱️

Good luck! 🎉
