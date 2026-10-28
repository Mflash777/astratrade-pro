"""Council orchestrator: gather intelligence → personas opine → debate → vote → synthesize."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from data_sources import IntelligenceAggregator

from .llm import LLMClient, get_llm_client
from .personas import ANALYST_PERSONAS, Optimizer, Persona, PersonaOpinion

DISCLAIMER = "Not financial advice. Trades require user approval."


class CouncilOrchestrator:
    def __init__(self, llm: LLMClient | None = None, aggregator: IntelligenceAggregator | None = None,
                 personas: list[type[Persona]] | None = None) -> None:
        self.llm = llm or get_llm_client()
        self.aggregator = aggregator or IntelligenceAggregator()
        self.personas: list[Persona] = [cls(self.llm) for cls in (personas or ANALYST_PERSONAS)]
        self.optimizer = Optimizer(self.llm)

    def analyze_symbol(self, symbol: str, question: str | None = None) -> dict[str, Any]:
        bundle = self.aggregator.bundle(symbol)
        return self.deliberate(bundle, question)

    def deliberate(self, bundle: dict[str, Any], question: str | None = None) -> dict[str, Any]:
        opinions: list[PersonaOpinion] = [p.analyze(bundle) for p in self.personas]
        debate = [p.rebut(o, opinions) for p, o in zip(self.personas, opinions)]
        votes = {"BUY": 0, "HOLD": 0, "SELL": 0}
        for o in opinions:
            votes[o.vote] += 1
        final = self.optimizer.synthesize(opinions, bundle)
        risk = next((o for o in opinions if o.persona == "Risk Manager"), None)
        return {
            "symbol": bundle["symbol"],
            "question": question or f"Should the portfolio be long {bundle['symbol']}?",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "quote": bundle["quote"],
            "signal_summary": bundle["summary"],
            "opinions": [o.to_dict() for o in opinions],
            "debate": debate,
            "votes": votes,
            "final": final.to_dict(),
            "recommendation": {
                "action": final.vote,
                "score": final.score,
                "confidence": final.confidence,
                "max_position_pct": self._position_size(risk),
                "requires_user_approval": True,
            },
            "disclaimer": DISCLAIMER,
        }

    @staticmethod
    def _position_size(risk: PersonaOpinion | None) -> float:
        if not risk:
            return 5.0
        for p in risk.key_points:
            if p.startswith("Max position size:"):
                try:
                    return float(p.split(":")[1].strip().rstrip("% of portfolio"))
                except ValueError:
                    break
        return 5.0

    def portfolio_health(self, positions: list[dict[str, Any]]) -> dict[str, Any]:
        """Run the council per holding and aggregate into a portfolio report."""
        total = sum(abs(float(p.get("market_value", 0))) for p in positions) or 1.0
        reports, weighted = [], 0.0
        for p in positions:
            r = self.analyze_symbol(p["symbol"])
            w = abs(float(p.get("market_value", 0))) / total
            weighted += r["final"]["score"] * w
            reports.append({"symbol": p["symbol"], "weight": round(w, 4), "action": r["recommendation"]["action"],
                            "score": r["final"]["score"], "summary": r["final"]["rationale"]})
        concentration = max((r["weight"] for r in reports), default=0.0)
        health = "healthy" if weighted > 0.1 and concentration < 0.3 else "watch" if weighted > -0.1 else "at risk"
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": health,
            "weighted_score": round(weighted, 3),
            "max_concentration": round(concentration, 3),
            "holdings": reports,
            "suggestions": self._suggestions(reports),
            "disclaimer": DISCLAIMER,
        }

    @staticmethod
    def _suggestions(reports: list[dict[str, Any]]) -> list[str]:
        out = []
        for r in reports:
            if r["weight"] > 0.3:
                out.append(f"Trim {r['symbol']}: {r['weight']:.0%} of portfolio exceeds 30% concentration limit.")
            if r["action"] == "SELL" and r["weight"] > 0.05:
                out.append(f"Review {r['symbol']}: council leans SELL (score {r['score']:+.2f}).")
        return out or ["No rebalancing actions suggested by the council."]
