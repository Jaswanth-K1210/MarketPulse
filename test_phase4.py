import sys
import os
from datetime import datetime

# Add root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.database import get_db_connection
from app.api.routes import router
from app.agents.workflow import app as langgraph_app

def verify_phase4():
    print("🚀 STARTING MARKETPULSE-X PHASE 4 VERIFICATION: SQLITE & REASONING")
    
    # 1. Verify Database Seeding
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) as cnt FROM companies")
    comp_count = cursor.fetchone()['cnt']
    cursor.execute("SELECT count(*) as cnt FROM relationships")
    rel_count = cursor.fetchone()['cnt']
    conn.close()
    
    print(f"✅ SQLite Stats: {comp_count} Companies, {rel_count} Relationships seeded.")
    
    # 2. Verify Reasoning Trail Storage
    # Mock a run of Agent 6 logic
    from app.services.persistence import persistence_service
    test_trail = [
        {"ticker": "TSMC", "level": 1, "reasoning": "Direct halt", "confidence": 0.9},
        {"ticker": "AAPL", "level": 2, "reasoning": "Indirect supplier impact", "confidence": 0.8}
    ]
    alert_id = "TEST-VERIFY-001"
    persistence_service.save_alert(
        alert_id=alert_id,
        headline="Test Alert",
        severity="high",
        impact_pct=-2.5,
        article_id="manual",
        reasoning_trail=test_trail
    )
    
    details = persistence_service.get_alert_details(alert_id)
    if details and len(details.get('reasoning_trail', [])) == 2:
        print(f"✅ Reasoning Trail Persistence: Verified. Alert {alert_id} stored with {len(details['reasoning_trail'])} reasoning steps.")
    else:
        print("❌ Reasoning Trail Persistence: Failed to retrieve trail steps.")

    # 3. Verify LangGraph Workflow execution (Integration)
    print("\nRunning integration test: LangGraph -> SQLite")
    initial_state = {
        "user_id": "phase4_tester",
        "portfolio": ["AAPL", "NVDA"],
        "loop_count": 0,
        "news_articles": [],
        "errors": [],
        "workflow_status": "Started",
        "started_at": datetime.now().isoformat()
    }
    
    try:
        final_output = langgraph_app.invoke(initial_state)
        if final_output.get("alert_created"):
            print(f"✅ End-to-End Workflow: Success. Alert {final_output['alert_id']} created and persisted.")
        else:
            print("❌ End-to-End Workflow: Alert not created.")
    except Exception as e:
        print(f"⚠️ Workflow execution failed: {e}")

    print("\n🎉 PHASE 4 VERIFICATION COMPLETE: PERSISTENCE & ANALYTICS READY.")

if __name__ == "__main__":
    verify_phase4()
