# ARCHITECTURE COMPARISON: CURRENT vs. SPECIFICATION

---

## 🏗️ CURRENT ARCHITECTURE (What You Have)

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                  │
│  ┌──────────────┬──────────────┬──────────────────────────┐│
│  │  Basic       │   Basic      │  Missing:                ││
│  │  Dashboard   │   Alerts     │  - Agent Viz             ││
│  │              │              │  - Supply Chain Graph    ││
│  │              │              │  - Reasoning Trail       ││
│  └──────────────┴──────────────┴──────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              ↕ REST API
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                    │
│  Basic endpoints: /portfolio, /alerts, /health             │
│  Missing: /relationships/discover, /graph/build            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              7-STAGE PIPELINE (Sequential)                  │
│                                                             │
│  Stage 1: Event Validator                                  │
│      ↓                                                      │
│  Stage 2: Relation Extractor (Gemini)                      │
│      ↓                                                      │
│  Stage 3: Relation Verifier                                │
│      ↓                                                      │
│  Stage 4: Cascade Inferencer (Gemini)                      │
│      ↓                                                      │
│  Stage 5: Impact Scorer                                    │
│      ↓                                                      │
│  Stage 6: Explanation Generator (Gemini)                   │
│      ↓                                                      │
│  Stage 7: Graph Orchestrator                               │
│                                                             │
│  ❌ NO LOOPING - Sequential only                           │
│  ❌ NO CONFIDENCE VALIDATION                               │
│  ❌ NO DYNAMIC DISCOVERY                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              4 BASIC AGENTS (Not Spec-Compliant)            │
│                                                             │
│  1. Analyst Agent (market analysis)                        │
│  2. Researcher Agent (info gathering)                      │
│  3. Calculator Agent (impact calc)                         │
│  4. Synthesizer Agent (orchestration)                      │
│                                                             │
│  ❌ MISSING: News Monitor Agent                            │
│  ❌ MISSING: Classification Agent                          │
│  ❌ MISSING: Portfolio Matcher Agent                       │
│  ❌ MISSING: Dynamic Discovery Agent ⭐                    │
│  ❌ MISSING: Confidence Validator Agent ⭐                 │
│  ❌ MISSING: Alert Generator Agent                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVICES LAYER                           │
│                                                             │
│  ✅ Gemini Client (basic)                                  │
│  ✅ News Aggregator (3 sources)                            │
│  ✅ Market Data (Yahoo Finance)                            │
│  ❌ SEC Parser (missing)                                   │
│  ❌ Website Scraper (missing)                              │
│  ❌ Multi-Source Fusion (missing)                          │
│  ❌ 10-Factor Framework (missing)                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER (JSON Files)                  │
│                                                             │
│  articles.json                                              │
│  alerts.json                                                │
│  relationships.json (basic, static)                         │
│  portfolio.json                                             │
│  knowledge_graphs.json                                      │
│                                                             │
│  ❌ NO SQLite                                              │
│  ❌ NO Relationship Cache (24h TTL)                        │
│  ❌ NO Historical Events                                   │
│  ❌ NO Agent Logs                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 REQUIRED ARCHITECTURE (Per Specification v3.0)

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  ┌──────────────┬──────────────┬──────────────────────────┐│
│  │  Portfolio   │   Alert      │  Agent Activity          ││
│  │  Dashboard   │   Feed       │  Visualization ⭐        ││
│  │              │              │  (Animated Pipeline)     ││
│  └──────────────┴──────────────┴──────────────────────────┘│
│  ┌──────────────┬──────────────┬──────────────────────────┐│
│  │  Supply      │  Reasoning   │  Impact                  ││
│  │  Chain       │  Trail ⭐    │  Analysis                ││
│  │  Graph (D3)⭐│  (Transparency)│                         ││
│  └──────────────┴──────────────┴──────────────────────────┘│
│                     (React + TypeScript + D3.js)            │
└─────────────────────────────────────────────────────────────┘
                              ↕ REST API
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                      │
│  POST /api/portfolio/analyze                                │
│  GET  /api/alerts/{user_id}                                 │
│  POST /api/relationships/discover ⭐                        │
│  GET  /api/graph/build                                      │
│  GET  /api/news/recent                                      │
│                        (FastAPI)                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              MULTI-AGENT ORCHESTRATION LAYER                │
│                     (LangGraph State Machine) ⭐            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                   AGENT WORKFLOW                      │ │
│  │                                                       │ │
│  │   Agent 1          Agent 2         Agent 3A/3B       │ │
│  │   News      ──→    Classifier  ──→  Portfolio        │ │
│  │   Monitor                           Matcher          │ │
│  │                                         │            │ │
│  │                                    Cache Miss?       │ │
│  │                                         ↓            │ │
│  │                                    Agent 3B ⭐       │ │
│  │                                    Dynamic           │ │
│  │                                    Discovery         │ │
│  │                                         │            │ │
│  │                                         ↓            │ │
│  │                    Agent 4         Agent 5 ⭐        │ │
│  │                    Impact    ──→   Confidence        │ │
│  │                    Calculator      Validator         │ │
│  │                                         │            │ │
│  │                                    Confidence         │ │
│  │                                    < 70%?            │ │
│  │                                         │            │ │
│  │                    YES ←────────────────┘            │ │
│  │                     │                                │ │
│  │                     ↓                                │ │
│  │              🔄 LOOP BACK to Agent 1 ⭐              │ │
│  │              (refined search)                        │ │
│  │                     │                                │ │
│  │                    NO                                │ │
│  │                     │                                │ │
│  │                     ↓                                │ │
│  │                 Agent 6                              │ │
│  │                 Alert                                │ │
│  │                 Generator                            │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE LAYER                       │
│                                                             │
│  ┌──────────────┬──────────────┬──────────────────────┐   │
│  │   Dynamic    │   News       │   Impact             │   │
│  │   Discovery⭐│   Fetcher    │   Calculator         │   │
│  │   Engine     │   (Multi)    │   (TIER 1/2/3)       │   │
│  └──────────────┴──────────────┴──────────────────────┘   │
│                                                             │
│  Multi-Source Fusion ⭐:                                   │
│  • SEC Filing Parser (Confidence: 0.85-0.95)              │
│  • News Aggregator (Confidence: 0.60-0.75)                │
│  • Web Scraper (Confidence: 0.50-0.70)                    │
│  • LLM Extractor (Confidence: 0.30-0.50)                  │
│  • Confidence Scorer (Boost when sources agree)           │
│                                                             │
│  10-Factor Analysis Framework ⭐:                          │
│  1. Macroeconomic    6. Geopolitical                       │
│  2. Interest Rates   7. Currency                           │
│  3. Supply Chain     8. Market Sentiment                   │
│  4. Earnings         9. Industry Trends                    │
│  5. Policy          10. Black Swan                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER (SQLite) ⭐                │
│                                                             │
│  ┌──────────────┬──────────────┬──────────────────────┐   │
│  │  users       │   portfolios │   companies          │   │
│  └──────────────┴──────────────┴──────────────────────┘   │
│  ┌──────────────┬──────────────┬──────────────────────┐   │
│  │relationships⭐│ news_articles│ portfolio_alerts     │   │
│  │(24h TTL)     │              │                      │   │
│  └──────────────┴──────────────┴──────────────────────┘   │
│  ┌──────────────┬──────────────┐                          │
│  │historical_   │  agent_logs  │                          │
│  │events        │  (debug)     │                          │
│  └──────────────┴──────────────┘                          │
│                                                             │
│  Pre-populated: Top 50 companies (80% coverage)            │
│  Dynamic cache: 24-hour TTL                                │
│  News retention: 90 days                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                         │
│                                                             │
│  ┌──────────────┬──────────────┬──────────────────────┐   │
│  │  Google      │   NewsAPI    │   SEC EDGAR ⭐       │   │
│  │  Gemini      │   (News)     │   (Filings)          │   │
│  │  (LLM)       │              │                      │   │
│  └──────────────┴──────────────┴──────────────────────┘   │
│                                                             │
│  All free tier / public APIs                               │
│  Rate limiting handled                                     │
└─────────────────────────────────────────────────────────────┘
```

**Legend:** ⭐ = Critical missing component

---

## 🔴 CRITICAL DIFFERENCES

### 1. Orchestration Layer

| Aspect | Current | Required | Impact |
|--------|---------|----------|--------|
| **Framework** | Custom pipeline | LangGraph StateGraph | HIGH |
| **Execution** | Sequential only | Conditional + Looping | CRITICAL |
| **State Management** | None | Shared state across agents | HIGH |
| **Agent Count** | 4 generic agents | 6 specialized agents | HIGH |
| **Looping** | ❌ None | ✅ Confidence-based | CRITICAL |

### 2. Agent 3B: Dynamic Discovery (THE KEY INNOVATION)

**Current:**
```
❌ Does not exist
❌ Relationships are static/pre-loaded
❌ Cannot discover new companies
❌ Single source (basic LLM extraction)
```

**Required:**
```
✅ Multi-source intelligence gathering:
   - SEC EDGAR filings (0.85-0.95 confidence)
   - News articles (0.60-0.75 confidence)
   - Company websites (0.50-0.70 confidence)
   - LLM knowledge (0.30-0.50 confidence)
✅ Fusion algorithm (boost confidence when sources agree)
✅ Works for ANY publicly traded company
✅ 24-hour cache with TTL
✅ Discovery time: 10-15 seconds
```

**Why Critical:**
- Without this, you're just a static database lookup
- This is what makes the system work for 5,000+ companies vs. 50
- This is the #1 differentiator from competitors

### 3. Agent 5: Confidence Validator (THE AGENTIC LOOP)

**Current:**
```
❌ Does not exist
❌ No confidence validation
❌ No quality control
❌ No looping mechanism
```

**Required:**
```
✅ Validates overall confidence ≥ 70%
✅ If low: Identifies gaps in analysis
✅ Generates refined search queries
✅ AUTONOMOUSLY DECIDES to loop back to Agent 1
✅ Tracks loop count (max 3 iterations)
✅ Prevents infinite loops
```

**The Agentic Loop:**
```
Agent 1 → Agent 2 → Agent 3 → Agent 4 → Agent 5
                                            │
                                  Confidence < 70%?
                                            │
                                           YES
                                            │
                              [Identify gaps]
                              [Generate refined queries]
                                            │
                                            ↓
Agent 1 ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ┘
(refined search with new queries)

Loop continues until:
- Confidence ≥ 70% OR
- Loop count ≥ 3
```

**Why Critical:**
- This is what makes the system "agentic" vs. sequential
- This is what earns the 9.2/10 agentic rating
- Without this, it's just a pipeline with no intelligence

### 4. 10-Factor Analysis Framework

**Current:**
```
❌ No factor classification
❌ Basic sentiment only
❌ No structured analysis
```

**Required:**
```
✅ 10 distinct market factors:
   1. Macroeconomic Indicators
   2. Interest Rates & Central Bank Policy
   3. Supply Chain Events
   4. Company Earnings & Performance
   5. Government Policy & Regulation
   6. Geopolitical Events
   7. Currency Fluctuations
   8. Market Sentiment & Psychology
   9. Industry-Specific Trends
   10. Black Swan Events

✅ Detection keywords for each factor
✅ Impact rules per factor
✅ Multi-factor handling (primary + secondary)
✅ Sentiment scoring (-1 to +1)
```

**Why Critical:**
- Demonstrates depth of intelligence
- Enables precise impact calculation
- Differentiates from simple news aggregators

### 5. Data Architecture

**Current:**
```
❌ JSON files (5 files)
❌ No caching strategy
❌ No relationship TTL
❌ No historical precedents
❌ No agent logging
```

**Required:**
```
✅ SQLite database (8 tables)
✅ Relationship cache (24-hour TTL)
✅ Pre-populated: 50 companies + 200 relationships
✅ Historical events: 20-30 precedents
✅ Agent logs (for debugging/demo)
✅ Proper indexing for performance
```

**Why Critical:**
- Enables caching strategy (performance)
- Supports historical precedent matching
- Provides demo transparency (agent logs)

### 6. Frontend Demo Features

**Current:**
```
❌ Basic dashboard
❌ Basic alerts
❌ No agent visualization
❌ No supply chain graph
❌ No reasoning trail
```

**Required:**
```
✅ Agent Visualization (animated pipeline) ⭐
   - 6 agent cards with progress bars
   - Real-time status messages
   - Loop-back animation
   - Processing time display

✅ Supply Chain Graph (D3.js) ⭐
   - Force-directed layout
   - Draggable nodes
   - Color coding by criticality
   - Interactive tooltips

✅ Reasoning Trail ⭐
   - Step-by-step agent execution
   - Timing for each step
   - Confidence scores
   - Source citations
   - Loop visualization
```

**Why Critical:**
- Agent visualization is the "wow factor" for demos
- Reasoning trail builds trust (transparency)
- Supply chain graph shows relationships visually
- These are what judges remember

---

## 📊 FEATURE COMPARISON TABLE

| Feature | Current | Required | Priority | Est. Time |
|---------|---------|----------|----------|-----------|
| **LangGraph Orchestration** | ❌ | ✅ | CRITICAL | 2h |
| **Agent 1: News Monitor** | Partial | ✅ | HIGH | 1h |
| **Agent 2: Classifier** | Partial | ✅ | HIGH | 2h |
| **Agent 3A: Matcher** | Partial | ✅ | MEDIUM | 1h |
| **Agent 3B: Discovery** | ❌ | ✅ | CRITICAL | 4h |
| **Agent 4: Calculator** | Partial | ✅ | HIGH | 2h |
| **Agent 5: Validator** | ❌ | ✅ | CRITICAL | 2h |
| **Agent 6: Alerts** | Partial | ✅ | MEDIUM | 1h |
| **10-Factor Framework** | ❌ | ✅ | HIGH | 3h |
| **SEC Parser** | ❌ | ✅ | HIGH | 2h |
| **Website Scraper** | ❌ | ✅ | MEDIUM | 2h |
| **Multi-Source Fusion** | ❌ | ✅ | HIGH | 2h |
| **SQLite Migration** | ❌ | ✅ | MEDIUM | 4h |
| **Pre-population** | ❌ | ✅ | MEDIUM | 3h |
| **Agent Visualization** | ❌ | ✅ | CRITICAL | 3h |
| **Supply Chain Graph** | ❌ | ✅ | HIGH | 3h |
| **Reasoning Trail** | ❌ | ✅ | HIGH | 2h |
| **API Endpoints** | Partial | ✅ | MEDIUM | 2h |

**Total Estimated Time: ~42 hours**

---

## 🎯 TRANSFORMATION ROADMAP

### Phase 1: Core Architecture (Week 1)
**Goal:** Transform pipeline into LangGraph multi-agent system

```
Day 1-2: LangGraph Foundation
├─ Install dependencies
├─ Create state schema
├─ Build LangGraph workflow
└─ Test basic execution

Day 3-4: Critical Agents
├─ Build Agent 5 (Confidence Validator) ⭐
├─ Build Agent 3B (Dynamic Discovery) ⭐
├─ Test looping behavior
└─ Test dynamic discovery

Day 5: Agent Alignment
├─ Rebuild Agent 1 (News Monitor)
├─ Rebuild Agent 2 (Classifier + 10-factor)
├─ Create Agent 3A (Matcher)
├─ Rebuild Agent 4 (Calculator + TIER logic)
└─ Rebuild Agent 6 (Alert Generator)
```

### Phase 2: Intelligence Layer (Week 2)
**Goal:** Add multi-source fusion and 10-factor analysis

```
Day 1: Multi-Source Fusion
├─ Create SEC parser
├─ Create news relationship extractor
├─ Create website scraper
└─ Create fusion algorithm

Day 2: 10-Factor Framework
├─ Define all 10 factors
├─ Create detection keywords
├─ Update Agent 2
└─ Create factor impact calculator

Day 3-4: Database Migration
├─ Create SQLite schema
├─ Create database manager
├─ Migrate existing data
├─ Pre-populate 50 companies
└─ Update all services
```

### Phase 3: Frontend & Demo (Week 3)
**Goal:** Build demo-ready UI with wow factor

```
Day 1: Agent Visualization
├─ Create AgentVisualization component
├─ Implement animations
├─ Add progress bars
└─ Test with real workflow

Day 2: Advanced Components
├─ Create SupplyChainGraph (D3.js)
├─ Create ReasoningTrail
├─ Update ImpactAnalysis
└─ Test all components

Day 3: Integration
├─ Update Dashboard layout
├─ Connect to backend APIs
├─ Test WebSocket updates
└─ Polish UI/UX
```

### Phase 4: Testing & Demo Prep (Week 4)
**Goal:** Production-ready and demo-ready

```
Day 1: Testing
├─ End-to-end workflow tests
├─ Performance benchmarking
├─ Bug fixes
└─ Edge case handling

Day 2: Demo Preparation
├─ Create demo scenarios
├─ Record backup video
├─ Create pitch deck
└─ Rehearse 5x
```

---

## 🚀 QUICK WINS (Build These First)

### Quick Win 1: Agent 5 (Confidence Validator) - 2 hours
**Why:** Creates the agentic loop - the core innovation  
**Impact:** Transforms system from sequential to autonomous  
**Complexity:** Medium (decision logic + query generation)

### Quick Win 2: Agent 3B (Dynamic Discovery) - 4 hours
**Why:** The key differentiator - works for ANY company  
**Impact:** Enables 5,000+ companies vs. 50  
**Complexity:** High (multi-source integration)

### Quick Win 3: LangGraph Workflow - 2 hours
**Why:** Orchestrates all agents properly  
**Impact:** Enables conditional routing and looping  
**Complexity:** Medium (graph definition + compilation)

**Total: 8 hours → You'll have the core innovations working**

---

## 💡 ARCHITECTURE INSIGHTS

### Why LangGraph vs. Simple Pipeline?

**Simple Pipeline (Current):**
```python
def process_news(article):
    validated = validate(article)
    relationships = extract_relationships(validated)
    verified = verify_relationships(relationships)
    impacts = calculate_impacts(verified)
    explanation = generate_explanation(impacts)
    graph = build_graph(explanation)
    return graph
```
- ❌ Sequential only
- ❌ No state management
- ❌ No conditional routing
- ❌ No looping
- ❌ No agent autonomy

**LangGraph (Required):**
```python
workflow = StateGraph(SupplyChainState)

# Agents as nodes
workflow.add_node("news_monitor", agent_1)
workflow.add_node("classifier", agent_2)
workflow.add_node("matcher_fast", agent_3a)
workflow.add_node("matcher_discovery", agent_3b)
workflow.add_node("calculator", agent_4)
workflow.add_node("validator", agent_5)
workflow.add_node("alerts", agent_6)

# Conditional routing
workflow.add_conditional_edges(
    "matcher_fast",
    lambda state: "discovery" if state["cache_miss"] else "skip",
    {"discovery": "matcher_discovery", "skip": "calculator"}
)

# Looping logic
workflow.add_conditional_edges(
    "validator",
    lambda state: "loop" if state["confidence"] < 0.70 else "accept",
    {"accept": "alerts", "loop": "news_monitor"}
)

app = workflow.compile()
```
- ✅ Conditional routing (cache hit vs. discovery)
- ✅ Looping (confidence-based)
- ✅ Shared state across agents
- ✅ Agent autonomy (each makes decisions)
- ✅ Workflow visualization
- ✅ State inspection/debugging

### Why Agent 3B is Critical?

**Without Agent 3B (Static Database):**
```
User: "Analyze Rivian"
System: "Sorry, Rivian not in our database"

Limitation: Only works for 50 pre-loaded companies
Coverage: ~10% of retail investor portfolios
Scalability: Manual data curation required
```

**With Agent 3B (Dynamic Discovery):**
```
User: "Analyze Rivian"
System: "Discovering relationships for Rivian..."
  ├─ SEC 10-K: Panasonic (batteries), Samsung (batteries)
  ├─ News: Amazon (customer, 100k vehicle order)
  ├─ Website: Ford (partnership)
  └─ Confidence: 87%
System: "Analysis complete in 12.3 seconds"

Capability: Works for ANY of 5,000+ US companies
Coverage: ~95% of retail investor portfolios
Scalability: Fully automated, no manual work
```

**This is THE differentiator from competitors.**

### Why Agent 5 Creates "Agentic" Behavior?

**Without Agent 5 (No Looping):**
```
News: "TSMC production issue"
Agent 4: Calculates impact based on limited data
Confidence: 45% (LOW - not enough information)
System: Returns low-confidence result anyway
User: Gets unreliable analysis
```

**With Agent 5 (Confidence Looping):**
```
News: "TSMC production issue"
Agent 4: Calculates impact
Confidence: 45% (LOW)

Agent 5: "Confidence too low (< 70%), requesting more data"
  ├─ Gap: "No historical precedent for TSMC production issues"
  ├─ Gap: "Unclear if Apple has alternative suppliers"
  └─ Refined queries:
      - "TSMC historical production disruptions"
      - "Apple chip supplier alternatives"

🔄 LOOP BACK to Agent 1 with refined queries

Agent 1: Searches with refined queries
  └─ Found: 2021 TSMC halt precedent (Apple -8.2%, NVIDIA -6.7%)

Agent 4: Recalculates with precedent data
Confidence: 82% (ACCEPTABLE)

Agent 5: "Confidence meets threshold, finalizing"
System: Returns high-confidence result
User: Gets reliable analysis
```

**This autonomous decision-making is what makes it "agentic".**

---

## 🎬 FINAL CHECKLIST

### Before You Start Coding:
- [ ] Read full specification (MarketPulse-X v3.0 FINAL)
- [ ] Understand LangGraph basics
- [ ] Review current codebase
- [ ] Identify all gaps (use this document)
- [ ] Plan implementation order

### Core Architecture:
- [ ] LangGraph dependencies installed
- [ ] State schema created
- [ ] All 6 agents implemented per spec
- [ ] Conditional routing working
- [ ] Looping logic working
- [ ] End-to-end workflow tested

### Intelligence Layer:
- [ ] Agent 3B (Dynamic Discovery) working
- [ ] Agent 5 (Confidence Validator) working
- [ ] 10-factor framework implemented
- [ ] Multi-source fusion working
- [ ] SEC parser working
- [ ] Confidence scoring accurate

### Data Layer:
- [ ] SQLite migration complete
- [ ] All 8 tables created
- [ ] Relationship cache working (24h TTL)
- [ ] 50 companies pre-populated
- [ ] 200 relationships pre-loaded
- [ ] Historical events loaded

### Frontend:
- [ ] AgentVisualization component (animated)
- [ ] SupplyChainGraph component (D3.js)
- [ ] ReasoningTrail component
- [ ] ImpactAnalysis component
- [ ] Dashboard updated
- [ ] All components tested

### Demo Readiness:
- [ ] Demo scenarios prepared
- [ ] Backup video recorded
- [ ] Pitch deck created
- [ ] Q&A prepared
- [ ] Rehearsed 5x
- [ ] Can handle live judge portfolio

---

**Remember: The specification is the SINGLE SOURCE OF TRUTH.**

**Your current implementation is ~30% complete.**  
**Focus on the 3 critical gaps: Agent 3B, Agent 5, LangGraph.**

Last Updated: December 20, 2024
