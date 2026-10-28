"""Common signal schema consumed by the AI Council."""

from __future__ import annotations

import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Signal:
    """A normalized, structured piece of market intelligence.

    ``score`` is always in [-1, 1]: -1 = maximally bearish, +1 = maximally bullish.
    ``confidence`` is in [0, 1].
    """

    source: str
    category: str  # market | fundamental | technical | macro | political | news | social | prediction | analyst | sector | sec | earnings | calendar
    symbol: str
    title: str
    score: float
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        self.score = max(-1.0, min(1.0, float(self.score)))
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SignalSource(ABC):
    """Base class for every intelligence source."""

    name: str = "base"
    category: str = "market"

    @abstractmethod
    def fetch(self, symbol: str) -> list[Signal]:
        """Return normalized signals for ``symbol``."""

    def rng(self, symbol: str, salt: str = "") -> random.Random:
        """Deterministic RNG per symbol so mock data is stable across calls."""
        seed = int(hashlib.sha256(f"{self.name}:{symbol}:{salt}".encode()).hexdigest()[:12], 16)
        return random.Random(seed)


def signal_summary(signals: list[Signal]) -> dict[str, Any]:
    """Aggregate signals by category into weighted scores."""
    by_cat: dict[str, list[Signal]] = {}
    for s in signals:
        by_cat.setdefault(s.category, []).append(s)
    out: dict[str, Any] = {}
    for cat, items in by_cat.items():
        weight = sum(i.confidence for i in items) or 1.0
        out[cat] = {
            "score": round(sum(i.score * i.confidence for i in items) / weight, 4),
            "count": len(items),
            "confidence": round(weight / len(items), 4),
        }
    return out
