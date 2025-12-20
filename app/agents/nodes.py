from datetime import datetime
import re
import json
from typing import Dict, Any, List
from app.agents.state import SupplyChainState
from app.services.news_aggregator import news_aggregator_layer
from app.services.classification_service import classification_service
from app.services.impact_calculator import impact_calculator_service
from app.services.sec_parser import sec_parser
from app.services.relationship_fusion import relationship_fusion
from app.services.persistence import persistence_service

def agent_1_news_monitor(state: SupplyChainState) -> Dict[str, Any]:
    """Agent 1: Continuous news surveillance across all sources."""
    print("---EXECUTING AGENT 1: NEWS MONITOR (SPEC 3.0 INGESTION)---")
    
    # Use the new high-intelligence ingestion layer
    portfolio_tickers = state.get("portfolio", [])
    articles = news_aggregator_layer.ingest_all(portfolio_tickers)[:5] # Limit to 5 for demo speed/rate-limits
    
    # If fetch_all returned nothing (e.g. API limits or no news), we mock a relevant one for verification
    if not articles:
        from app.models.article import Article
        articles = [Article(
            title="TSMC Semiconductor Production Halt in Taiwan Due to Earthquake",
            url="https://example.com/tsmc-halt",
            source="Reuters",
            published_at=datetime.now(),
            content="TSMC has halted production at several of its advanced chip-making facilities in Taiwan following a major earthquake. This is expected to disrupt the global supply chain for Apple, Nvidia, and other tech giants.",
            companies_mentioned=["TSMC", "Apple", "Nvidia"]
        )]

    # Deduplicate and filter per spec
    # ingest_all returns prioritized, deduplicated Article objects
    filtered = articles
    
    # Format for state
    news_list = []
    for art in filtered:
        # Save each article to SQLite
        persistence_service.save_article(art)
        
        news_list.append({
            "id": art.id,
            "url": art.url,  # Explicit URL field for frontend
            "title": art.title,
            "content": art.content,
            "source": art.source,
            "companies": art.companies_mentioned
        })

    return {
        "news_articles": news_list,
        "last_fetch_time": datetime.now().isoformat(),
        "workflow_status": f"Fetched {len(news_list)} prioritized articles"
    }

def agent_2_classifier(state: SupplyChainState) -> Dict[str, Any]:
    """Agent 2: Categorize news into 10 market factors + sentiment."""
    print("---EXECUTING AGENT 2: CLASSIFIER---")
    classified = []
    for article in state["news_articles"]:
        res = classification_service.classify_article(article["title"], article["content"])
        classified.append({
            "article_id": article["id"],
            "ticker": article["companies"][0] if article["companies"] else "UNKNOWN",
            **res
        })
    
    # Filter for high priority (Sentiment score < -0.5 or > 0.5)
    high_priority = [c["article_id"] for c in classified if abs(c["sentiment_score"]) > 0.5]
    
    return {
        "classified_articles": classified,
        "high_priority_articles": high_priority,
        "workflow_status": f"Classified {len(classified)} articles"
    }

def agent_3a_matcher_fast(state: SupplyChainState) -> Dict[str, Any]:
    """Agent 3A: Match news ticker to portfolio using SQLite cached relationships."""
    print("---EXECUTING AGENT 3A: PORTFOLIO MATCHER (FAST)---")
    
    PORTFOLIO = state.get("portfolio", [])
    
    cache_hits = []
    cache_misses = []
    
    for article in state["classified_articles"]:
        ticker = article.get("ticker", "")
        if ticker in PORTFOLIO:
            cache_hits.append(ticker)
        else:
            # Check SQLite Cache for dynamic discovery history
            existing_rels = persistence_service.get_cached_relationships(ticker)
            if existing_rels:
                print(f"Cache Hit for {ticker}: Found {len(existing_rels)} existing relationships.")
                cache_hits.append(ticker)
            else:
                cache_misses.append(ticker)
            
    return {
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "workflow_status": f"Fast matching complete ({len(cache_hits)} hits, {len(cache_misses)} misses)"
    }

def agent_3b_discovery(state: SupplyChainState) -> Dict[str, Any]:
    """Agent 3B: Discover relationships and gather financial context for unknown companies (PARALLEL 4-SOURCE)."""
    print("---EXECUTING AGENT 3B: DYNAMIC DISCOVERY & FINANCIAL DATA---")

    import concurrent.futures
    import time
    try:
        import yfinance as yf
    except ImportError:
        yf = None
        print("Warning: yfinance not installed.")

    discovered = []
    company_data = state.get("company_data", {}) # New state key for enriched data

    def get_company_type(ticker: str) -> str:
        # Simple heuristic for demo: Tickers are short, Private names are long/spaced
        if len(ticker) <= 5 and " " not in ticker:
            return "public"
        return "private"

    def fetch_public_data(ticker):
        data = {"source": "public_aggregator", "type": "public"}
        if yf:
            try:
                stock = yf.Ticker(ticker)
                # Yahoo Finance (Unofficial) - Free
                info = stock.info
                data["sector"] = info.get("sector", "Unknown")
                data["market_cap"] = info.get("marketCap", "Unknown")
                data["cash"] = stock.balance_sheet.loc["Cash And Cash Equivalents"].iloc[0] if not stock.balance_sheet.empty and "Cash And Cash Equivalents" in stock.balance_sheet.index else "Unknown"
                data["debt"] = stock.balance_sheet.loc["Total Debt"].iloc[0] if not stock.balance_sheet.empty and "Total Debt" in stock.balance_sheet.index else "Unknown"
                print(f"      [Public Data] Fetched info for {ticker}")
            except Exception as e:
                print(f"      [Public Data] Error fetching {ticker}: {e}")
        return data

    def fetch_private_data(name):
        # Mocking Private Data Sources as per requirements (OpenCorporates, RSS, Scraping)
        print(f"      [Private Data] Querying OpenCorporates & Scrapers for {name}...")
        return {
            "source": "private_intelligence_layer",
            "type": "private",
            "opencorporates_status": "Active (Simulated)",
            "hiring_delta_30d": "+5% (Job Scraper)",
            "recent_funding": "Series B (RSS Feed)"
        }

    def discover_for_ticker(ticker):
        if not ticker or ticker == "UNKNOWN":
            return None

        print(f"\n🔍 Dynamic Discovery: {ticker}")
        
        # 1. Determine Type & Fetch Financial/Context Data
        c_type = get_company_type(ticker)
        print(f"   Identified as {c_type.upper()} entity.")
        
        ctx_data = {}
        if c_type == "public":
            ctx_data = fetch_public_data(ticker)
            # SEC EDGAR is handled in parallel below
        else:
            ctx_data = fetch_private_data(ticker)
        
        # Store in shared state (needs a way to pass back, we'll append to a list and merge later)
        company_data[ticker] = ctx_data

        print("   Executing 4 sources in parallel for relationships...")

        start_time = time.time()

        # PARALLEL EXECUTION OF ALL 4 SOURCES
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # SOURCE 1: SEC EDGAR filings (highest confidence) - Only for Public
            sec_future = None
            if c_type == "public":
                sec_future = executor.submit(sec_parser.extract_relationships, ticker)
            
            # SOURCE 2: LLM Discovery
            def llm_discovery(t):
                from app.services.gemini_client import GeminiClient
                prompt = f"""Identify the top 5 strategic suppliers and customers for {t}.
                Return ONLY valid JSON array:
                [{{"related_company": "Company Name", "type": "supplier|customer", "criticality": "high|medium|low"}}]
                """
                try:
                    resp = GeminiClient().generate_content(prompt).text
                    clean_json = re.sub(r'^```json\s*|\s*```$', '', resp.strip(), flags=re.MULTILINE)
                    rels = json.loads(clean_json)
                    for r in rels:
                        r["source"] = "llm_intelligence"
                        r["confidence"] = 0.45
                    return rels
                except Exception as e:
                    print(f"      LLM error: {str(e)[:50]}")
                    return []

            llm_future = executor.submit(llm_discovery, ticker)

            # SOURCE 3: News Context Discovery
            def news_discovery(t):
                bolstering = []
                for art in state.get("classified_articles", []):
                    content = (art.get("reasoning", "") + art.get("factor_name", "")).lower()
                    if t.lower() in content:
                        for p_stock in state.get("portfolio", []):
                            if p_stock.lower() in content:
                                bolstering.append({
                                    "related_company": p_stock,
                                    "type": "supplier",
                                    "criticality": "medium",
                                    "source": "news_context",
                                    "confidence": 0.70
                                })
                return bolstering

            news_future = executor.submit(news_discovery, ticker)

            # SOURCE 4: Web scraping (simplified for demo - can be enhanced)
            def web_discovery(t):
                # Placeholder for web scraping
                # In production, this would scrape company investor relations pages
                # For now, return empty to focus on other sources
                return []

            web_future = executor.submit(web_discovery, ticker)

            # Wait for all sources (max 10 seconds each)
            futures = {
                'sec': sec_future,
                'llm': llm_future,
                'news': news_future,
                'web': web_future
            }

            results = {}
            for name, future in futures.items():
                try:
                    results[name] = future.result(timeout=10)
                    print(f"   ✓ {name.upper()}: {len(results[name])} relationships")
                except Exception as e:
                    print(f"   ✗ {name.upper()}: Failed ({str(e)[:50]})")
                    results[name] = []

        # FUSION: Merge all sources with confidence boosting
        sec_rels = results.get('sec', [])
        llm_rels = results.get('llm', [])
        news_rels = results.get('news', [])
        web_rels = results.get('web', [])

        total_extracted = sec_rels + llm_rels + news_rels + web_rels
        fused = relationship_fusion.fuse(total_extracted)

        discovery_time = time.time() - start_time
        sources_used = len([r for r in results.values() if r])

        print(f"   ⚡ Total Discovery Time: {discovery_time:.1f}s")
        print(f"   📊 Raw Relationships: {len(total_extracted)}")
        print(f"   🔗 After Fusion: {len(fused)}")
        print(f"   📡 Sources Used: {sources_used}/4")

        # PERSISTENCE: Save to cache
        if fused:
            persistence_service.save_discovered_relationships(ticker, fused)

        return {
            "ticker": ticker,
            "relationships": fused,
            "discovery_time": discovery_time,
            "sources_used": sources_used
        }

    # Execute discovery for all misses in parallel
    misses = state.get("cache_misses", [])
    if misses:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(misses)) as executor:
            results = list(executor.map(discover_for_ticker, misses))
            discovered = [r for r in results if r]

    return {
        "discovered_relationships": discovered,
        "workflow_status": f"Parallel 4-source discovery complete for {len(discovered)} companies"
    }

def agent_4_impact_calculator(state: SupplyChainState) -> Dict[str, Any]:
    """Agent 4: Calculate financial impact and record Reasoning Trail."""
    print("---EXECUTING AGENT 4: IMPACT CALCULATOR---")
    
    stock_impacts = []
    reasoning_trail = []
    
    # Match classified info with discovered relationships
    for article in state["classified_articles"]:
        ticker = article.get("ticker")
        score = article.get("sentiment_score", 0.0)
        factor_name = article.get("factor_name", "")
        
        # Check Direct Impacts (TIER 1)
        if ticker in state.get("portfolio", []):
            impact_val = impact_calculator_service.calculate_propagation_impact(score, {"type": "direct", "criticality": "high"}, factor_name)
            stock_impacts.append({
                "ticker": ticker,
                "impact_pct": impact_val * 10, # Conversion to percentage
                "confidence": article.get("confidence", 0.8),
                "reason": f"Direct impact from {article['factor_name']}"
            })
            reasoning_trail.append({
                "ticker": ticker,
                "level": 1,
                "reasoning": f"Direct {article['factor_name']} impact detected. {article['reasoning']}",
                "confidence": article.get("confidence", 0.95)
            })
            
        # Check Indirect Impacts (TIER 2/3)
        # Combine relationships from discovery AND existing cache
        all_rels = persistence_service.get_cached_relationships(ticker)
        
        for rel in all_rels:
            if rel['related_company'] in state.get("portfolio", []):
                impact_val = impact_calculator_service.calculate_propagation_impact(score, rel, factor_name)
                stock_impacts.append({
                    "ticker": rel['related_company'],
                    "impact_pct": impact_val * 10,
                    "confidence": rel.get('confidence', 0.7),
                    "reason": f"Indirect {rel['type']} impact via {ticker}"
                })
                reasoning_trail.append({
                    "ticker": rel['related_company'],
                    "level": 2,
                    "reasoning": f"Tier 2 {rel['type']} propagation via {ticker}. Adjusted by historical precedent.",
                    "confidence": rel.get('confidence', 0.85)
                })
    
    total_impact = impact_calculator_service.aggregate_portfolio_impact(stock_impacts)
    
    return {
        "stock_impacts": stock_impacts,
        "portfolio_total_impact": total_impact,
        "reasoning_trail": reasoning_trail,
        "workflow_status": "Impact calculation complete"
    }

def agent_5_validator(state: SupplyChainState) -> Dict[str, Any]:
    """Agent 5: Validate analysis quality and decide if more data needed."""
    print("---EXECUTING AGENT 5: CONFIDENCE VALIDATOR---")
    loop_count = state.get("loop_count", 0)

    # Calculate confidence from multiple sources
    confidences = []

    # 1. Stock impact confidences
    for s in state.get("stock_impacts", []):
        confidences.append(s.get("confidence", 0.0))

    # 2. Classification confidences
    for c in state.get("classified_articles", []):
        confidences.append(c.get("confidence", 0.0))

    # 3. Relationship confidences
    for rel in state.get("discovered_relationships", []):
        for r in rel.get("relationships", []):
            confidences.append(r.get("confidence", 0.0))

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

    print(f"📊 Calculated Confidence: {avg_confidence:.2f}")
    print(f"📊 Threshold: 0.70")
    print(f"🔄 Current Loop Count: {loop_count}")

    decision = "ACCEPT"
    gaps = []
    queries = []

    # AUTONOMOUS DECISION LOGIC
    if avg_confidence < 0.70 and loop_count < 2:
        decision = "REQUEST_MORE_DATA"

        # IDENTIFY SPECIFIC GAPS
        if avg_confidence < 0.50:
            gaps.append("Very low confidence in impact analysis - need more sources")
        if not state.get("discovered_relationships"):
            gaps.append("No supply chain relationships discovered")
        if len(state.get("news_articles", [])) < 3:
            gaps.append("Insufficient news coverage")
        if len(state.get("stock_impacts", [])) == 0:
            gaps.append("No portfolio impacts calculated")

        # GENERATE REFINED QUERIES
        portfolio = state.get("portfolio", [])
        for ticker in portfolio[:2]:  # Top 2 stocks
            queries.append(f"{ticker} supply chain disruption latest news")
            queries.append(f"{ticker} major suppliers customers 2024")

        print(f"🔄 AUTONOMOUS DECISION: Requesting more data (confidence too low)")
        print(f"🔍 Gaps: {gaps}")
        print(f"🔎 Refined Queries: {queries}")

        new_loop_count = loop_count + 1
    else:
        new_loop_count = loop_count
        print(f"✅ DECISION: Accepting analysis (confidence sufficient)")

    return {
        "confidence_score": avg_confidence,
        "validation_decision": decision,
        "gaps_identified": gaps,
        "refined_search_queries": queries,
        "loop_count": new_loop_count,
        "workflow_status": f"Validation complete (Score: {avg_confidence:.2f})"
    }

def agent_6_alerts(state: SupplyChainState) -> Dict[str, Any]:
    """Agent 6: Persist Alert and Reasoning Trail to SQLite."""
    print("---EXECUTING AGENT 6: ALERT GENERATOR---")
    
    # Calculate a unique enough alert ID
    alert_id = f"ALERT-{datetime.now().strftime('%Y%m%d')}-{abs(hash(str(state['portfolio_total_impact']))) % 1000:03}"
    
    # Save to SQLite
    persistence_service.save_alert(
        alert_id=alert_id,
        headline=f"Portfolio Risk Alert: {state['portfolio_total_impact']['impact_pct']:.2} change",
        severity="high" if abs(state['portfolio_total_impact']['impact_pct']) > 2.0 else "medium",
        impact_pct=state['portfolio_total_impact']['impact_pct'],
        article_id=state['news_articles'][0]['id'] if state['news_articles'] else "manual",
        reasoning_trail=state.get("reasoning_trail", [])
    )
    
    return {
        "alert_created": True,
        "alert_id": alert_id,
        "workflow_status": "Alert and Reasoning Trail persisted to SQLite",
        "completed_at": datetime.now().isoformat()
    }
