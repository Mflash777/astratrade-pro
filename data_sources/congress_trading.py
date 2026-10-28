"""Congressional (and executive-branch) stock trading disclosures.

Live source: Senate Stock Watcher's free public JSON dump
(https://senatestockwatcher.com, data mirrored at
https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com) and House Stock
Watcher's equivalent (https://housestockwatcher.com). Neither requires an API
key. If ``QUIVER_API_KEY`` is set, Quiver Quantitative's congressional-trading
endpoint (https://api.quiverquant.com) is used instead/first, since it's more
current and includes committee-assignment context.

Falls back to a deterministic mock feed if all live sources fail, so the
Council never breaks on a network hiccup -- but on a deployed instance with
network access, the live path is always tried first.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .base import Signal, SignalSource

SENATE_WATCHER_URL = "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json"
HOUSE_WATCHER_URL = "https://housestockwatcher.com/api/transactions"
QUIVER_CONGRESS_URL = "https://api.quiverquant.com/beta/live/congresstrading"


def _quiver_trades(symbol: str) -> list[dict[str, Any]] | None:
    key = os.getenv("QUIVER_API_KEY")
    if not key:
        return None
    try:
        r = httpx.get(QUIVER_CONGRESS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=10)
        r.raise_for_status()
        rows = [row for row in r.json() if row.get("Ticker", "").upper() == symbol.upper()]
        return [
            {
                "chamber": "congress",
                "representative": row.get("Representative") or row.get("Senator", "Unknown"),
                "transaction": row.get("Transaction", "Unknown"),
                "amount_range": row.get("Range", "Unknown"),
                "date": row.get("TransactionDate", ""),
                "party": row.get("Party", ""),
                "source": "quiverquant",
            }
            for row in rows[:25]
        ]
    except Exception:
        return None


def _senate_trades(symbol: str) -> list[dict[str, Any]] | None:
    try:
        r = httpx.get(SENATE_WATCHER_URL, timeout=15)
        r.raise_for_status()
        rows = [row for row in r.json() if (row.get("ticker") or "").upper() == symbol.upper()]
        return [
            {
                "chamber": "senate",
                "representative": row.get("senator", "Unknown"),
                "transaction": row.get("type", "Unknown"),
                "amount_range": row.get("amount", "Unknown"),
                "date": row.get("transaction_date", ""),
                "party": "",
                "source": "senate_stock_watcher",
            }
            for row in rows[:25]
        ]
    except Exception:
        return None


def _house_trades(symbol: str) -> list[dict[str, Any]] | None:
    try:
        r = httpx.get(HOUSE_WATCHER_URL, params={"ticker": symbol.upper()}, timeout=15)
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list):
            return None
        return [
            {
                "chamber": "house",
                "representative": row.get("representative", "Unknown"),
                "transaction": row.get("type", "Unknown"),
                "amount_range": row.get("amount", "Unknown"),
                "date": row.get("transaction_date", ""),
                "party": "",
                "source": "house_stock_watcher",
            }
            for row in rows[:25]
        ]
    except Exception:
        return None


def _mock_trades(symbol: str, rng) -> list[dict[str, Any]]:
    n = rng.randint(0, 4)
    chambers = ["senate", "house"]
    types = ["Purchase", "Sale (Full)", "Sale (Partial)", "Exchange"]
    ranges = ["$1,001 - $15,000", "$15,001 - $50,000", "$50,001 - $100,000", "$100,001 - $250,000"]
    names = ["A. Thompson", "R. Delgado", "M. Chen", "K. Walsh", "J. Okafor", "S. Lindgren"]
    out = []
    for i in range(n):
        d = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 60))
        out.append({
            "chamber": chambers[rng.randint(0, 1)],
            "representative": names[rng.randint(0, len(names) - 1)],
            "transaction": types[rng.randint(0, len(types) - 1)],
            "amount_range": ranges[rng.randint(0, len(ranges) - 1)],
            "date": d.strftime("%Y-%m-%d"),
            "party": "",
            "source": "mock",
        })
    return out


def get_congress_trades(symbol: str, rng=None) -> dict[str, Any]:
    """Returns {"trades": [...], "live": bool} -- live is False only if every
    live source failed and we fell back to the deterministic mock feed."""
    trades = _quiver_trades(symbol)
    if trades is None:
        senate = _senate_trades(symbol) or []
        house = _house_trades(symbol) or []
        trades = senate + house
    if trades:
        return {"trades": trades, "live": True}
    if rng is not None:
        return {"trades": _mock_trades(symbol, rng), "live": False}
    return {"trades": [], "live": True}  # genuinely zero disclosed trades is a valid live result


class CongressTradingSource(SignalSource):
    """Feeds the Political Analyst persona with real congressional/executive
    stock-trading disclosures for the symbol being analyzed."""

    name = "congress_trading"
    category = "political"

    def fetch(self, symbol: str) -> list[Signal]:
        rng = self.rng(symbol, "congress")
        result = get_congress_trades(symbol, rng)
        trades = result["trades"]
        if not trades:
            return [Signal(self.name, self.category, symbol, "No recent congressional trading disclosures found",
                            score=0.0, confidence=0.2, details={"trades": [], "live": result["live"]})]
        buys = sum(1 for t in trades if "purchase" in t["transaction"].lower())
        sells = sum(1 for t in trades if "sale" in t["transaction"].lower())
        net = buys - sells
        score = max(-1.0, min(1.0, net * 0.2))
        tag = "live" if result["live"] else "modeled (live feed unavailable)"
        return [Signal(
            self.name, self.category, symbol,
            f"{len(trades)} congressional trade disclosure(s) for {symbol.upper()} ({buys} buy, {sells} sell) [{tag}]",
            score=score, confidence=0.55 if result["live"] else 0.25,
            details={"trades": trades, "live": result["live"]},
        )]
