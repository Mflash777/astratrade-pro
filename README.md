# AstraTrade Pro

A Bloomberg-style market-intelligence terminal with a seven-persona **AI Council**, **user-approved** brokerage trading, and a clearly-labelled **paper-trading simulation engine**.

> **Not financial advice. Trades require user approval.** AstraTrade Pro never holds funds and never sends an order to a brokerage without an explicit, logged approval from the user.

```
Frontend (Next.js static export → GitHub Pages)
        │  REST / JSON
        ▼
Backend (FastAPI)
  ├── ai_council/      7 personas · debate · vote · synthesis   (LLM optional)
  ├── data_sources/    market · fundamentals · SEC · macro · news · social · prediction markets · analysts · sector rotation
  ├── brokers/         Alpaca (live/paper) · built-in paper broker · approval gate
  ├── simulation/      backtester · forward sim · 4 strategies · Sharpe/drawdown/trade log
  └── backend/app/     auth (JWT + API keys) · roles · subscription tiers · audit log · Postgres/SQLite
```

## Repository layout

```
astratrade-pro/
├── frontend/                 Next.js 14 + Tailwind terminal UI (static export)
│   └── src/
│       ├── app/              pages: / (terminal), /council, /portfolio, /simulation
│       ├── components/       Shell, CommandPalette, Charts, CouncilPanel, TradeApprovalModal, …
│       └── lib/              api.ts (client + demo fallback), mock.ts, types.ts
├── backend/
│   ├── app/                  FastAPI app, config, auth, audit, routers/
│   └── tests/                pytest suite
├── ai_council/               llm.py · orchestrator.py · personas/
├── brokers/                  base.py · alpaca.py · paper.py
├── simulation/               strategies.py · backtester.py · forward.py · metrics.py
├── data_sources/             one module per source + aggregator.py (common Signal schema)
├── db/                       schema.sql · migrations/
├── docs/                     architecture, API, extension guides, deployment, compliance, UI mockups
├── infra/                    Dockerfiles, nginx.conf
├── .github/workflows/        deploy-frontend.yml (GitHub Pages) · backend-ci.yml (tests, lint, types)
├── docker-compose.yml · requirements.txt · pyproject.toml · .env.example
```

## Quick start

### 1. Backend (Python 3.11+)

```bash
git clone https://github.com/<you>/astratrade-pro.git
cd astratrade-pro
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # edit as needed (all keys optional)
uvicorn backend.app.main:app --reload                  # http://localhost:8000/docs
```

With no API keys configured the backend runs entirely on deterministic mock data. A default admin is created from `ADMIN_EMAIL` / `ADMIN_PASSWORD` (`admin@example.com` / `admin12345`).

### 2. Frontend (Node 20+)

```bash
cd frontend
npm install
cp .env.example .env.local                              # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                                             # http://localhost:3000
```

If `NEXT_PUBLIC_API_URL` is empty (as on GitHub Pages by default) the UI runs in **demo mode** with built-in mock data and a browser-local paper book, so the whole product is explorable without a server.

### 3. Docker (backend + Postgres + static frontend)

```bash
cp .env.example .env
docker compose up --build      # API :8000, UI :8080, Postgres :5432
```

### 4. Tests, lint, types

```bash
pytest -q                      # backend
ruff check . && mypy ai_council brokers simulation data_sources backend
cd frontend && npm run lint && npm run typecheck
```

## Using the terminal

| Mnemonic | Function | Key |
|---|---|---|
| `GP` | Price chart, volume, realized volatility | F2 |
| `DES` | Fundamentals, earnings, SEC filings, analysts | F3 |
| `N` | News headlines + social sentiment | F4 |
| `ECO` | Macro snapshot, economic calendar, political events, prediction markets | F5 |
| `SECT` | Sector-rotation heatmap | F6 |
| `COUNCIL` | Convene the AI Council | F7 |
| `PORT` | Portfolio, risk dashboard, scenarios, council health report | F8 |
| `SIM` | Backtest / forward paper simulation | F9 |
| `TRADE` | Ask the Council for a trade recommendation (held until you approve) | — |

Open the palette with `/` or `⌘K`, type `NVDA DES`, press Enter.

## Trade approval flow

1. `POST /api/brokers/recommend` — the Council proposes a trade; it is stored as **pending** with a one-time token.
2. The user reviews it in the **Trade Approval** modal (can edit qty / order type / limit / stop).
3. `POST /api/brokers/orders {approval_token, approve: true}` — only now is the order sent. Live (non-paper) brokers additionally require `confirm_phrase: "I APPROVE"` and the env switch `ALPACA_LIVE_TRADING_ENABLED=true`.
4. Every step (`trade.recommended`, `trade.approved`, `trade.rejected`, `trade.submitted`, `trade.failed`) is written to `audit_logs`.

## Configuration

See `.env.example`. Everything is optional; mock data fills any gap.

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Let personas write narrative with a hosted LLM (scores stay rule-based) |
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` / `ALPACA_PAPER` | Alpaca brokerage + market data |
| `ALPACA_LIVE_TRADING_ENABLED` | Second, deliberate switch for real-money orders |
| `ALPHA_VANTAGE_API_KEY`, `FRED_API_KEY`, `NEWS_API_KEY`, `SEC_USER_AGENT` | Live fundamentals, macro, news, EDGAR |
| `DATABASE_URL` | SQLite (default) or PostgreSQL |
| `SECRET_KEY`, `JWT_EXPIRE_MINUTES`, `CORS_ORIGINS` | Auth / CORS |

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components, data flow, security model
- [docs/API.md](docs/API.md) — every endpoint with request/response examples
- [docs/ADDING_BROKERS.md](docs/ADDING_BROKERS.md) — implement a new connector
- [docs/EXTENDING_COUNCIL.md](docs/EXTENDING_COUNCIL.md) — add personas, signals, LLM providers
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — GitHub Pages, Docker, cloud plan
- [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md) — create the repo, push, enable Pages step by step
- [docs/COMPLIANCE.md](docs/COMPLIANCE.md) — disclaimers, custody, audit, data handling
- [docs/UI_MOCKUPS.md](docs/UI_MOCKUPS.md) — terminal, council, approval modal, portfolio wireframes
- [docs/SAAS.md](docs/SAAS.md) — tiers, teams, API access, white-label

## License

MIT. Market data and third-party APIs are subject to their own terms.
