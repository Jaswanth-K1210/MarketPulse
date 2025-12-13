"""
Researcher Agent
Gathers additional context and historical data for deeper analysis
"""

from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta
from app.agents.base_agent import BaseAgent
from app.services.portfolio import portfolio_service
from app.services.database import database

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """Agent specialized in gathering context and historical data"""

    def __init__(self):
        super().__init__(
            name="Researcher Agent",
            description="Context gathering and historical analysis specialist"
        )

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research companies and gather contextual data

        Args:
            input_data: {
                "companies": list,
                "event_type": str (optional)
            }

        Returns:
            {
                "success": bool,
                "company_data": dict,  # Current prices, changes
                "historical_context": list,  # Recent related articles
                "price_trends": dict,  # Price movement summary
                "related_events": list
            }
        """
        try:
            # Validate input
            if not self.validate_input(input_data, ["companies"]):
                return {"success": False, "error": "Missing companies"}

            companies = input_data["companies"]
            self.log_action("Starting research", f"Companies: {companies}")

            # Gather company data
            company_data = self._gather_company_data(companies)

            # Get historical context
            historical_context = self._get_historical_context(companies)

            # Analyze price trends
            price_trends = self._analyze_price_trends(company_data)

            # Find related events
            related_events = self._find_related_events(companies)

            self.log_action("Research complete", f"Gathered data for {len(companies)} companies")

            return {
                "success": True,
                "company_data": company_data,
                "historical_context": historical_context,
                "price_trends": price_trends,
                "related_events": related_events,
                "agent": self.name
            }

        except Exception as e:
            return self.handle_error(e, "process")

    def _gather_company_data(self, companies: List[str]) -> Dict[str, Any]:
        """
        Get current stock data for companies

        Args:
            companies: List of company names

        Returns:
            Company data dict
        """
        try:
            data = {}

            for company in companies:
                stock_info = portfolio_service.get_stock_info(company)

                if stock_info:
                    data[company] = {
                        "ticker": stock_info.get("ticker"),
                        "current_price": stock_info.get("current_price", 0.0),
                        "day_change": stock_info.get("day_change", 0.0),
                        "day_change_percent": stock_info.get("day_change_percent", 0.0),
                        "volume": stock_info.get("volume", 0),
                        "market_cap": stock_info.get("market_cap", 0)
                    }
                else:
                    logger.warning(f"No stock data for {company}")
                    data[company] = {"error": "Data unavailable"}

            return data

        except Exception as e:
            logger.error(f"Error gathering company data: {e}")
            return {}

    def _get_historical_context(self, companies: List[str]) -> List[Dict[str, Any]]:
        """
        Get recent articles about these companies

        Args:
            companies: List of company names

        Returns:
            List of related articles
        """
        try:
            all_articles = database.get_all_articles()

            # Filter articles mentioning these companies (last 7 days)
            cutoff_date = datetime.now() - timedelta(days=7)
            related = []

            for article in all_articles:
                # Check if article mentions any of the companies
                article_companies = article.companies_mentioned
                if any(comp in article_companies for comp in companies):
                    # Check if within time window
                    if article.published_at >= cutoff_date:
                        related.append({
                            "title": article.title,
                            "published_at": article.published_at.isoformat(),
                            "companies": article.companies_mentioned,
                            "event_type": article.event_type
                        })

            # Sort by date (most recent first)
            related.sort(key=lambda x: x["published_at"], reverse=True)

            return related[:10]  # Return up to 10 most recent

        except Exception as e:
            logger.error(f"Error getting historical context: {e}")
            return []

    def _analyze_price_trends(self, company_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Analyze price trends from company data

        Args:
            company_data: Company data dict

        Returns:
            Trend summary
        """
        try:
            trends = {}

            for company, data in company_data.items():
                if "error" in data:
                    trends[company] = "No data"
                    continue

                change_pct = data.get("day_change_percent", 0.0)

                if change_pct > 2.0:
                    trends[company] = "Strong upward"
                elif change_pct > 0.5:
                    trends[company] = "Upward"
                elif change_pct > -0.5:
                    trends[company] = "Stable"
                elif change_pct > -2.0:
                    trends[company] = "Downward"
                else:
                    trends[company] = "Strong downward"

            return trends

        except Exception as e:
            logger.error(f"Error analyzing price trends: {e}")
            return {}

    def _find_related_events(self, companies: List[str]) -> List[str]:
        """
        Find recent events related to these companies

        Args:
            companies: List of company names

        Returns:
            List of event descriptions
        """
        try:
            all_alerts = database.get_all_alerts()

            # Get recent alerts involving these companies
            related = []
            cutoff_date = datetime.now() - timedelta(days=7)

            for alert in all_alerts:
                # Check if alert involves these companies
                alert_companies = [h.company for h in alert.affected_holdings]
                if any(comp in alert_companies for comp in companies):
                    if alert.created_at >= cutoff_date:
                        related.append(
                            f"{alert.severity.upper()}: {alert.recommendation} ({alert.created_at.strftime('%Y-%m-%d')})"
                        )

            return related[:5]  # Return up to 5 recent events

        except Exception as e:
            logger.error(f"Error finding related events: {e}")
            return []


# Create singleton instance
researcher_agent = ResearcherAgent()
