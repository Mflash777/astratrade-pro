from __future__ import annotations

from typing import Any

from .base import Persona, PersonaOpinion


class PoliticalAnalyst(Persona):
    name = "Political Analyst"
    role = "Elections, legislation, geopolitical risk, regulatory changes"
    categories = ("political", "prediction")
    system_prompt = ("You are a political-risk analyst. You reason about elections, legislation, regulation, "
                     "trade policy and geopolitics and how they map to sectors. Concise, no financial advice.")

    def analyze(self, bundle: dict[str, Any]) -> PersonaOpinion:
        sig = self.relevant_signals(bundle)
        score, conf = self.weighted(sig)
        pol = next((s["details"] for s in sig if s["source"] == "political"), {"events": []})
        congress = next((s["details"] for s in sig if s["source"] == "congress_trading"), {"trades": [], "live": False})
        events = pol.get("events", [])
        trades = congress.get("trades", [])
        points = [f"{e['event']} ({e['date']}, {e['risk']} risk)" for e in events[:3]] or ["No sector-specific political catalysts in window"]
        if trades:
            buys = sum(1 for t in trades if "purchase" in t["transaction"].lower())
            sells = sum(1 for t in trades if "sale" in t["transaction"].lower())
            points.append(f"Congressional disclosures: {buys} buy / {sells} sell in {bundle['symbol']} recently"
                          f"{'' if congress.get('live') else ' (modeled)'}")
        high = sum(1 for e in events if e["risk"] == "high")
        fallback = (f"{bundle['symbol']}'s sector faces {len(events)} upcoming political/regulatory catalysts, {high} of them high-risk. "
                    f"{'Headline risk argues for tighter stops into these dates.' if high else 'Policy risk looks manageable near term.'} "
                    + (f"Congress has disclosed {len(trades)} recent trade(s) in this name." if trades else ""))
        return self.build(bundle, score, conf, points, fallback, sig)
