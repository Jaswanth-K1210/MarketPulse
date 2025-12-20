
import sqlite3
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.database import DATABASE_PATH

def seed_precedents():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Clear existing to avoid duplicates if re-run
    cursor.execute("DELETE FROM historical_precedents")

    precedents = [
        # Supply Chain Events (TIER 1 - Direct Impact)
        ("Supply Chain & Logistics", "Taiwan Earthquake 2024", "2024-04-03", 1.8, "Major disruption to TSMC facilities, causing global chip supply concerns. AAPL -8.2%, NVDA -6.7%"),
        ("Supply Chain & Logistics", "Suez Canal Blockage (Ever Given)", "2021-03-23", 1.5, "Significant global trade bottleneck impacting electronics and energy components."),
        ("Supply Chain & Logistics", "TSMC Fab 18 Equipment Malfunction", "2021-04-15", 1.6, "2-week production halt at TSMC caused Apple iPhone delays and NVIDIA GPU shortages."),
        ("Supply Chain & Logistics", "Samsung COVID Lockdown China", "2022-04-01", 1.4, "45-day production disruption at Samsung facilities due to COVID lockdowns in China."),
        ("Supply Chain & Logistics", "Rivian Battery Supplier Delays", "2022-09-15", 2.3, "Panasonic delays battery shipments to Rivian. RIVN -22.5%, production cuts announced."),
        ("Supply Chain & Logistics", "Japan Earthquake Chip Shortage", "2024-01-01", 1.7, "Renesas and Toshiba fabs affected, automotive chip supply disrupted."),

        # Earnings & Profitability
        ("Earnings & Profitability", "NVIDIA Q2 2023 Earnings", "2023-08-23", 2.2, "Massive AI demand surge led to record guidance and stock breakout. NVDA +24.4%"),
        ("Earnings & Profitability", "Apple Record Q4 2023", "2023-11-02", 1.5, "Apple reports record Q4 earnings, beats by 15%. AAPL +8.2%"),
        ("Earnings & Profitability", "Tesla Production Ramp 2023", "2023-01-12", 1.6, "Tesla announces 50% production increase. TSLA +11.3%"),
        ("Earnings & Profitability", "Meta Earnings Miss Q1 2022", "2022-02-03", 1.9, "Meta misses on earnings, guides lower due to Apple privacy changes. META -26%"),
        ("Earnings & Profitability", "Amazon AWS Growth Slowdown", "2023-04-27", 1.3, "AWS growth decelerates to 16% vs 20% expected. AMZN -4.2%"),

        # Macroeconomic & Interest Rates
        ("Macroeconomic Factors", "Fed Rate Hike March 2022", "2022-03-16", 1.2, "Start of tightening cycle impacting tech valuations and growth stocks. Tech sector -3.8%"),
        ("Macroeconomic Factors", "Fed Emergency Rate Cut COVID", "2020-03-03", 1.4, "Fed cuts rates by 0.5% in emergency move. Initial rally +4.2%, then COVID crash."),
        ("Macroeconomic Factors", "Fed Largest Hike Since 1994", "2022-06-15", 1.5, "Fed raises rates by 0.75% - largest hike since 1994. NVDA -8%, AAPL -5%"),
        ("Macroeconomic Factors", "Inflation Reaches 40-Year High", "2022-06-10", 1.7, "CPI hits 9.1%, highest since 1981. Broad tech selloff -5.2%"),

        # Geopolitical Events
        ("Geopolitical Risk", "Russia-Ukraine War Start", "2022-02-24", 2.5, "Extreme volatility in energy and neon gas (semiconductor input) sectors. Market -12.9%"),
        ("Geopolitical Risk", "US Bans AI Chip Exports to China", "2023-10-17", 1.8, "US restricts NVIDIA/AMD advanced AI chip sales to China. NVDA -6.8%, lost 20-30% China revenue"),
        ("Geopolitical Risk", "Taiwan Strait Tensions 2024", "2024-05-20", 1.4, "Cross-strait military exercises raise semiconductor supply concerns."),
        ("Geopolitical Risk", "China Tech Crackdown 2021", "2021-07-24", 2.1, "China announces sweeping tech regulations. BABA -28%, tech sector contagion."),

        # Market Sentiment & Black Swan
        ("Market Sentiment & Psychology", "SVB Collapse", "2023-03-10", 1.9, "Banking contagion fears briefly impacted overall market liquidity and tech lending. Banking -25%"),
        ("Market Sentiment & Psychology", "COVID-19 Market Crash", "2020-03-16", 3.0, "Fastest bear market in history. S&P -12.9% in single day. Recovery took 6 months with Fed support."),
        ("Market Sentiment & Psychology", "Flash Crash 2010", "2010-05-06", 1.6, "Algorithmic trading caused 1000-point Dow drop in minutes. Recovered same day."),
        ("Market Sentiment & Psychology", "Crypto Winter Impact on Tech", "2022-05-09", 1.3, "Bitcoin crashes from $69K to $20K. Tech stocks correlated selloff."),

        # Regulatory & Policy
        ("Regulatory & Legal", "EU DMA Implementation", "2024-03-07", 1.1, "Forced Apple and Google to open ecosystems, impacting long-term service revenue models."),
        ("Regulatory & Legal", "Apple iOS Privacy Changes", "2021-06-07", 1.8, "App Tracking Transparency hurts Meta ad revenue. META -18.2% over 90 days"),
        ("Regulatory & Legal", "FTC Blocks Microsoft-Activision", "2023-06-12", 1.2, "Initial FTC block (later overturned). MSFT -1.2%, regulatory uncertainty."),

        # Product & Innovation
        ("Product & Innovation", "ChatGPT Launch", "2022-11-30", 2.0, "Triggered absolute AI transformation and capex surge across datacenter suppliers."),
        ("Product & Innovation", "Apple Vision Pro Announcement", "2023-06-05", 1.3, "Mixed reality headset announced. AAPL +2%, spatial computing era begins."),
        ("Product & Innovation", "AMD Zen Architecture Launch", "2019-07-07", 1.7, "AMD gains massive server market share from Intel. INTC -16.8% over 6 months"),

        # M&A and Corporate Actions
        ("M&A and Structural", "Broadcom-VMware Close", "2023-11-22", 1.3, "Consolidation of enterprise software and cloud infrastructure segments."),
        ("M&A and Structural", "Microsoft Activision $69B", "2022-01-18", 1.1, "MSFT announces Activision acquisition. MSFT +2.4%, regulatory approval takes 18 months."),

        # Labor & Operations
        ("Labor & Operations", "Samsung Labor Strike 2024", "2024-07-08", 1.4, "First major strike at Samsung, impacting memory chip yield forecasts."),
        ("Labor & Operations", "Amazon Warehouse Unionization", "2022-04-01", 1.0, "First successful Amazon union vote. Labor cost concerns. AMZN -3.2%")
    ]

    cursor.executemany("""
        INSERT INTO historical_precedents (event_type, event_name, date_occurred, impact_magnitude, description)
        VALUES (?, ?, ?, ?, ?)
    """, precedents)

    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(precedents)} historical precedents into the database.")

if __name__ == "__main__":
    seed_precedents()
