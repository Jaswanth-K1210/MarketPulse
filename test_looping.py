
import json
from datetime import datetime
from app.agents.workflow import app
from app.agents.state import SupplyChainState

def test_autonomous_looping():
    print("\n" + "="*80)
    print("DEMONSTRATING AUTONOMOUS LOOPING (SPEC 3.0 AGENTIC BEHAVIOR)")
    print("="*80)
    
    # We'll use a ticker that is likely to have 'low confidence' news or no direct hits initially
    # to test if Agent 5 triggers a loop back to Agent 1.
    
    # We can also simulate low confidence by providing a ticker that isn't in our initial 'seed' set
    # OR by simply mocking the confidence score in a test-wrapper if we wanted to be 100% sure.
    # However, let's try a real run with a complex/obscure company.
    
    initial_state = {
        "user_id": "test_loop_user",
        "portfolio": ["Apple", "NVIDIA", "ASML"],
        "loop_count": 0,
        "news_articles": [],
        "errors": [],
        "workflow_status": "Starting Loop Test",
        "started_at": datetime.now().isoformat()
    }

    print(f"Engaging LangGraph with Portfolio: {initial_state['portfolio']}")
    
    # Execute workflow
    # Note: Agent 5 logic: if avg_confidence < 0.7 and loop_count < 2: decision = "REQUEST_MORE_DATA"
    
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*80)
    print("WORKFLOW COMPLETE")
    print("="*80)
    print(f"Final Loop Count: {final_state.get('loop_count')}")
    print(f"Validation Decision: {final_state.get('validation_decision')}")
    print(f"Final Confidence: {final_state.get('confidence_score'):.2f}")
    
    if final_state.get('loop_count') > 0:
        print("✅ SUCCESS: Autonomous looping demonstrated!")
    else:
        print("⚠️  Looping NOT triggered. Confidence was likely above 70% threshold.")
        # We can force a loop if needed for the demo by lowering the threshold or mocking a low-confidence article.

if __name__ == "__main__":
    test_autonomous_looping()
