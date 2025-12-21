import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.services.database import get_db_connection
from app.models.article import Article

logger = logging.getLogger(__name__)

class PersistenceService:
    def __init__(self):
        pass

    # --- COMPANY MANAGEMENT ---
    def get_portfolio_stocks(self) -> List[str]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM companies WHERE is_portfolio = 1")
        rows = cursor.fetchall()
        conn.close()
        return [row['ticker'] for row in rows]

    def get_all_tracked_tickers(self) -> List[str]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM companies")
        rows = cursor.fetchall()
        conn.close()
        return [row['ticker'] for row in rows]

    # --- RELATIONSHIP CACHING ---
    def get_cached_relationships(self, ticker: str) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT target_ticker, relationship_type, criticality, confidence 
            FROM relationships 
            WHERE source_ticker = ?
        """, (ticker,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "related_company": row['target_ticker'],
            "type": row['relationship_type'],
            "criticality": row['criticality'],
            "confidence": row['confidence']
        } for row in rows]

    def save_discovered_relationships(self, source_ticker: str, relationships: List[Dict]):
        conn = get_db_connection()
        cursor = conn.cursor()
        for rel in relationships:
            cursor.execute("""
                INSERT OR REPLACE INTO relationships 
                (source_ticker, target_ticker, relationship_type, criticality, confidence, source_discovery, last_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                source_ticker, 
                rel['related_company'], 
                rel['type'], 
                rel['criticality'], 
                rel.get('confidence', 0.8),
                rel.get('source', 'dynamic_discovery'),
                datetime.now()
            ))
        conn.commit()
        conn.close()

    # --- ARTICLE PERSISTENCE ---
    def save_article(self, article: Article):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO articles 
            (id, title, url, source, content, published_at, priority, relevance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article.id, article.title, article.url, article.source, 
            article.content, article.published_at, article.priority, article.relevance
        ))
        conn.commit()
        conn.close()

    def get_recent_articles(self, limit: int = 10) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles ORDER BY published_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_articles_for_portfolio(self, tickers: List[str], limit: int = 10) -> List[Dict]:
        """Get articles that mention any of the portfolio companies."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query to find articles mentioning any ticker
        placeholders = ' OR '.join([f"(title LIKE ? OR content LIKE ? OR reasoning LIKE ?)" for _ in tickers])
        query = f"SELECT * FROM articles WHERE {placeholders} ORDER BY published_at DESC LIMIT ?"
        
        # Create parameters: for each ticker, we need 3 wildcards
        params = []
        for ticker in tickers:
            search_term = f"%{ticker}%"
            params.extend([search_term, search_term, search_term])
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Add affected_companies field
        articles = []
        for row in rows:
            article = dict(row)
            affected = []
            text = f"{article.get('title', '')} {article.get('content', '')} {article.get('reasoning', '')}".upper()
            for ticker in tickers:
                if ticker.upper() in text:
                    affected.append(ticker.upper())
            article['affected_companies'] = affected
            articles.append(article)
        
        return articles

    # --- ALERT & REASONING TRAIL ---
    def save_alert(self, alert_id: str, headline: str, severity: str, impact_pct: float, article_id: str,
                   reasoning_trail: List[Dict], source_urls: List[str] = None, ai_analysis: str = None, full_reasoning: str = None):
        conn = get_db_connection()
        cursor = conn.cursor()

        # Save Alert with new fields
        cursor.execute("""
            INSERT OR REPLACE INTO alerts
            (id, headline, severity, impact_pct, trigger_article_id, source_urls, ai_analysis, full_reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (alert_id, headline, severity, impact_pct, article_id,
              json.dumps(source_urls or []), ai_analysis or "", full_reasoning or "", datetime.now()))

        # Save Reasoning Trail (Impact Analysis)
        for step in reasoning_trail:
            cursor.execute("""
                INSERT INTO impact_analysis (alert_id, ticker, impact_level, reasoning, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (alert_id, step['ticker'], step['level'], step['reasoning'], step.get('confidence', 0.9)))

        conn.commit()
        conn.close()

    def get_alerts(self, limit: int = 20) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()

        # Parse JSON fields
        alerts = []
        for row in rows:
            alert = dict(row)
            # Parse source_urls from JSON
            if 'source_urls' in alert and alert['source_urls']:
                try:
                    alert['source_urls'] = json.loads(alert['source_urls'])
                except:
                    alert['source_urls'] = []
            else:
                alert['source_urls'] = []
            alerts.append(alert)

        return alerts

    def get_alert_details(self, alert_id: str) -> Dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        alert = cursor.fetchone()
        if not alert:
            conn.close()
            return None
            
        cursor.execute("SELECT * FROM impact_analysis WHERE alert_id = ?", (alert_id,))
        trail = cursor.fetchall()
        conn.close()
        
        res = dict(alert)
        res['reasoning_trail'] = [dict(t) for t in trail]
        return res

    def ensure_company_exists(self, ticker: str, sector: str = "Technology", market_cap: str = "Unknown"):
        """Ensures a company record exists, creating it if necessary."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT ticker FROM companies WHERE ticker = ?", (ticker,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO companies (ticker, name, sector, market_cap, is_portfolio)
                    VALUES (?, ?, ?, ?, ?)
                """, (ticker, ticker, sector, market_cap, 0)) # Default is_portfolio to 0, updated separately if needed
                conn.commit()
                logger.info(f"Created new company record for {ticker}")
        except Exception as e:
            logger.error(f"Error ensuring company existence: {e}")
        finally:
            conn.close()

    def get_all_relationships(self, limit: int = 100) -> List[Dict]:
        """Get all relationships for graph visualization."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT source_ticker, target_ticker, relationship_type, criticality 
            FROM relationships 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self) -> Dict:
        """Get system statistics."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        cursor.execute("SELECT COUNT(*) as count FROM alerts")
        stats['active_alerts'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM companies WHERE is_portfolio = 1")
        stats['watched_companies'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM articles")
        stats['articles_processed'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM relationships")
        stats['relationships_mapped'] = cursor.fetchone()['count']
        
        conn.close()
        return stats

persistence_service = PersistenceService()
