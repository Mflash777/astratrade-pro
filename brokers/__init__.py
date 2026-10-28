"""Brokerage connectors. Register new brokers in ``BROKER_REGISTRY``."""

from __future__ import annotations

import os

from .alpaca import AlpacaConnector
from .base import (Account, ApprovalRequired, BrokerConnector, BrokerError, OrderRequest, OrderResult,
                   Position)
from .paper import PaperBroker

BROKER_REGISTRY: dict[str, type[BrokerConnector]] = {
    "alpaca": AlpacaConnector,
    "paper": PaperBroker,
}

_paper_singleton = PaperBroker()


def get_broker(name: str | None = None) -> BrokerConnector:
    """Return the requested broker, or the best available default.

    Default resolution: Alpaca if keys are configured, otherwise the built-in
    paper broker. The paper broker is a process-wide singleton so its state
    persists across requests.
    """
    name = (name or "").lower()
    if not name:
        name = "alpaca" if os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY") else "paper"
    if name == "paper":
        return _paper_singleton
    cls = BROKER_REGISTRY.get(name)
    if cls is None:
        raise BrokerError(f"Unknown broker '{name}'. Available: {', '.join(BROKER_REGISTRY)}")
    return cls()


__all__ = ["Account", "ApprovalRequired", "BrokerConnector", "BrokerError", "OrderRequest", "OrderResult", "Position",
           "AlpacaConnector", "PaperBroker", "BROKER_REGISTRY", "get_broker"]
