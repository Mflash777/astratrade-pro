"""Strategy implementations. Each returns a target position in [-1, 1] (fraction
of capital, long-only here so [0, 1]) for every bar. SIMULATION ONLY."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd


class Strategy(ABC):
    key: str = "base"
    label: str = "Base"
    description: str = ""

    def __init__(self, **params: Any) -> None:
        self.params = params

    @abstractmethod
    def signals(self, df: pd.DataFrame, context: dict[str, Any]) -> pd.Series:
        """Return target exposure per bar (0..1), indexed like ``df``."""


class MomentumStrategy(Strategy):
    key, label = "momentum", "Momentum"
    description = "Long when fast SMA is above slow SMA and 3-month return is positive."

    def signals(self, df: pd.DataFrame, context: dict[str, Any]) -> pd.Series:
        fast, slow = self.params.get("fast", 20), self.params.get("slow", 50)
        c = df["close"]
        trend = (c.rolling(fast).mean() > c.rolling(slow).mean()).astype(float)
        mom = (c.pct_change(63) > 0).astype(float)
        return (trend * mom).fillna(0.0)


class MeanReversionStrategy(Strategy):
    key, label = "mean_reversion", "Mean Reversion"
    description = "Buy when price is >2σ below its 20-day mean (RSI<30); exit at the mean."

    def signals(self, df: pd.DataFrame, context: dict[str, Any]) -> pd.Series:
        c = df["close"]
        mid, sd = c.rolling(20).mean(), c.rolling(20).std()
        z = (c - mid) / sd.replace(0, np.nan)
        out = pd.Series(0.0, index=df.index)
        holding = 0.0
        for i in range(len(df)):
            zi = z.iloc[i]
            if np.isnan(zi):
                out.iloc[i] = 0.0
                continue
            if holding == 0.0 and zi < -self.params.get("entry_z", 2.0):
                holding = 1.0
            elif holding == 1.0 and zi >= 0:
                holding = 0.0
            out.iloc[i] = holding
        return out


class FundamentalStrategy(Strategy):
    key, label = "fundamental", "Fundamental"
    description = "Hold when fundamentals score (valuation + growth + quality) is positive; rebalance monthly."

    def signals(self, df: pd.DataFrame, context: dict[str, Any]) -> pd.Series:
        f = context.get("fundamentals", {})
        pe, growth, margin = f.get("pe_ratio") or 20, f.get("revenue_growth_yoy") or 0, f.get("profit_margin") or 0.1
        score = (25 - pe) / 25 * 0.4 + growth * 2 * 0.4 + (margin - 0.1) * 2 * 0.2
        exposure = 1.0 if score > 0 else 0.3
        # Scale exposure by drawdown from 1y high (cheaper = larger)
        c = df["close"]
        dd = c / c.rolling(252, min_periods=20).max() - 1
        return (exposure * (1 + dd.clip(-0.4, 0) * -0.5)).fillna(exposure).clip(0, 1)


class AIHybridStrategy(Strategy):
    key, label = "ai_hybrid", "AI Hybrid"
    description = "Blends momentum, mean reversion and fundamentals, weighted by the Council's final score."

    def signals(self, df: pd.DataFrame, context: dict[str, Any]) -> pd.Series:
        council = float(context.get("council_score", 0.0))
        m = MomentumStrategy().signals(df, context)
        r = MeanReversionStrategy().signals(df, context)
        f = FundamentalStrategy().signals(df, context)
        blend = 0.4 * m + 0.2 * r + 0.4 * f
        tilt = 1.0 + 0.5 * council  # council score in [-1,1] → multiplier 0.5..1.5
        return (blend * tilt).clip(0, 1)


STRATEGIES: dict[str, type[Strategy]] = {s.key: s for s in (MomentumStrategy, MeanReversionStrategy, FundamentalStrategy, AIHybridStrategy)}


def get_strategy(key: str, **params: Any) -> Strategy:
    if key not in STRATEGIES:
        raise ValueError(f"Unknown strategy '{key}'. Available: {', '.join(STRATEGIES)}")
    return STRATEGIES[key](**params)
