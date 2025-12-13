"""
Portfolio Service
Manages user portfolio data and provides stock information
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from app.services.market_data import market_data_service
from app.config import PORTFOLIO_COMPANIES

logger = logging.getLogger(__name__)

# Data file path
PORTFOLIO_FILE = Path(__file__).parent.parent / "data" / "portfolio.json"


class PortfolioService:
    """Service for managing portfolio data"""

    def __init__(self):
        """Initialize portfolio service"""
        self.portfolio_file = PORTFOLIO_FILE
        logger.info("Portfolio service initialized")

    def _read_portfolio(self) -> List[Dict]:
        """Read portfolio from JSON file"""
        try:
            if not self.portfolio_file.exists():
                logger.warning(f"Portfolio file not found: {self.portfolio_file}")
                return []

            with open(self.portfolio_file, 'r') as f:
                data = json.load(f)
                return data

        except Exception as e:
            logger.error(f"Error reading portfolio: {e}")
            return []

    def get_portfolio(self) -> Dict:
        """
        Get current portfolio with live values

        Returns:
            Portfolio data with current prices
        """
        try:
            portfolio_data = self._read_portfolio()

            if not portfolio_data or len(portfolio_data) == 0:
                logger.warning("No portfolio data found")
                return {"total_value": 0, "holdings": []}

            # Get first user's portfolio (Jaswanth)
            user_portfolio = portfolio_data[0]
            holdings = user_portfolio.get("portfolio", [])

            # Get current prices for all holdings
            total_value = 0.0
            holdings_with_prices = []

            for holding in holdings:
                ticker = holding["ticker"]
                quantity = holding["quantity"]

                # Get current stock data
                stock_data = market_data_service.get_stock_data(ticker)

                if stock_data and stock_data.get("current_price"):
                    current_price = stock_data["current_price"]
                    holding_value = current_price * quantity

                    holdings_with_prices.append({
                        "company": holding["company"],
                        "ticker": ticker,
                        "quantity": quantity,
                        "purchase_price": holding["purchase_price"],
                        "current_price": current_price,
                        "holding_value": holding_value
                    })

                    total_value += holding_value

            return {
                "user_name": user_portfolio.get("user_name", "Jaswanth"),
                "total_value": round(total_value, 2),
                "holdings": holdings_with_prices
            }

        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return {"total_value": 0, "holdings": []}

    def get_holding(self, company_name: str) -> Optional[Dict]:
        """
        Get specific holding by company name

        Args:
            company_name: Company name (e.g., "Apple", "NVIDIA")

        Returns:
            Holding data or None
        """
        try:
            portfolio = self.get_portfolio()
            holdings = portfolio.get("holdings", [])

            # Normalize company name for matching
            company_lower = company_name.lower()

            for holding in holdings:
                holding_company = holding["company"].lower()

                # Match by company name or if company name is in holding name
                if company_lower in holding_company or holding_company in company_lower:
                    return holding

                # Also try matching by ticker mapping
                if company_name in PORTFOLIO_COMPANIES:
                    expected_ticker = PORTFOLIO_COMPANIES[company_name]
                    if holding["ticker"] == expected_ticker:
                        return holding

            logger.warning(f"Holding not found for company: {company_name}")
            return None

        except Exception as e:
            logger.error(f"Error getting holding for {company_name}: {e}")
            return None

    def get_stock_info(self, company_name: str) -> Optional[Dict]:
        """
        Get stock information for a company

        Args:
            company_name: Company name

        Returns:
            Stock info dict or None
        """
        try:
            # Get ticker from company name
            ticker = None

            if company_name in PORTFOLIO_COMPANIES:
                ticker = PORTFOLIO_COMPANIES[company_name]
            else:
                # Try to find holding
                holding = self.get_holding(company_name)
                if holding:
                    ticker = holding["ticker"]

            if not ticker:
                logger.warning(f"No ticker found for: {company_name}")
                return None

            # Get stock data
            stock_data = market_data_service.get_stock_data(ticker)

            if stock_data:
                return {
                    "ticker": ticker,
                    "current_price": stock_data.get("current_price", 0.0),
                    "day_change": stock_data.get("change", 0.0),
                    "day_change_percent": stock_data.get("change_percent", 0.0),
                    "volume": stock_data.get("volume", 0),
                    "market_cap": stock_data.get("market_cap", 0)
                }

            return None

        except Exception as e:
            logger.error(f"Error getting stock info for {company_name}: {e}")
            return None


# Create singleton instance
portfolio_service = PortfolioService()
