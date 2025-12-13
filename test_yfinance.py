#!/usr/bin/env python3
"""Quick test to verify yfinance is working"""

import yfinance as yf

tickers = ['AAPL', 'NVDA', 'AMD', 'INTC', 'AVGO']

print("Testing yfinance stock price fetching...")
print("=" * 50)

for ticker in tickers:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='2d')

        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            previous_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close > 0 else 0

            print(f"{ticker:6s}: ${current_price:7.2f}  ({change_percent:+.2f}%)")
        else:
            print(f"{ticker:6s}: NO DATA")
    except Exception as e:
        print(f"{ticker:6s}: ERROR - {str(e)}")

print("=" * 50)
