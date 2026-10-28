"""Market data endpoints used by the terminal UI (no auth required for read-only data)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from data_sources.fundamentals import get_earnings_transcript_summary, get_fundamentals, get_sec_filings
from data_sources.macro import get_economic_calendar, get_macro_snapshot
from data_sources.market_data import SECTORS, compute_indicators, get_history, get_quote
from data_sources.news import (get_analyst_consensus, get_news, get_political_events, get_prediction_markets,
                               get_social_sentiment)
from data_sources.sector_rotation import sector_heatmap

router = APIRouter(prefix="/api/market", tags=["market"])


def _check(symbol: str) -> str:
    s = symbol.upper().strip()
    if not s.isalpha() or len(s) > 6:
        raise HTTPException(400, "Invalid symbol")
    return s


@router.get("/symbols")
def symbols() -> list[dict]:
    return [{"symbol": s, "sector": sec} for s, sec in SECTORS.items()]


@router.get("/quote/{symbol}")
def quote(symbol: str) -> dict:
    return get_quote(_check(symbol))


@router.get("/quotes")
def quotes(symbols: str = Query("AAPL,MSFT,NVDA,SPY")) -> list[dict]:
    return [get_quote(_check(s)) for s in symbols.split(",") if s.strip()][:40]


@router.get("/history/{symbol}")
def history(symbol: str, days: int = Query(180, ge=20, le=1500)) -> dict:
    df = get_history(_check(symbol), days)
    return {"symbol": symbol.upper(), "bars": [
        {"date": str(d.date()), "open": float(o), "high": float(h), "low": float(lo), "close": float(c), "volume": int(v)}
        for d, o, h, lo, c, v in zip(df["date"], df["open"], df["high"], df["low"], df["close"], df["volume"])]}


@router.get("/indicators/{symbol}")
def indicators(symbol: str) -> dict:
    return compute_indicators(get_history(_check(symbol), 365))


@router.get("/fundamentals/{symbol}")
def fundamentals(symbol: str) -> dict:
    s = _check(symbol)
    return {"fundamentals": get_fundamentals(s), "earnings": get_earnings_transcript_summary(s),
            "filings": get_sec_filings(s), "analysts": get_analyst_consensus(s)}


@router.get("/news/{symbol}")
def news(symbol: str) -> dict:
    s = _check(symbol)
    return {"news": get_news(s), "social": get_social_sentiment(s)}


@router.get("/macro")
def macro() -> dict:
    return {"snapshot": get_macro_snapshot(), "calendar": get_economic_calendar(),
            "political": get_political_events(), "prediction_markets": get_prediction_markets()}


@router.get("/sectors")
def sectors() -> list[dict]:
    return sector_heatmap()
