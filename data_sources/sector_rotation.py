"""Sector rotation model: ranks sectors by relative momentum vs the index."""

from __future__ import annotations

from typing import Any

from .base import Signal, SignalSource
from .market_data import SECTORS, get_history

SECTOR_PROXIES: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "NVDA"], "Communication": ["GOOGL", "META"],
    "Consumer Discretionary": ["AMZN", "TSLA"], "Financials": ["JPM", "BAC", "GS"],
    "Energy": ["XOM", "CVX"], "Health Care": ["JNJ", "PFE", "UNH"], "Consumer Staples": ["PG", "KO", "WMT"],
    "Industrials": ["CAT", "BA"], "Utilities": ["NEE"], "Materials": ["LIN"], "Real Estate": ["PLD"],
}


def _ret(symbol: str, lookback: int) -> float:
    df = get_history(symbol, lookback + 5)
    return float(df["close"].iloc[-1] / df["close"].iloc[-lookback] - 1)


def sector_heatmap() -> list[dict[str, Any]]:
    bench_1m, bench_3m = _ret("SPY", 21), _ret("SPY", 63)
    rows = []
    for sector, syms in SECTOR_PROXIES.items():
        r1 = sum(_ret(s, 21) for s in syms) / len(syms)
        r3 = sum(_ret(s, 63) for s in syms) / len(syms)
        rows.append({"sector": sector, "return_1m": round(r1 * 100, 2), "return_3m": round(r3 * 100, 2),
                     "relative_1m": round((r1 - bench_1m) * 100, 2), "relative_3m": round((r3 - bench_3m) * 100, 2),
                     "constituents": syms})
    rows.sort(key=lambda x: x["relative_3m"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1
        r["phase"] = "leading" if r["relative_3m"] > 0 and r["relative_1m"] > 0 else \
                     "weakening" if r["relative_3m"] > 0 else \
                     "improving" if r["relative_1m"] > 0 else "lagging"
    return rows


class SectorRotationSource(SignalSource):
    name = "sector_rotation"
    category = "sector"

    def fetch(self, symbol: str) -> list[Signal]:
        sector = SECTORS.get(symbol.upper(), "Unknown")
        rows = sector_heatmap()
        n = len(rows)
        mine = next((r for r in rows if r["sector"] == sector), None)
        if mine is None:
            return [Signal(self.name, "sector", symbol, "Sector not in rotation model", 0.0, 0.2, {"rows": rows})]
        score = 1 - 2 * (mine["rank"] - 1) / max(n - 1, 1)
        return [Signal(self.name, "sector", symbol, f"{sector} ranks #{mine['rank']}/{n} ({mine['phase']})",
                       score=score, confidence=0.55, details={"sector": mine, "leaders": rows[:3], "laggards": rows[-3:]})]
