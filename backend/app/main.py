"""AstraTrade Pro API. Run from the repository root:

    uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import hash_password
from .config import get_settings
from .db import SessionLocal, User, init_db
from .routers import auth, brokers, council, market, portfolio, simulation

settings = get_settings()


def bootstrap_admin() -> None:
    with SessionLocal() as db:
        if not db.query(User).filter(User.email == settings.admin_email.lower()).first():
            db.add(User(email=settings.admin_email.lower(), password_hash=hash_password(settings.admin_password),
                        role="admin", subscription_tier="team"))
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    bootstrap_admin()
    yield


app = FastAPI(
    title="AstraTrade Pro API",
    version="1.0.0",
    description="Bloomberg-style market intelligence, AI Council, user-approved brokerage orders and paper simulation. "
                "Not financial advice. Trades require user approval.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, market.router, council.router, brokers.router, simulation.router, portfolio.router):
    app.include_router(r)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "env": settings.app_env, "disclaimer": "Not financial advice. Trades require user approval."}
