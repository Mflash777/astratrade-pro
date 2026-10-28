from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai_council import CouncilOrchestrator

from ..audit import audit
from ..auth import get_current_user
from ..db import CouncilRun, User, dumps, get_db

router = APIRouter(prefix="/api/council", tags=["council"])
_council = CouncilOrchestrator()


class AnalyzeIn(BaseModel):
    symbol: str = Field(..., max_length=6)
    question: str | None = None


@router.post("/analyze")
def analyze(body: AnalyzeIn, request: Request, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)) -> dict:
    result = _council.analyze_symbol(body.symbol.upper(), body.question)
    run = CouncilRun(user_id=user.id, symbol=result["symbol"], action=result["recommendation"]["action"],
                     score=result["final"]["score"], result_json=dumps(result))
    db.add(run)
    db.commit()
    audit(db, "council.run", f"symbol:{result['symbol']}",
          {"action": result["recommendation"]["action"], "score": result["final"]["score"]}, user_id=user.id, request=request)
    result["run_id"] = run.id
    return result


@router.get("/personas")
def personas() -> list[dict]:
    return [{"name": p.name, "role": p.role, "categories": list(p.categories)} for p in _council.personas] + \
           [{"name": _council.optimizer.name, "role": _council.optimizer.role, "categories": []}]


@router.get("/history")
def history(limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(CouncilRun).filter(CouncilRun.user_id == user.id).order_by(CouncilRun.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "symbol": r.symbol, "action": r.action, "score": r.score, "created_at": r.created_at.isoformat()} for r in rows]


def get_council() -> CouncilOrchestrator:
    return _council
