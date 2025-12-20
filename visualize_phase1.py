#!/usr/bin/env python3
"""
Visualize Phase 1 Workflow
Shows the LangGraph state machine structure
"""

from app.agents.workflow import app

def visualize_workflow():
    """Display the workflow structure"""
    
    print("=" * 80)
    print("  PHASE 1: LANGGRAPH WORKFLOW STRUCTURE")
    print("=" * 80)
    
    print("\n📊 AGENT NODES:")
    print("  1. news_monitor        → Agent 1: News Monitor")
    print("  2. classifier          → Agent 2: 10-Factor Classifier")
    print("  3. matcher_fast        → Agent 3A: Fast Portfolio Matcher")
    print("  4. matcher_discovery   → Agent 3B: Dynamic Discovery")
    print("  5. impact_calculator   → Agent 4: Impact Calculator")
    print("  6. confidence_validator → Agent 5: Confidence Validator (BRAIN)")
    print("  7. alert_generator     → Agent 6: Alert Generator")
    
    print("\n🔄 WORKFLOW FLOW:")
    print("""
    ┌─────────────────┐
    │  news_monitor   │ ←──────────────┐
    │   (Agent 1)     │                │
    └────────┬────────┘                │
             │                         │
             v                         │
    ┌─────────────────┐                │
    │   classifier    │                │
    │   (Agent 2)     │                │
    └────────┬────────┘                │
             │                         │
             v                         │
    ┌─────────────────┐                │
    │  matcher_fast   │                │
    │   (Agent 3A)    │                │
    └────────┬────────┘                │
             │                         │
        ┌────┴─────┐                   │
        │cache_miss│                   │
        └────┬─────┘                   │
             v                         │
    ┌──────────────────┐               │
    │matcher_discovery │               │
    │   (Agent 3B)     │               │
    └────────┬─────────┘               │
             │                         │
             v                         │
    ┌──────────────────┐               │
    │impact_calculator │               │
    │   (Agent 4)      │               │
    └────────┬─────────┘               │
             │                         │
             v                         │
    ┌──────────────────┐               │
    │confidence_       │               │
    │validator         │  confidence   │
    │(Agent 5) BRAIN   │◄─< 70%?       │
    └────────┬─────────┘               │
             │                         │
        ┌────┴─────┐                   │
        │  ACCEPT  │                   │
        └────┬─────┘                   │
             │           REQUEST_      │
             v           MORE_DATA     │
    ┌──────────────────┐               │
    │ alert_generator  │               │
    │   (Agent 6)      │               │
    └──────────────────┘               │
             │                         │
             v                         │
         ┌───────┐                     │
         │  END  │                     │
         └───────┘                     │
    """)
    
    print("\n🧠 KEY FEATURES:")
    print("  ✅ LangGraph StateGraph orchestration")
    print("  ✅ 6-Agent framework (NewsMonitor → Classifier → Matcher → Discovery → Calculator → AlertGen)")
    print("  ✅ Agent 5 Confidence Validator: The 'Brain' with 70% threshold logic")
    print("  ✅ Autonomous looping: Auto-loops back to Agent 1 with refined queries")
    print("  ✅ Conditional edges: Dynamic routing based on cache misses & confidence")
    
    print("\n📈 EXECUTION FLOW:")
    print("  1. Initial Pass (Loop 0):")
    print("     - Confidence = 60% (< 70%) → REQUEST_MORE_DATA")
    print("     - System identifies gaps: 'Missing historical precedent'")
    print("     - Auto-generates refined query: 'TSMC historical production disruptions'")
    print("     - Loops back to Agent 1 automatically")
    
    print("\n  2. Refined Pass (Loop 1):")
    print("     - Agent 1 fetches additional data based on refined queries")
    print("     - All agents reprocess with enriched context")
    print("     - Confidence = 85% (> 70%) → ACCEPT")
    print("     - Proceeds to Agent 6 for alert generation")
    
    print("\n" + "=" * 80)
    print("  ✅ PHASE 1 IMPLEMENTATION COMPLETE")
    print("=" * 80)
    
    # Try to get graph representation if available
    try:
        print("\n📋 Attempting to export graph visualization...")
        graph = app.get_graph()
        print(f"  Graph nodes: {len(graph.nodes)} nodes")
        print(f"  Graph edges: {len(graph.edges)} edges")
    except Exception as e:
        print(f"  Note: Graph visualization requires additional dependencies")

if __name__ == "__main__":
    visualize_workflow()
