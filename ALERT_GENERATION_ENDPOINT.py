@router.post("/analyze-news-for-alerts")
async def analyze_news_for_alerts(background_tasks: BackgroundTasks):
    """Analyze current news articles and generate alerts for portfolio impacts."""
    
    def generate_alerts_from_news():
        """Background task to analyze news and create alerts"""
        try:
            from app.services.gemini_client import GeminiClient
            from app.services.database import get_db_connection
            import uuid
            
            logger.info("🔍 Starting news analysis for alert generation...")
            
            # Get portfolio
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker, company_name FROM holdings")
            portfolio = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if not portfolio:
                logger.warning("No portfolio found, skipping alert generation")
                return
            
            # Get recent articles (from our multi-source feed)
            from app.services.news_aggregator import NewsIngestionLayer
            news_layer = NewsIngestionLayer()
            tickers = [p['ticker'] for p in portfolio]
            query = " OR ".join(tickers)
            
            articles = []
            articles.extend(news_layer.fetch_news_api(query) or [])
            articles.extend(news_layer.fetch_finnhub(query) or [])
            
            logger.info(f"📰 Analyzing {len(articles)} articles for portfolio impact...")
            
            # Analyze each article with Gemini
            gemini = GeminiClient()
            alerts_generated = 0
            
            for article in articles[:5]:  # Limit to 5 most recent
                title = article.get('title', '')
                content = article.get('content', '')
                
                # Check if article mentions portfolio companies
                mentioned_companies = []
                for p in portfolio:
                    if p['ticker'] in f"{title} {content}".upper():
                        mentioned_companies.append(p)
                
                if not mentioned_companies:
                    continue
                
                # Ask Gemini to analyze impact
                prompt = f"""Analyze this news article for investment impact:

Title: {title}
Content: {content}

Portfolio companies mentioned: {', '.join([c['company_name'] for c in mentioned_companies])}

Provide:
1. Impact assessment (positive/negative/neutral)
2. Severity (high/medium/low)
3. Brief reasoning (2-3 sentences)
4. Estimated impact percentage (-10% to +10%)

Return JSON: {{"impact": "positive/negative/neutral", "severity": "high/medium/low", "reasoning": "...", "impact_pct": 0.0}}
"""
                
                try:
                    response = gemini.generate_content(prompt)
                    import json, re
                    clean = re.sub(r'```json\\s*|\\s*```', '', response.text.strip())
                    analysis = json.loads(clean)
                    
                    # Create alert for each affected company
                    for company in mentioned_companies:
                        alert_id = str(uuid.uuid4())
                        
                        headline = f"{analysis['severity'].upper()}: {title[:80]}"
                        
                        # Save to database
                        persistence_service.save_alert(
                            alert_id=alert_id,
                            headline=headline,
                            severity=analysis['severity'],
                            impact_pct=analysis.get('impact_pct', 0),
                            article_id=article.get('url', ''),
                            reasoning_trail=[{
                                "agent": "News Analyzer",
                                "reasoning": analysis['reasoning'],
                                "source": article.get('source', 'Unknown'),
                                "url": article.get('url', ''),
                                "confidence": 0.75
                            }]
                        )
                        
                        alerts_generated += 1
                        logger.info(f"✅ Generated alert for {company['ticker']}: {headline}")
                
                except Exception as e:
                    logger.error(f"Error analyzing article: {e}")
                    continue
            
            logger.info(f"🎉 Alert generation complete! Created {alerts_generated} alerts")
            
        except Exception as e:
            logger.error(f"❌ Alert generation failed: {e}")
    
    # Run in background
    background_tasks.add_task(generate_alerts_from_news)
    
    return {
        "status": "started",
        "message": "Analyzing news articles for portfolio impacts in background..."
    }
