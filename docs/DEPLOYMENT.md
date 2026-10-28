# Deployment

## Topology

```
GitHub Pages (static Next.js export)  ──HTTPS──▶  FastAPI backend  ──▶  PostgreSQL
                                                     │
                                                     ├──▶ Alpaca / other brokers (user credentials)
                                                     ├──▶ Market & intelligence APIs
                                                     └──▶ OpenAI / Anthropic (optional)
```

## Frontend — GitHub Pages

Covered step by step in `GITHUB_SETUP.md`. Summary: Pages → Source = GitHub Actions; push to `main`; the workflow exports `frontend/out` with the correct `basePath`.

Any static host works the same way (Netlify, Vercel static, S3+CloudFront, nginx): build with `NEXT_PUBLIC_API_URL=<backend> NEXT_PUBLIC_BASE_PATH= npm run build` and serve `out/`.

## Backend — options

### A. Docker Compose on a VM (simplest production)

```bash
cp .env.example .env            # set SECRET_KEY, DATABASE_URL (postgres), CORS_ORIGINS, API keys
docker compose up -d --build
```

Put a TLS-terminating reverse proxy (Caddy, nginx, Traefik) in front of `:8000`. Example Caddyfile:

```
api.yourdomain.com {
    reverse_proxy localhost:8000
}
```

### B. Managed container platforms

Build `infra/Dockerfile.backend` and deploy to Fly.io, Render, Railway, Google Cloud Run, AWS App Runner or Azure Container Apps. Required env vars: `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`; everything else optional. Attach a managed Postgres and run `db/schema.sql` once (or rely on SQLAlchemy `create_all` at startup).

### C. Kubernetes

Deploy the backend image as a Deployment with 2+ replicas behind an Ingress; keep forward-simulation sessions sticky (or persist them) and use Redis if you add caching.

## Cloud deployment plan (reference)

| Concern | Choice |
|---|---|
| Compute | Cloud Run / Fly.io (scale-to-zero for dev; min 1 instance in prod) |
| Database | Managed Postgres (Neon, Supabase, RDS) with daily snapshots |
| Secrets | Platform secret manager; never commit `.env` |
| TLS | Platform-managed certificates |
| Observability | Structured uvicorn logs → Loki/Datadog; `/api/health` for uptime checks; `audit_logs` table for business events |
| Backups | Postgres PITR; export `audit_logs` to cold storage monthly |
| CI/CD | `backend-ci.yml` gates merges; add a deploy job that builds the image on tag push |

## Environment matrix

| Env | `APP_ENV` | DB | LLM | Broker |
|---|---|---|---|---|
| local | development | SQLite | mock | paper |
| staging | staging | Postgres | mock or real | Alpaca paper |
| production | production | Postgres | real | Alpaca paper by default; live only with `ALPACA_LIVE_TRADING_ENABLED=true` |

## Hardening checklist before live trading

- [ ] Rotate `SECRET_KEY`; set `JWT_EXPIRE_MINUTES` ≤ 60 for live accounts.
- [ ] Restrict `CORS_ORIGINS` to your exact frontend origin.
- [ ] Enable HTTPS everywhere; set `Secure`/`HttpOnly` if you move tokens to cookies.
- [ ] Review `audit_logs` retention and access (admin only).
- [ ] Confirm `ALPACA_PAPER=true` on every non-production environment.
- [ ] Add rate limiting (e.g. `slowapi`) on `/api/auth/login` and `/api/brokers/orders`.
