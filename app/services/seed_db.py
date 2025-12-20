from app.services.database import get_db_connection, init_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def seed_database():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Seed Portfolio & Core Supply Chain Companies
    companies = [
        ("AAPL", "Apple Inc.", "Technology", 1),
        ("NVDA", "NVIDIA Corporation", "Semiconductors", 1),
        ("AMD", "Advanced Micro Devices", "Semiconductors", 1),
        ("INTC", "Intel Corporation", "Semiconductors", 1),
        ("AVGO", "Broadcom Inc.", "Semiconductors", 1),
        ("TSM", "TSMC", "Semiconductors", 0),
        ("ASML", "ASML Holding", "Semiconductors", 0),
        ("AMAT", "Applied Materials", "Semiconductors", 0),
        ("LRCX", "Lam Research", "Semiconductors", 0),
        ("KLAC", "KLA Corporation", "Semiconductors", 0),
        # Adding more to reach closer to 50 or at least high coverage
        ("MSFT", "Microsoft", "Technology", 0),
        ("GOOGL", "Alphabet", "Technology", 0),
        ("AMZN", "Amazon", "Consumer Discretionary", 0),
        ("TSLA", "Tesla", "Automotive", 0),
        ("MU", "Micron Technology", "Semiconductors", 0),
        ("ARM", "ARM Holdings", "Semiconductors", 0),
        ("TXN", "Texas Instruments", "Semiconductors", 0),
        ("QCOM", "Qualcomm", "Semiconductors", 0),
        ("ADI", "Analog Devices", "Semiconductors", 0),
        ("NXPI", "NXP Semiconductors", "Semiconductors", 0),
        ("ON", "ON Semiconductor", "Semiconductors", 0),
        ("MCHP", "Microchip Technology", "Semiconductors", 0),
        ("STM", "STMicroelectronics", "Semiconductors", 0),
        ("INFY", "Infosys", "Technology", 0),
        ("WIT", "Wipro", "Technology", 0),
        ("HMC", "Honda Motor", "Automotive", 0),
        ("TM", "Toyota Motor", "Automotive", 0),
        ("F", "Ford Motor", "Automotive", 0),
        ("GM", "General Motors", "Automotive", 0),
        ("STLA", "Stellantis", "Automotive", 0),
    ]

    for ticker, name, sector, is_p in companies:
        cursor.execute('''
            INSERT OR IGNORE INTO companies (ticker, name, sector, is_portfolio, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticker, name, sector, is_p, datetime.now()))

    # 2. Seed Critical Relationships
    relationships = [
        ("TSM", "AAPL", "supplier", "critical"),
        ("TSM", "NVDA", "supplier", "critical"),
        ("TSM", "AMD", "supplier", "critical"),
        ("TSM", "INTC", "supplier", "medium"),
        ("ASML", "TSM", "supplier", "critical"),
        ("ARM", "AAPL", "partner", "critical"),
        ("ARM", "NVDA", "partner", "high"),
        ("AMAT", "TSM", "supplier", "high"),
        ("LRCX", "TSM", "supplier", "high"),
        ("NVDA", "MSFT", "supplier", "critical"),
        ("NVDA", "GOOGL", "supplier", "critical"),
        ("AVGO", "AAPL", "supplier", "high"),
        ("QCOM", "AAPL", "supplier", "high"),
        ("MU", "NVDA", "supplier", "medium"),
        ("ASML", "INTC", "supplier", "critical"),
        ("ASML", "SSNLF", "supplier", "high"),
    ]

    for src, target, rtype, crit in relationships:
        cursor.execute('''
            INSERT OR IGNORE INTO relationships (source_ticker, target_ticker, relationship_type, criticality, confidence, source_discovery, last_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (src, target, rtype, crit, 0.95, "manual", datetime.now()))

    # 3. Seed Mock Holdings for Jaswanth
    holdings = [
        ("AAPL", 150, 145.50, 185.20),
        ("NVDA", 80, 420.00, 480.50),
        ("AMD", 120, 95.00, 112.30),
        ("INTC", 200, 42.50, 38.40),
        ("AVGO", 60, 540.00, 890.10)
    ]

    for ticker, q, ap, cp in holdings:
        cursor.execute('''
            INSERT OR IGNORE INTO holdings (ticker, quantity, avg_price, current_price)
            VALUES (?, ?, ?, ?)
        ''', (ticker, q, ap, cp))

    conn.commit()
    logger.info("Database seeded with core companies, relationships, and holdings.")
    conn.close()

if __name__ == "__main__":
    seed_database()
