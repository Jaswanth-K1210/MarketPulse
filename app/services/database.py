import sqlite3
import os
import logging
from app.config import DATA_DIR

logger = logging.getLogger(__name__)

DATABASE_PATH = os.path.join(DATA_DIR, "marketpulse.db")

def init_db():
    """Initialize the SQLite database with the 8-table schema from spec v3.0."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 1. Companies Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sector TEXT,
            is_portfolio INTEGER DEFAULT 0,
            last_updated DATETIME
        )
    ''')

    # 2. News Articles Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT UNIQUE,
            source TEXT,
            content TEXT,
            published_at DATETIME,
            priority INTEGER,
            relevance TEXT,
            factor_type INTEGER,
            sentiment_score REAL
        )
    ''')

    # 3. Supply Chain Relationships Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_ticker TEXT NOT NULL,
            target_ticker TEXT NOT NULL,
            relationship_type TEXT, -- supplier, customer, partner
            criticality TEXT, -- critical, high, medium, low
            confidence REAL,
            source_discovery TEXT, -- sec_edgar, news, llm, manual
            last_verified DATETIME,
            UNIQUE(source_ticker, target_ticker, relationship_type)
        )
    ''')

    # 4. Alerts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            headline TEXT NOT NULL,
            severity TEXT,
            impact_pct REAL,
            trigger_article_id TEXT,
            source_urls TEXT,
            ai_analysis TEXT,
            full_reasoning TEXT,
            created_at DATETIME,
            status TEXT DEFAULT 'active'
        )
    ''')

    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE alerts ADD COLUMN source_urls TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE alerts ADD COLUMN ai_analysis TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE alerts ADD COLUMN full_reasoning TEXT")
    except:
        pass

    # 5. Impact Analysis Table (The Reasoning Trail)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS impact_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT,
            ticker TEXT,
            impact_level INTEGER, -- 1=Direct, 2=Indirect, etc
            reasoning TEXT,
            confidence REAL,
            FOREIGN KEY(alert_id) REFERENCES alerts(id)
        )
    ''')

    # 6. Portfolio Holdings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            ticker TEXT,
            company_name TEXT,
            quantity REAL,
            avg_price REAL,
            current_price REAL,
            FOREIGN KEY(ticker) REFERENCES companies(ticker)
        )
    ''')


    # 7. Agent Discovery Logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            task TEXT,
            result_summary TEXT,
            timestamp DATETIME
        )
    ''')

    # 8. System Config / Cache Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache_metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            expires_at DATETIME
        )
    ''')

    # 9. Historical Precedents Table (Spec 3.0)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_precedents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            event_name TEXT,
            date_occurred DATETIME,
            impact_magnitude REAL, -- 1.0 (average), 2.0 (high), etc
            description TEXT
        )
    ''')

    conn.commit()
    conn.close()
    logger.info(f"SQLite Database initialized at {DATABASE_PATH}")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == "__main__":
    init_db()
