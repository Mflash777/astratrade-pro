from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from .db import AuditLog, dumps


def audit(db: Session, action: str, resource: str, detail: dict[str, Any] | None = None,
          user_id: int | None = None, request: Request | None = None) -> AuditLog:
    entry = AuditLog(user_id=user_id, action=action, resource=resource, detail=dumps(detail or {}),
                     ip=request.client.host if request and request.client else None)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
