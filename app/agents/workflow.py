from langgraph.graph import StateGraph, END
from app.agents.state import SupplyChainState
from app.agents.nodes import (
    agent_1_news_monitor,
    agent_2_classifier,
    agent_quant_tool_dispatcher,
    agent_3a_matcher_fast,
    agent_3b_discovery,
    agent_4_impact_calculator,
    agent_5_validator,
    agent_6_alerts,
    agent_memory_store,
    agent_kg_retrieval,
    agent_quality_eval,
    agent_audit_final,
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
# ── Core analysis pipeline (FinGPT + FinSphere) ────────────────────────────
workflow.add_node("news_monitor", agent_1_news_monitor)
workflow.add_node("classifier", agent_2_classifier)
workflow.add_node("quant_tools", agent_quant_tool_dispatcher)
workflow.add_node("alpha_scorer", agent_alpha_scorer)
workflow.add_node("convergence_detector", agent_convergence_detector)

# ── Relationship discovery ──────────────────────────────────────────────────
workflow.add_node("matcher_fast", agent_3a_matcher_fast)
workflow.add_node("matcher_discovery", agent_3b_discovery)

# ── Impact + validation ─────────────────────────────────────────────────────
workflow.add_node("impact_calculator", agent_4_impact_calculator)
workflow.add_node("confidence_validator", agent_5_validator)
workflow.add_node("alert_generator", agent_6_alerts)

# ── Post-alert intelligence (Memory + KG + Quality + Audit) ────────────────
workflow.add_node("memory_store", agent_memory_store)
workflow.add_node("kg_retrieval", agent_kg_retrieval)
workflow.add_node("quality_eval", agent_quality_eval)
workflow.add_node("audit_final", agent_audit_final)

# ── Core pipeline edges ─────────────────────────────────────────────────────
# classifier → quant_tools → alpha_scorer (TOOL-FIRST: tools dispatch before analysis)
workflow.add_edge("news_monitor", "classifier")
workflow.add_edge("classifier", "quant_tools")
workflow.add_edge("quant_tools", "alpha_scorer")
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

# ── Post-alert pipeline (Memory → KG → Quality → Audit → END) ─────────────
# These run after every alert to build cross-run intelligence
workflow.add_edge("alert_generator", "memory_store")
workflow.add_edge("memory_store", "kg_retrieval")
workflow.add_edge("kg_retrieval", "quality_eval")
workflow.add_edge("quality_eval", "audit_final")
workflow.add_edge("audit_final", END)

# Set entry point
workflow.set_entry_point("news_monitor")

# Compile
app = workflow.compile()
