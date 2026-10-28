"""News headlines + sentiment, social-media sentiment, political events,
prediction markets and analyst consensus.

News uses NewsAPI.org when NEWS_API_KEY is set; prediction markets query the
public Polymarket Gamma API (no key required). Everything else is deterministic
mock data when live sources are unavailable.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .base import Signal, SignalSource

POSITIVE = {"beat", "beats", "surge", "surges", "record", "upgrade", "upgrades", "growth", "strong", "rally",
            "bullish", "profit", "gain", "gains", "outperform", "raises", "expands", "wins", "approval", "soars"}
NEGATIVE = {"miss", "misses", "fall", "falls", "plunge", "plunges", "downgrade", "downgrades", "lawsuit", "probe",
            "weak", "bearish", "loss", "losses", "cut", "cuts", "recall", "slump", "warning", "layoffs", "fraud"}


def lexicon_sentiment(text: str) -> float:
    words = re.findall(r"[a-z']+", text.lower())
    pos = sum(w in POSITIVE for w in words)
    neg = sum(w in NEGATIVE for w in words)
    total = pos + neg
    return 0.0 if total == 0 else (pos - neg) / total


def get_news(symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    key = os.getenv("NEWS_API_KEY")
    if key:
        try:
            r = httpx.get("https://newsapi.org/v2/everything",
                          params={"q": symbol, "language": "en", "sortBy": "publishedAt", "pageSize": limit, "apiKey": key},
                          timeout=10)
            arts = r.json().get("articles") or []
            if arts:
                return [{"title": a["title"], "source": a["source"]["name"], "published": a["publishedAt"],
                         "url": a["url"], "sentiment": round(lexicon_sentiment(a["title"] or ""), 3)} for a in arts]
        except (httpx.HTTPError, ValueError, KeyError):
            pass
    src = NewsSentimentSource()
    rng = src.rng(symbol, "news")
    templates = [
        f"{symbol} beats quarterly estimates as demand stays strong",
        f"Analysts upgrade {symbol} on margin expansion",
        f"{symbol} faces regulatory probe over data practices",
        f"{symbol} shares fall after guidance cut",
        f"{symbol} announces record buyback program",
        f"Supply-chain warning weighs on {symbol}",
        f"{symbol} expands AI partnership, shares rally",
        f"Lawsuit filed against {symbol} by former employees",
        f"{symbol} wins major government contract",
        f"Weak consumer demand hits {symbol} outlook",
    ]
    picks = rng.sample(templates, min(limit, len(templates)))
    now = datetime.now(timezone.utc)
    return [{"title": t, "source": rng.choice(["Reuters", "Bloomberg", "WSJ", "CNBC", "FT"]),
             "published": (now - timedelta(hours=rng.randint(1, 72))).isoformat(),
             "url": f"https://example.com/news/{symbol.lower()}/{i}", "sentiment": round(lexicon_sentiment(t), 3)}
            for i, t in enumerate(picks)]


def get_social_sentiment(symbol: str) -> dict[str, Any]:
    rng = SocialSentimentSource().rng(symbol, "social")
    return {
        "symbol": symbol.upper(),
        "mentions_24h": rng.randint(800, 60000),
        "mention_change_pct": round(rng.uniform(-40, 120), 1),
        "bullish_pct": round(rng.uniform(35, 75), 1),
        "platforms": {"x": round(rng.uniform(-0.4, 0.6), 2), "reddit": round(rng.uniform(-0.5, 0.6), 2), "stocktwits": round(rng.uniform(-0.3, 0.7), 2)},
        "source": "mock",
    }


def get_prediction_markets(query: str = "fed") -> list[dict[str, Any]]:
    try:
        r = httpx.get("https://gamma-api.polymarket.com/markets",
                      params={"limit": 6, "active": "true", "closed": "false", "order": "volume24hr", "ascending": "false"},
                      timeout=8)
        rows = r.json()
        out = []
        for m in rows:
            prices = m.get("outcomePrices")
            if isinstance(prices, str):
                try:
                    import json
                    prices = json.loads(prices)
                except ValueError:
                    prices = None
            yes = float(prices[0]) if prices else None
            out.append({"question": m.get("question"), "yes_probability": yes, "volume_24h": m.get("volume24hr"),
                        "source": "polymarket"})
        if out:
            return out
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        pass
    return [
        {"question": "Fed cuts rates at next FOMC meeting?", "yes_probability": 0.62, "volume_24h": 1.8e6, "source": "mock"},
        {"question": "US recession declared in 2026?", "yes_probability": 0.21, "volume_24h": 9.4e5, "source": "mock"},
        {"question": "10y Treasury above 4.5% by year end?", "yes_probability": 0.33, "volume_24h": 4.1e5, "source": "mock"},
        {"question": "New tariffs on semiconductors announced this quarter?", "yes_probability": 0.41, "volume_24h": 6.7e5, "source": "mock"},
    ]


def get_political_events() -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    return [
        {"date": (today + timedelta(days=21)).isoformat(), "event": "US midterm elections", "risk": "high",
         "sectors": ["Health Care", "Energy", "Financials"]},
        {"date": (today + timedelta(days=5)).isoformat(), "event": "Senate vote on digital-services tax bill", "risk": "medium",
         "sectors": ["Technology", "Communication"]},
        {"date": (today + timedelta(days=12)).isoformat(), "event": "EU AI Act enforcement deadline", "risk": "medium",
         "sectors": ["Technology"]},
        {"date": (today + timedelta(days=30)).isoformat(), "event": "Debt-ceiling negotiation window", "risk": "high",
         "sectors": ["Index", "Financials"]},
        {"date": (today + timedelta(days=2)).isoformat(), "event": "Trade talks: tariff review on autos", "risk": "medium",
         "sectors": ["Consumer Discretionary", "Industrials"]},
    ]


def get_analyst_consensus(symbol: str) -> dict[str, Any]:
    rng = AnalystSource().rng(symbol, "analyst")
    buy, hold = rng.randint(8, 30), rng.randint(2, 12)
    sell = rng.randint(0, 5)
    return {"symbol": symbol.upper(), "buy": buy, "hold": hold, "sell": sell,
            "consensus": "Buy" if buy > hold + sell else "Hold",
            "target_upside_pct": round(rng.uniform(-10, 28), 1), "source": "mock"}


class NewsSentimentSource(SignalSource):
    name = "news"
    category = "news"

    def fetch(self, symbol: str) -> list[Signal]:
        items = get_news(symbol)
        avg = sum(i["sentiment"] for i in items) / max(len(items), 1)
        return [Signal(self.name, "news", symbol, f"Headline sentiment across {len(items)} stories",
                       score=avg, confidence=0.55, details={"headlines": items})]


class SocialSentimentSource(SignalSource):
    name = "social"
    category = "social"

    def fetch(self, symbol: str) -> list[Signal]:
        s = get_social_sentiment(symbol)
        plat = sum(s["platforms"].values()) / 3
        crowd = (s["bullish_pct"] - 50) / 50
        return [Signal(self.name, "social", symbol, f"Social buzz: {s['mentions_24h']:,} mentions, {s['bullish_pct']}% bullish",
                       score=(plat + crowd) / 2, confidence=0.35, details=s)]


class PredictionMarketSource(SignalSource):
    name = "prediction_markets"
    category = "prediction"

    def fetch(self, symbol: str) -> list[Signal]:
        markets = get_prediction_markets()
        score = 0.0
        for m in markets:
            q = (m.get("question") or "").lower()
            p = m.get("yes_probability") or 0.5
            if "cut" in q and "rate" in q:
                score += (p - 0.5)
            elif "recession" in q or "tariff" in q:
                score -= (p - 0.3)
        return [Signal(self.name, "prediction", symbol, f"Prediction-market implied macro stance ({len(markets)} markets)",
                       score=max(-1, min(1, score)), confidence=0.45, details={"markets": markets})]


class PoliticalSource(SignalSource):
    name = "political"
    category = "political"

    def fetch(self, symbol: str) -> list[Signal]:
        from .market_data import SECTORS
        sector = SECTORS.get(symbol.upper(), "Unknown")
        events = get_political_events()
        relevant = [e for e in events if sector in e["sectors"] or "Index" in e["sectors"]]
        risk = sum(0.3 if e["risk"] == "high" else 0.15 for e in relevant)
        return [Signal(self.name, "political", symbol, f"{len(relevant)} upcoming political/regulatory events affecting {sector}",
                       score=-min(1.0, risk), confidence=0.5, details={"events": relevant, "all_events": events})]


class AnalystSource(SignalSource):
    name = "analyst"
    category = "analyst"

    def fetch(self, symbol: str) -> list[Signal]:
        a = get_analyst_consensus(symbol)
        total = a["buy"] + a["hold"] + a["sell"]
        score = (a["buy"] - a["sell"]) / total * 0.6 + max(-1, min(1, a["target_upside_pct"] / 25)) * 0.4
        return [Signal(self.name, "analyst", symbol, f"Analyst consensus {a['consensus']} ({a['buy']}B/{a['hold']}H/{a['sell']}S)",
                       score=score, confidence=0.5, details=a)]
