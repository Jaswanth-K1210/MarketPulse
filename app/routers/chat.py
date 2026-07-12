"""
Chat API Router — Natural language queries about market data.
"Tell me about sentiment for NVDA" → returns structured data.
"""
import logging
import json
import re
from typing import Optional

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/query")
async def chat_query(
    q: str = Query(..., description="Natural language query"),
):
    query = q.lower()
    ticker = _extract_ticker(q)

    intent = _detect_intent(query)
    response = {
        "query": q,
        "intent": intent,
        "ticker": ticker,
        "response": "",
        "data": {},
    }

    if intent == "sentiment" and ticker:
        try:
            from app.services.data.retail_sentiment import retail_sentiment_service
            data = await retail_sentiment_service.get_sentiment(ticker)
            response["data"] = data
            response["response"] = (
                f"Sentiment for {ticker}: {data.get('bullish_pct', 0)}% bullish, "
                f"{data.get('bearish_pct', 0)}% bearish "
                f"({data.get('total_mentions', 0)} mentions)"
            )
        except Exception as e:
            response["response"] = f"Could not fetch sentiment: {e}"

    elif intent == "alpha" and ticker:
        try:
            from app.services.intelligence.alpha_aggregator import alpha_aggregator
            data = await alpha_aggregator.get_alpha_score(ticker)
            response["data"] = data
            response["response"] = (
                f"Alpha Score for {ticker}: {data.get('alpha_score', 0):+.1f} ({data.get('signal', 'NEUTRAL')}). "
                f"Active signals: {', '.join(data.get('active_signals', []))}"
            )
        except Exception as e:
            response["response"] = f"Could not compute alpha: {e}"

    elif intent == "insider" and ticker:
        try:
            from app.services.data.insider_trades import insider_trades_service
            data = await insider_trades_service.get_insider_trades(ticker)
            score = insider_trades_service.score_insider_activity(data)
            response["data"] = {"trades": data[:5], "score": score}
            response["response"] = (
                f"Insider activity for {ticker}: {len(data)} filings found. "
                f"Score: {score:+.1f}"
            )
        except Exception as e:
            response["response"] = f"Could not fetch insider data: {e}"

    elif intent == "fundamentals" and ticker:
        try:
            from app.services.data.financial_fundamentals import financial_fundamentals_service
            data = await financial_fundamentals_service.get_fundamentals(ticker)
            score = financial_fundamentals_service.score_fundamentals(data)
            response["data"] = data
            response["response"] = (
                f"Fundamentals for {ticker}: P/E {data.get('pe_ratio', 'N/A')}, "
                f"Revenue Growth {data.get('revenue_growth', 'N/A')}, "
                f"Score: {score:+.1f}"
            )
        except Exception as e:
            response["response"] = f"Could not fetch fundamentals: {e}"

    elif intent == "technical" and ticker:
        try:
            from app.services.data.technical_analysis import technical_analysis_service
            data = await technical_analysis_service.get_indicators(ticker)
            score = technical_analysis_service.score_technical(data)
            response["data"] = data
            response["response"] = (
                f"Technical analysis for {ticker}: RSI {data.get('rsi', 'N/A')}, "
                f"Price ${data.get('price', 'N/A')}, "
                f"Signals: {', '.join(data.get('signals', []))}. "
                f"Score: {score:+.1f}"
            )
        except Exception as e:
            response["response"] = f"Could not fetch technical data: {e}"

    elif intent == "macro":
        try:
            from app.services.data.macro_economic import MacroEconomicService
            svc = MacroEconomicService()
            data = await svc.get_snapshot()
            response["data"] = data
            response["response"] = (
                f"Fed Funds Rate: {data.get('fed_funds_rate', 'N/A')}%, "
                f"10Y Treasury: {data.get('treasury_10y', 'N/A')}%, "
                f"VIX: {data.get('vix', 'N/A')}, "
                f"CPI: {data.get('cpi', 'N/A')}%"
            )
        except Exception as e:
            response["response"] = f"Could not fetch macro data: {e}"

    elif intent == "help":
        response["response"] = (
            "I can answer questions about:\n"
            "• Sentiment for a ticker: 'sentiment for NVDA'\n"
            "• Alpha score: 'alpha score for AAPL'\n"
            "• Insider activity: 'insider trades for TSLA'\n"
            "• Fundamentals: 'fundamentals for MSFT'\n"
            "• Technical analysis: 'technical analysis for AMD'\n"
            "• Macro data: 'what is the macro outlook'"
        )
    else:
        if ticker:
            response["response"] = (
                f"I found ticker {ticker} in your query. "
                f"Try asking about sentiment, alpha, insider, fundamentals, or technical analysis."
            )
        else:
            response["response"] = (
                "I didn't understand the query. Try 'sentiment for NVDA' "
                "or 'alpha score for AAPL' or 'help'."
            )

    return response


_TICKER_STOPWORDS = {
    "A", "I", "IS", "THE", "FOR", "WHAT", "WHATS", "HOW", "AND", "OF", "ON",
    "IN", "TO", "ME", "MY", "DO", "ARE", "ABOUT", "TELL", "SHOW", "GIVE",
    "WITH", "VS", "BUY", "SELL", "NOW", "TODAY", "STOCK", "PRICE", "NEWS",
}


def _extract_ticker(q: str) -> Optional[str]:
    cashtag = re.search(r"\$([A-Za-z]{1,5})\b", q)
    if cashtag:
        return cashtag.group(1).upper()

    for token in re.findall(r"\b[A-Z]{1,5}\b", q):
        if token not in _TICKER_STOPWORDS:
            return token

    try:
        from app.config import COMPANY_TICKERS
        words = {w.upper() for w in re.findall(r"[A-Za-z]{1,5}", q)}
        for t in COMPANY_TICKERS.values():
            if t.upper() in words:
                return t.upper()
    except Exception:
        pass
    return None


def _detect_intent(query: str) -> str:
    if any(w in query for w in ["sentiment", "reddit", "wallstreetbets", "retail"]):
        return "sentiment"
    if any(w in query for w in ["alpha", "score", "rating", "overall"]):
        return "alpha"
    if any(w in query for w in ["insider", "form 4", "sec filing", "insider trade"]):
        return "insider"
    if any(w in query for w in ["fundamental", "pe", "earnings", "revenue", "financial"]):
        return "fundamentals"
    if any(w in query for w in ["technical", "rsi", "chart", "pattern", "indicator"]):
        return "technical"
    if any(w in query for w in ["macro", "fed", "treasury", "economy", "cpi", "vix"]):
        return "macro"
    if any(w in query for w in ["help", "what can", "commands"]):
        return "help"
    return "unknown"
