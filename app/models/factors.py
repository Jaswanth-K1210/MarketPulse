from enum import Enum
from typing import Dict, List

class MarketFactor(Enum):
    MACROECONOMIC = 1
    INTEREST_RATES = 2
    SUPPLY_CHAIN = 3
    COMPANY_EARNINGS = 4
    GOVERNMENT_POLICY = 5
    GEOPOLITICAL = 6
    CURRENCY = 7
    MARKET_SENTIMENT = 8
    INDUSTRY_TRENDS = 9
    BLACK_SWAN = 10

FACTOR_METADATA = {
    MarketFactor.MACROECONOMIC: {
        "name": "Macroeconomic Indicators",
        "keywords": ["GDP", "inflation", "CPI", "unemployment", "jobs report", "payroll", "PMI", "recession"],
        "description": "Overall economic health indicators."
    },
    MarketFactor.INTEREST_RATES: {
        "name": "Interest Rates & Central Bank Policy",
        "keywords": ["Federal Reserve", "Fed", "interest rate", "rate hike", "quantitative easing", "Powell", "FOMC", "yield"],
        "description": "Monetary policy and interest rate decisions."
    },
    MarketFactor.SUPPLY_CHAIN: {
        "name": "Supply Chain Events",
        "keywords": ["supply chain", "shortage", "disruption", "factory shutdown", "production halt", "logistics", "shipping delay"],
        "description": "Events affecting production and distribution."
    },
    MarketFactor.COMPANY_EARNINGS: {
        "name": "Company Earnings & Performance",
        "keywords": ["earnings", "revenue", "profit", "EPS", "guidance", "quarterly results", "beat", "miss"],
        "description": "Individual company financial results."
    },
    MarketFactor.GOVERNMENT_POLICY: {
        "name": "Government Policy & Regulation",
        "keywords": ["regulation", "antitrust", "tax policy", "subsidy", "compliance", "legislation", "FDA"],
        "description": "Laws and government actions affecting markets."
    },
    MarketFactor.GEOPOLITICAL: {
        "name": "Geopolitical Events",
        "keywords": ["trade war", "tariff", "sanction", "geopolitical", "conflict", "election", "diplomacy"],
        "description": "International relations and political events."
    },
    MarketFactor.CURRENCY: {
        "name": "Currency Fluctuations",
        "keywords": ["exchange rate", "forex", "dollar strength", "appreciation", "depreciation", "currency"],
        "description": "Changes in currency values."
    },
    MarketFactor.MARKET_SENTIMENT: {
        "name": "Market Sentiment & Psychology",
        "keywords": ["VIX", "volatility", "bullish", "bearish", "sell-off", "rally", "fear index"],
        "description": "Investor mood and market psychology."
    },
    MarketFactor.INDUSTRY_TRENDS: {
        "name": "Industry-Specific Trends",
        "keywords": ["breakthrough", "innovation", "adoption", "market share", "disruption", "consolidation"],
        "description": "Trends specific to certain industries."
    },
    MarketFactor.BLACK_SWAN: {
        "name": "Black Swan Events",
        "keywords": ["unprecedented", "catastrophe", "pandemic", "natural disaster", "unexpected", "rare event"],
        "description": "Rare, high-impact, unpredictable events."
    }
}
