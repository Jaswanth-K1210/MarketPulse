"""
Backtesting Engine — Tests trading strategies using vectorbt-like logic.
"Buy when Alpha Score > 7" → P&L, Sharpe, max DD.
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class Backtester:
    async def run(self, ticker: str, strategy: str = "alpha_momentum",
                  start_date: str = None, end_date: str = None,
                  initial_capital: float = 10000) -> dict:
        ticker = ticker.upper()

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        result = {
            "ticker": ticker,
            "strategy": strategy,
            "period": {"start": start_date, "end": end_date},
            "initial_capital": initial_capital,
            "final_value": initial_capital,
            "total_return_pct": 0,
            "annualized_return": 0,
            "sharpe_ratio": 0,
            "max_drawdown_pct": 0,
            "num_trades": 0,
            "win_rate": 0,
            "vs_buy_hold": {},
            "trades": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if data.empty or len(data) < 20:
                return result

            close = data["Close"]

            if strategy == "alpha_momentum":
                return await self._alpha_momentum(ticker, close, initial_capital, result)
            elif strategy == "buy_hold":
                return self._buy_and_hold(close, initial_capital, result)
            elif strategy == "sma_cross":
                return self._sma_crossover(close, initial_capital, result)
            else:
                return self._buy_and_hold(close, initial_capital, result)

        except Exception as e:
            logger.warning(f"Backtest failed for {ticker}: {e}")
            return result

    async def _alpha_momentum(self, ticker: str, close: pd.Series,
                                initial_capital: float, result: dict) -> dict:
        try:
            sma_20 = close.rolling(20).mean()
            sma_50 = close.rolling(50).mean()
            rsi = self._compute_rsi(close, 14)

            in_position = False
            position_size = 0
            cash = initial_capital
            trades = []
            entry_price = 0

            for i in range(50, len(close)):
                date = close.index[i]
                price = float(close.iloc[i])
                sma_20_val = float(sma_20.iloc[i]) if not pd.isna(sma_20.iloc[i]) else 0
                sma_50_val = float(sma_50.iloc[i]) if not pd.isna(sma_50.iloc[i]) else 0
                rsi_val = float(rsi.iloc[i]) if not pd.isna(rsi.iloc[i]) else 50

                buy_signal = (
                    sma_20_val > sma_50_val and
                    30 < rsi_val < 70
                )

                sell_signal = (
                    sma_20_val < sma_50_val or
                    rsi_val > 75
                )

                if buy_signal and not in_position and cash > 0:
                    position_size = cash / price * 0.95
                    in_position = True
                    entry_price = price
                    trades.append({
                        "date": str(date.date()),
                        "type": "BUY",
                        "price": round(price, 2),
                        "shares": round(position_size, 2),
                    })

                elif sell_signal and in_position:
                    value = position_size * price
                    pnl = value - (position_size * entry_price)
                    pnl_pct = (price - entry_price) / entry_price * 100
                    cash = value
                    in_position = False
                    trades.append({
                        "date": str(date.date()),
                        "type": "SELL",
                        "price": round(price, 2),
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 2),
                    })

            if in_position:
                final_price = float(close.iloc[-1])
                value = position_size * final_price
                cash = value

            result["final_value"] = round(cash, 2)
            result["total_return_pct"] = round((cash - initial_capital) / initial_capital * 100, 2)
            result["num_trades"] = len(trades)
            result["trades"] = trades[-20:]

            if trades:
                wins = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
                result["win_rate"] = round(wins / len(trades) * 100, 1)

            buy_hold_return = (float(close.iloc[-1]) - float(close.iloc[50])) / float(close.iloc[50]) * 100
            result["vs_buy_hold"] = {
                "strategy_return": result["total_return_pct"],
                "buy_hold_return": round(buy_hold_return, 2),
                "alpha": round(result["total_return_pct"] - buy_hold_return, 2),
            }

            daily_returns = close.pct_change().dropna()
            if len(daily_returns) > 0:
                result["annualized_return"] = round(float(daily_returns.mean() * 252 * 100), 2)
                if daily_returns.std() > 0:
                    result["sharpe_ratio"] = round(float(daily_returns.mean() / daily_returns.std() * np.sqrt(252)), 3)

                cummax = close.cummax()
                drawdown = (close - cummax) / cummax
                result["max_drawdown_pct"] = round(float(drawdown.min() * 100), 2)

        except Exception as e:
            logger.warning(f"Alpha momentum backtest failed: {e}")

        return result

    def _buy_and_hold(self, close: pd.Series, initial_capital: float, result: dict) -> dict:
        try:
            start_price = float(close.iloc[0])
            end_price = float(close.iloc[-1])
            shares = initial_capital / start_price
            final_value = shares * end_price

            result["final_value"] = round(final_value, 2)
            result["total_return_pct"] = round((final_value - initial_capital) / initial_capital * 100, 2)
            result["num_trades"] = 1
            result["win_rate"] = 100.0 if final_value > initial_capital else 0.0
            result["trades"] = [{"date": str(close.index[0].date()), "type": "BUY", "price": round(start_price, 2)},
                                {"date": str(close.index[-1].date()), "type": "SELL", "price": round(end_price, 2)}]

            daily_returns = close.pct_change().dropna()
            if len(daily_returns) > 0:
                result["annualized_return"] = round(float(daily_returns.mean() * 252 * 100), 2)
                if daily_returns.std() > 0:
                    result["sharpe_ratio"] = round(float(daily_returns.mean() / daily_returns.std() * np.sqrt(252)), 3)
                cummax = close.cummax()
                drawdown = (close - cummax) / cummax
                result["max_drawdown_pct"] = round(float(drawdown.min() * 100), 2)

        except Exception as e:
            logger.warning(f"Buy/hold backtest failed: {e}")

        return result

    def _sma_crossover(self, close: pd.Series, initial_capital: float, result: dict) -> dict:
        try:
            sma_20 = close.rolling(20).mean()
            sma_50 = close.rolling(50).mean()

            in_position = False
            cash = initial_capital
            shares = 0
            trades = []

            for i in range(50, len(close)):
                price = float(close.iloc[i])

                if sma_20.iloc[i] > sma_50.iloc[i] and not in_position:
                    shares = cash / price * 0.95
                    in_position = True
                    cash = 0
                    trades.append({"date": str(close.index[i].date()), "type": "BUY", "price": round(price, 2)})

                elif sma_20.iloc[i] < sma_50.iloc[i] and in_position:
                    cash = shares * price
                    in_position = False
                    trades.append({"date": str(close.index[i].date()), "type": "SELL", "price": round(price, 2)})

            if in_position:
                cash = shares * float(close.iloc[-1])

            result["final_value"] = round(cash, 2)
            result["total_return_pct"] = round((cash - initial_capital) / initial_capital * 100, 2)
            result["num_trades"] = len(trades)
            result["trades"] = trades[-20:]

            if trades:
                wins = sum(1 for i in range(1, len(trades), 2) if i < len(trades) and trades[i].get("price", 0) > trades[i - 1].get("price", 0))
                result["win_rate"] = round(wins / (len(trades) // 2) * 100, 1)

        except Exception as e:
            logger.warning(f"SMA crossover backtest failed: {e}")

        return result

    def _compute_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)


backtester = Backtester()
