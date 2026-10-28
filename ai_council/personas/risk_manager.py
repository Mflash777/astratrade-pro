from __future__ import annotations

from typing import Any

from .base import Persona, PersonaOpinion


class RiskManager(Persona):
    name = "Risk Manager"
    role = "Drawdown, exposure, hedging, scenario analysis"
    categories = ("market", "political", "calendar", "sector")
    system_prompt = ("You are a portfolio risk manager. You reason about drawdowns, tail risk, concentration, "
                     "hedging and scenario analysis. You lean conservative. Concise, no financial advice.")

    def analyze(self, bundle: dict[str, Any]) -> PersonaOpinion:
        sig = self.relevant_signals(bundle)
        ind = bundle["indicators"]
        vol = ind["volatility_30d_annualized"]
        beta = bundle["fundamentals"].get("beta") or 1.0
        price = ind["price"]
        # Risk manager never votes BUY on its own; it caps enthusiasm.
        raw, conf = self.weighted(sig)
        risk_penalty = min(1.0, vol / 0.5) * 0.5 + max(0, beta - 1) * 0.3
        score = min(0.15, raw - risk_penalty)
        var_1d_95 = price * vol / (252**0.5) * 1.65
        scenarios = {
            "rate_hike_100bp": round(-0.08 * beta * 100, 1),
            "recession": round(-0.25 * beta * 100, 1),
            "election_shock": round(-0.06 * beta * 100, 1),
            "soft_landing": round(0.12 * beta * 100, 1),
        }
        points = [
            f"1-day 95% VaR ≈ ${var_1d_95:.2f}/share ({var_1d_95 / price:.1%})",
            f"Suggested stop {price * (1 - 2 * vol / 252**0.5 * 2):.2f} (2× daily σ)",
            f"Scenario P/L: rate hike {scenarios['rate_hike_100bp']}%, recession {scenarios['recession']}%, soft landing +{scenarios['soft_landing']}%",
            f"Max position size: {max(1, int(10 / max(vol / 0.2, 1)))}% of portfolio",
        ]
        fallback = (f"Risk profile for {bundle['symbol']}: {points[0]}. Beta {beta:.2f} amplifies macro shocks. "
                    f"{points[3]}; hedge via index puts or sector-pair if exposure exceeds that.")
        op = self.build(bundle, score, max(conf, 0.6), points, fallback, sig)
        op.evidence.append({"title": "Scenario analysis", "score": 0.0, "source": "risk_manager", "scenarios": scenarios})
        return op
