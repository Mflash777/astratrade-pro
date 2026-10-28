# Architecture

## Components

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | Next.js 14 (App Router), React 18, Tailwind, Recharts; `output: "export"` | Terminal UI, command palette, charts, council panel, approval modal, portfolio & simulation pages. Falls back to in-browser demo data when no backend is configured. |
| API | FastAPI + Pydantic v2 | REST surface, JWT/API-key auth, roles, subscription gates, audit logging, CORS. |
| AI Council | `ai_council/` (pure Python) | Six analyst personas + Optimizer; deterministic scoring, optional LLM narration. |
| Intelligence | `data_sources/` | Every source normalizes to `Signal(category, score∈[-1,1], confidence∈[0,1], details)`. Live integrations (Alpaca data, Alpha Vantage, FRED, NewsAPI, SEC EDGAR, Polymarket) with deterministic mock fallbacks. |
| Brokers | `brokers/` | `BrokerConnector` interface, `AlpacaConnector` (REST v2), `PaperBroker` (in-memory). Approval invariant enforced in `OrderRequest.validate()`. |
| Simulation | `simulation/` | Backtester, forward simulator (owns its own `PaperBroker`), four strategies, metrics. |
| Database | SQLAlchemy 2 → SQLite (dev) / PostgreSQL (prod) | users, teams, audit_logs, trade_recommendations, council_runs. |

## Request flow: "Convene council on NVDA"

```
UI (CouncilPanel) ──POST /api/council/analyze──▶ routers/council.py
                                                   │ get_current_user (JWT)
                                                   ▼
                                       CouncilOrchestrator.analyze_symbol
                                                   │
                       IntelligenceAggregator.bundle(symbol)  (ThreadPool over 9 sources)
                                                   │ signals[] + quote + indicators + fundamentals + macro
                                                   ▼
                 ┌── MacroEconomist.analyze ──┐
                 ├── QuantAnalyst.analyze ────┤  each: relevant_signals → weighted score → vote → rationale (LLM optional)
                 ├── FundamentalInvestor ─────┤
                 ├── PoliticalAnalyst ────────┤
                 ├── SentimentAnalyst ────────┤
                 └── RiskManager ─────────────┘  (caps at HOLD; computes VaR, scenarios, max position)
                                                   │ opinions[]
                                   persona.rebut() ─▶ debate[]  ·  tally ─▶ votes
                                                   ▼
                                   Optimizer.synthesize ─▶ final (weighted by confidence × persona weight)
                                                   │
                     CouncilRun row + audit("council.run") ─▶ JSON response with disclaimer
```

## Trade approval state machine

```
recommend ──▶ pending ──(user approve)──▶ approved ──(broker accepts)──▶ submitted
                 │                                      └──(broker error)──▶ failed
                 └──(user reject)──▶ rejected
```

* A recommendation token is single-use; replay returns HTTP 409.
* `OrderRequest.user_approved` must be `True` or every connector raises `ApprovalRequired`.
* Live Alpaca requires `ALPACA_PAPER=false` **and** `ALPACA_LIVE_TRADING_ENABLED=true` **and** `confirm_phrase == "I APPROVE"`.
* The forward simulator passes `approval_token="simulation"` to its private `PaperBroker` only; it can never reach a real connector.

## Security model

* Passwords: PBKDF2-HMAC-SHA256, 200k iterations, per-user salt.
* Auth: HS256 JWT (`SECRET_KEY`), 24h default; optional `X-API-Key` header for Pro/Team programmatic access.
* Roles: `admin` (tier management, audit log) / `user`. Tiers: `free` / `pro` / `team`.
* Secrets only via environment; never persisted to DB or logs.
* Audit log captures user, action, resource, JSON detail, client IP, timestamp.
* CORS restricted to `CORS_ORIGINS`.
* No custody: the backend holds only API credentials the user supplies; funds stay at the brokerage.

## Data model

See `db/schema.sql`. SQLAlchemy models in `backend/app/db.py` are the single source of truth for the ORM; the SQL file is the canonical DDL for Postgres deployments.

## Frontend data layer

`src/lib/api.ts` wraps `fetch`. Each call is `withFallback(live, demo)`: network failures (status 0) switch the app into demo mode (`mock.ts`) and surface a "DEMO DATA" badge; 4xx/5xx are surfaced as toasts. This is what makes the GitHub Pages deployment useful standalone.

## Scaling notes

* Council runs are CPU-light (<100 ms without an LLM). With an LLM provider, persona narration is 6–7 sequential calls; parallelize with a thread pool in `CouncilOrchestrator.deliberate` if latency matters.
* Market data calls are cached per process only in `_CIK_CACHE`; add Redis for multi-instance deployments.
* Forward-simulation sessions live in process memory; persist `ForwardSession.report()` to the DB for durability.
