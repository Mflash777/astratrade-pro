from __future__ import annotations

from typing import Any

from .base import Persona, PersonaOpinion, vote_from_score


class Optimizer(Persona):
    name = "Optimizer"
    role = "Synthesizes all viewpoints into a final recommendation"
    categories = ()
    system_prompt = ("You chair an investment committee. You weigh each member's view by its confidence and "
                     "produce a balanced synthesis. Concise, no financial advice.")

    WEIGHTS = {
        "Macro Economist": 1.0, "Quant Analyst": 1.1, "Fundamental Investor": 1.2, "Political Analyst": 0.8,
        "News & Sentiment Analyst": 0.8, "Risk Manager": 1.3,
    }

    def analyze(self, bundle: dict[str, Any]) -> PersonaOpinion:
        raise RuntimeError("Optimizer.synthesize(opinions, bundle) must be used instead of analyze().")

    def synthesize(self, opinions: list[PersonaOpinion], bundle: dict[str, Any]) -> PersonaOpinion:
        total_w = sum(self.WEIGHTS.get(o.persona, 1.0) * o.confidence for o in opinions) or 1.0
        score = sum(self.WEIGHTS.get(o.persona, 1.0) * o.confidence * o.score for o in opinions) / total_w
        votes = {"BUY": 0, "HOLD": 0, "SELL": 0}
        for o in opinions:
            votes[o.vote] += 1
        disp = max(o.score for o in opinions) - min(o.score for o in opinions)
        conf = max(0.1, min(1.0, (sum(o.confidence for o in opinions) / len(opinions)) * (1 - disp / 4)))
        strongest = max(opinions, key=lambda o: abs(o.score) * o.confidence)
        points = [
            f"Weighted score {score:+.2f}; votes BUY {votes['BUY']} / HOLD {votes['HOLD']} / SELL {votes['SELL']}",
            f"Dispersion {disp:.2f} ({'consensus' if disp < 0.6 else 'contested'})",
            f"Strongest conviction: {strongest.persona} ({strongest.vote}, {strongest.score:+.2f})",
        ]
        vote = vote_from_score(score, threshold=0.15)
        fallback = (f"Synthesis for {bundle['symbol']}: the council leans {vote} with a weighted score of {score:+.2f}. "
                    f"{strongest.persona} carries the most conviction; "
                    f"{'views are broadly aligned' if disp < 0.6 else 'the panel is split, so conviction is tempered'}. "
                    "Risk-manager sizing limits apply.")
        return PersonaOpinion(persona=self.name, role=self.role, score=round(score, 3), confidence=round(conf, 3),
                              vote=vote, rationale=self.narrate(fallback, bundle, points), key_points=points,
                              evidence=[{"title": o.persona, "score": o.score, "source": o.vote} for o in opinions])
