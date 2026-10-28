"""Vectorized-ish daily backtester with a simple trade log. PAPER / SIMULATION ONLY."""

from __future__ import annotations

from typing import Any

import pandas as pd

from data_sources.fundamentals import get_fundamentals
from data_sources.market_data import get_history

from .metrics import drawdown_series, performance_metrics, trade_stats
from .strategies import get_strategy

SIMULATION_LABEL = "SIMULATION ONLY — paper trading, no real orders are placed."


def run_backtest(symbol: str, strategy_key: str, days: int = 365, initial_cash: float = 100_000.0,
                 commission_bps: float = 1.0, slippage_bps: float = 2.0, council_score: float = 0.0,
                 strategy_params: dict[str, Any] | None = None) -> dict[str, Any]:
    symbol = symbol.upper()
    df = get_history(symbol, days + 260).reset_index(drop=True)  # warm-up for indicators
    strat = get_strategy(strategy_key, **(strategy_params or {}))
    context = {"fundamentals": get_fundamentals(symbol), "council_score": council_score}
    target = strat.signals(df, context).clip(0, 1)

    cash, qty = initial_cash, 0.0
    equity, trades = [], []
    open_trade: dict[str, Any] | None = None
    cost_rate = (commission_bps + slippage_bps) / 10_000
    start_idx = max(0, len(df) - days)

    for i in range(len(df)):
        px = float(df["close"].iloc[i])
        date = df["date"].iloc[i]
        if i >= start_idx:
            port = cash + qty * px
            desired_qty = (port * float(target.iloc[i])) / px
            delta = desired_qty - qty
            if abs(delta * px) > port * 0.01:  # ignore tiny rebalances
                fee = abs(delta) * px * cost_rate
                cash -= delta * px + fee
                qty = desired_qty
                if delta > 0 and open_trade is None:
                    open_trade = {"symbol": symbol, "entry_date": str(date.date()), "entry_price": px, "qty": round(qty, 4), "side": "buy"}
                    trades.append(open_trade)
                elif delta < 0 and open_trade is not None and qty < 1e-9:
                    open_trade.update({"exit_date": str(date.date()), "exit_price": px,
                                       "pnl": round((px - open_trade["entry_price"]) * open_trade["qty"] - fee, 2)})
                    open_trade = None
        equity.append(cash + qty * px)

    eq = pd.Series(equity[start_idx:], index=df["date"].iloc[start_idx:])
    bench = df["close"].iloc[start_idx:] / df["close"].iloc[start_idx] * initial_cash
    bench.index = eq.index
    if open_trade is not None and "pnl" not in open_trade:
        open_trade["unrealized_pnl"] = round((float(df["close"].iloc[-1]) - open_trade["entry_price"]) * open_trade["qty"], 2)

    return {
        "label": SIMULATION_LABEL,
        "symbol": symbol,
        "strategy": strat.key,
        "strategy_label": strat.label,
        "days": days,
        "initial_cash": initial_cash,
        "final_equity": round(float(eq.iloc[-1]), 2),
        "metrics": performance_metrics(eq),
        "benchmark_metrics": performance_metrics(bench),
        "trade_stats": trade_stats(trades),
        "equity_curve": [{"date": str(d.date()), "equity": round(float(v), 2), "benchmark": round(float(b), 2)}
                         for d, v, b in zip(eq.index, eq.values, bench.values)],
        "drawdown": drawdown_series(eq),
        "trades": trades,
    }
