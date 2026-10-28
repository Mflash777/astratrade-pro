# Going live: real data, real deployment

This repo already runs end-to-end with zero credentials (every data source
falls back to deterministic mock data). This guide is for turning that into a
real, publicly deployed site with live market data, live news, live
congressional-trading disclosures, and (optionally) real brokerage execution.

**Why this has to happen outside the Claude session that built it**: the
sandbox that generates this code has no general internet access (only package
registries) — it cannot reach Yahoo Finance, NewsAPI, FRED, Alpaca, GitHub (for
pushing), or Render/Vercel's APIs. Everything below needs to run from your own
machine or those providers' own dashboards, where normal internet access
exists.

## 0. What already works without any keys

- **Market data** — Yahoo Finance via `yfinance`, no key needed, on by default.
- **Congressional trading** — Senate/House Stock Watcher, no key needed, on by default.
- **SEC Form 4 insider filings** — SEC EDGAR, no key needed (just a descriptive `SEC_USER_AGENT`).
- **Prediction markets** — Polymarket's public Gamma API, no key needed.

So pushing this repo and deploying it as-is already gets you real price data,
real congressional trades, and real SEC filings. The keys below upgrade the
remaining pieces (news, macro, richer congressional data, LLM narrative
writing, real brokerage).

## 1. Get accounts & API keys (free tiers exist for all of these)

| Key | Where to get it | Needed for |
|---|---|---|
| `NEWS_API_KEY` | newsapi.org (free tier: 100 req/day) | Live news headlines & sentiment |
| `FRED_API_KEY` | fred.stlouisfed.org/docs/api/api_key.html (free) | Live macro data (rates, CPI, GDP) |
| `QUIVER_API_KEY` | quiverquant.com (optional — free Stock Watcher sources work without it) | Richer/faster congressional trading data |
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | alpaca.markets (free paper account) | Brokerage sync & trade execution |
| `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` | platform.openai.com or console.anthropic.com | The Council personas' narrative prose (optional — `LLM_PROVIDER=mock` works without one) |

None of these are required to deploy — leave any of them blank and that one
feature uses its mock fallback, visibly flagged, instead of crashing.

## 2. Push the code to GitHub

From your own machine (not this sandbox):

```bash
cd astratrade-pro
git init
git add .
git commit -m "AstraTrade Pro"
gh repo create astratrade-pro --private --source=. --push
# or: create the repo on github.com, then `git remote add origin ... && git push -u origin main`
```

## 3. Deploy the backend (Render)

1. Go to https://dashboard.render.com → **New +** → **Blueprint**, point it at your GitHub repo.
2. Render reads `render.yaml` at the repo root and provisions a web service (`astratrade-pro-api`) + a Postgres database together.
3. In the service's **Environment** tab, fill in the keys from the table above, plus:
   - `CORS_ORIGINS` — your Vercel URL once you have it (step 4), comma-separated if more than one
   - `SEC_USER_AGENT` — e.g. `AstraTradePro you@example.com` (SEC requires a real contact string)
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD` — your login for the bootstrapped admin account
4. Deploy. Confirm `https://astratrade-pro-api.onrender.com/api/health` returns `{"status":"ok"}`.

## 4. Deploy the frontend (Vercel)

1. Go to https://vercel.com/new, import the same GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Add environment variable `NEXT_PUBLIC_API_URL` = your Render backend URL from step 3.
4. Leave `NEXT_PUBLIC_BASE_PATH` unset (that's only for GitHub Pages subpath hosting).
5. Deploy. Vercel gives you a URL like `astratrade-pro.vercel.app` — set that as `CORS_ORIGINS` back on Render (step 3) and redeploy the backend so the browser isn't blocked by CORS.

## 5. Verify it's actually live

- Open the deployed frontend URL — the header badge should read **LIVE API**, not DEMO DATA.
- Pull up a symbol (e.g. `AAPL`) and confirm the price moves day to day (i.e. isn't the same every refresh — that's the synthetic fallback).
- Run a Council deliberation and check the Political Analyst's key points for a line like `Congressional disclosures: N buy / M sell ... ` without `(modeled)` at the end — that confirms the live Stock Watcher feed is being hit.
- Log in with your `ADMIN_EMAIL`/`ADMIN_PASSWORD`, go to Portfolio, click **Sync** — this should hit your real (paper) Alpaca account if you set those keys.

## 6. Going from paper to real-money trading (optional, do this last and deliberately)

1. In Render's environment, set `ALPACA_PAPER=false` **and** `ALPACA_LIVE_TRADING_ENABLED=true` — both are required; either alone is not enough, by design.
2. Point `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` at your live (not paper) Alpaca keys.
3. In the UI, approving a live order now requires typing the exact phrase `I APPROVE` — this is enforced in the backend, not just the UI, so it can't be bypassed by a modified frontend request.
4. Start small. This is real money and AstraTrade Pro's analysis is not financial advice.

## 7. Custom domain (optional)

Both Render and Vercel support attaching a custom domain for free under their
own dashboards (**Settings → Domains** on each). Point your domain's DNS at
whichever one you want as the public-facing host, typically the Vercel
frontend, with the Render backend on a subdomain like `api.yourdomain.com`.
