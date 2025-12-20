import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agents.workflow import app

def run_phase1_test():
    print("🚀 STARTING MARKETPULSE-X PHASE 1 TEST: CORE ORCHESTRATION")
    
    # 1. Initialize Starting State
    initial_state = {
        "user_id": "user_demo_1",
        "portfolio": ["AAPL", "NVDA"],
        "loop_count": 0,
        "news_articles": [],
        "errors": [],
        "workflow_status": "Started",
        "started_at": datetime.now().isoformat()
    }
    
    # 2. Execute the Workflow
    # LangGraph apps are invoked with the initial state
    print("\n--- INVOCATION START ---")
    final_output = app.invoke(initial_state)
    print("--- INVOCATION END ---\n")
    
    # 3. Validation
    success = True
    
    print("📋 VALIDATION RESULTS:")
    
    # Verify Agent 1 execution
    if final_output.get("news_articles"):
        print("✅ Agent 1: News Monitoring articles found.")
    else:
        print("❌ Agent 1: News Monitoring failed to populate news_articles.")
        success = False
        
    # Verify Agent 3B discovery (triggered because we hardcoded a cache miss)
    if final_output.get("discovered_relationships"):
        print("✅ Agent 3B: Dynamic Discovery triggered successfully.")
    else:
        print("❌ Agent 3B: Dynamic Discovery was not triggered.")
        success = False
        
    # Verify Agent 5 looping (triggered because loop_count increases and decision was set to loop)
    # Note: In nodes.py, we set confidence to 0.85 and decision to ACCEPT on loop_count=1
    if final_output.get("loop_count") > 0:
        print(f"✅ Agent 5: Agentic Loop executed successfully (Loop count: {final_output['loop_count']}).")
    else:
        print("❌ Agent 5: Agentic Loop failed to execute.")
        success = False
        
    # Verify Agent 6 completion
    if final_output.get("alert_created"):
        print("✅ Agent 6: Alert generation complete.")
    else:
        print("❌ Agent 6: Alert generation failed.")
        success = False
        
    if success:
        print("\n🎉 PHASE 1 TEST PASSED: ALL ORCHESTRATION LOGIC VERIFIED.")
    else:
        print("\n💥 PHASE 1 TEST FAILED: CHECK LOGS FOR DETAILS.")

if __name__ == "__main__":
    run_phase1_test()
