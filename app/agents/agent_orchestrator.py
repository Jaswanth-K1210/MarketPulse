"""
Agent Orchestrator
Coordinates all specialized agents to process news and generate insights
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime
from app.agents.analyst_agent import analyst_agent
from app.agents.researcher_agent import researcher_agent
from app.agents.calculator_agent import calculator_agent
from app.agents.synthesizer_agent import synthesizer_agent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates multi-agent collaboration for news analysis"""

    def __init__(self):
        """Initialize orchestrator"""
        self.analyst = analyst_agent
        self.researcher = researcher_agent
        self.calculator = calculator_agent
        self.synthesizer = synthesizer_agent
        logger.info("🤖 Agent Orchestrator initialized with 4 agents")

    def process_news(
        self,
        article_title: str,
        article_content: str,
        article_url: str,
        companies_mentioned: list
    ) -> Optional[Dict[str, Any]]:
        """
        Process news article through multi-agent pipeline

        Args:
            article_title: Article title
            article_content: Article content
            article_url: Article URL
            companies_mentioned: List of companies mentioned

        Returns:
            Complete analysis result or None if processing fails
        """
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"🤖 MULTI-AGENT ANALYSIS: {article_title[:60]}...")
            logger.info(f"{'='*80}\n")

            start_time = datetime.now()

            # STEP 1: Analyst Agent - Market Analysis
            logger.info("📊 Step 1/4: Analyst Agent - Analyzing market sentiment...")
            analysis_result = self.analyst.process({
                "article_title": article_title,
                "article_content": article_content,
                "companies_mentioned": companies_mentioned
            })

            if not analysis_result.get("success"):
                logger.error("❌ Analyst agent failed")
                return None

            logger.info(f"✓ Sentiment: {analysis_result.get('sentiment')}")
            logger.info(f"✓ Score: {analysis_result.get('sentiment_score')}")

            # STEP 2: Researcher Agent - Gather Context
            logger.info("\n🔍 Step 2/4: Researcher Agent - Gathering context...")
            research_result = self.researcher.process({
                "companies": companies_mentioned
            })

            if not research_result.get("success"):
                logger.warning("⚠️  Researcher agent failed, continuing without context")
                research_result = {}

            logger.info(f"✓ Company data gathered for {len(companies_mentioned)} companies")

            # STEP 3: Calculator Agent - Quantify Impact
            logger.info("\n💰 Step 3/4: Calculator Agent - Calculating portfolio impact...")
            calculation_result = self.calculator.process({
                "affected_companies": companies_mentioned,
                "sentiment_score": analysis_result.get("sentiment_score", 0.0),
                "estimated_impact_percent": None  # Let calculator estimate
            })

            if not calculation_result.get("success"):
                logger.error("❌ Calculator agent failed")
                return None

            impact_pct = calculation_result.get("portfolio_impact_percent", 0.0)
            impact_dollar = calculation_result.get("portfolio_impact_dollar", 0.0)
            severity = calculation_result.get("severity", "low")

            logger.info(f"✓ Impact: {impact_pct:+.2f}% (${impact_dollar:,.2f})")
            logger.info(f"✓ Severity: {severity}")

            # STEP 4: Synthesizer Agent - Generate Final Recommendation
            logger.info("\n🧠 Step 4/4: Synthesizer Agent - Synthesizing insights...")
            synthesis_result = self.synthesizer.process({
                "analysis_result": analysis_result,
                "research_result": research_result,
                "calculation_result": calculation_result,
                "article_title": article_title,
                "article_url": article_url
            })

            if not synthesis_result.get("success"):
                logger.error("❌ Synthesizer agent failed")
                return None

            logger.info(f"✓ Recommendation: {synthesis_result.get('recommendation')}")
            logger.info(f"✓ Confidence: {synthesis_result.get('confidence'):.0%}")

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"\n⏱️  Processing time: {processing_time:.2f}s")

            # Combine all results
            final_result = {
                "success": True,
                "analysis": analysis_result,
                "research": research_result,
                "calculation": calculation_result,
                "synthesis": synthesis_result,
                "metadata": {
                    "processing_time_seconds": processing_time,
                    "agents_used": 4,
                    "timestamp": datetime.now().isoformat()
                }
            }

            logger.info(f"{'='*80}")
            logger.info("✅ Multi-agent analysis complete\n")

            return final_result

        except Exception as e:
            logger.error(f"❌ Orchestrator error: {str(e)}")
            return None

    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get status of all agents

        Returns:
            Status information
        """
        return {
            "orchestrator": "active",
            "agents": {
                "analyst": {
                    "name": self.analyst.name,
                    "description": self.analyst.description,
                    "status": "ready"
                },
                "researcher": {
                    "name": self.researcher.name,
                    "description": self.researcher.description,
                    "status": "ready"
                },
                "calculator": {
                    "name": self.calculator.name,
                    "description": self.calculator.description,
                    "status": "ready"
                },
                "synthesizer": {
                    "name": self.synthesizer.name,
                    "description": self.synthesizer.description,
                    "status": "ready"
                }
            },
            "total_agents": 4
        }


# Create singleton instance
agent_orchestrator = AgentOrchestrator()
