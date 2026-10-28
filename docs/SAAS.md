# Commercial (SaaS) design

## Subscription tiers

| | Free | Pro | Team |
|---|---|---|---|
| Terminal, charts, news, macro, sectors | ✓ | ✓ | ✓ |
| AI Council runs | 5 / day (enforce in `routers/council.py` via `council_runs` count) | unlimited | unlimited |
| Brokerage sync + approved trades | paper only | ✓ | ✓ |
| Backtests / forward sims | 3 / day | unlimited | unlimited |
| API access (`X-API-Key`) | — | ✓ | ✓ |
| Team dashboards, shared audit log | — | — | ✓ |
| White-label branding | — | — | ✓ (`teams.white_label_brand`) |

`users.subscription_tier` ∈ {free, pro, team}; `require_pro` dependency gates endpoints; admins change tiers via `POST /api/auth/admin/set-tier/{id}`. Hook a billing provider (Stripe Checkout + webhook) that calls the same tier-setting logic on `checkout.session.completed` / `customer.subscription.deleted`.

## Teams

`teams` table ↔ `users.team_id`. A team dashboard is the existing portfolio/council pages filtered by team members' `council_runs` and `trade_recommendations`; expose `GET /api/team/activity` joining those tables on `team_id` (admins of the team only).

## API access

Pro/Team users mint keys with `POST /api/auth/api-key` (prefix `atp_`). Keys are accepted on every 🔒 endpoint via the `X-API-Key` header. Rotate by calling the endpoint again; the previous key is invalidated immediately. Rate-limit per key at the proxy.

## White-label

* Backend: `teams.white_label_brand` is returned with the user payload; add a `GET /api/branding` endpoint reading the caller's team.
* Frontend: the header wordmark, favicon and Tailwind `term.amber` accent are the only brand touchpoints — read them from that endpoint (or a build-time env var) to re-skin.
* Deploy one static build per brand with `NEXT_PUBLIC_API_URL` pointing at the shared API, or host each tenant on its own custom domain via GitHub Pages `CNAME`.

## Cloud deployment plan

See `DEPLOYMENT.md`. Multi-tenant notes: store per-user brokerage credentials encrypted (KMS) in a `broker_credentials` table instead of environment variables; instantiate `AlpacaConnector(api_key, secret_key, paper)` per request with the decrypted values.

## Audit & compliance

`audit_logs` already records every monetizable or risk-relevant action. Expose it to team admins read-only, retain ≥ 7 years for live-trading tenants, and ship to a SIEM.
