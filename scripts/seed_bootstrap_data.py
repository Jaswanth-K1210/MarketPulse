"""
Script to generate bootstrap_seed.json for L0 caching layer.
This ensures the application always has data on first start.
"""

import json
import os
import time
from pathlib import Path

# Try importing the services, if available in the PYTHONPATH
try:
    from app.services.market_data import MarketDataService
    from app.services.data.macro_economic import MacroEconomicService
    has_services = True
except ImportError:
    has_services = False

SEED_FILE = Path(__file__).parent.parent / "data" / "bootstrap_seed.json"

def generate_mock_data():
    """Fallback generator if services cannot be imported/invoked."""
    return {
        "news:top_headlines": [
            {
                "title": "Markets rally on rate cut hopes",
                "content": "Global markets rallied today as investors anticipate potential interest rate cuts.",
                "source": "MockNews",
                "timestamp": time.time(),
                "url": "https://example.com/news/1"
            }
        ],
        "market:major_indices": {
            "S&P 500": {"price": 5000.0, "change": 1.2},
            "NASDAQ": {"price": 16000.0, "change": 1.5},
            "DJIA": {"price": 39000.0, "change": 0.8},
            "VIX": {"price": 13.5, "change": -5.0}
        },
        "market:sector_etfs": {
            "XLE": {"price": 90.0, "change": 0.5},
            "XLF": {"price": 40.0, "change": 1.1},
            "XLK": {"price": 200.0, "change": 1.8}
        },
        "macro:fed_funds_rate": {"rate": 5.25, "date": "2025-12-01"},
        "macro:treasury_yields": {
            "2Y": {"yield": 4.5, "change": -0.05},
            "10Y": {"yield": 4.1, "change": -0.03},
            "30Y": {"yield": 4.3, "change": -0.02}
        },
        "market:commodities": {
            "crude_oil": {"price": 75.0, "change": 0.5},
            "gold": {"price": 2050.0, "change": 0.2},
            "natural_gas": {"price": 2.5, "change": -1.5}
        }
    }

async def generate_real_data():
    """Generates real data using application services."""
    market_service = MarketDataService()
    macro_service = MacroEconomicService()
    
    # Example fetching, adjust to actual service methods
    try:
        macro_snapshot = await macro_service.get_macro_snapshot()
    except Exception:
        macro_snapshot = {}
        
    return {
        "market:major_indices": {"status": "seeded"},
        "macro:snapshot": macro_snapshot,
    }

def main():
    print("Generating bootstrap seed data...")
    # For now, generate mock data to ensure the file exists and is valid.
    # We can invoke `generate_real_data` if we run this in an async context with env vars.
    data = generate_mock_data()
    
    # Ensure data directory exists
    SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(SEED_FILE, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"Successfully generated {SEED_FILE} with {len(data)} keys.")

if __name__ == "__main__":
    main()
