"""Portfolio sync, risk metrics, rebalancing and Council health reports."""

from __future__ import annotations

import math

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from brokers import BrokerError, get_broker
from data_sources.market_data import SECTORS, get_history

from ..audit import audit
from ..auth import get_current_user
from ..db import User, get_db
from .council import get_council

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

SCENARIOS = {
    "rate_hike_100bp": {"label": "Fed hikes 100bp", "index_shock": -0.08},
    "rate_cut_100bp": {"label": "Fed cuts 100bp", "index_shock": 0.06},
    "recession": {"label": "Recession", "index_shock": -0.25},
    "election_shock": {"label": "Contested election", "index_shock": -0.07},
    "soft_landing": {"label": "Soft landing", "index_shock": 0.12},
    "oil_spike": {"label": "Oil +40%", "index_shock": -0.05},
}


def _positions(broker: str | None) -> list[dict]:
    try:
        return [p.to_dict() for p in get_broker(broker).get_positions()]
    except BrokerError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/")
def portfolio(broker: str | None = None, user: User = Depends(get_current_user)) -> dict:
    try:
        b = get_broker(broker)
        acct = b.get_account().to_dict()
    except BrokerError as exc:
        raise HTTPException(502, str(exc)) from exc
    pos = _positions(broker)
    total = sum(p["market_value"] for p in pos) or 1.0
    for p in pos:
        p["weight"] = round(p["market_value"] / total, 4)
        p["sector"] = SECTORS.get(p["symbol"], "Unknown")
    sectors: dict[str, float] = {}
    for p in pos:
        sectors[p["sector"]] = sectors.get(p["sector"], 0) + p["weight"]
    return {"account": acct, "positions": pos, "sector_weights": {k: round(v, 4) for k, v in sectors.items()},
            "paper": acct.get("paper", True)}


@router.get("/risk")
def risk(broker: str | None = None, user: User = Depends(get_current_user)) -> dict:
    pos = _positions(broker)
    if not pos:
        return {"positions": 0, "message": "No positions", "scenarios": {}}
    symbols = [p["symbol"] for p in pos]
    values = np.array([p["market_value"] for p in pos])
    weights = values / values.sum()
    rets = np.column_stack([get_history(s, 252)["close"].pct_change().dropna().tail(250).values for s in symbols])
    spy = get_history("SPY", 252)["close"].pct_change().dropna().tail(250).values
    n = min(len(spy), rets.shape[0])
    rets, spy = rets[-n:], spy[-n:]
    cov = np.cov(rets.T) if len(symbols) > 1 else np.array([[np.var(rets[:, 0])]])
    port_vol = float(math.sqrt(weights @ cov @ weights) * math.sqrt(252))
    port_ret = rets @ weights
    betas = [float(np.cov(rets[:, i], spy)[0, 1] / np.var(spy)) for i in range(len(symbols))]
    port_beta = float(np.dot(weights, betas))
    var95 = float(-np.percentile(port_ret, 5) * values.sum())
    cvar95 = float(-port_ret[port_ret <= np.percentile(port_ret, 5)].mean() * values.sum())
    corr = np.corrcoef(rets.T) if len(symbols) > 1 else np.array([[1.0]])
    hhi = float((weights**2).sum())
    scenarios = {k: {"label": v["label"], "pnl": round(v["index_shock"] * port_beta * values.sum(), 2),
                     "pnl_pct": round(v["index_shock"] * port_beta * 100, 2)} for k, v in SCENARIOS.items()}
    return {
        "positions": len(pos), "total_value": round(float(values.sum()), 2),
        "annualized_volatility": round(port_vol, 4), "beta": round(port_beta, 3),
        "var_95_1d": round(var95, 2), "cvar_95_1d": round(cvar95, 2),
        "concentration_hhi": round(hhi, 4), "effective_positions": round(1 / hhi, 2),
        "per_position": [{"symbol": s, "weight": round(float(w), 4), "beta": round(b, 3),
                          "vol": round(float(rets[:, i].std() * math.sqrt(252)), 4)}
                         for i, (s, w, b) in enumerate(zip(symbols, weights, betas))],
        "correlation": {"symbols": symbols, "matrix": [[round(float(x), 3) for x in row] for row in corr]},
        "scenarios": scenarios,
    }


@router.get("/rebalance")
def rebalance(broker: str | None = None, max_weight: float = 0.25, user: User = Depends(get_current_user)) -> dict:
    pos = _positions(broker)
    total = sum(p["market_value"] for p in pos) or 1.0
    suggestions = []
    for p in pos:
        w = p["market_value"] / total
        if w > max_weight:
            excess = (w - max_weight) * total
            suggestions.append({"symbol": p["symbol"], "action": "trim", "current_weight": round(w, 4),
                                "target_weight": max_weight, "notional": round(excess, 2),
                                "qty": round(excess / p["current_price"], 4)})
    sectors: dict[str, float] = {}
    for p in pos:
        sec = SECTORS.get(p["symbol"], "Unknown")
        sectors[sec] = sectors.get(sec, 0) + p["market_value"] / total
    for sec, w in sectors.items():
        if w > 0.4:
            suggestions.append({"sector": sec, "action": "reduce sector exposure", "current_weight": round(w, 4), "target_weight": 0.4})
    return {"max_weight": max_weight, "suggestions": suggestions or [{"action": "none", "message": "Portfolio within limits"}],
            "note": "Suggestions only. Any trade requires explicit approval via /api/brokers/orders."}


@router.get("/health")
def health(request: Request, broker: str | None = None, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> dict:
    pos = _positions(broker)
    if not pos:
        return {"health": "empty", "holdings": [], "suggestions": ["No positions to analyze."],
                "disclaimer": "Not financial advice. Trades require user approval."}
    report = get_council().portfolio_health(pos)
    audit(db, "council.portfolio_health", "portfolio", {"health": report["health"]}, user_id=user.id, request=request)
    return report
