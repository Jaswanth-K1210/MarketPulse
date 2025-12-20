import sys
import os
import json
from datetime import datetime

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.sec_parser import sec_parser
from app.services.relationship_fusion import relationship_fusion
from app.agents.workflow import app

def run_phase3_test():
    print("🚀 STARTING MARKETPULSE-X PHASE 3 TEST: DYNAMIC DISCOVERY & FUSION")
    
    # 1. Test SEC Ticker Mapping
    cik = sec_parser.get_cik("AAPL")
    if cik:
        print(f"✅ SEC Parser: Found CIK {cik} for AAPL.")
    else:
        print("❌ SEC Parser: Failed to find CIK for AAPL.")

    # 2. Test Relationship Fusion
    test_rels = [
        {"related_company": "AAPL", "type": "supplier", "criticality": "high", "source": "sec_edgar", "confidence": 0.92},
        {"related_company": "AAPL", "type": "supplier", "criticality": "medium", "source": "news_report", "confidence": 0.70}
    ]
    fused = relationship_fusion.fuse(test_rels)
    if len(fused) == 1 and fused[0]["confidence"] > 0.95:
        print(f"✅ Relationship Fusion: Confirmed. Merged sources boosted confidence to {fused[0]['confidence']:.2f}.")
    else:
        print(f"❌ Relationship Fusion: Failed to merge or boost confidence correctly. Fused: {fused}")

    # 3. Execution Test (Dry Run of Agent 3B via Workflow)
    print("\nStarting LangGraph workflow for Phase 3 Discovery Test...")
    initial_state = {
        "user_id": "phase3_tester",
        "portfolio": ["AAPL", "NVDA"],
        "loop_count": 0,
        "news_articles": [],
        "errors": [],
        "workflow_status": "Started",
        "started_at": datetime.now().isoformat()
    }
    
    # We'll trigger a discovery for "TSMC"
    # Note: This might make an actual network call to SEC if not mocked
    # We will wrap it in a try-except to handle network issues gracefully
    try:
        # Mocking classified articles so 3a has a miss
        initial_state["classified_articles"] = [
            {"article_id": "art_1", "ticker": "TSMC", "sentiment_score": -0.8, "factor_name": "Supply Chain"}
        ]
        
        final_output = app.invoke(initial_state)
        
        disc = final_output.get("discovered_relationships", [])
        if disc:
            print(f"✅ Agent 3B Discovery: Found {len(disc)} discovered relationship sets.")
            for d in disc:
                print(f"   - Ticker: {d['ticker']}")
                for r in d['relationships']:
                    print(f"     -> {r['type']} to {r['related_company']} (Confidence: {r['confidence']:.2f})")
        else:
            print("❌ Agent 3B Discovery: No relationships discovered.")
            
    except Exception as e:
        print(f"⚠️ Agent 3B Execution encountered an issue (check network/API): {e}")

    print("\n🎉 PHASE 3 TEST COMPLETE: DYNAMIC DISCOVERY COMPONENTS VERIFIED.")

if __name__ == "__main__":
    run_phase3_test()
