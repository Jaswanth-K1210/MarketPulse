from langgraph.graph import StateGraph, END
from app.agents.state import SupplyChainState
from app.agents.nodes import (
    agent_1_news_monitor,
    agent_2_classifier,
    agent_3a_matcher_fast,
    agent_3b_discovery,
    agent_4_impact_calculator,
    agent_5_validator,
    agent_6_alerts
)
from app.agents.alpha_scorer import agent_alpha_scorer
from app.agents.convergence_detector import agent_convergence_detector

def route_to_discovery_if_needed(state: SupplyChainState) -> str:
    """Routes to discovery if there are cache misses."""
    if state.get("cache_misses"):
        return "discovery"
    return "skip"

def check_confidence_threshold(state: SupplyChainState) -> str:
    """Decides whether to loop back or move to alerts based on validator decision."""
    decision = state.get("validation_decision")
    if decision == "REQUEST_MORE_DATA":
        return "loop"
    return "accept"

# Create the workflow
workflow = StateGraph(SupplyChainState)

# Add nodes
workflow.add_node("news_monitor", agent_1_news_monitor)
workflow.add_node("classifier", agent_2_classifier)
workflow.add_node("alpha_scorer", agent_alpha_scorer)
workflow.add_node("convergence_detector", agent_convergence_detector)
workflow.add_node("matcher_fast", agent_3a_matcher_fast)
workflow.add_node("matcher_discovery", agent_3b_discovery)
workflow.add_node("impact_calculator", agent_4_impact_calculator)
workflow.add_node("confidence_validator", agent_5_validator)
workflow.add_node("alert_generator", agent_6_alerts)

# Set up edges
workflow.add_edge("news_monitor", "classifier")
workflow.add_edge("classifier", "alpha_scorer")
workflow.add_edge("alpha_scorer", "convergence_detector")
workflow.add_edge("convergence_detector", "matcher_fast")

# Conditional edges from matcher_fast
workflow.add_conditional_edges(
    "matcher_fast",
    route_to_discovery_if_needed,
    {
        "discovery": "matcher_discovery",
        "skip": "impact_calculator"
    }
)

workflow.add_edge("matcher_discovery", "impact_calculator")
workflow.add_edge("impact_calculator", "confidence_validator")

# Conditional edges from confidence_validator
workflow.add_conditional_edges(
    "confidence_validator",
    check_confidence_threshold,
    {
        "loop": "news_monitor",
        "accept": "alert_generator"
    }
)

workflow.add_edge("alert_generator", END)

# Set entry point
workflow.set_entry_point("news_monitor")

# Compile
app = workflow.compile()
