"""Paper-trading simulation endpoints. Everything here is SIMULATION ONLY."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from simulation import STRATEGIES, ForwardSimulator, run_backtest

from ..audit import audit
from ..auth import get_current_user
from ..db import User, get_db
from .council import get_council

router = APIRouter(prefix="/api/simulation", tags=["simulation"])
_forward = ForwardSimulator()


@router.get("/strategies")
def strategies() -> list[dict]:
    return [{"key": k, "label": s.label, "description": s.description} for k, s in STRATEGIES.items()]


class BacktestIn(BaseModel):
    symbol: str = Field(..., max_length=6)
    strategy: str = "momentum"
    days: int = Field(365, ge=60, le=1200)
    initial_cash: float = Field(100_000, gt=0)
    use_council: bool = False


@router.post("/backtest")
def backtest(body: BacktestIn, request: Request, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)) -> dict:
    if body.strategy not in STRATEGIES:
        raise HTTPException(400, f"Unknown strategy. Available: {', '.join(STRATEGIES)}")
    council_score = get_council().analyze_symbol(body.symbol)["final"]["score"] if body.use_council else 0.0
    result = run_backtest(body.symbol, body.strategy, body.days, body.initial_cash, council_score=council_score)
    audit(db, "simulation.backtest", f"symbol:{body.symbol.upper()}",
          {"strategy": body.strategy, "sharpe": result["metrics"]["sharpe"]}, user_id=user.id, request=request)
    return result


class ForwardIn(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["AAPL", "MSFT", "NVDA"])
    strategy: str = "ai_hybrid"
    initial_cash: float = Field(100_000, gt=0)
    use_council: bool = True
    steps: int = Field(1, ge=1, le=20)


@router.post("/forward")
def forward_create(body: ForwardIn, request: Request, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> dict:
    if body.strategy not in STRATEGIES:
        raise HTTPException(400, "Unknown strategy")
    report = _forward.create(body.symbols[:10], body.strategy, body.initial_cash, body.use_council, body.steps)
    audit(db, "simulation.forward_create", f"session:{report['session_id']}", {"symbols": body.symbols}, user_id=user.id, request=request)
    return report


@router.post("/forward/{session_id}/step")
def forward_step(session_id: str, steps: int = 1, user: User = Depends(get_current_user)) -> dict:
    if session_id not in _forward.sessions:
        raise HTTPException(404, "Session not found")
    return _forward.step(session_id, min(steps, 20))


@router.get("/forward/{session_id}")
def forward_get(session_id: str, user: User = Depends(get_current_user)) -> dict:
    if session_id not in _forward.sessions:
        raise HTTPException(404, "Session not found")
    return _forward.get(session_id)


@router.get("/forward")
def forward_list(user: User = Depends(get_current_user)) -> list[dict]:
    return _forward.list()
