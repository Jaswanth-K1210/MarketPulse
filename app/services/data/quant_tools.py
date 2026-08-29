"""
Quantitative Tool Dispatcher — Calls all quantitative tools in parallel,
returns structured JSON for downstream LLM synthesis.

This is the core of the tool-first architecture (FinSphere insight).
Instead of prompting an LLM with text, each agent node calls real quantitative
tools first, then the LLM synthesizes the structured tool outputs.
"""
import asyncio
import concurrent.futures
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QuantToolDispatcher:
    """
    Fans out to all quantitative tools in parallel for a set of tickers.
    Returns structured data that LLM nodes consume for synthesis.
    """

    def dispatch_all(self, tickers: List[str], timeout: int = 30) -> Dict[str, Dict]:
        """
        Call all quantitative tools for the given tickers in parallel.

        Returns:
            {ticker: {technical: {...}, options_flow: {...}, insider: {...},
                       fundamentals: {...}, short_interest: {...}, retail_sentiment: {...}}}
        """
        if not tickers:
            return {}

        results: Dict[str, Dict] = {t: {} for t in tickers}

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tickers) * 6, 30)) as executor:
            future_map: Dict[concurrent.futures.Future, tuple] = {}

            for ticker in tickers:
                # Technical Analysis
                fut = executor.submit(self._safe_call_technical, ticker)
                future_map[fut] = (ticker, "technical")

                # Options Flow
                fut = executor.submit(self._safe_call_options, ticker)
                future_map[fut] = (ticker, "options_flow")

                # Insider Trades
                fut = executor.submit(self._safe_call_insider, ticker)
                future_map[fut] = (ticker, "insider")

                # Fundamentals
                fut = executor.submit(self._safe_call_fundamentals, ticker)
                future_map[fut] = (ticker, "fundamentals")

                # Short Interest
                fut = executor.submit(self._safe_call_short_interest, ticker)
                future_map[fut] = (ticker, "short_interest")

                # Retail Sentiment
                fut = executor.submit(self._safe_call_retail_sentiment, ticker)
                future_map[fut] = (ticker, "retail_sentiment")

            for future in concurrent.futures.as_completed(future_map, timeout=timeout):
                ticker, tool_name = future_map[future]
                try:
                    results[ticker][tool_name] = future.result(timeout=5)
                except Exception as e:
                    logger.warning(f"Tool '{tool_name}' failed for {ticker}: {e}")
                    results[ticker][tool_name] = {"error": str(e)}

        # Add composite scores
        for ticker in tickers:
            results[ticker]["composite_scores"] = self._compute_composite(results[ticker])

        return results

    def dispatch_technical(self, tickers: List[str]) -> Dict[str, Dict]:
        """Dispatch only technical analysis for all tickers."""
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tickers), 10)) as executor:
            future_map = {executor.submit(self._safe_call_technical, t): t for t in tickers}
            for future in concurrent.futures.as_completed(future_map, timeout=15):
                ticker = future_map[future]
                try:
                    results[ticker] = future.result(timeout=5)
                except Exception as e:
                    results[ticker] = {"error": str(e)}
        return results

    def dispatch_options(self, tickers: List[str]) -> Dict[str, Dict]:
        """Dispatch only options flow for all tickers."""
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tickers), 10)) as executor:
            future_map = {executor.submit(self._safe_call_options, t): t for t in tickers}
            for future in concurrent.futures.as_completed(future_map, timeout=15):
                ticker = future_map[future]
                try:
                    results[ticker] = future.result(timeout=5)
                except Exception as e:
                    results[ticker] = {"error": str(e)}
        return results

    def dispatch_insider(self, tickers: List[str]) -> Dict[str, Dict]:
        """Dispatch only insider trades for all tickers."""
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tickers), 10)) as executor:
            future_map = {executor.submit(self._safe_call_insider, t): t for t in tickers}
            for future in concurrent.futures.as_completed(future_map, timeout=15):
                ticker = future_map[future]
                try:
                    results[ticker] = future.result(timeout=5)
                except Exception as e:
                    results[ticker] = {"error": str(e)}
        return results

    # ── Individual tool calls (each wrapped for fault tolerance) ──────────────

    def _safe_call_technical(self, ticker: str) -> dict:
        try:
            from app.services.data.technical_analysis import technical_analysis_service
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                data = loop.run_until_complete(technical_analysis_service.get_indicators(ticker))
                data["score"] = technical_analysis_service.score_technical(data)
                return data
            finally:
                loop.close()
        except Exception as e:
            return {"error": str(e)}

    def _safe_call_options(self, ticker: str) -> dict:
        try:
            from app.services.data.options_flow import options_flow_service
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                data = loop.run_until_complete(options_flow_service.get_options_flow(ticker))
                data["score"] = options_flow_service.score_options_flow(data)
                return data
            finally:
                loop.close()
        except Exception as e:
            return {"error": str(e)}

    def _safe_call_insider(self, ticker: str) -> dict:
        try:
            from app.services.data.insider_trades import insider_trades_service
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                trades = loop.run_until_complete(insider_trades_service.get_insider_trades(ticker))
                score = insider_trades_service.score_insider_activity(trades)
                return {"trades": trades[:10], "score": score, "trade_count": len(trades)}
            finally:
                loop.close()
        except Exception as e:
            return {"error": str(e)}

    def _safe_call_fundamentals(self, ticker: str) -> dict:
        try:
            from app.services.data.financial_fundamentals import financial_fundamentals_service
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                data = loop.run_until_complete(financial_fundamentals_service.get_fundamentals(ticker))
                data["score"] = financial_fundamentals_service.score_fundamentals(data)
                return data
            finally:
                loop.close()
        except Exception as e:
            return {"error": str(e)}

    def _safe_call_short_interest(self, ticker: str) -> dict:
        try:
            from app.services.data.short_interest import short_interest_service
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                data = loop.run_until_complete(short_interest_service.get_short_interest(ticker))
                data["score"] = short_interest_service.score_short_interest(data)
                return data
            finally:
                loop.close()
        except Exception as e:
            return {"error": str(e)}

    def _safe_call_retail_sentiment(self, ticker: str) -> dict:
        try:
            from app.services.data.retail_sentiment import retail_sentiment_service
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                data = loop.run_until_complete(retail_sentiment_service.get_sentiment(ticker))
                data["score"] = retail_sentiment_service.score_sentiment(data)
                return data
            finally:
                loop.close()
        except Exception as e:
            return {"error": str(e)}

    # ── Composite scoring ────────────────────────────────────────────────────

    def _compute_composite(self, ticker_data: dict) -> dict:
        """
        Weighted composite from all tool scores.
        Matches alpha_aggregator weights but uses fresh tool data.
        """
        WEIGHTS = {
            "technical": 0.20,
            "options_flow": 0.15,
            "insider": 0.20,
            "fundamentals": 0.25,
            "short_interest": 0.10,
            "retail_sentiment": 0.10,
        }

        total_score = 0.0
        total_weight = 0.0
        signal_agreement = []

        for tool, weight in WEIGHTS.items():
            tool_data = ticker_data.get(tool, {})
            if isinstance(tool_data, dict) and "error" not in tool_data:
                score = tool_data.get("score", 0.0)
                total_score += score * weight
                total_weight += weight
                if abs(score) > 1.0:
                    signal_agreement.append(score > 0)

        if total_weight > 0:
            alpha = total_score / total_weight * (total_weight / 1.0)  # normalize by available weight
        else:
            alpha = 0.0

        # Signal agreement: if all signals point same direction, boost confidence
        if len(signal_agreement) >= 3:
            all_bullish = all(signal_agreement)
            all_bearish = all(not s for s in signal_agreement)
            agreement = "strong_agreement" if (all_bullish or all_bearish) else "mixed"
        elif len(signal_agreement) >= 2:
            agreement = "partial"
        else:
            agreement = "insufficient_data"

        tools_succeeded = sum(
            1 for tool in WEIGHTS
            if isinstance(ticker_data.get(tool), dict) and "error" not in ticker_data.get(tool, {})
        )

        return {
            "alpha_score": round(max(-10.0, min(10.0, total_score)), 2),
            "signal": (
                "STRONG_BUY" if total_score >= 5 else
                "BUY" if total_score >= 2 else
                "NEUTRAL" if total_score >= -2 else
                "SELL" if total_score >= -5 else
                "STRONG_SELL"
            ),
            "agreement": agreement,
            "tools_succeeded": tools_succeeded,
            "tools_total": len(WEIGHTS),
            "data_coverage": round(tools_succeeded / len(WEIGHTS) * 100, 1),
        }

    def format_for_llm(self, ticker: str, data: dict) -> str:
        """
        Format tool output into a concise string suitable for LLM consumption.
        Strips raw data, keeps scores and key signals.
        """
        lines = [f"=== QUANTITATIVE ANALYSIS: {ticker} ==="]

        tech = data.get("technical", {})
        if tech and "error" not in tech:
            lines.append(f"Technical: price=${tech.get('price', '?')}, RSI={tech.get('rsi', '?')}, "
                         f"MACD_hist={tech.get('macd_histogram', '?')}, "
                         f"signals={tech.get('signals', [])}")

        opts = data.get("options_flow", {})
        if opts and "error" not in opts:
            lines.append(f"Options: P/C={opts.get('put_call_ratio', '?')}, "
                         f"max_pain={opts.get('max_pain', '?')}, "
                         f"unusual_count={len(opts.get('unusual_activity', []))}")

        insider = data.get("insider", {})
        if insider and "error" not in insider:
            lines.append(f"Insider: trades={insider.get('trade_count', 0)}, "
                         f"score={insider.get('score', 0):+.2f}")

        fund = data.get("fundamentals", {})
        if fund and "error" not in fund:
            lines.append(f"Fundamentals: PE={fund.get('pe_ratio', '?')}, "
                         f"revenue_growth={fund.get('revenue_growth', '?')}, "
                         f"profit_margin={fund.get('profit_margin', '?')}")

        si = data.get("short_interest", {})
        if si and "error" not in si:
            lines.append(f"Short Interest: %float={si.get('short_pct_float', '?')}, "
                         f"days_to_cover={si.get('days_to_cover', '?')}")

        retail = data.get("retail_sentiment", {})
        if retail and "error" not in retail:
            lines.append(f"Retail: sentiment={retail.get('sentiment_score', 0):+.1f}, "
                         f"bullish={retail.get('bullish_pct', 0)}%, "
                         f"mentions={retail.get('total_mentions', 0)}")

        composite = data.get("composite_scores", {})
        if composite:
            lines.append(f"COMPOSITE: alpha={composite.get('alpha_score', 0):+.2f}, "
                         f"signal={composite.get('signal', '?')}, "
                         f"agreement={composite.get('agreement', '?')}, "
                         f"coverage={composite.get('data_coverage', 0)}%")

        return "\n".join(lines)


# Singleton
quant_tool_dispatcher = QuantToolDispatcher()
