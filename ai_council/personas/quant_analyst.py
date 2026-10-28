from __future__ import annotations

from typing import Any

from .base import Persona, PersonaOpinion


class QuantAnalyst(Persona):
    name = "Quant Analyst"
    role = "Technical indicators, volatility, risk models, backtests"
    categories = ("technical", "market")
    system_prompt = ("You are a quantitative analyst. You reason about trend, momentum, mean reversion, "
                     "realized volatility and statistical edge. Concise, no financial advice.")

    def analyze(self, bundle: dict[str, Any]) -> PersonaOpinion:
        sig = self.relevant_signals(bundle)
        score, conf = self.weighted(sig)
        ind = bundle["indicators"]
        points = []
        if ind.get("sma50") and ind.get("sma200"):
            points.append(f"SMA50 {'>' if ind['sma50'] > ind['sma200'] else '<'} SMA200 ({'uptrend' if ind['sma50'] > ind['sma200'] else 'downtrend'})")
        if ind.get("rsi14") is not None:
            r = ind["rsi14"]
            points.append(f"RSI(14) {r:.0f} ({'overbought' if r > 70 else 'oversold' if r < 30 else 'neutral'})")
        if ind.get("macd") is not None and ind.get("macd_signal") is not None:
            points.append(f"MACD {'above' if ind['macd'] > ind['macd_signal'] else 'below'} signal")
        points.append(f"30d realized vol {ind['volatility_30d_annualized']:.0%} annualized")
        points.append(f"3m return {(ind.get('return_3m') or 0):+.1%}, volume ratio {ind['volume_ratio']:.2f}x")
        fallback = (f"Price action for {bundle['symbol']}: {'; '.join(points[:3])}. "
                    f"Volatility at {ind['volatility_30d_annualized']:.0%} is {'elevated' if ind['volatility_30d_annualized'] > 0.35 else 'moderate'}; "
                    "position sizing should scale inversely with it.")
        return self.build(bundle, score, conf, points, fallback, sig)
