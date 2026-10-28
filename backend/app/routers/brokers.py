"""Brokerage endpoints. The approval flow is:

1. POST /api/brokers/recommend  → Council proposes a trade, stored as *pending* with a token.
2. POST /api/brokers/orders     → user submits the token with ``approve=true`` (or rejects).
   Only then is the order sent to the broker. Every step is audit-logged.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from brokers import BROKER_REGISTRY, ApprovalRequired, BrokerError, OrderRequest, get_broker

from ..audit import audit
from ..auth import get_current_user
from ..db import TradeRecommendation, User, get_db
from .council import get_council

router = APIRouter(prefix="/api/brokers", tags=["brokers"])


def _broker(name: str | None):
    try:
        return get_broker(name)
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/")
def list_brokers() -> list[dict]:
    return [{"name": n, "supports_fractional": c.supports_fractional, "order_types": list(c.supported_order_types)}
            for n, c in BROKER_REGISTRY.items()]


@router.get("/account")
def account(broker: str | None = None, user: User = Depends(get_current_user)) -> dict:
    try:
        return _broker(broker).get_account().to_dict()
    except BrokerError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/positions")
def positions(broker: str | None = None, user: User = Depends(get_current_user)) -> list[dict]:
    try:
        return [p.to_dict() for p in _broker(broker).get_positions()]
    except BrokerError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/orders")
def orders(broker: str | None = None, status: str = "all", user: User = Depends(get_current_user)) -> list[dict]:
    try:
        return [o.to_dict() for o in _broker(broker).list_orders(status)]
    except BrokerError as exc:
        raise HTTPException(502, str(exc)) from exc


class RecommendIn(BaseModel):
    symbol: str = Field(..., max_length=6)
    budget: float = Field(1000.0, gt=0, description="Dollar budget for a BUY recommendation")
    order_type: str = "market"


@router.post("/recommend")
def recommend(body: RecommendIn, request: Request, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> dict:
    verdict = get_council().analyze_symbol(body.symbol.upper())
    action = verdict["recommendation"]["action"]
    if action == "HOLD":
        return {"recommendation": None, "council": verdict, "message": "Council recommends HOLD — no trade proposed."}
    px = verdict["quote"]["price"]
    qty = round(body.budget / px, 4)
    rec = TradeRecommendation(user_id=user.id, token=secrets.token_urlsafe(24), symbol=verdict["symbol"],
                              side="buy" if action == "BUY" else "sell", qty=qty, order_type=body.order_type,
                              limit_price=px if body.order_type == "limit" else None,
                              rationale=verdict["final"]["rationale"])
    db.add(rec)
    db.commit()
    db.refresh(rec)
    audit(db, "trade.recommended", f"recommendation:{rec.id}", {"symbol": rec.symbol, "side": rec.side, "qty": qty},
          user_id=user.id, request=request)
    return {"recommendation": _rec_out(rec), "council": verdict,
            "message": "Review and approve explicitly. Nothing is sent to the broker until you approve."}


@router.get("/recommendations")
def recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(TradeRecommendation).filter(TradeRecommendation.user_id == user.id) \
        .order_by(TradeRecommendation.created_at.desc()).limit(50).all()
    return [_rec_out(r) for r in rows]


class OrderIn(BaseModel):
    approval_token: str
    approve: bool
    broker: str | None = None
    # Optional overrides the user can edit in the approval modal
    qty: float | None = None
    notional: float | None = None
    order_type: str | None = None
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: str = "day"
    confirm_phrase: str = Field("", description='Must equal "I APPROVE" for live (non-paper) brokers')


@router.post("/orders")
def submit_order(body: OrderIn, request: Request, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict:
    rec = db.query(TradeRecommendation).filter(TradeRecommendation.token == body.approval_token,
                                               TradeRecommendation.user_id == user.id).first()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    if rec.status != "pending":
        raise HTTPException(409, f"Recommendation already {rec.status}")
    rec.decided_at = datetime.now(timezone.utc)
    if not body.approve:
        rec.status = "rejected"
        db.commit()
        audit(db, "trade.rejected", f"recommendation:{rec.id}", user_id=user.id, request=request)
        return {"status": "rejected", "recommendation": _rec_out(rec)}

    broker = _broker(body.broker)
    if not getattr(broker, "paper", True) and body.confirm_phrase != "I APPROVE":
        raise HTTPException(400, 'Live trading requires confirm_phrase="I APPROVE"')

    order = OrderRequest(symbol=rec.symbol, side=rec.side, qty=body.qty if body.qty is not None else (rec.qty if body.notional is None else None),
                         notional=body.notional, order_type=body.order_type or rec.order_type,
                         limit_price=body.limit_price if body.limit_price is not None else rec.limit_price,
                         stop_price=body.stop_price if body.stop_price is not None else rec.stop_price,
                         time_in_force=body.time_in_force, user_approved=True, approval_token=rec.token,
                         client_order_id=f"atp-{rec.id}")
    rec.status = "approved"
    db.commit()
    audit(db, "trade.approved", f"recommendation:{rec.id}", {"broker": broker.name, "order": order.__dict__},
          user_id=user.id, request=request)
    try:
        result = broker.submit_order(order)
    except ApprovalRequired as exc:
        rec.status = "failed"
        db.commit()
        raise HTTPException(403, str(exc)) from exc
    except BrokerError as exc:
        rec.status = "failed"
        db.commit()
        audit(db, "trade.failed", f"recommendation:{rec.id}", {"error": str(exc)}, user_id=user.id, request=request)
        raise HTTPException(502, str(exc)) from exc
    rec.status = "submitted"
    rec.broker_order_id = result.order_id
    db.commit()
    audit(db, "trade.submitted", f"recommendation:{rec.id}", result.to_dict(), user_id=user.id, request=request)
    return {"status": "submitted", "order": result.to_dict(), "recommendation": _rec_out(rec)}


@router.delete("/orders/{order_id}")
def cancel(order_id: str, request: Request, broker: str | None = None, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> dict:
    ok = _broker(broker).cancel_order(order_id)
    audit(db, "trade.cancel", f"order:{order_id}", {"ok": ok}, user_id=user.id, request=request)
    return {"canceled": ok}


def _rec_out(r: TradeRecommendation) -> dict:
    return {"id": r.id, "token": r.token, "symbol": r.symbol, "side": r.side, "qty": r.qty, "notional": r.notional,
            "order_type": r.order_type, "limit_price": r.limit_price, "stop_price": r.stop_price,
            "rationale": r.rationale, "status": r.status, "broker_order_id": r.broker_order_id,
            "created_at": r.created_at.isoformat(), "decided_at": r.decided_at.isoformat() if r.decided_at else None}
