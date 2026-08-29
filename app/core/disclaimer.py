"""
Regulatory disclaimer.

MarketPulse emits trade recommendations (alpha scores, BUY/SELL signals,
portfolio weights). It is not a registered investment adviser, so every
surface that carries a recommendation must carry this notice. The
implementation blueprint calls this out explicitly.

Attached in three places:
  * `DISCLAIMER` on recommendation-bearing payloads (alpha score, signals)
  * `X-Disclaimer` response header on every /api response, via middleware
  * the frontend banner
"""

DISCLAIMER = (
    "For informational and research purposes only. This is not investment "
    "advice, and MarketPulse is not a registered investment adviser. Nothing "
    "here is a recommendation, offer, or solicitation to buy or sell any "
    "security. Data is aggregated from third-party sources and may be "
    "incomplete, delayed, or wrong. Do your own research and consult a "
    "licensed financial professional before trading."
)

# Short form for headers and tight UI (headers must stay ASCII/one line).
DISCLAIMER_SHORT = (
    "Informational only - not investment advice. MarketPulse is not a "
    "registered investment adviser."
)
