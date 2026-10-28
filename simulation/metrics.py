"""Performance metrics for simulated equity curves."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def performance_metrics(equity: pd.Series, risk_free: float = 0.04, periods: int = 252) -> dict[str, Any]:
    equity = equity.dropna()
    if len(equity) < 2:
        return {"total_return": 0.0, "cagr": 0.0, "sharpe": 0.0, "sortino": 0.0, "max_drawdown": 0.0,
                "volatility": 0.0, "calmar": 0.0, "days": len(equity)}
    rets = equity.pct_change().dropna()
    total = float(equity.iloc[-1] / equity.iloc[0] - 1)
    years = len(equity) / periods
    cagr = float((1 + total) ** (1 / years) - 1) if years > 0 and total > -1 else -1.0
    vol = float(rets.std() * math.sqrt(periods))
    excess = rets - risk_free / periods
    sharpe = float(excess.mean() / rets.std() * math.sqrt(periods)) if rets.std() > 0 else 0.0
    downside = rets[rets < 0].std()
    sortino = float(excess.mean() / downside * math.sqrt(periods)) if downside and downside > 0 else 0.0
    peak = equity.cummax()
    dd = (equity / peak - 1)
    max_dd = float(dd.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    return {
        "total_return": round(total, 4), "cagr": round(cagr, 4), "sharpe": round(sharpe, 3), "sortino": round(sortino, 3),
        "max_drawdown": round(max_dd, 4), "volatility": round(vol, 4), "calmar": round(calmar, 3),
        "best_day": round(float(rets.max()), 4), "worst_day": round(float(rets.min()), 4),
        "win_rate_days": round(float((rets > 0).mean()), 4), "days": int(len(equity)),
    }


def drawdown_series(equity: pd.Series) -> list[float]:
    peak = equity.cummax()
    return [round(float(x), 4) for x in (equity / peak - 1).fillna(0)]


def trade_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    closed = [t for t in trades if t.get("pnl") is not None]
    if not closed:
        return {"trades": len(trades), "closed": 0, "win_rate": 0.0, "avg_pnl": 0.0, "profit_factor": 0.0}
    pnls = np.array([t["pnl"] for t in closed])
    wins, losses = pnls[pnls > 0].sum(), -pnls[pnls < 0].sum()
    return {"trades": len(trades), "closed": len(closed), "win_rate": round(float((pnls > 0).mean()), 4),
            "avg_pnl": round(float(pnls.mean()), 2),
            "profit_factor": round(float(wins / losses), 3) if losses > 0 else float("inf") if wins > 0 else 0.0}
