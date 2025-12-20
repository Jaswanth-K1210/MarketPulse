# MARKETPULSE-X IMPLEMENTATION TODO LIST
## Mapping Specification v3.0 to Current Project

**Last Updated:** December 20, 2024  
**Current Project Status:** Phase 1 Complete (Backend Infrastructure)  
**Specification Target:** Full MarketPulse-X v3.0 FINAL Architecture

---

## 📊 GAP ANALYSIS SUMMARY

### ✅ WHAT EXISTS (Current Implementation)
- Basic backend infrastructure (FastAPI)
- Simple 7-stage pipeline (not the 6-agent system)
- Gemini AI integration (basic)
- News aggregation (Google News, NewsAPI, NewsData.io)
- JSON database storage
- Basic REST API endpoints
- WebSocket support
- Basic agent system (4 agents, not the specified 6)
- Basic frontend (React + Vite)

### ❌ WHAT'S MISSING (Per Specification)
- **6-Agent Multi-Agent System** (Spec requires specific 6 agents)
- **LangGraph State Machine** (Not implemented)
- **Dynamic Relationship Discovery** (Agent 3B - Core Innovation)
- **10-Factor Analysis Framework** (Not implemented)
- **Confidence-Based Looping** (Agent 5 - Agentic Loop)
- **Complete Data Architecture** (Missing many tables/schemas)
- **Supply Chain Graph Visualization** (D3.js)
- **Agent Reasoning Trail UI** (Transparency layer)
- **Complete API Specification** (Missing many endpoints)
- **Demo-Ready Features** (Agent animation, etc.)

---

## 🎯 IMPLEMENTATION STRATEGY

### Phase 1: Core Architecture Alignment (8-10 hours)
Transform existing system to match specification exactly

### Phase 2: Advanced Features (6-8 hours)
Add dynamic discovery, 10-factor analysis, visualization

### Phase 3: Demo Polish (4-6 hours)
Agent animations, reasoning trails, demo scenarios

### Phase 4: Testing & Validation (2-4 hours)
End-to-end testing against specification

**Total Estimated Time: 20-28 hours**

---

# DETAILED TODO LIST

## 🔴 CRITICAL PRIORITY 1: MULTI-AGENT SYSTEM TRANSFORMATION

### ❌ TODO 1.1: Replace Pipeline with 6-Agent LangGraph System
**Current:** 7-stage pipeline in `app/services/pipeline.py`  
**Required:** 6 autonomous agents orchestrated by LangGraph  
**Files to Modify/Create:**

#### 1.1.1 Install LangGraph Dependencies
```bash
# Add to requirements.txt
langgraph==0.0.45
langchain==0.1.0
langchain-google-genai==0.0.5
langchain-community==0.0.10
```

#### 1.1.2 Create LangGraph State Schema
**New File:** `app/agents/state_schema.py`
```python
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph

class SupplyChainState(TypedDict):
    # Inputs
    user_id: str
    portfolio: List[str]
    
    # Agent 1 Output
    news_articles: List[Dict]
    last_fetch_time: str
    
    # Agent 2 Output
    classified_articles: List[Dict]
    high_priority_articles: List[str]
    
    # Agent 3A/3B Output
    matched_stocks: List[Dict]
    relationship_data: Dict
    discovered_relationships: List[Dict]
    
    # Agent 4 Output
    impact_analysis: Dict
    stock_impacts: List[Dict]
    
    # Agent 5 Output (CRITICAL - Looping Logic)
    confidence_score: float
    validation_decision: str  # "ACCEPT" or "REQUEST_MORE_DATA"
    gaps_identified: List[str]
    refined_search_queries: List[str]
    loop_count: int
    
    # Agent 6 Output
    alert_created: bool
    alert_id: str
    
    # Metadata
    workflow_status: str
    errors: List[str]
    processing_time: float
```

#### 1.1.3 Rebuild Agent 1: News Monitoring Agent
**File to Modify:** `app/agents/news_monitor_agent.py` (NEW)
**Current:** Exists in pipeline stage 1
**Changes Required:**
- Make autonomous (decides which sources to prioritize)
- Add decision logic for HIGH/URGENT/NORMAL priority
- Output exact schema from spec (Section 4, Agent 1)
- Integrate with LangGraph state

**Specification Reference:** Section 4, Agent 1 (Page 7-8)

#### 1.1.4 Rebuild Agent 2: Classification Agent
**File to Modify:** `app/agents/classification_agent.py` (NEW)
**Current:** Exists in pipeline stage 2
**Changes Required:**
- Implement 10-factor classification (currently missing)
- Add sentiment analysis (-1 to +1 scale)
- Output exact schema from spec
- Use Gemini with classification prompts from spec

**Specification Reference:** Section 4, Agent 2 (Page 8-9)
**Dependency:** Requires 10-Factor Framework (TODO 2.1)

#### 1.1.5 Create Agent 3A: Portfolio Matching Agent (Fast Path)
**File to Create:** `app/agents/portfolio_matcher_agent.py` (NEW)
**Current:** Partially exists in pipeline
**Changes Required:**
- Cache-based matching logic
- Decision: cache hit vs trigger Agent 3B
- Output exact schema from spec
- Relationship strength assessment (CRITICAL/HIGH/MODERATE/LOW)

**Specification Reference:** Section 4, Agent 3A (Page 9-10)

#### 1.1.6 Create Agent 3B: Dynamic Discovery Agent ⭐ CORE INNOVATION
**File to Create:** `app/agents/dynamic_discovery_agent.py` (NEW)
**Current:** DOES NOT EXIST - This is the key differentiator
**Changes Required:**
- Multi-source intelligence gathering:
  - SEC EDGAR filing parser
  - News article aggregation
  - Company website scraping
  - LLM knowledge fallback
- Fusion algorithm (confidence boosting when sources agree)
- Cache storage with 24-hour TTL
- Output exact schema from spec

**Specification Reference:** Section 4, Agent 3B (Page 10-12) + Section 5 (Page 13-16)

**This is THE most important feature - without this, system is just a database lookup**

#### 1.1.7 Rebuild Agent 4: Impact Calculator Agent
**File to Modify:** `app/agents/calculator_agent.py` (EXISTS, needs major changes)
**Current:** Basic impact calculation
**Changes Required:**
- Implement TIER 1/2/3 impact calculation (direct/supplier/customer)
- Historical precedent matching
- Formula-based calculation for novel scenarios
- LLM estimation fallback
- Output exact schema from spec (with reasoning field)

**Specification Reference:** Section 4, Agent 4 (Page 12-13)

#### 1.1.8 Create Agent 5: Confidence Validator Agent ⭐ AGENTIC LOOP
**File to Create:** `app/agents/confidence_validator_agent.py` (NEW)
**Current:** DOES NOT EXIST - This creates the agentic behavior
**Changes Required:**
- Confidence threshold checking (70%)
- Gap analysis logic
- Refined query generation
- **AUTONOMOUS DECISION: Loop back or finalize**
- Loop count tracking (max 3 iterations)
- Output exact schema from spec

**Specification Reference:** Section 4, Agent 5 (Page 13-14)

**This is what makes the system "agentic" vs sequential processing**

#### 1.1.9 Rebuild Agent 6: Alert Generator Agent
**File to Modify:** `app/agents/alert_generator_agent.py` (NEW)
**Current:** Exists in pipeline stage 7
**Changes Required:**
- Severity classification (CRITICAL/HIGH/MODERATE/LOW)
- Delivery channel decision logic
- Agent trail formatting
- Output exact schema from spec

**Specification Reference:** Section 4, Agent 6 (Page 14-15)

#### 1.1.10 Create LangGraph Workflow Orchestrator
**File to Create:** `app/agents/langgraph_workflow.py` (NEW)
**Current:** DOES NOT EXIST
**Changes Required:**
- Define StateGraph with all 6 agents as nodes
- Add conditional edges:
  - Agent 3A → Agent 3B (if cache miss)
  - Agent 5 → Agent 1 (if confidence < 70%, loop back)
- Compile workflow
- Execute with state management

**Specification Reference:** Section 4, LangGraph State Machine (Page 15-16)

**Code Template:**
```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(SupplyChainState)

# Add nodes
workflow.add_node("news_monitor", agent_1_news_monitor)
workflow.add_node("classifier", agent_2_classifier)
workflow.add_node("matcher_fast", agent_3a_matcher)
workflow.add_node("matcher_discovery", agent_3b_discovery)
workflow.add_node("impact_calculator", agent_4_calculator)
workflow.add_node("confidence_validator", agent_5_validator)
workflow.add_node("alert_generator", agent_6_alerts)

# Add edges
workflow.add_edge("news_monitor", "classifier")
workflow.add_edge("classifier", "matcher_fast")

# Conditional: cache hit or discovery needed?
workflow.add_conditional_edges(
    "matcher_fast",
    route_to_discovery_if_needed,
    {"discovery": "matcher_discovery", "skip": "impact_calculator"}
)

workflow.add_edge("matcher_discovery", "impact_calculator")
workflow.add_edge("impact_calculator", "confidence_validator")

# Conditional: confidence acceptable or loop back?
workflow.add_conditional_edges(
    "confidence_validator",
    check_confidence_threshold,
    {"accept": "alert_generator", "loop": "news_monitor"}
)

workflow.add_edge("alert_generator", END)
workflow.set_entry_point("news_monitor")

app = workflow.compile()
```

---

## 🔴 CRITICAL PRIORITY 2: DYNAMIC RELATIONSHIP DISCOVERY

### ❌ TODO 2.1: Implement Multi-Source Intelligence Fusion
**Current:** Basic relationship extraction exists
**Required:** 4-source fusion with confidence scoring

#### 2.1.1 Create SEC EDGAR Parser
**File to Create:** `app/services/sec_parser.py` (NEW)
**Functionality:**
- Download 10-K filings from SEC EDGAR API
- Extract "Business" and "Risk Factors" sections
- LLM-based relationship extraction
- Confidence: 0.85-0.95

**Specification Reference:** Section 5, Step 3 (Page 17-18)

**API Endpoint:** `https://www.sec.gov/cgi-bin/browse-edgar`

#### 2.1.2 Create News Relationship Aggregator
**File to Create:** `app/services/news_relationship_extractor.py` (NEW)
**Functionality:**
- Search NewsAPI for "{company} supplier customer partner"
- Fetch top 20 articles (past 90 days)
- LLM extraction
- Cross-reference across articles (consensus)
- Confidence: 0.60-0.75

**Specification Reference:** Section 5, Step 4 (Page 18)

#### 2.1.3 Create Company Website Scraper
**File to Create:** `app/services/website_scraper.py` (NEW)
**Functionality:**
- Scrape /about, /investors, /partners pages
- LLM extraction
- Confidence: 0.50-0.70

**Specification Reference:** Section 5, Step 5 (Page 18)

**Dependencies:**
```bash
pip install beautifulsoup4 requests
```

#### 2.1.4 Create LLM Knowledge Fallback
**File to Modify:** `app/services/gemini_client.py`
**Add Method:** `extract_relationships_from_knowledge(company: str)`
**Functionality:**
- Prompt Gemini for known relationships
- Mark as "unverified"
- Max confidence: 0.45
- Only use if other sources fail

**Specification Reference:** Section 5, Step 6 (Page 18)

#### 2.1.5 Create Fusion Algorithm
**File to Create:** `app/services/relationship_fusion.py` (NEW)
**Functionality:**
- Merge relationships from 4 sources
- Boost confidence when sources agree (+15%)
- Deduplication logic
- Store in cache with 24-hour TTL

**Specification Reference:** Section 5, Step 7 (Page 18-19)

**Algorithm:**
```python
def merge_relationships(sec_rels, news_rels, web_rels, llm_rels):
    # Group by (company_pair, relationship_type)
    # Take highest confidence as base
    # Add bonus for agreement (+15%)
    # Cap at 0.98 (never 100% certain)
    # Return merged list
```

#### 2.1.6 Create Relationship Confidence Scorer
**File to Create:** `app/services/confidence_scorer.py` (NEW)
**Functionality:**
- Base confidence by source type
- Criticality keyword boost
- Multiple sources boost
- Recency penalty
- Cap at 98%

**Specification Reference:** Section 5, Relationship Confidence Scoring (Page 19)

---

## 🟡 HIGH PRIORITY 3: 10-FACTOR ANALYSIS FRAMEWORK

### ❌ TODO 3.1: Implement 10-Factor Classification System
**Current:** DOES NOT EXIST
**Required:** Complete 10-factor framework with detection keywords

#### 3.1.1 Create Factor Definitions
**File to Create:** `app/models/factors.py` (NEW)
**Content:**
```python
from enum import Enum

class MarketFactor(Enum):
    MACROECONOMIC = 1
    INTEREST_RATES = 2
    SUPPLY_CHAIN = 3
    COMPANY_EARNINGS = 4
    GOVERNMENT_POLICY = 5
    GEOPOLITICAL = 6
    CURRENCY = 7
    MARKET_SENTIMENT = 8
    INDUSTRY_TRENDS = 9
    BLACK_SWAN = 10

FACTOR_KEYWORDS = {
    MarketFactor.MACROECONOMIC: [
        "GDP", "economic growth", "inflation", "CPI", 
        "unemployment", "jobs report", "recession", ...
    ],
    MarketFactor.INTEREST_RATES: [
        "Federal Reserve", "Fed", "interest rate", 
        "rate hike", "FOMC", "Powell", ...
    ],
    # ... all 10 factors
}

FACTOR_IMPACT_RULES = {
    MarketFactor.SUPPLY_CHAIN: {
        "supplier_disruption": "customer_stocks_down",
        "shortage": "companies_with_inventory_up",
        ...
    },
    # ... all 10 factors
}
```

**Specification Reference:** Section 7, Complete Factor Definitions (Page 21-27)

#### 3.1.2 Update Classification Agent with 10-Factor Logic
**File to Modify:** `app/agents/classification_agent.py`
**Changes:**
- Use factor keywords for initial classification
- LLM reasoning for ambiguous cases
- Multi-factor handling (primary + secondary)
- Sentiment scoring (-1 to +1)

**Specification Reference:** Section 7, Multi-Factor Classification (Page 27)

#### 3.1.3 Create Factor Impact Calculator
**File to Create:** `app/services/factor_impact_calculator.py` (NEW)
**Functionality:**
- Factor-specific impact rules
- Multi-factor weighting (70% primary, 30% secondary)
- Historical precedent lookup by factor
- Output impact estimates per factor

**Specification Reference:** Section 7 (Page 21-27)

---

## 🟡 HIGH PRIORITY 4: DATA ARCHITECTURE ALIGNMENT

### ❌ TODO 4.1: Migrate from JSON to SQLite with Complete Schema
**Current:** JSON file storage
**Required:** SQLite with 8 tables per specification

#### 4.1.1 Create Database Schema
**File to Create:** `app/database/schema.sql` (NEW)
**Tables Required:**
1. `users`
2. `portfolios`
3. `companies`
4. `relationships` ⭐ (Core table)
5. `news_articles`
6. `portfolio_alerts`
7. `historical_events`
8. `agent_logs` (for demo/debug)

**Specification Reference:** Section 8, Database Schema (Page 27-31)

#### 4.1.2 Create SQLite Database Manager
**File to Create:** `app/database/sqlite_manager.py` (NEW)
**Replace:** `app/services/database.py` (current JSON storage)
**Functionality:**
- Connection pooling
- CRUD operations for all 8 tables
- Indexing (per spec)
- Cache cleanup (24-hour TTL for relationships)

#### 4.1.3 Pre-populate Top 50 Companies
**File to Create:** `app/database/seed_data.py` (NEW)
**Data Required:**
- Top 50 companies (ticker, name, sector, industry)
- ~200 pre-loaded relationships (from SEC filings)
- 20-30 historical events

**Specification Reference:** Section 8, Pre-Population Strategy (Page 31-32)

**Time Required:** 6-8 hours of manual data curation (can be done in parallel)

#### 4.1.4 Update All Services to Use SQLite
**Files to Modify:**
- `app/agents/*.py` (all agents)
- `app/api/routes.py`
- `app/services/*.py`

**Changes:** Replace JSON file I/O with SQLite queries

---

## 🟢 MEDIUM PRIORITY 5: FRONTEND TRANSFORMATION

### ❌ TODO 5.1: Build Agent Visualization Component ⭐ DEMO WOW FACTOR
**Current:** Basic frontend exists
**Required:** Animated 6-agent pipeline visualization

#### 5.1.1 Create AgentVisualization Component
**File to Create:** `frontend/src/components/AgentVisualization.jsx` (NEW)
**Features:**
- 6 agent cards in vertical pipeline
- Real-time progress bars
- Status messages ("Scanning 47 news sources...")
- Animated transitions between agents
- Loop-back visualization (when confidence < 70%)

**Specification Reference:** Section 9, AgentVisualization.tsx (Page 35-37)

**Design:**
```
🌐 Agent 1: News Monitoring
━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░ 75%
Scanning 47 news sources...
         ↓
📋 Agent 2: Classification
━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░ 80%
Classified 23 articles...
         ↓
... (all 6 agents)
```

#### 5.1.2 Create Supply Chain Graph Component (D3.js)
**File to Create:** `frontend/src/components/SupplyChainGraph.jsx` (NEW)
**Current:** DOES NOT EXIST
**Features:**
- Force-directed graph layout
- Draggable nodes
- Color coding by criticality (RED/ORANGE/YELLOW/GREEN)
- Edge thickness by confidence
- Interactive (click for details)

**Specification Reference:** Section 9, SupplyChainGraph.tsx (Page 37-38)

**Dependencies:**
```bash
npm install d3@7.8.5
```

#### 5.1.3 Create Reasoning Trail Component
**File to Create:** `frontend/src/components/ReasoningTrail.jsx` (NEW)
**Current:** DOES NOT EXIST
**Features:**
- Step-by-step agent execution log
- Timing for each step
- Confidence scores at each stage
- Loop-back visualization
- Source citations

**Specification Reference:** Section 9, ReasoningTrail.tsx (Page 38-40)

**This builds trust and demonstrates agentic behavior**

#### 5.1.4 Create Impact Analysis Display
**File to Create:** `frontend/src/components/ImpactAnalysis.jsx` (NEW)
**Current:** Basic alert display exists
**Features:**
- Portfolio total impact ($ and %)
- Per-stock breakdown
- Risk level badges (CRITICAL/HIGH/MODERATE/LOW)
- Confidence score visualization
- Recommendation text
- "View Full Analysis" / "View Supply Chain Graph" buttons

**Specification Reference:** Section 9, ImpactAnalysis.tsx (Page 38)

#### 5.1.5 Update Dashboard Layout
**File to Modify:** `frontend/src/pages/Dashboard.jsx`
**Changes:**
- Portfolio summary at top
- Active risks section (alert cards)
- "Analyze Current Market" button (triggers agent visualization)
- Real-time updates via WebSocket

**Specification Reference:** Section 9, Dashboard.tsx (Page 34-35)

---

## 🟢 MEDIUM PRIORITY 6: API SPECIFICATION ALIGNMENT

### ❌ TODO 6.1: Implement Missing API Endpoints
**Current:** Basic endpoints exist
**Required:** Complete API per specification

#### 6.1.1 Create POST /api/portfolio/analyze Endpoint
**File to Modify:** `app/api/routes.py`
**Current:** Partially exists
**Changes:**
- Trigger LangGraph workflow (not old pipeline)
- Return complete analysis with agent trail
- Include processing time, loop count
- Match exact response schema from spec

**Specification Reference:** Section 10, POST /api/portfolio/analyze (Page 40-41)

#### 6.1.2 Create POST /api/relationships/discover Endpoint
**File to Create:** `app/api/routes.py` (add endpoint)
**Current:** DOES NOT EXIST
**Functionality:**
- Trigger Agent 3B for specific company
- Return discovered relationships
- Include discovery time, sources, confidence
- Cache results

**Specification Reference:** Section 10, POST /api/relationships/discover (Page 41)

#### 6.1.3 Create GET /api/graph/build Endpoint
**File to Create:** `app/api/routes.py` (add endpoint)
**Current:** Partial graph endpoint exists
**Changes:**
- Build supply chain graph for portfolio
- Support depth parameter (relationship hops)
- Return nodes + edges + insights
- Include "single point of failure" detection

**Specification Reference:** Section 10, GET /api/graph/build (Page 41-42)

#### 6.1.4 Update GET /api/alerts Endpoint
**File to Modify:** `app/api/routes.py`
**Changes:**
- Add query parameters (limit, severity, read, since)
- Return total + unread count
- Match exact response schema

**Specification Reference:** Section 10, GET /api/alerts (Page 42)

#### 6.1.5 Create GET /api/news/recent Endpoint
**File to Create:** `app/api/routes.py` (add endpoint)
**Functionality:**
- Return recent news articles
- Filter by factor, companies
- Include classification data

**Specification Reference:** Section 10, GET /api/news/recent (Page 42)

---

## 🟢 MEDIUM PRIORITY 7: NEWS INTELLIGENCE ENGINE

### ❌ TODO 7.1: Enhance News Fetching Strategy
**Current:** Basic news aggregation exists
**Required:** Production-grade monitoring system

#### 7.1.1 Add RSS Feed Sources
**File to Modify:** `app/services/news_aggregator.py`
**Add Sources:**
- Reuters Business RSS
- Bloomberg Markets RSS
- CNBC Breaking RSS
- Wall Street Journal RSS
- Financial Times RSS

**Specification Reference:** Section 6, News Sources (Page 20)

**URLs:**
```python
RSS_FEEDS = {
    'reuters': 'http://feeds.reuters.com/reuters/businessNews',
    'bloomberg': 'https://feeds.bloomberg.com/markets/news.rss',
    'cnbc': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
    'wsj': 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
}
```

#### 7.1.2 Implement Deduplication Logic
**File to Modify:** `app/services/news_aggregator.py`
**Add Function:** `deduplicate_news(articles)`
**Logic:**
- Cluster by headline similarity (60% word overlap)
- Prefer higher-priority sources (Reuters > Bloomberg > Others)
- Return best article from each cluster

**Specification Reference:** Section 6, Step 3: Deduplication (Page 21)

#### 7.1.3 Implement Relevance Filtering
**File to Modify:** `app/services/news_aggregator.py`
**Add Function:** `filter_relevant_news(articles, portfolio)`
**Logic:**
- Priority 1: Portfolio companies mentioned
- Priority 2: High-impact keywords (halt, shutdown, etc.)
- Priority 3: Sector mentions
- Limit to top 50 (cost control)

**Specification Reference:** Section 6, Step 2: Relevance Filtering (Page 20-21)

---

## 🔵 LOW PRIORITY 8: DEMO PREPARATION

### ❌ TODO 8.1: Create Demo Scenarios
**File to Create:** `demo/scenarios.md` (NEW)
**Content:**
- Scenario 1: TSMC production halt (main demo)
- Scenario 2: Fed interest rate hike
- Scenario 3: Geopolitical event (China export restrictions)
- Scenario 4: Judge's own portfolio (dynamic)

**Specification Reference:** Section 15, Demo Scenarios (Page 48-50)

### ❌ TODO 8.2: Create Demo Video (Backup)
**Time Required:** 2 hours
**Content:**
- 3-minute recorded demo
- Narration of key features
- Show: Portfolio input → Agent execution → Results
- Multiple formats (MP4, MOV)

**Specification Reference:** Section 13, Hour 28-30 (Page 45)

### ❌ TODO 8.3: Create Pitch Deck
**File to Create:** `demo/pitch_deck.pptx` (NEW)
**Slides:**
1. Hook + Problem (retail investors lose money)
2. Solution (MarketPulse-X overview)
3. Live Demo (screenshots)
4. Technical Architecture (diagram)
5. Close (pricing, validation)

**Specification Reference:** Section 15, 3-Minute Pitch Script (Page 47-48)

### ❌ TODO 8.4: Prepare Q&A Responses
**File to Create:** `demo/qa_prep.md` (NEW)
**Questions to Prepare:**
- "How is this different from Bloomberg Terminal?"
- "What if the LLM hallucinates relationships?"
- "How do you handle API rate limits?"
- "Can you analyze MY portfolio?" (be ready to demo live)

**Specification Reference:** Section 15, Demo Strategy (Page 47-50)

---

## 🔵 LOW PRIORITY 9: TESTING & VALIDATION

### ❌ TODO 9.1: Create End-to-End Test Suite
**File to Create:** `tests/test_e2e_workflow.py` (NEW)
**Tests:**
- Full LangGraph workflow execution
- Confidence looping (trigger low confidence scenario)
- Dynamic discovery (test unknown company)
- Multi-factor classification
- Alert generation

### ❌ TODO 9.2: Create Agent Unit Tests
**Files to Create:**
- `tests/test_agent_1_news_monitor.py`
- `tests/test_agent_2_classifier.py`
- `tests/test_agent_3a_matcher.py`
- `tests/test_agent_3b_discovery.py`
- `tests/test_agent_4_calculator.py`
- `tests/test_agent_5_validator.py`
- `tests/test_agent_6_alerts.py`

### ❌ TODO 9.3: Create Performance Tests
**File to Create:** `tests/test_performance.py` (NEW)
**Metrics:**
- Total processing time < 15 seconds
- Dynamic discovery < 15 seconds
- Database queries < 100ms
- API response time < 500ms

---

## 📦 DEPENDENCIES TO ADD

### Backend (requirements.txt)
```
# Add these to existing requirements.txt
langgraph==0.0.45
langchain==0.1.0
langchain-google-genai==0.0.5
langchain-community==0.0.10
beautifulsoup4==4.12.0  # Already exists
feedparser==6.0.11  # Already exists
duckduckgo-search==4.1.0  # For web scraping
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "d3": "^7.8.5",
    "recharts": "^2.9.0",
    "lucide-react": "^0.294.0"
  }
}
```

---

## 🎯 EXECUTION PRIORITY ORDER

### Week 1: Core Transformation (20 hours)
1. ✅ Install LangGraph dependencies (30 min)
2. ✅ Create state schema (1 hour)
3. ✅ Rebuild 6 agents (8 hours)
4. ✅ Create LangGraph workflow (2 hours)
5. ✅ Implement Agent 3B (Dynamic Discovery) (4 hours)
6. ✅ Implement Agent 5 (Confidence Validator) (2 hours)
7. ✅ Test end-to-end workflow (2 hours)

### Week 2: Data & Features (16 hours)
1. ✅ Migrate to SQLite (4 hours)
2. ✅ Implement 10-factor framework (3 hours)
3. ✅ Build multi-source fusion (4 hours)
4. ✅ Pre-populate 50 companies (3 hours)
5. ✅ Update API endpoints (2 hours)

### Week 3: Frontend & Demo (12 hours)
1. ✅ Build AgentVisualization component (3 hours)
2. ✅ Build SupplyChainGraph (D3.js) (3 hours)
3. ✅ Build ReasoningTrail component (2 hours)
4. ✅ Update Dashboard layout (2 hours)
5. ✅ Create demo scenarios (1 hour)
6. ✅ Record demo video (1 hour)

### Week 4: Testing & Polish (8 hours)
1. ✅ End-to-end testing (3 hours)
2. ✅ Performance optimization (2 hours)
3. ✅ Bug fixes (2 hours)
4. ✅ Final demo rehearsal (1 hour)

**Total: ~56 hours (spread over 4 weeks)**

---

## 🚨 CRITICAL SUCCESS FACTORS

### Must-Have Features (Non-Negotiable):
1. ✅ **6-Agent LangGraph System** - This is the core architecture
2. ✅ **Agent 3B (Dynamic Discovery)** - The key differentiator
3. ✅ **Agent 5 (Confidence Looping)** - What makes it "agentic"
4. ✅ **10-Factor Analysis** - Demonstrates intelligence depth
5. ✅ **Agent Visualization UI** - The demo wow factor
6. ✅ **Reasoning Trail** - Builds trust and transparency

### Nice-to-Have Features (If Time Permits):
1. ⏳ D3.js Supply Chain Graph
2. ⏳ Historical precedent database (20-30 events)
3. ⏳ Multi-factor weighting
4. ⏳ Demo video backup
5. ⏳ Comprehensive test suite

---

## 📊 PROGRESS TRACKING

### Phase 1: Core Architecture (0% Complete)
- [ ] LangGraph dependencies installed
- [ ] State schema created
- [ ] Agent 1 rebuilt
- [ ] Agent 2 rebuilt
- [ ] Agent 3A created
- [ ] Agent 3B created ⭐
- [ ] Agent 4 rebuilt
- [ ] Agent 5 created ⭐
- [ ] Agent 6 rebuilt
- [ ] LangGraph workflow created
- [ ] End-to-end test passing

### Phase 2: Data & Intelligence (0% Complete)
- [ ] SQLite migration complete
- [ ] 10-factor framework implemented
- [ ] Multi-source fusion working
- [ ] SEC parser working
- [ ] 50 companies pre-populated
- [ ] API endpoints updated

### Phase 3: Frontend (0% Complete)
- [ ] AgentVisualization component
- [ ] SupplyChainGraph component
- [ ] ReasoningTrail component
- [ ] Dashboard updated
- [ ] Demo scenarios prepared

### Phase 4: Testing (0% Complete)
- [ ] E2E tests passing
- [ ] Performance benchmarks met
- [ ] Demo rehearsed 5x
- [ ] Q&A prepared

---

## 🎬 NEXT IMMEDIATE STEPS

### Step 1: Install Dependencies (15 minutes)
```bash
cd /Users/apple/Documents/Projects/Marketpulse/MarketPulse
source .venv/bin/activate
pip install langgraph langchain langchain-google-genai langchain-community duckduckgo-search
```

### Step 2: Create State Schema (30 minutes)
Create `app/agents/state_schema.py` with exact schema from spec

### Step 3: Start with Agent 5 (Confidence Validator) (2 hours)
This is the most critical missing piece - creates the agentic loop

### Step 4: Create Agent 3B (Dynamic Discovery) (4 hours)
This is the key differentiator - makes system work for ANY company

### Step 5: Rebuild Other Agents to Match Spec (6 hours)
Align existing agents with exact specification requirements

---

## 📝 NOTES

- **DO NOT** simplify or skip features from the specification
- **DO NOT** assume existing implementation matches spec (it doesn't)
- **DO** follow exact naming, schemas, and logic from specification
- **DO** prioritize Agent 3B and Agent 5 (core innovations)
- **DO** test each agent independently before integration
- **DO** maintain backward compatibility with existing data during migration

---

**This TODO list is the SINGLE SOURCE OF TRUTH for implementation.**  
**All work must align with MarketPulse-X Specification v3.0 FINAL.**

Last Updated: December 20, 2024
