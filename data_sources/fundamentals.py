"""Company fundamentals, SEC filings and earnings transcripts.

* Fundamentals: Alpha Vantage OVERVIEW endpoint when ALPHA_VANTAGE_API_KEY is set,
  otherwise deterministic mock financials.
* SEC filings: live query against the SEC EDGAR submissions API (free, requires a
  descriptive User-Agent per SEC policy). Falls back to mock if unreachable.
* Earnings transcripts: structured mock summaries (no free public transcript API).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from .base import Signal, SignalSource
from .market_data import SECTORS

_CIK_CACHE: dict[str, str] = {}


def _alpha_vantage_overview(symbol: str) -> dict[str, Any] | None:
    key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not key:
        return None
    try:
        r = httpx.get("https://www.alphavantage.co/query",
                      params={"function": "OVERVIEW", "symbol": symbol, "apikey": key}, timeout=10)
        data = r.json()
        if not data or "Symbol" not in data:
            return None
        f = lambda k: float(data[k]) if data.get(k) not in (None, "None", "-", "") else None  # noqa: E731
        return {
            "name": data.get("Name"), "sector": data.get("Sector"), "market_cap": f("MarketCapitalization"),
            "pe_ratio": f("PERatio"), "forward_pe": f("ForwardPE"), "peg": f("PEGRatio"), "eps": f("EPS"),
            "revenue_ttm": f("RevenueTTM"), "profit_margin": f("ProfitMargin"), "roe": f("ReturnOnEquityTTM"),
            "debt_to_equity": None, "dividend_yield": f("DividendYield"), "beta": f("Beta"),
            "revenue_growth_yoy": f("QuarterlyRevenueGrowthYOY"), "earnings_growth_yoy": f("QuarterlyEarningsGrowthYOY"),
            "source": "alpha_vantage",
        }
    except (httpx.HTTPError, ValueError):
        return None


def mock_fundamentals(symbol: str) -> dict[str, Any]:
    src = FundamentalsSource()
    rng = src.rng(symbol)
    sector = SECTORS.get(symbol.upper(), "Technology")
    growth_sector = sector in {"Technology", "Communication", "Consumer Discretionary"}
    return {
        "name": f"{symbol.upper()} Corp.",
        "sector": sector,
        "market_cap": round(rng.uniform(20e9, 3e12), 0),
        "pe_ratio": round(rng.uniform(22, 45) if growth_sector else rng.uniform(9, 22), 2),
        "forward_pe": round(rng.uniform(18, 38) if growth_sector else rng.uniform(8, 20), 2),
        "peg": round(rng.uniform(0.8, 2.8), 2),
        "eps": round(rng.uniform(1.5, 14), 2),
        "revenue_ttm": round(rng.uniform(10e9, 400e9), 0),
        "profit_margin": round(rng.uniform(0.05, 0.35), 3),
        "roe": round(rng.uniform(0.08, 0.45), 3),
        "debt_to_equity": round(rng.uniform(0.1, 1.8), 2),
        "dividend_yield": round(rng.uniform(0.0, 0.04), 4),
        "beta": round(rng.uniform(0.6, 1.8), 2),
        "revenue_growth_yoy": round(rng.uniform(-0.05, 0.3) if growth_sector else rng.uniform(-0.08, 0.12), 3),
        "earnings_growth_yoy": round(rng.uniform(-0.1, 0.4), 3),
        "source": "mock",
    }


def get_fundamentals(symbol: str) -> dict[str, Any]:
    return _alpha_vantage_overview(symbol.upper()) or mock_fundamentals(symbol)


def get_sec_filings(symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    ua = os.getenv("SEC_USER_AGENT", "AstraTradePro contact@example.com")
    headers = {"User-Agent": ua, "Accept": "application/json"}
    try:
        if not _CIK_CACHE:
            r = httpx.get("https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=10)
            r.raise_for_status()
            for row in r.json().values():
                _CIK_CACHE[row["ticker"].upper()] = str(row["cik_str"]).zfill(10)
        cik = _CIK_CACHE.get(symbol.upper())
        if not cik:
            raise ValueError("unknown ticker")
        r = httpx.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers, timeout=10)
        r.raise_for_status()
        recent = r.json()["filings"]["recent"]
        out = []
        for i in range(min(limit, len(recent["form"]))):
            out.append({"form": recent["form"][i], "filed": recent["filingDate"][i],
                        "description": recent["primaryDocDescription"][i] or recent["form"][i],
                        "accession": recent["accessionNumber"][i], "source": "sec_edgar"})
        return out
    except (httpx.HTTPError, ValueError, KeyError):
        rng = FundamentalsSource().rng(symbol, "sec")
        forms = ["10-Q", "8-K", "4", "10-K", "8-K", "SC 13G", "4", "DEF 14A"]
        return [{"form": f, "filed": f"2026-{rng.randint(1, 10):02d}-{rng.randint(1, 28):02d}",
                 "description": f"{f} filing", "accession": f"0000000000-26-{rng.randint(100000, 999999)}",
                 "source": "mock"} for f in forms[:limit]]


def get_earnings_transcript_summary(symbol: str) -> dict[str, Any]:
    rng = FundamentalsSource().rng(symbol, "earnings")
    beat = rng.random() > 0.35
    guidance = rng.choice(["raised", "maintained", "lowered"])
    themes = rng.sample(["AI capex", "margin expansion", "pricing power", "inventory normalization",
                         "FX headwinds", "share buybacks", "supply-chain easing", "demand softness in Europe",
                         "cloud growth", "cost discipline"], 4)
    return {
        "symbol": symbol.upper(),
        "quarter": "Q3 2026",
        "eps_surprise_pct": round(rng.uniform(2, 12) if beat else rng.uniform(-9, -1), 2),
        "revenue_surprise_pct": round(rng.uniform(0.5, 5) if beat else rng.uniform(-4, 0.5), 2),
        "guidance": guidance,
        "management_tone": "confident" if beat and guidance != "lowered" else "cautious",
        "key_themes": themes,
        "source": "mock",
    }


class FundamentalsSource(SignalSource):
    name = "fundamentals"
    category = "fundamental"

    def fetch(self, symbol: str) -> list[Signal]:
        f = get_fundamentals(symbol)
        signals: list[Signal] = []
        pe = f.get("pe_ratio")
        if pe:
            fair = 30 if f.get("sector") in {"Technology", "Communication"} else 18
            signals.append(Signal(self.name, "fundamental", symbol, f"Valuation: P/E {pe}",
                                  score=max(-1, min(1, (fair - pe) / fair)), confidence=0.6, details={"pe": pe, "fair_pe": fair}))
        growth = f.get("revenue_growth_yoy")
        if growth is not None:
            signals.append(Signal(self.name, "fundamental", symbol, f"Revenue growth YoY {growth:+.1%}",
                                  score=max(-1, min(1, growth * 4)), confidence=0.7, details={"revenue_growth_yoy": growth}))
        margin = f.get("profit_margin")
        if margin is not None:
            signals.append(Signal(self.name, "fundamental", symbol, f"Profit margin {margin:.1%}",
                                  score=max(-1, min(1, (margin - 0.12) * 4)), confidence=0.55, details={"profit_margin": margin}))
        de = f.get("debt_to_equity")
        if de is not None:
            signals.append(Signal(self.name, "fundamental", symbol, f"Leverage D/E {de}",
                                  score=max(-1, min(1, (1.0 - de) * 0.6)), confidence=0.5, details={"debt_to_equity": de}))
        e = get_earnings_transcript_summary(symbol)
        gscore = {"raised": 0.7, "maintained": 0.1, "lowered": -0.7}[e["guidance"]]
        signals.append(Signal(self.name, "earnings", symbol, f"Earnings: EPS surprise {e['eps_surprise_pct']:+.1f}%, guidance {e['guidance']}",
                              score=max(-1, min(1, e["eps_surprise_pct"] / 10 * 0.5 + gscore * 0.5)), confidence=0.7, details=e))
        filings = get_sec_filings(symbol, 5)
        insider_sales = sum(1 for x in filings if x["form"] == "4")
        signals.append(Signal(self.name, "sec", symbol, f"{len(filings)} recent SEC filings ({insider_sales} Form 4)",
                              score=-0.1 * insider_sales, confidence=0.3, details={"filings": filings}))
        return signals
