"""
Backtesting Engine — Walk-forward validation with slippage, transaction costs,
and out-of-sample metrics. Replaces the single-pass backtester to ensure
no model result is trusted without rigorous validation.
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

import yfinance as yf
from app.core.disclaimer import DISCLAIMER

logger = logging.getLogger(__name__)



class Backtester:
    def __init__(self, slippage_bps: float = 5.0, commission_bps: float = 10.0):
        self.slippage_bps = slippage_bps
        self.commission_bps = commission_bps

    async def run(self, ticker: str, strategy: str = "alpha_momentum",
                  start_date: str = None, end_date: str = None,
                  initial_capital: float = 10000) -> dict:
        ticker = ticker.upper()

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

        result = {
            "ticker": ticker,
            "strategy": strategy,
            "period": {"start": start_date, "end": end_date},
            "initial_capital": initial_capital,
            "final_value": initial_capital,
            "total_return_pct": 0,
            "annualized_return": 0,
            "sharpe_ratio": 0,
            "calmar_ratio": 0,
            "max_drawdown_pct": 0,
            "num_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "vs_buy_hold": {},
            "walk_forward": {},
            "trades": [],
            "disclaimer": DISCLAIMER,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if data.empty or len(data) < 100:
                return result

            close = data["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            if strategy == "buy_hold":
                return self._buy_and_hold(close, initial_capital, result)
            elif strategy == "sma_cross":
                return self._sma_crossover(close, initial_capital, result)
            else:
                return await self._alpha_momentum(ticker, close, initial_capital, result)

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

                buy_signal = sma_20_val > sma_50_val and 30 < rsi_val < 70
                sell_signal = sma_20_val < sma_50_val or rsi_val > 75

                if buy_signal and not in_position and cash > 0:
                    exec_price = price * (1 + self.slippage_bps / 10000)
                    shares = cash / exec_price * 0.95
                    commission = cash * (self.commission_bps / 10000)
                    cash -= commission
                    position_size = shares
                    in_position = True
                    entry_price = exec_price
                    trades.append({
                        "date": str(date.date()),
                        "type": "BUY",
                        "price": round(exec_price, 2),
                        "shares": round(shares, 4),
                        "commission": round(commission, 4),
                    })

                elif sell_signal and in_position:
                    exec_price = price * (1 - self.slippage_bps / 10000)
                    value = position_size * exec_price
                    commission = value * (self.commission_bps / 10000)
                    pnl = value - commission - (position_size * entry_price)
                    pnl_pct = (exec_price - entry_price) / entry_price * 100
                    cash = value - commission
                    in_position = False
                    trades.append({
                        "date": str(date.date()),
                        "type": "SELL",
                        "price": round(exec_price, 2),
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 2),
                        "commission": round(commission, 4),
                    })

            if in_position:
                final_price = float(close.iloc[-1])
                exec_price = final_price * (1 - self.slippage_bps / 10000)
                value = position_size * exec_price
                commission = value * (self.commission_bps / 10000)
                cash = value - commission

            result["final_value"] = round(cash, 2)
            result["total_return_pct"] = round((cash - initial_capital) / initial_capital * 100, 2)
            result["num_trades"] = len(trades)
            result["trades"] = trades[-20:]

            self._compute_metrics(close, initial_capital, result, trades, start_idx=50)

        except Exception as e:
            logger.warning(f"Alpha momentum backtest failed: {e}")

        return result

    def _buy_and_hold(self, close: pd.Series, initial_capital: float, result: dict) -> dict:
        try:
            start_price = float(close.iloc[0])
            end_price = float(close.iloc[-1])
            exec_start = start_price * (1 + self.slippage_bps / 10000)
            exec_end = end_price * (1 - self.slippage_bps / 10000)
            commission = initial_capital * (self.commission_bps / 10000)
            shares = (initial_capital - commission) / exec_start
            final_value = shares * exec_end - shares * exec_end * (self.commission_bps / 10000)

            result["final_value"] = round(final_value, 2)
            result["total_return_pct"] = round((final_value - initial_capital) / initial_capital * 100, 2)
            result["num_trades"] = 1
            result["win_rate"] = 100.0 if final_value > initial_capital else 0.0
            result["trades"] = [
                {"date": str(close.index[0].date()), "type": "BUY", "price": round(exec_start, 2)},
                {"date": str(close.index[-1].date()), "type": "SELL", "price": round(exec_end, 2)},
            ]

            self._compute_metrics(close, initial_capital, result, result["trades"], start_idx=0)

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
                date = close.index[i]
                price = float(close.iloc[i])

                if not in_position and sma_20.iloc[i] > sma_50.iloc[i]:
                    exec_price = price * (1 + self.slippage_bps / 10000)
                    commission = cash * (self.commission_bps / 10000)
                    shares = (cash - commission) / exec_price
                    in_position = True
                    cash = 0
                    trades.append({"date": str(date.date()), "type": "BUY", "price": round(exec_price, 2)})

                elif in_position and sma_20.iloc[i] < sma_50.iloc[i]:
                    exec_price = price * (1 - self.slippage_bps / 10000)
                    value = shares * exec_price
                    commission = value * (self.commission_bps / 10000)
                    cash = value - commission
                    in_position = False
                    trades.append({"date": str(date.date()), "type": "SELL", "price": round(exec_price, 2)})

            if in_position:
                exec_price = float(close.iloc[-1]) * (1 - self.slippage_bps / 10000)
                value = shares * exec_price
                commission = value * (self.commission_bps / 10000)
                cash = value - commission

            result["final_value"] = round(cash, 2)
            result["total_return_pct"] = round((cash - initial_capital) / initial_capital * 100, 2)
            result["num_trades"] = len(trades)
            result["trades"] = trades[-20:]

            self._compute_metrics(close, initial_capital, result, trades, start_idx=50)

        except Exception as e:
            logger.warning(f"SMA crossover backtest failed: {e}")

        return result

    def walk_forward(self, ticker: str, strategy: str = "alpha_momentum",
                     start_date: str = None, end_date: str = None,
                     initial_capital: float = 10000,
                     train_days: int = 252, test_days: int = 63,
                     step_days: int = 63) -> dict:
        ticker = ticker.upper()

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

        result = {
            "ticker": ticker,
            "strategy": strategy,
            "walk_forward": {
                "train_days": train_days,
                "test_days": test_days,
                "step_days": step_days,
                "num_folds": 0,
                "folds": [],
                "oos_metrics": {},
            },
            "disclaimer": DISCLAIMER,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if data.empty or len(data) < train_days + test_days:
                result["error"] = "Insufficient data for walk-forward"
                return result

            close = data["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            oos_returns = []
            fold_results = []

            for start in range(0, len(close) - train_days - test_days + 1, step_days):
                train_end = start + train_days
                test_end = train_end + test_days

                if test_end > len(close):
                    break

                train_close = close.iloc[start:train_end]
                test_close = close.iloc[train_end:test_end]

                fold_result = self._run_fold(
                    ticker, train_close, test_close, strategy, initial_capital
                )
                fold_result["fold"] = len(fold_results) + 1
                fold_result["train_period"] = f"{train_close.index[0].date()} to {train_close.index[-1].date()}"
                fold_result["test_period"] = f"{test_close.index[0].date()} to {test_close.index[-1].date()}"
                fold_results.append(fold_result)

                if "test_returns" in fold_result:
                    oos_returns.extend(fold_result["test_returns"])

            result["walk_forward"]["num_folds"] = len(fold_results)
            result["walk_forward"]["folds"] = fold_results

            if oos_returns:
                oos_arr = np.array(oos_returns)
                result["walk_forward"]["oos_metrics"] = {
                    "mean_return": round(float(oos_arr.mean() * 252 * 100), 2),
                    "sharpe": round(float(oos_arr.mean() / oos_arr.std() * np.sqrt(252)) if oos_arr.std() > 0 else 0, 3),
                    "max_drawdown": round(float(oos_arr.min() * 100), 2),
                    "win_rate": round(float((oos_arr > 0).sum() / len(oos_arr) * 100), 1),
                    "total_observations": len(oos_arr),
                }

        except Exception as e:
            logger.warning(f"Walk-forward failed for {ticker}: {e}")
            result["error"] = str(e)

        return result

    def _run_fold(self, ticker: str, train_close: pd.Series, test_close: pd.Series,
                  strategy: str, initial_capital: float) -> dict:
        fold = {"trades": 0, "return_pct": 0}

        try:
            combined_close = pd.concat([train_close, test_close])

            if strategy == "alpha_momentum":
                sma_20 = combined_close.rolling(20).mean()
                sma_50 = combined_close.rolling(50).mean()
                rsi = self._compute_rsi(combined_close, 14)
                signal_fn = lambda i: (
                    float(sma_20.iloc[i]) > float(sma_50.iloc[i]) and 30 < float(rsi.iloc[i]) < 70,
                    float(sma_20.iloc[i]) < float(sma_50.iloc[i]) or float(rsi.iloc[i]) > 75,
                )
                warmup = 50
            elif strategy == "sma_cross":
                sma_20 = combined_close.rolling(20).mean()
                sma_50 = combined_close.rolling(50).mean()
                signal_fn = lambda i: (
                    float(sma_20.iloc[i]) > float(sma_50.iloc[i]),
                    float(sma_20.iloc[i]) < float(sma_50.iloc[i]),
                )
                warmup = 50
            else:
                signal_fn = lambda i: (False, False)
                warmup = 0

            train_len = len(train_close)
            test_start_idx = max(warmup, train_len)

            in_position = False
            cash = initial_capital
            position_size = 0
            entry_price = 0
            test_returns = []
            prev_value = initial_capital

            for i in range(test_start_idx, len(combined_close)):
                price = float(combined_close.iloc[i])
                buy_sig, sell_sig = signal_fn(i)

                if buy_sig and not in_position and cash > 0:
                    exec_price = price * (1 + self.slippage_bps / 10000)
                    commission = cash * (self.commission_bps / 10000)
                    position_size = (cash - commission) / exec_price
                    in_position = True
                    entry_price = exec_price
                    cash = 0
                    fold["trades"] += 1

                elif sell_sig and in_position:
                    exec_price = price * (1 - self.slippage_bps / 10000)
                    value = position_size * exec_price
                    commission = value * (self.commission_bps / 10000)
                    cash = value - commission
                    in_position = False
                    fold["trades"] += 1

                current_value = cash + (position_size * price if in_position else 0)
                if prev_value > 0:
                    test_returns.append(current_value / prev_value - 1)
                prev_value = current_value

            if in_position:
                final_price = float(combined_close.iloc[-1])
                exec_price = final_price * (1 - self.slippage_bps / 10000)
                cash = position_size * exec_price * (1 - self.commission_bps / 10000)

            fold["return_pct"] = round((cash - initial_capital) / initial_capital * 100, 2)
            fold["test_returns"] = test_returns

        except Exception as e:
            logger.warning(f"Fold execution failed: {e}")

        return fold

    def _compute_metrics(self, close: pd.Series, initial_capital: float,
                         result: dict, trades: list, start_idx: int = 0):
        buy_hold_start = float(close.iloc[start_idx]) if start_idx < len(close) else float(close.iloc[0])
        buy_hold_end = float(close.iloc[-1])
        buy_hold_return = (buy_hold_end - buy_hold_start) / buy_hold_start * 100

        result["vs_buy_hold"] = {
            "strategy_return": result["total_return_pct"],
            "buy_hold_return": round(buy_hold_return, 2),
            "alpha": round(result["total_return_pct"] - buy_hold_return, 2),
        }

        daily_returns = close.pct_change().dropna()
        if len(daily_returns) > 0:
            result["annualized_return"] = round(float(daily_returns.mean() * 252 * 100), 2)
            if daily_returns.std() > 0:
                result["sharpe_ratio"] = round(
                    float(daily_returns.mean() / daily_returns.std() * np.sqrt(252)), 3
                )

            cummax = close.cummax()
            drawdown = (close - cummax) / cummax
            max_dd = float(drawdown.min())
            result["max_drawdown_pct"] = round(max_dd * 100, 2)

            if max_dd != 0:
                result["calmar_ratio"] = round(
                    float(daily_returns.mean() * 252 / abs(max_dd)), 3
                )

        if trades:
            pnls = [t.get("pnl_pct", 0) for t in trades if t.get("type") == "SELL"]
            if pnls:
                wins = [p for p in pnls if p > 0]
                losses = [p for p in pnls if p <= 0]
                result["win_rate"] = round(len(wins) / len(pnls) * 100, 1)
                total_gains = sum(wins) if wins else 0
                total_losses = abs(sum(losses)) if losses else 0.001
                result["profit_factor"] = round(total_gains / total_losses, 2)

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
