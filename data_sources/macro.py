"""Macro-economic indicators and the economic calendar.

Uses the FRED API when FRED_API_KEY is set (free key from fred.stlouisfed.org);
otherwise returns a realistic static snapshot.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .base import Signal, SignalSource

FRED_SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "cpi_yoy": "CPIAUCSL",
    "unemployment_rate": "UNRATE",
    "gdp_growth": "A191RL1Q225SBEA",
    "treasury_10y": "DGS10",
    "treasury_2y": "DGS2",
}

MOCK_MACRO: dict[str, Any] = {
    "fed_funds_rate": 4.00,
    "cpi_yoy": 2.7,
    "unemployment_rate": 4.3,
    "gdp_growth": 2.1,
    "treasury_10y": 4.05,
    "treasury_2y": 3.70,
    "source": "mock",
}


def _fred_latest(series: str, key: str) -> float | None:
    try:
        r = httpx.get("https://api.stlouisfed.org/fred/series/observations",
                      params={"series_id": series, "api_key": key, "file_type": "json", "sort_order": "desc", "limit": 13},
                      timeout=10)
        obs = [o for o in r.json()["observations"] if o["value"] != "."]
        if not obs:
            return None
        if series == "CPIAUCSL" and len(obs) >= 13:
            return round((float(obs[0]["value"]) / float(obs[12]["value"]) - 1) * 100, 2)
        return float(obs[0]["value"])
    except (httpx.HTTPError, ValueError, KeyError):
        return None


def get_macro_snapshot() -> dict[str, Any]:
    key = os.getenv("FRED_API_KEY")
    if not key:
        return dict(MOCK_MACRO)
    out: dict[str, Any] = {}
    for name, series in FRED_SERIES.items():
        v = _fred_latest(series, key)
        out[name] = v if v is not None else MOCK_MACRO[name]
    out["source"] = "fred"
    return out


def get_economic_calendar(days_ahead: int = 14) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    events = [
        (2, "CPI (MoM/YoY)", "high"), (3, "Initial Jobless Claims", "medium"), (6, "FOMC Rate Decision", "high"),
        (7, "Retail Sales", "medium"), (9, "PPI", "medium"), (10, "Housing Starts", "low"),
        (13, "Nonfarm Payrolls", "high"), (14, "ISM Manufacturing PMI", "medium"),
    ]
    return [{"date": (today + timedelta(days=d)).isoformat(), "event": e, "impact": i}
            for d, e, i in events if d <= days_ahead]


class MacroSource(SignalSource):
    name = "macro"
    category = "macro"

    def fetch(self, symbol: str) -> list[Signal]:
        m = get_macro_snapshot()
        curve = m["treasury_10y"] - m["treasury_2y"]
        real_rate = m["fed_funds_rate"] - m["cpi_yoy"]
        signals = [
            Signal(self.name, "macro", symbol, f"Yield curve 10y-2y = {curve:+.2f}%",
                   score=max(-1, min(1, curve * 1.5)), confidence=0.6, details={"spread": curve}),
            Signal(self.name, "macro", symbol, f"Real policy rate = {real_rate:+.2f}%",
                   score=max(-1, min(1, -real_rate / 3)), confidence=0.6,
                   details={"fed_funds": m["fed_funds_rate"], "cpi": m["cpi_yoy"]}),
            Signal(self.name, "macro", symbol, f"GDP growth {m['gdp_growth']:.1f}%, unemployment {m['unemployment_rate']:.1f}%",
                   score=max(-1, min(1, (m["gdp_growth"] - 1.5) / 2 - (m["unemployment_rate"] - 4.0) / 3)), confidence=0.65,
                   details={"gdp": m["gdp_growth"], "unemployment": m["unemployment_rate"]}),
        ]
        cal = get_economic_calendar(7)
        high = [e for e in cal if e["impact"] == "high"]
        signals.append(Signal(self.name, "calendar", symbol, f"{len(high)} high-impact macro events in next 7 days",
                              score=-0.15 * len(high), confidence=0.5, details={"events": cal}))
        return signals
