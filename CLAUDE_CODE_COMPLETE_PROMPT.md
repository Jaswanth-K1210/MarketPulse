# 🚀 MarketPulse-X: Complete Claude Code Prompt (Multi-Agent System)

Copy this entire prompt and paste it into Claude Code. Claude will understand everything and build your complete system!

---

```
🤖 BUILD MARKETPULSE-X: MULTI-AGENT PORTFOLIO INTELLIGENCE SYSTEM

YOU ARE BUILDING:
- Real-time supply chain monitoring system for Jaswanth (Portfolio Manager)
- Deterministic pipeline for automated alerts
- Multi-agent system for intelligent Q&A exploraxtion
- React frontend with real-time dashboard

TECH STACK (Important - Follow Exactly):

BACKEND:
- Python 3.10+
- FastAPI (async REST API framework)
- Uvicorn (ASGI server)
- Python-dotenv (environment variables)
- Pydantic 2.5+ (data validation)
- Google Generative AI (Gemini API)
- APScheduler (background tasks)
- Feedparser (RSS parsing)
- Requests + BeautifulSoup4 (web scraping)
- python-socketio (WebSocket)
- Pytest (testing)

FRONTEND:
- React 18
- TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Shadcn UI (components)
- Zustand (state management)
- Socket.io-client (WebSocket)
- Recharts (charts)
- React Flow (graph visualization)
- Lucide React (icons)
- Axios (HTTP client)
- React Router v6 (routing)

DATABASE (Optional):
- JSON files (for quick start)
- OR Supabase PostgreSQL (for production)

API KEYS REQUIRED:
1. GEMINI_API_KEY: https://makersuite.google.com/app/apikey (60 req/min free)
2. NEWSAPI_KEY: https://newsapi.org (100 req/day free)
3. NEWSDATA_IO_KEY: https://newsdata.io (200 req/day free)

═════════════════════════════════════════════════════════════════════════════

USER PROFILE - JASWANTH (Portfolio Manager)

Portfolio Holdings (5 companies):
1. Apple Inc. (AAPL) - 150 shares
2. NVIDIA Corp (NVDA) - 80 shares
3. AMD (AMD) - 120 shares
4. Intel (INTC) - 200 shares
5. Broadcom (AVGO) - 60 shares

Supply Chain Companies to Monitor (5):
1. TSMC (Taiwan Semiconductor Manufacturing)
2. Samsung Electronics
3. MediaTek
4. ARM Holdings
5. ASML Holding

═════════════════════════════════════════════════════════════════════════════

SYSTEM ARCHITECTURE (4 LAYERS):

LAYER 1: Continuous News Monitoring (Background, every 5 minutes)
- Fetch from: Google News RSS, NewsAPI, NewsData.io, Times of India, BBC, Reuters
- Detect: Any mention of 10 tracked companies
- Store: Articles in database

LAYER 2: Deterministic Pipeline (Process each article)
- EventValidator → RelationExtractor → RelationVerifier → 
- CascadeInferencer → ImpactScorer → ExplanationGenerator → 
- GraphOrchestrator → Generate Alerts → WebSocket Broadcast

LAYER 3: Multi-Agent Exploration (On-demand, user-triggered)
- User asks question via chat
- Orchestrator routes to specialized agents:
  * Analyst Agent (market analysis)
  * Researcher Agent (data gathering)
  * Calculator Agent (impact calculation)
  * Synthesizer Agent (combines findings)
- Each agent uses specialized tools
- Returns: Comprehensive answer with evidence

LAYER 4: API & Frontend
- REST API endpoints
- WebSocket for real-time alerts
- React dashboard with alerts, portfolio, agent chat
- Agent workflow visualization

═════════════════════════════════════════════════════════════════════════════

BACKEND: 18 FILES TO BUILD (UMESH)

FILE 1: app/main.py
─────────────────
FastAPI setup with:
- CORS enabled for http://localhost:3000
- APScheduler for background news monitoring
- WebSocket handler mounting
- Dependency injection setup
- Error handlers
- Startup/shutdown events

FILE 2: app/config.py
─────────────────────
- Load environment variables (GEMINI_API_KEY, NEWSAPI_KEY, NEWSDATA_IO_KEY)
- Validate API keys are present
- Define constants:
  * TRACKED_COMPANIES = ["Apple", "NVIDIA", "AMD", "Intel", "Broadcom", "TSMC", "Samsung", "MediaTek", "ARM", "ASML"]
  * NEWS_SOURCES = ["google_news", "newsapi", "newsdata", "times_of_india", "bbc", "reuters"]
  * PORTFOLIO_COMPANIES = ["AAPL", "NVDA", "AMD", "INTC", "AVGO"]
  * SUPPLY_CHAIN_COMPANIES = ["TSMC", "Samsung", "MediaTek", "ARM", "ASML"]
- Logging configuration
- API rate limit settings
- Database URL configuration

FILE 3: services/gemini_client.py
─────────────────────────────────
Wrapper around google-generativeai for:
- extract_relationships(article_text) → {from_company, to_company, relationship_type}
- infer_cascade(event, companies) → {cascade_chain, affected_companies}
- generate_explanation(event, companies, impacts) → String
- answer_agent_question(context, question, tool_results) → String
- Error handling for API failures
- Logging of all API calls

FILE 4: services/news_aggregator.py
────────────────────────────────────
NewsAggregator class with:
- fetch_from_google_news_rss() → List[Article]
- fetch_from_newsapi() → List[Article]
- fetch_from_newsdata_io() → List[Article]
- scrape_times_of_india() → List[Article]
- scrape_bbc() → List[Article]
- scrape_reuters() → List[Article]
- deduplicate_articles(articles) → List[Article]
- contains_tracked_company(article) → Boolean
- Background task: run_aggregation() every 5 minutes
- Returns queue of new articles mentioning tracked companies

FILE 5: services/pipeline.py
────────────────────────────
Processing pipeline with 7 stages:
1. event_validator(article) → validated_article or None
2. relation_extractor(article) → {company_pairs, relationships}
3. relation_verifier(relationships) → {verified_relationships, confidence_scores}
4. cascade_inferencer(relationships) → {cascade_chain, affected_companies}
5. impact_scorer(cascade_chain, portfolio) → {impact_percent, impacted_holdings}
6. explanation_generator(event, chain, impact) → String
7. graph_orchestrator(event, companies, relationships) → JSON graph
Returns: Alert object with all fields populated

FILE 6: services/database.py
────────────────────────────
Database abstraction layer with:
- save_article(article) → None
- save_alert(alert) → None
- save_relationship(relationship) → None
- get_all_alerts() → List[Alert]
- get_alerts_for_company(company) → List[Alert]
- get_knowledge_graph(alert_id) → JSON
- Option: JSON file storage (quick start) or PostgreSQL

FILE 7: models/article.py
─────────────────────────
Article dataclass:
- id, title, url, source, published_at, content
- companies_mentioned: List[String]
- processed_at: DateTime
- event_type: String (production_halt, acquisition, partnership, etc.)

FILE 8: models/alert.py
──────────────────────
Alert dataclass:
- id, type (portfolio_impact or opportunity)
- severity (high, medium, low)
- trigger_article_id
- affected_holdings: List[{company, quantity, impact_percent, impact_dollar}]
- target_company: String
- impact_percent, impact_dollar: Float
- recommendation: String (HOLD, SELL, BUY)
- confidence: Float (0-1)
- chain: JSON ({level_1, level_2, level_3})
- sources: List[String] (URLs)
- created_at: DateTime
- explanation: String

FILE 9: models/knowledge_graph.py
──────────────────────────────────
KnowledgeGraph dataclass:
- nodes: List[{id, type, label}] (type: event, company, impact)
- edges: List[{from, to, type, confidence}]
- alert_id: String

FILE 10: api/routes.py
──────────────────────
REST endpoints:
- GET /health → {"status": "ok"}
- POST /portfolio → Store Jaswanth's portfolio
- GET /alerts → Recent alerts list
- GET /alerts/{alert_id} → Specific alert with details
- GET /graph/{alert_id} → Knowledge graph
- POST /agent-question → Multi-agent question
  * Request: {question: String, context: optional}
  * Response: {routing, agent_responses, final_response}
- GET /market-data/{company} → Stock price info

FILE 11: api/websocket.py
─────────────────────────
WebSocket handler:
- Handle connection/disconnection
- On alert generation: broadcast to all connected clients
- Message format: {type: "alert" or "opportunity", data: {...}}
- Support multiple simultaneous connections

FILES 12-18: MULTI-AGENT SYSTEM (7 files)
──────────────────────────────────────────

FILE 12: agents/base_agent.py
──────────────────────────────
BaseAgent abstract class:
- __init__(name, description, gemini_client)
- register_tools() → abstract method
- think(query) → Dict (decide which tools to use)
- act(thinking) → Dict (execute tools)
- observe(action_results) → String (analyze results)
- execute(query) → Full Think-Act-Observe cycle
- memory: List[Dict] (store past interactions)

FILE 13: agents/analyst_agent.py
─────────────────────────────────
AnalystAgent extends BaseAgent:
- Specializes in: Market fundamentals analysis
- Tools:
  * get_market_data(company) → {price, volatility, market_cap}
  * get_company_fundamentals(company) → {P/E, revenue, growth}
  * get_sector_trends(sector) → {sector_performance, volatility}
  * compare_companies(company1, company2) → {relative_metrics}
- think(): Decides which tools for market analysis
- act(): Executes tools, gathers market data
- observe(): Analyzes data, creates summary

FILE 14: agents/researcher_agent.py
────────────────────────────────────
ResearcherAgent extends BaseAgent:
- Specializes in: Information gathering & verification
- Tools:
  * search_news(query, timeframe) → List[Article]
  * search_supply_chain_data(company) → {suppliers, customers}
  * get_industry_reports(sector) → [Industry analysis]
  * verify_relationship(company1, company2) → {confidence}
  * search_company_announcements(company) → [Statements]
- think(): Decides what to search
- act(): Executes searches, verifies facts
- observe(): Summarizes findings with confidence

FILE 15: agents/calculator_agent.py
────────────────────────────────────
CalculatorAgent extends BaseAgent:
- Specializes in: Impact quantification & scenarios
- Tools:
  * calculate_cascade_impact(event, companies) → {impact_%}
  * estimate_stock_impact(company, impact_factor) → {price_change}
  * run_scenario(scenario_name, parameters) → {results}
  * calculate_correlation(company1, company2) → {correlation}
  * estimate_recovery_time(disruption_type) → {days/weeks}
- think(): Decides what calculations to run
- act(): Executes calculations
- observe(): Analyzes numeric results

FILE 16: agents/synthesizer_agent.py
─────────────────────────────────────
SynthesizerAgent extends BaseAgent:
- Specializes in: Orchestration & response synthesis
- Tools:
  * call_agent(agent_name, query) → {agent_response}
  * combine_findings(findings_list) → {synthesized}
  * assign_confidence(analysis, evidence) → {confidence_score}
  * cite_sources(findings) → {sources_list}
  * format_response(analysis, format_type) → {formatted}
- think(): Decides which other agents to call
- act(): Calls other agents, collects results
- observe(): Combines findings, creates final answer

FILE 17: agents/orchestrator.py
────────────────────────────────
AgentOrchestrator class:
- __init__(gemini_client)
- register_agent(agent) → Add to registry
- route_query(query) → {primary_agent, supporting_agents, reasoning}
- execute_query(query) → Full multi-agent execution:
  1. Route query to appropriate agents
  2. Execute primary agent
  3. Execute supporting agents
  4. Synthesize response
- Returns: {query, routing, agent_responses, final_response}

FILE 18: agents/agent_registry.py
──────────────────────────────────
AgentRegistry class:
- __init__(database, gemini_client)
- register_agent(agent) → Add to registry
- register_tool(tool_name, tool_function) → Add tool
- _register_tools() → Register all 20+ tools
- _register_agents() → Create all 4 agents
- get(tool_name) → Get tool by name
- get_agent(agent_name) → Get agent by name
- Tool implementations for all agents

═════════════════════════════════════════════════════════════════════════════

FRONTEND: 9 FILES TO BUILD (JASWANTH)

FILE 1: src/App.jsx
───────────────────
Main React app:
- Zustand store setup (alerts, portfolio, connected status)
- WebSocket connection initialization
- Routes: /dashboard, /alerts, /explore, /agents
- Global error boundary
- Loading state management

FILE 2: src/pages/Dashboard.jsx
────────────────────────────────
Main dashboard page:
- Show Jaswanth's portfolio (5 holdings)
- Portfolio summary: total value, % change
- Real-time alerts panel (latest 5)
- Opportunities panel
- Refresh buttons and timestamps

FILE 3: src/components/AlertCard.jsx
──────────────────────────────────────
Display single alert:
- Event title + timestamp
- Affected holdings with impact % and $
- Supply chain impact chain (visual)
- Recommendation (HOLD/SELL/BUY)
- Confidence score
- Evidence sources (clickable)
- "Ask More" button → Opens chat

FILE 4: src/components/PortfolioSummary.jsx
──────────────────────────────────────────────
Portfolio overview:
- Total portfolio value
- Total gain/loss
- 5 holdings with:
  * Company name
  * Quantity + price
  * Current value
  * Gain/loss % + $
  * Price sparkline chart

FILE 5: src/components/KnowledgeGraph.jsx
────────────────────────────────────────────
Visualize supply chain impact:
- Use React Flow for graph visualization
- Show: Event → Company A → Company B → Portfolio Impact
- Interactive nodes and edges
- Display relationship confidence scores
- Zoom/pan support
- Color-coded by impact level

FILE 6: src/components/AgentChat.jsx (UPDATED for multi-agent)
──────────────────────────────────────────────────────────────
Enhanced chat interface:
- Display user messages
- Show agent response with:
  * Main answer
  * Confidence score
  * Agents used
  * Evidence list
  * Sources
- Expandable agent details showing:
  * Each agent's thinking
  * Tools used
  * Findings
- Suggested questions buttons
- Loading state with "Agents thinking..."
- Error handling

FILE 7: src/components/AgentWorkflow.jsx (NEW)
───────────────────────────────────────────────
Visualize agent collaboration:
- Show Orchestrator decision
- Show which agents were activated
- Primary agent highlighted
- Supporting agents listed
- Final answer box
- Agent stats:
  * Number of agents active
  * Number of tools used
  * Process time

FILE 8: src/pages/Agents.jsx (NEW)
───────────────────────────────────
Agent capabilities page:
- Display all 4 agents with:
  * Agent icon
  * Agent name and description
  * Available tools list
- How Multi-Agent Works section:
  * 4-step process visualization
  * Numbered flow: Ask → Route → Collaborate → Answer
- Multi-agent benefits explanation

FILE 9: src/services/api.js
────────────────────────────
API client:
- axios instance configured for http://localhost:8000
- Methods:
  * setPortfolio(portfolio) → POST /portfolio
  * getAlerts() → GET /alerts
  * getAlert(id) → GET /alerts/{id}
  * getGraph(alertId) → GET /graph/{id}
  * askAgent(question, context) → POST /agent-question
    - Handles multi-agent response format
    - Extracts routing, agent_responses, final_response
  * getMarketData(company) → GET /market-data/{company}

═════════════════════════════════════════════════════════════════════════════

REQUIRED SETUP BEFORE BUILDING:

1. ENVIRONMENT SETUP
   Create .env file with:
   ```
   GEMINI_API_KEY=your_gemini_key_here
   NEWSAPI_KEY=your_newsapi_key_here
   NEWSDATA_IO_KEY=your_newsdata_key_here
   ENVIRONMENT=development
   DEBUG=True
   PORT=8000
   HOST=0.0.0.0
   FRONTEND_URL=http://localhost:3000
   LOG_LEVEL=INFO
   ```

2. PORTFOLIO DATA (for testing)
   ```json
   {
     "user_name": "Jaswanth",
     "portfolio": [
       {"company": "Apple Inc.", "ticker": "AAPL", "quantity": 150, "current_price": 198.75},
       {"company": "NVIDIA Corporation", "ticker": "NVDA", "quantity": 80, "current_price": 875.50},
       {"company": "Advanced Micro Devices", "ticker": "AMD", "quantity": 120, "current_price": 168.30},
       {"company": "Intel Corporation", "ticker": "INTC", "quantity": 200, "current_price": 36.45},
       {"company": "Broadcom Inc.", "ticker": "AVGO", "quantity": 60, "current_price": 795.20}
     ]
   }
   ```

3. COMPANY TRACKING CONSTANTS (hardcoded in config.py)
   ```python
   PORTFOLIO_COMPANIES = {
     "Apple": "AAPL",
     "NVIDIA": "NVDA",
     "AMD": "AMD",
     "Intel": "INTC",
     "Broadcom": "AVGO"
   }
   
   SUPPLY_CHAIN_COMPANIES = {
     "TSMC": "TSM",
     "Samsung": "SSNLF",
     "MediaTek": "MTCR",
     "ARM": "ARM",
     "ASML": "ASML"
   }
   ```

═════════════════════════════════════════════════════════════════════════════

BUILD ORDER:

PHASE 1: BACKEND INFRASTRUCTURE (6-8 hours)
──────────────────────────────────────────

1. Create project structure
2. app/config.py
3. app/main.py
4. models/ (article.py, alert.py, knowledge_graph.py)
5. services/gemini_client.py
6. services/news_aggregator.py
7. services/database.py
8. services/pipeline.py (CRITICAL - 7 stages)
9. api/routes.py
10. api/websocket.py
11. Test Layers 1-2 (deterministic pipeline)

PHASE 2: MULTI-AGENT SYSTEM (4-5 hours)
────────────────────────────────────────

12. agents/base_agent.py
13. agents/agent_registry.py (with tool implementations)
14. agents/analyst_agent.py
15. agents/researcher_agent.py
16. agents/calculator_agent.py
17. agents/synthesizer_agent.py
18. agents/orchestrator.py
19. Modify api/routes.py to add /agent-question endpoint
20. Test Layer 3 (multi-agent)

PHASE 3: FRONTEND (4-5 hours)
────────────────────────────

21. src/App.jsx setup
22. src/pages/Dashboard.jsx
23. src/components/PortfolioSummary.jsx
24. src/components/AlertCard.jsx
25. src/components/KnowledgeGraph.jsx
26. src/components/AgentChat.jsx (enhanced)
27. src/components/AgentWorkflow.jsx (NEW)
28. src/pages/Agents.jsx (NEW)
29. src/services/api.js
30. Test Layer 4 (API & Frontend)

PHASE 4: INTEGRATION & TESTING (2-3 hours)
───────────────────────────────────────────

31. End-to-end testing
32. WebSocket real-time testing
33. Multi-agent Q&A testing
34. UI/UX polish
35. Error handling & edge cases

═════════════════════════════════════════════════════════════════════════════

TESTING DATA (for quick testing):

Sample Article:
```json
{
  "id": "test_1",
  "title": "TSMC announces production halt due to power outage",
  "url": "https://example.com/tsmc-halt",
  "source": "Reuters",
  "published_at": "2025-01-15T10:30:00Z",
  "content": "Taiwan Semiconductor Manufacturing Company has announced a temporary production halt...",
  "companies_mentioned": ["TSMC", "Apple", "NVIDIA", "AMD"],
  "event_type": "production_halt"
}
```

Expected Alert Output:
```json
{
  "id": "alert_1",
  "type": "portfolio_impact",
  "severity": "high",
  "affected_holdings": [
    {"company": "Apple", "quantity": 150, "impact_percent": -2.1, "impact_dollar": -620.63},
    {"company": "NVIDIA", "quantity": 80, "impact_percent": -1.8, "impact_dollar": -1255.9}
  ],
  "impact_percent": -2.05,
  "recommendation": "HOLD",
  "confidence": 0.92,
  "chain": {
    "level_1": "TSMC halt",
    "level_2": "Apple & NVIDIA chip shortage",
    "level_3": "Portfolio -2.05%"
  },
  "sources": ["https://example.com/tsmc-halt"],
  "explanation": "TSMC halt reduces chip supplies..."
}
```

Expected Multi-Agent Response:
```json
{
  "query": "Will semiconductors be hit harder?",
  "routing": {
    "primary_agent": "analyst",
    "supporting_agents": ["researcher", "calculator"],
    "reasoning": "This requires market analysis + supply chain research + impact calculation"
  },
  "agent_responses": {
    "analyst": {
      "agent": "Analyst",
      "thinking": {
        "reasoning": "I need to analyze semiconductor sector volatility",
        "selected_tools": ["get_sector_trends", "compare_companies"],
        "parameters": {"sector": "semiconductors"}
      },
      "results": {"tools_executed": ["get_sector_trends"], "tool_results": {...}},
      "observation": "Semiconductor sector shows 3x higher volatility"
    },
    "researcher": {...},
    "calculator": {...}
  },
  "final_response": {
    "answer": "Yes, semiconductors face 85% impact vs 35% others. TSMC is critical.",
    "confidence": 0.92,
    "agents_used": ["analyst", "researcher", "calculator"],
    "evidence": [
      "TSMC supplies 100% of Apple A-chips",
      "Semiconductor sector 3x more volatile",
      "Recovery time: 3-4 weeks"
    ],
    "sources": ["Reuters", "Bloomberg"]
  }
}
```

═════════════════════════════════════════════════════════════════════════════

KEY IMPLEMENTATION NOTES:

1. ASYNC/AWAIT: Use async throughout for performance
2. ERROR HANDLING: Comprehensive try-catch blocks everywhere
3. LOGGING: Log all API calls, errors, and key decisions
4. VALIDATION: Use Pydantic for all data models
5. RATE LIMITING: Respect API rate limits (Gemini: 60/min, NewsAPI: 100/day)
6. DATABASE: Use JSON for quick start, can switch to PostgreSQL later
7. WEBSOCKET: Broadcast alerts to all connected clients
8. MULTI-AGENT: Each agent has Think-Act-Observe lifecycle
9. GEMINI API: Use structured JSON prompts for consistent responses
10. FRONTEND STATE: Use Zustand for global state (alerts, portfolio, connection)

═════════════════════════════════════════════════════════════════════════════

SUCCESS CRITERIA:

BACKEND:
✓ News monitoring runs every 5 minutes without errors
✓ Pipeline processes articles in <10 seconds
✓ Gemini API calls work for extraction, inference, explanation
✓ Portfolio impact calculations accurate
✓ WebSocket broadcasts alerts in real-time
✓ API endpoints respond correctly
✓ Multi-agent orchestrator routes queries correctly
✓ All 4 agents execute their tools successfully
✓ Synthesizer creates coherent final answers

FRONTEND:
✓ Connects to WebSocket successfully
✓ Receives and displays real-time alerts
✓ Shows portfolio summary with 5 holdings
✓ Knowledge graph visualizes supply chains
✓ Agent chat sends questions and displays responses
✓ Shows agent routing and reasoning
✓ Responsive on mobile/desktop
✓ Professional, clean UI
✓ Error handling for disconnects

INTEGRATION:
✓ End-to-end flow: News → Pipeline → Alert → Frontend
✓ User gets value within 30 seconds of event
✓ Multi-agent Q&A works smoothly
✓ Agent reasoning is transparent
✓ All errors handled gracefully
✓ Production-ready for deployment

═════════════════════════════════════════════════════════════════════════════

IMPORTANT REMINDERS:

1. UMESH: Focus on LOGIC and DATA PROCESSING (no UI work)
2. JASWANTH: Focus on UI/UX and USER EXPERIENCE (no backend work)
3. Both: Agree on API response formats (multi-agent format specified above)
4. Never commit .env file to git
5. Backend must run before frontend testing
6. Use detailed error messages for debugging
7. Test each file before moving to next
8. Run both servers in separate terminals:
   Terminal 1: cd backend && python run.py
   Terminal 2: cd frontend && npm run dev

═════════════════════════════════════════════════════════════════════════════

DEPLOYMENT NOTES:

Backend deployment: Python 3.10+, FastAPI, Uvicorn
Frontend deployment: Vite build → Static hosting (Vercel, Netlify)
Database: Supabase PostgreSQL (optional, starts with JSON)
Environment: Production .env with real API keys

═════════════════════════════════════════════════════════════════════════════

YOU'RE READY! 🚀

This is a complete, production-grade multi-agent system for real-time supply chain monitoring.
Build it step by step following the build order.
Test each component before moving forward.
You've got this! 💪
```

---

END OF PROMPT FOR CLAUDE CODE

Copy everything between the triple backticks above and paste into Claude Code.
Claude will build your entire MarketPulse-X system!
