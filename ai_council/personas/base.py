"""Base persona: every council member scores a signal bundle and explains itself."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

from ..llm import LLMClient, MockLLM

VOTE_BUY, VOTE_HOLD, VOTE_SELL = "BUY", "HOLD", "SELL"


@dataclass
class PersonaOpinion:
    persona: str
    role: str
    score: float          # -1 (strong sell) .. +1 (strong buy)
    confidence: float     # 0 .. 1
    vote: str             # BUY | HOLD | SELL
    rationale: str
    key_points: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def vote_from_score(score: float, threshold: float = 0.2) -> str:
    return VOTE_BUY if score > threshold else VOTE_SELL if score < -threshold else VOTE_HOLD


class Persona(ABC):
    name: str = "Persona"
    role: str = "Generic"
    categories: tuple[str, ...] = ()
    system_prompt: str = "You are a financial analyst. Be concise, factual and never give personal financial advice."

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or MockLLM()

    def relevant_signals(self, bundle: dict[str, Any]) -> list[dict[str, Any]]:
        return [s for s in bundle["signals"] if s["category"] in self.categories and s["confidence"] > 0]

    @staticmethod
    def weighted(signals: list[dict[str, Any]]) -> tuple[float, float]:
        if not signals:
            return 0.0, 0.1
        w = sum(s["confidence"] for s in signals)
        return sum(s["score"] * s["confidence"] for s in signals) / w, min(1.0, w / len(signals))

    @abstractmethod
    def analyze(self, bundle: dict[str, Any]) -> PersonaOpinion:
        """Produce an opinion from the normalized signal bundle."""

    def narrate(self, fallback: str, bundle: dict[str, Any], points: list[str]) -> str:
        prompt = (f"Ticker {bundle['symbol']}. Your key observations: {'; '.join(points)}. "
                  "Write 2-3 sentences of analysis from your persona's perspective. Do not give financial advice.")
        text = self.llm.complete(self.system_prompt, prompt)
        return text or fallback

    def build(self, bundle: dict[str, Any], score: float, confidence: float, points: list[str],
              fallback: str, evidence: list[dict[str, Any]]) -> PersonaOpinion:
        return PersonaOpinion(
            persona=self.name, role=self.role, score=round(score, 3), confidence=round(confidence, 3),
            vote=vote_from_score(score), rationale=self.narrate(fallback, bundle, points),
            key_points=points, evidence=[{"title": e["title"], "score": e["score"], "source": e["source"]} for e in evidence],
        )

    def rebut(self, own: PersonaOpinion, others: list[PersonaOpinion]) -> str:
        """One short debate line responding to the strongest disagreeing peer."""
        disagree = [o for o in others if o.persona != self.name and (o.score - own.score) * (own.score or 1e-9) < 0]
        if not disagree:
            return f"{self.name}: no material disagreement with the panel; holding my {own.vote} view."
        peer = max(disagree, key=lambda o: abs(o.score - own.score))
        return (f"{self.name} to {peer.persona}: I see your {peer.vote} case, but {self.role.lower()} factors "
                f"({own.key_points[0] if own.key_points else 'my evidence'}) dominate on my horizon. Staying {own.vote}.")
