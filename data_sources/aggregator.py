"""Collects signals from every registered source into a Council-ready bundle."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .base import Signal, SignalSource, signal_summary
from .congress_trading import CongressTradingSource
from .fundamentals import FundamentalsSource, get_fundamentals
from .macro import MacroSource, get_macro_snapshot
from .market_data import MarketDataSource, compute_indicators, get_history, get_quote
from .news import (AnalystSource, NewsSentimentSource, PoliticalSource, PredictionMarketSource,
                   SocialSentimentSource)
from .sector_rotation import SectorRotationSource

DEFAULT_SOURCES: list[type[SignalSource]] = [
    MarketDataSource, FundamentalsSource, MacroSource, NewsSentimentSource, SocialSentimentSource,
    PredictionMarketSource, PoliticalSource, CongressTradingSource, AnalystSource, SectorRotationSource,
]


class IntelligenceAggregator:
    def __init__(self, sources: list[SignalSource] | None = None) -> None:
        self.sources = sources or [cls() for cls in DEFAULT_SOURCES]

    def collect(self, symbol: str) -> list[Signal]:
        symbol = symbol.upper()
        signals: list[Signal] = []
        with ThreadPoolExecutor(max_workers=6) as pool:
            for result in pool.map(lambda s: self._safe(s, symbol), self.sources):
                signals.extend(result)
        return signals

    @staticmethod
    def _safe(source: SignalSource, symbol: str) -> list[Signal]:
        try:
            return source.fetch(symbol)
        except Exception as exc:  # noqa: BLE001 - a failing source must never break the council
            return [Signal(source.name, source.category, symbol, f"{source.name} unavailable: {exc}", 0.0, 0.0)]

    def bundle(self, symbol: str) -> dict[str, Any]:
        symbol = symbol.upper()
        signals = self.collect(symbol)
        hist = get_history(symbol, 365)
        return {
            "symbol": symbol,
            "quote": get_quote(symbol),
            "indicators": compute_indicators(hist),
            "fundamentals": get_fundamentals(symbol),
            "macro": get_macro_snapshot(),
            "signals": [s.to_dict() for s in signals],
            "summary": signal_summary(signals),
        }
