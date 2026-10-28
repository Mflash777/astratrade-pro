# API reference

Base URL: `http://localhost:8000`. Interactive docs: `/docs` (Swagger) and `/redoc`.

Authentication: `Authorization: Bearer <jwt>` (from `/api/auth/login`) **or** `X-API-Key: atp_…` (Pro/Team). Endpoints marked 🔒 require auth; 🔑 require admin.

All responses that contain analysis include `"disclaimer": "Not financial advice. Trades require user approval."`

## System

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness + environment |

## Auth

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| POST | `/api/auth/register` | `{email, password}` (≥8 chars) | user |
| POST | `/api/auth/login` | form: `username`, `password` | `{access_token, token_type, user}` |
| GET 🔒 | `/api/auth/me` | — | user |
| POST 🔒 | `/api/auth/api-key` | — | user with new `api_key` (Pro/Team) |
| POST 🔑 | `/api/auth/admin/set-tier/{user_id}?tier=pro` | — | user |
| GET 🔑 | `/api/auth/admin/audit?limit=100` | — | audit rows |

```bash
curl -X POST localhost:8000/api/auth/login -d 'username=admin@example.com&password=admin12345'
```

## Market data (public)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/market/symbols` | Universe with sectors |
| GET | `/api/market/quote/{symbol}` | Last price, change, volume, high/low |
| GET | `/api/market/quotes?symbols=AAPL,MSFT` | Batch (≤40) |
| GET | `/api/market/history/{symbol}?days=180` | OHLCV bars (20–1500) |
| GET | `/api/market/indicators/{symbol}` | SMA20/50/200, RSI14, MACD, Bollinger, realized vol, returns, volume ratio |
| GET | `/api/market/fundamentals/{symbol}` | `{fundamentals, earnings, filings, analysts}` |
| GET | `/api/market/news/{symbol}` | `{news[], social}` |
| GET | `/api/market/macro` | `{snapshot, calendar, political, prediction_markets}` |
| GET | `/api/market/sectors` | Sector rotation rows (rank, phase, 1m/3m relative) |

## AI Council

### POST 🔒 `/api/council/analyze`

```json
{ "symbol": "NVDA", "question": "Is this a good entry ahead of earnings?" }
```

Response (abridged):

```json
{
  "symbol": "NVDA",
  "quote": { "price": 132.0, "change_pct": 1.2 },
  "signal_summary": { "technical": {"score": 0.31, "count": 5, "confidence": 0.62}, "macro": {...} },
  "opinions": [
    { "persona": "Macro Economist", "role": "...", "score": 0.12, "confidence": 0.6, "vote": "HOLD",
      "rationale": "...", "key_points": ["Fed funds 4.00% vs CPI 2.7% → real rate +1.3%", "..."], "evidence": [...] },
    { "persona": "Quant Analyst", ... }, { "persona": "Fundamental Investor", ... },
    { "persona": "Political Analyst", ... }, { "persona": "News & Sentiment Analyst", ... },
    { "persona": "Risk Manager", "key_points": ["1-day 95% VaR ≈ $3.41/share (2.6%)", "...", "Max position size: 6% of portfolio"] }
  ],
  "debate": ["Quant Analyst to Risk Manager: I see your HOLD case, but ...", "..."],
  "votes": { "BUY": 3, "HOLD": 2, "SELL": 1 },
  "final": { "persona": "Optimizer", "score": 0.24, "confidence": 0.52, "vote": "BUY", "rationale": "...", "key_points": [...] },
  "recommendation": { "action": "BUY", "score": 0.24, "confidence": 0.52, "max_position_pct": 6.0, "requires_user_approval": true },
  "disclaimer": "Not financial advice. Trades require user approval.",
  "run_id": 17
}
```

| Method | Path | Notes |
|---|---|---|
| GET | `/api/council/personas` | Names, roles, signal categories |
| GET 🔒 | `/api/council/history?limit=20` | The caller's recent runs |

## Brokers (user-approved trades only)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/brokers/` | Registered connectors and capabilities |
| GET 🔒 | `/api/brokers/account?broker=paper` | Cash, buying power, equity, `paper` flag |
| GET 🔒 | `/api/brokers/positions?broker=` | Positions with unrealized P/L |
| GET 🔒 | `/api/brokers/orders?broker=&status=all` | Order list |
| POST 🔒 | `/api/brokers/recommend` | `{symbol, budget, order_type}` → pending recommendation + council result (or `recommendation: null` on HOLD) |
| GET 🔒 | `/api/brokers/recommendations` | Caller's approval queue |
| POST 🔒 | `/api/brokers/orders` | **The approval gate** (below) |
| DELETE 🔒 | `/api/brokers/orders/{order_id}?broker=` | Cancel |

`broker` defaults to `alpaca` when keys are configured, otherwise `paper`.

### POST 🔒 `/api/brokers/orders`

```json
{
  "approval_token": "k9f…",
  "approve": true,
  "broker": "alpaca",
  "qty": 7.5,
  "order_type": "limit",
  "limit_price": 131.5,
  "time_in_force": "day",
  "confirm_phrase": "I APPROVE"
}
```

* `approve: false` → `{status: "rejected"}`; nothing is sent.
* Replaying a token → `409`. Unknown token → `404`. Live broker without `confirm_phrase` → `400`. Broker error → `502` and status `failed`.
* Success → `{status: "submitted", order: {order_id, status, filled_avg_price, paper, ...}, recommendation}`.

## Simulation (paper only)

| Method | Path | Body |
|---|---|---|
| GET | `/api/simulation/strategies` | — |
| POST 🔒 | `/api/simulation/backtest` | `{symbol, strategy, days, initial_cash, use_council}` → metrics (Sharpe, Sortino, max drawdown, CAGR, Calmar), benchmark metrics, equity curve, drawdown series, trade log, trade stats |
| POST 🔒 | `/api/simulation/forward` | `{symbols[], strategy, initial_cash, use_council, steps}` → session report |
| POST 🔒 | `/api/simulation/forward/{id}/step?steps=1` | Advance the session |
| GET 🔒 | `/api/simulation/forward/{id}` | Report: account, positions, metrics, decision log, orders |
| GET 🔒 | `/api/simulation/forward` | List sessions |

Every simulation payload carries `"label": "SIMULATION ONLY — paper trading, no real orders are placed."`

## Portfolio

| Method | Path | Returns |
|---|---|---|
| GET 🔒 | `/api/portfolio/?broker=` | account, positions (with weight & sector), sector_weights |
| GET 🔒 | `/api/portfolio/risk?broker=` | annualized vol, beta, VaR/CVaR 95% 1-day, HHI, per-position beta/vol, correlation matrix, scenario P/L (rate hike/cut, recession, election shock, soft landing, oil spike) |
| GET 🔒 | `/api/portfolio/rebalance?max_weight=0.25` | trim suggestions by position and sector |
| GET 🔒 | `/api/portfolio/health` | Council-driven health report per holding + suggestions |

## Error format

```json
{ "detail": "Human-readable message" }
```
