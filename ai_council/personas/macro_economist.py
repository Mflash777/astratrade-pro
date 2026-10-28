from __future__ import annotations

from typing import Any

from .base import Persona, PersonaOpinion


class MacroEconomist(Persona):
    name = "Macro Economist"
    role = "Rates, inflation, GDP, unemployment, Fed policy"
    categories = ("macro", "calendar", "prediction")
    system_prompt = ("You are a macro economist on an investment committee. You reason about interest rates, "
                     "inflation, growth, labor markets and central-bank policy. Concise, no financial advice.")

    def analyze(self, bundle: dict[str, Any]) -> PersonaOpinion:
        sig = self.relevant_signals(bundle)
        score, conf = self.weighted(sig)
        m = bundle["macro"]
        beta = bundle["fundamentals"].get("beta") or 1.0
        score *= min(1.5, max(0.6, beta))  # high-beta names are more macro-sensitive
        points = [
            f"Fed funds {m['fed_funds_rate']:.2f}% vs CPI {m['cpi_yoy']:.1f}% → real rate {m['fed_funds_rate'] - m['cpi_yoy']:+.1f}%",
            f"10y-2y spread {m['treasury_10y'] - m['treasury_2y']:+.2f}%",
            f"GDP {m['gdp_growth']:.1f}%, unemployment {m['unemployment_rate']:.1f}%",
            f"Beta {beta:.2f} scales macro sensitivity",
        ]
        stance = "supportive" if score > 0.15 else "restrictive" if score < -0.15 else "neutral"
        fallback = (f"The macro backdrop is {stance} for {bundle['symbol']}. {points[0]}. {points[1]}, "
                    f"and growth data ({points[2]}) suggests the cycle is {'late but intact' if m['gdp_growth'] > 1.5 else 'decelerating'}.")
        return self.build(bundle, max(-1, min(1, score)), conf, points, fallback, sig)
