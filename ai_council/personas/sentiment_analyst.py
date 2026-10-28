from __future__ import annotations

from typing import Any

from .base import Persona, PersonaOpinion


class SentimentAnalyst(Persona):
    name = "News & Sentiment Analyst"
    role = "Headlines, social media sentiment, prediction markets"
    categories = ("news", "social", "prediction")
    system_prompt = ("You are a news and sentiment analyst. You reason about headline flow, crowd positioning, "
                     "social-media buzz and prediction-market odds. Concise, no financial advice.")

    def analyze(self, bundle: dict[str, Any]) -> PersonaOpinion:
        sig = self.relevant_signals(bundle)
        score, conf = self.weighted(sig)
        news = next((s for s in sig if s["category"] == "news"), None)
        social = next((s["details"] for s in sig if s["category"] == "social"), {})
        points = []
        if news:
            heads = news["details"].get("headlines", [])
            points.append(f"Headline sentiment {news['score']:+.2f} across {len(heads)} stories")
            if heads:
                top = max(heads, key=lambda h: abs(h["sentiment"]))
                points.append(f"Most polarizing: \"{top['title']}\"")
        if social:
            points.append(f"{social.get('mentions_24h', 0):,} social mentions ({social.get('mention_change_pct', 0):+.0f}% d/d), {social.get('bullish_pct')}% bullish")
        contrarian = social.get("bullish_pct", 50) > 72
        if contrarian:
            points.append("Crowd euphoria is a contrarian warning")
            score -= 0.2
        fallback = (f"Narrative flow on {bundle['symbol']} is {'constructive' if score > 0.1 else 'negative' if score < -0.1 else 'mixed'}. "
                    + " ".join(points[:2]) + (" Extreme bullish positioning raises reversal risk." if contrarian else ""))
        return self.build(bundle, max(-1, min(1, score)), conf, points, fallback, sig)
