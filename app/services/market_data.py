"""
Market Data Service - Yahoo Finance Integration
Fetches real-time and historical stock data using yfinance
"""

import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching stock market data using Yahoo Finance"""

    def __init__(self):
        """Initialize the market data service"""
        self.cache = {}  # Simple in-memory cache
        self.cache_duration = timedelta(minutes=1)  # Cache for 1 minute

    def get_stock_data(self, ticker: str) -> Optional[Dict]:
        """
        Get current stock data for a given ticker

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'NVDA')

        Returns:
            Dictionary with stock data or None if error
        """
        try:
            # Check cache first
            cache_key = f"{ticker}_current"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if datetime.now() - cached_time < self.cache_duration:
                    logger.info(f"Returning cached data for {ticker}")
                    return cached_data

            # Fetch from Yahoo Finance
            stock = yf.Ticker(ticker)
            info = stock.info

            # Get current price and other metrics
            data = {
                "ticker": ticker,
                "company_name": info.get("longName", ticker),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "open": info.get("open") or info.get("regularMarketOpen"),
                "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
                "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
                "volume": info.get("volume") or info.get("regularMarketVolume"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "change": None,
                "change_percent": None,
                "timestamp": datetime.now().isoformat()
            }

            # Calculate change and change percent
            if data["current_price"] and data["previous_close"]:
                data["change"] = round(data["current_price"] - data["previous_close"], 2)
                data["change_percent"] = round(
                    (data["change"] / data["previous_close"]) * 100, 2
                )

            # Cache the result
            self.cache[cache_key] = (data, datetime.now())

            logger.info(f"Successfully fetched data for {ticker}: ${data['current_price']}")
            return data

        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
            return None

    def get_portfolio_value(self, holdings: List[Dict]) -> Dict:
        """
        Calculate total portfolio value and individual holdings

        Args:
            holdings: List of dicts with 'ticker', 'quantity', 'purchase_price'

        Returns:
            Dictionary with portfolio summary
        """
        try:
            portfolio_data = {
                "total_value": 0,
                "total_cost": 0,
                "total_gain_loss": 0,
                "total_gain_loss_percent": 0,
                "holdings": [],
                "timestamp": datetime.now().isoformat()
            }

            for holding in holdings:
                ticker = holding.get("ticker")
                quantity = holding.get("quantity", 0)
                purchase_price = holding.get("purchase_price", 0)

                # Get current stock data
                stock_data = self.get_stock_data(ticker)

                if stock_data and stock_data["current_price"]:
                    current_price = stock_data["current_price"]
                    current_value = current_price * quantity
                    cost_basis = purchase_price * quantity
                    gain_loss = current_value - cost_basis
                    gain_loss_percent = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

                    holding_data = {
                        "ticker": ticker,
                        "company_name": stock_data["company_name"],
                        "quantity": quantity,
                        "purchase_price": purchase_price,
                        "current_price": current_price,
                        "current_value": round(current_value, 2),
                        "cost_basis": round(cost_basis, 2),
                        "gain_loss": round(gain_loss, 2),
                        "gain_loss_percent": round(gain_loss_percent, 2),
                        "day_change": stock_data.get("change"),
                        "day_change_percent": stock_data.get("change_percent")
                    }

                    portfolio_data["holdings"].append(holding_data)
                    portfolio_data["total_value"] += current_value
                    portfolio_data["total_cost"] += cost_basis
                else:
                    logger.warning(f"Could not fetch data for {ticker}")

            # Calculate total portfolio metrics
            portfolio_data["total_value"] = round(portfolio_data["total_value"], 2)
            portfolio_data["total_cost"] = round(portfolio_data["total_cost"], 2)
            portfolio_data["total_gain_loss"] = round(
                portfolio_data["total_value"] - portfolio_data["total_cost"], 2
            )

            if portfolio_data["total_cost"] > 0:
                portfolio_data["total_gain_loss_percent"] = round(
                    (portfolio_data["total_gain_loss"] / portfolio_data["total_cost"]) * 100, 2
                )

            return portfolio_data

        except Exception as e:
            logger.error(f"Error calculating portfolio value: {str(e)}")
            return None

    def get_multiple_stocks(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Get data for multiple stocks at once

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to stock data
        """
        results = {}
        for ticker in tickers:
            data = self.get_stock_data(ticker)
            if data:
                results[ticker] = data
        return results

    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()
        logger.info("Market data cache cleared")


# Create singleton instance
market_data_service = MarketDataService()
