"""
Telegram Bot Service — Push alerts, insider trades, alpha signals to Telegram.
Uses python-telegram-bot or simple HTTP API.
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.enabled:
            logger.debug("Telegram bot not configured")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text[:4096],
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    logger.info("Telegram alert sent")
                    return True
                else:
                    logger.warning(f"Telegram API error: {resp.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"Telegram send failed: {e}")
            return False

    async def send_alert(self, ticker: str, signal: str, alpha_score: float,
                         reasons: list = None) -> bool:
        if not self.enabled:
            return False

        emoji_map = {
            "STRONG_BUY": "🚀", "BUY": "📈", "NEUTRAL": "➖",
            "SELL": "📉", "STRONG_SELL": "🔻",
        }
        emoji = emoji_map.get(signal, "ℹ️")

        text = (
            f"{emoji} <b>Alpha Signal: {ticker}</b>\n"
            f"Signal: <b>{signal}</b> | Score: <b>{alpha_score:+.1f}</b>\n"
        )
        if reasons:
            text += "\n".join(f"• {r}" for r in reasons[:3])

        return await self.send_message(text)

    async def send_insider_alert(self, trade: dict) -> bool:
        if not self.enabled:
            return False

        text = (
            f"🏦 <b>Insider Trade: {trade.get('ticker', '')}</b>\n"
            f"{trade.get('insider_name', 'Unknown')} ({trade.get('relationship', '')})\n"
            f"{trade.get('transaction_type', '')} {trade.get('shares', 0):,.0f} shares "
            f"@ ${trade.get('price', 0):.2f}\n"
            f"Value: ${trade.get('value', 0):,.0f}\n"
            f"Date: {trade.get('filing_date', '')}"
        )
        return await self.send_message(text)

    async def send_portfolio_alert(self, portfolio_impact: dict) -> bool:
        if not self.enabled:
            return False

        impact = portfolio_impact.get("impact_pct", 0)
        severity = "🔴" if abs(impact) > 2 else "🟡" if abs(impact) > 1 else "🟢"

        text = (
            f"{severity} <b>Portfolio Impact Alert</b>\n"
            f"Total Impact: <b>{impact:+.2f}%</b>\n"
            f"Confidence: {portfolio_impact.get('confidence', 0):.0%}\n"
        )
        return await self.send_message(text)


telegram_bot = TelegramBot()
