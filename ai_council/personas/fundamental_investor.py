from __future__ import annotations

from typing import Any

from .base import Persona, PersonaOpinion


class FundamentalInvestor(Persona):
    name = "Fundamental Investor"
    role = "Earnings, balance sheets, valuation, competitive landscape"
    categories = ("fundamental", "earnings", "sec", "analyst")
    system_prompt = ("You are a long-term fundamental investor. You reason about earnings quality, valuation, "
                     "balance-sheet strength and competitive moats. Concise, no financial advice.")

    def analyze(self, bundle: dict[str, Any]) -> PersonaOpinion:
        sig = self.relevant_signals(bundle)
        score, conf = self.weighted(sig)
        f = bundle["fundamentals"]
        earn = next((s["details"] for s in sig if s["category"] == "earnings"), {})
        points = [
            f"P/E {f.get('pe_ratio')} (fwd {f.get('forward_pe')}), PEG {f.get('peg')}",
            f"Revenue growth {(f.get('revenue_growth_yoy') or 0):+.1%}, margin {(f.get('profit_margin') or 0):.1%}",
            f"ROE {(f.get('roe') or 0):.1%}, D/E {f.get('debt_to_equity')}",
        ]
        if earn:
            points.append(f"Last quarter EPS surprise {earn.get('eps_surprise_pct', 0):+.1f}%, guidance {earn.get('guidance')}")
        quality = "high-quality compounder" if (f.get("roe") or 0) > 0.2 and (f.get("profit_margin") or 0) > 0.15 else "average-quality business"
        fallback = (f"{bundle['symbol']} screens as a {quality}. {points[0]}; {points[1]}. "
                    f"{'Valuation leaves limited margin of safety.' if (f.get('peg') or 1) > 2 else 'Valuation is reasonable relative to growth.'}")
        return self.build(bundle, score, conf, points, fallback, sig)
