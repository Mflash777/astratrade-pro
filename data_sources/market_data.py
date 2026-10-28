"""Market data: OHLCV history, quotes, technical indicators.

Resolution order for historical bars (first that succeeds wins):
  1. Yahoo Finance via the ``yfinance`` package -- free, no API key, the default
     live source.
  2. Alpaca's market-data API, if ``ALPACA_API_KEY``/``ALPACA_SECRET_KEY`` are set.
  3. Deterministic synthetic price history (geometric Brownian motion), so
     charts, backtests and the Council still work with zero credentials and
     zero network access (e.g. this exact sandbox).

Set ``MARKET_DATA_SOURCE=alpaca`` or ``MARKET_DATA_SOURCE=synthetic`` to force
a specific path (useful for tests, or if Yahoo rate-limits you).
"""

from __future__ import annotations

import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import numpy as np
import pandas as pd

from .base import Signal, SignalSource

_YF_CACHE: dict[tuple[str, int], tuple[float, pd.DataFrame]] = {}
_YF_CACHE_TTL = 60  # seconds -- Yahoo will rate-limit/soft-ban aggressive polling

SECTORS: dict[str, str] = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "GOOGL": "Communication",
    "META": "Communication", "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials", "XOM": "Energy", "CVX": "Energy",
    "JNJ": "Health Care", "PFE": "Health Care", "UNH": "Health Care", "PG": "Consumer Staples",
    "KO": "Consumer Staples", "WMT": "Consumer Staples", "CAT": "Industrials", "BA": "Industrials",
    "NEE": "Utilities", "LIN": "Materials", "PLD": "Real Estate", "SPY": "Index", "QQQ": "Index",
}

BASE_PRICES: dict[str, float] = {
    "AAPL": 228.0, "MSFT": 425.0, "NVDA": 132.0, "GOOGL": 168.0, "META": 560.0, "AMZN": 190.0,
    "TSLA": 240.0, "JPM": 215.0, "BAC": 41.0, "GS": 510.0, "XOM": 118.0, "CVX": 150.0,
    "JNJ": 160.0, "PFE": 29.0, "UNH": 580.0, "PG": 170.0, "KO": 69.0, "WMT": 80.0,
    "CAT": 370.0, "BA": 160.0, "NEE": 80.0, "LIN": 470.0, "PLD": 125.0, "SPY": 575.0, "QQQ": 490.0,
}


def synthetic_history(symbol: str, days: int = 365, seed_salt: str = "") -> pd.DataFrame:
    """Deterministic GBM price path with realistic volume."""
    seed = abs(hash((symbol.upper(), seed_salt))) % (2**32)
    rng = np.random.default_rng(seed)
    base = BASE_PRICES.get(symbol.upper(), 100.0)
    mu, sigma = 0.08 / 252, 0.25 / math.sqrt(252)
    start = base * rng.uniform(0.6, 0.9)
    rets = rng.normal(mu, sigma, days)
    closes = start * np.exp(np.cumsum(rets))
    closes *= base / closes[-1]
    dates = pd.bdate_range(end=datetime.now(timezone.utc).date(), periods=days)
    opens = closes * (1 + rng.normal(0, 0.004, days))
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(0, 0.006, days)))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(0, 0.006, days)))
    vol = rng.lognormal(mean=math.log(30_000_000), sigma=0.4, size=days).astype(int)
    df = pd.DataFrame({"date": dates, "open": opens, "high": highs, "low": lows, "close": closes, "volume": vol})
    return df.round({"open": 2, "high": 2, "low": 2, "close": 2})


def _yfinance_bars(symbol: str, days: int) -> pd.DataFrame | None:
    if os.getenv("MARKET_DATA_SOURCE", "").lower() in ("alpaca", "synthetic"):
        return None
    cache_key = (symbol.upper(), days)
    cached = _YF_CACHE.get(cache_key)
    if cached and time.time() - cached[0] < _YF_CACHE_TTL:
        return cached[1]
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        period_days = max(days + 10, 30)
        hist = yf.Ticker(symbol).history(period=f"{period_days}d", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return None
        df = hist.reset_index().rename(columns={
            "Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume",
        })
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df[["date", "open", "high", "low", "close", "volume"]].tail(days).reset_index(drop=True)
        if df.empty:
            return None
        _YF_CACHE[cache_key] = (time.time(), df)
        return df
    except Exception:
        return None


def _alpaca_bars(symbol: str, days: int) -> pd.DataFrame | None:
    if os.getenv("MARKET_DATA_SOURCE", "").lower() == "synthetic":
        return None
    key, secret = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
    if not key or not secret:
        return None
    start = (datetime.now(timezone.utc) - timedelta(days=int(days * 1.5))).strftime("%Y-%m-%d")
    try:
        r = httpx.get(
            f"https://data.alpaca.markets/v2/stocks/{symbol}/bars",
            params={"timeframe": "1Day", "start": start, "limit": days, "feed": "iex"},
            headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
            timeout=10,
        )
        r.raise_for_status()
        bars = r.json().get("bars") or []
        if not bars:
            return None
        df = pd.DataFrame(bars).rename(columns={"t": "date", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df["date"] = pd.to_datetime(df["date"])
        return df[["date", "open", "high", "low", "close", "volume"]]
    except (httpx.HTTPError, ValueError, KeyError):
        return None


def get_history(symbol: str, days: int = 365) -> pd.DataFrame:
    df = _yfinance_bars(symbol.upper(), days)
    if df is None:
        df = _alpaca_bars(symbol.upper(), days)
    return df if df is not None else synthetic_history(symbol, days)


def is_live_history(symbol: str, days: int = 365) -> bool:
    """True if get_history(symbol, days) would resolve to a real data source
    rather than the synthetic fallback. Used by the API layer to flag demo data."""
    return _yfinance_bars(symbol.upper(), days) is not None or _alpaca_bars(symbol.upper(), days) is not None


def compute_indicators(df: pd.DataFrame) -> dict[str, Any]:
    close = df["close"]
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    ema12, ema26 = close.ewm(span=12).mean(), close.ewm(span=26).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9).mean()
    daily_ret = close.pct_change().dropna()
    vol_annual = float(daily_ret.tail(30).std() * math.sqrt(252)) if len(daily_ret) >= 2 else 0.0
    bb_mid, bb_std = close.rolling(20).mean(), close.rolling(20).std()
    last = float(close.iloc[-1])

    def _f(series: pd.Series) -> float | None:
        v = series.iloc[-1]
        return None if pd.isna(v) else round(float(v), 4)

    return {
        "price": last,
        "sma20": _f(sma20), "sma50": _f(sma50), "sma200": _f(sma200),
        "rsi14": _f(rsi), "macd": _f(macd), "macd_signal": _f(macd_signal),
        "bollinger_upper": _f(bb_mid + 2 * bb_std), "bollinger_lower": _f(bb_mid - 2 * bb_std),
        "volatility_30d_annualized": round(vol_annual, 4),
        "return_1m": round(float(close.iloc[-1] / close.iloc[-21] - 1), 4) if len(close) > 21 else None,
        "return_3m": round(float(close.iloc[-1] / close.iloc[-63] - 1), 4) if len(close) > 63 else None,
        "avg_volume_20d": int(df["volume"].tail(20).mean()),
        "volume_ratio": round(float(df["volume"].iloc[-1] / max(df["volume"].tail(20).mean(), 1)), 3),
    }


def get_quote(symbol: str) -> dict[str, Any]:
    df = get_history(symbol, 60)
    last, prev = float(df["close"].iloc[-1]), float(df["close"].iloc[-2])
    return {
        "symbol": symbol.upper(),
        "price": round(last, 2),
        "change": round(last - prev, 2),
        "change_pct": round((last / prev - 1) * 100, 2),
        "volume": int(df["volume"].iloc[-1]),
        "high": float(df["high"].iloc[-1]),
        "low": float(df["low"].iloc[-1]),
        "sector": SECTORS.get(symbol.upper(), "Unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "live": is_live_history(symbol, 60),
    }


class MarketDataSource(SignalSource):
    name = "market_data"
    category = "technical"

    def fetch(self, symbol: str) -> list[Signal]:
        df = get_history(symbol, 365)
        ind = compute_indicators(df)
        signals: list[Signal] = []
        price = ind["price"]

        if ind["sma50"] and ind["sma200"]:
            trend = 1.0 if ind["sma50"] > ind["sma200"] else -1.0
            signals.append(Signal(self.name, "technical", symbol, "Golden/death cross (SMA50 vs SMA200)",
                                  score=0.6 * trend, confidence=0.7, details={"sma50": ind["sma50"], "sma200": ind["sma200"]}))
        if ind["rsi14"] is not None:
            rsi = ind["rsi14"]
            score = -0.8 if rsi > 70 else 0.8 if rsi < 30 else (50 - rsi) / 50
            signals.append(Signal(self.name, "technical", symbol, f"RSI(14) = {rsi:.1f}",
                                  score=score, confidence=0.6, details={"rsi": rsi}))
        if ind["macd"] is not None and ind["macd_signal"] is not None:
            diff = ind["macd"] - ind["macd_signal"]
            signals.append(Signal(self.name, "technical", symbol, "MACD vs signal line",
                                  score=max(-1, min(1, diff / max(price * 0.01, 1e-6))), confidence=0.55,
                                  details={"macd": ind["macd"], "signal": ind["macd_signal"]}))
        signals.append(Signal(self.name, "technical", symbol, "Momentum (3m return)",
                              score=max(-1, min(1, (ind["return_3m"] or 0) * 4)), confidence=0.65,
                              details={"return_1m": ind["return_1m"], "return_3m": ind["return_3m"]}))
        signals.append(Signal(self.name, "market", symbol, "Realized volatility (30d)",
                              score=-min(1.0, ind["volatility_30d_annualized"] / 0.6), confidence=0.6,
                              details={"volatility": ind["volatility_30d_annualized"], "volume_ratio": ind["volume_ratio"]}))
        return signals
