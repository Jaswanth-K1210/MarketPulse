
import sqlite3
import json
import uuid
from datetime import datetime

DB_PATH = "app/data/marketpulse.db"

def seed_mock_alert():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we already have this alert
    cursor.execute("SELECT id FROM alerts WHERE headline LIKE '%TSMC Production Delays%'")
    if cursor.fetchone():
        print("Mock alert already exists.")
        conn.close()
        return

    alert_id = str(uuid.uuid4())
    headline = "Report: TSMC Production Delays May Affect Apple's iPhone 16 Rollout"
    severity = "high"
    impact_pct = -3.4
    article_id = "https://example.com/mock-news-tsmc"
    
    source_urls = ["https://bloomberg.com/technology", "https://reuters.com/business"]
    
    ai_analysis = """**Impact Analysis for AAPL**

**News Event:** TSMC reports potential 2-week delay in 3nm chip production due to equipment calibration issues.
**Impact Mechanism:** Supply Chain Constraint -> Reduced Inventory -> Delayed Product Launch
**Estimated Impact:** -3.4% on projected quarterly revenue.

**Reasoning:**
TSMC is the exclusive supplier for Apple's A17/A18 chips. A 2-week delay typically cascades into a 4-6 week retail delay due to shipping and assembly logistics. This threatens the critical Holiday Q4 window.
"""

    full_reasoning = ai_analysis

    # Insert Alert
    cursor.execute("""
        INSERT INTO alerts
        (id, headline, severity, impact_pct, trigger_article_id, source_urls, ai_analysis, full_reasoning, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (alert_id, headline, severity, impact_pct, article_id,
          json.dumps(source_urls), ai_analysis, full_reasoning, datetime.now()))

    # Insert Impact Analysis (The Chain)
    chain_steps = [
        {
            "tier": 1, 
            "level": 1,
            "ticker": "TSMC",
            "reasoning": "Manufacturing Delay: 3nm production calibration issues causing 14-day halt.",
            "confidence": 0.95
        },
        {
            "tier": 2, 
            "level": 2,
            "ticker": "FOXA", # Foxconn
            "reasoning": "Assembly Bottleneck: Foxconn idles assembly lines awaiting logic boards.",
            "confidence": 0.85
        },
        {
            "tier": 3, 
            "level": 3,
            "ticker": "AAPL",
            "reasoning": "Revenue Risk: iPhone 16 launch volume constrained by 15-20%, risking Q4 guidance miss.",
            "confidence": 0.90
        }
    ]

    for step in chain_steps:
        cursor.execute("""
            INSERT INTO impact_analysis (alert_id, ticker, impact_level, reasoning, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (alert_id, step['ticker'], step['level'], step['reasoning'], step['confidence']))

    conn.commit()
    conn.close()
    print(f"✅ Successfully seeded mock alert: {alert_id}")

if __name__ == "__main__":
    seed_mock_alert()
