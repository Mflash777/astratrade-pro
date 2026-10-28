"""Multi-source intelligence layer.

Every source exposes a ``fetch(symbol)`` returning a list of :class:`Signal`
objects in a common schema so that the AI Council can consume them uniformly.
Real integrations are used when API keys are configured; otherwise deterministic
mock data is generated so the platform works out of the box.
"""

from .base import Signal, SignalSource, signal_summary
from .aggregator import IntelligenceAggregator

__all__ = ["Signal", "SignalSource", "signal_summary", "IntelligenceAggregator"]
