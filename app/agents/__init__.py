"""
Multi-Agent System
Collaborative AI agents for market intelligence analysis
"""

# Re-exporting the new LangGraph components for v3.0 logic
from app.agents.workflow import app as workflow_app
from app.agents.nodes import (
    agent_1_news_monitor,
    agent_2_classifier,
    agent_3a_matcher_fast,
    agent_3b_discovery,
    agent_4_impact_calculator,
    agent_5_validator,
    agent_6_alerts
)

__all__ = [
    "workflow_app",
    "agent_1_news_monitor",
    "agent_2_classifier",
    "agent_3a_matcher_fast",
    "agent_3b_discovery",
    "agent_4_impact_calculator",
    "agent_5_validator",
    "agent_6_alerts"
]
