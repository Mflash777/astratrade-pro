# Compliance notes

AstraTrade Pro is software that **displays information and routes user-approved orders to the user's own brokerage account**. It is designed so that the operator of the platform does not take custody of assets, does not exercise discretion over trades, and does not give personalized investment advice.

> This document is engineering guidance, not legal advice. Consult counsel before offering the product commercially, especially regarding investment-adviser registration, broker-dealer rules, and data-licensing terms in your jurisdiction.

## Design principles that support compliance

| Principle | Implementation |
|---|---|
| **No custody** | Backend stores only API credentials supplied via environment; funds and securities remain at the brokerage. No deposit/withdrawal endpoints exist. |
| **No autonomous trading** | `OrderRequest.validate()` raises `ApprovalRequired` unless `user_approved=True`; the only code path that sets it is `POST /api/brokers/orders` after an authenticated user sends `approve: true` with a single-use token. Simulation uses a private `PaperBroker` that cannot reach a real venue. |
| **Explicit live-money consent** | Three independent switches: `ALPACA_PAPER=false`, `ALPACA_LIVE_TRADING_ENABLED=true`, and the `confirm_phrase: "I APPROVE"` typed by the user per order. |
| **Disclaimers everywhere** | Every Council, portfolio-health and simulation payload includes `Not financial advice. Trades require user approval.`; the UI footer, approval modal and council panel repeat it. Simulation payloads carry `SIMULATION ONLY`. |
| **Auditability** | `audit_logs` records registration, logins (incl. failures), council runs, recommendation creation, approval, rejection, submission, failures, cancellations, admin tier changes, API-key rotation — with user id, IP and JSON detail. Council results are stored verbatim in `council_runs` for reconstruction. |
| **Least privilege** | Roles `admin`/`user`; subscription gates for API keys. Admin endpoints are the only way to read audit logs. |
| **Determinism** | Numeric scores and votes are rule-based and reproducible (`test_council_is_deterministic_with_mock_llm`); LLMs only write prose, so an explanation can always be traced to signals. |

## Data handling

* **PII**: email + password hash only. Passwords use PBKDF2-SHA256 (200k iterations). No card data is stored — integrate a payment processor (Stripe) that handles PCI scope.
* **Brokerage credentials**: environment variables on the server; for multi-tenant SaaS, store per-user tokens encrypted at rest (KMS envelope encryption) and never log them.
* **Market data**: Alpaca, Alpha Vantage, FRED, NewsAPI, SEC EDGAR and Polymarket each have usage terms (attribution, redistribution limits, rate limits). Review before commercial redistribution; SEC requires a descriptive `User-Agent` (`SEC_USER_AGENT`).
* **Retention**: keep `audit_logs` and `council_runs` for at least the period your regulator expects for communications records; export to immutable storage.

## Regulatory considerations (non-exhaustive)

* **Investment advice**: the Council produces general, model-driven analysis with disclaimers. Personalized recommendations tied to a user's holdings (the portfolio-health report) may be viewed as advice in some jurisdictions; consider adviser registration or restricting that feature to self-directed "educational" framing with suitability disclaimers.
* **Order routing**: the platform sends orders only through the user's brokerage API with the user's own credentials. Introducing-broker or payment-for-order-flow arrangements would change the analysis.
* **Marketing**: backtest and simulation results are hypothetical; present them with the SIMULATION label, note that past performance is not indicative of future results, and never imply guaranteed returns.
* **Privacy**: GDPR/CCPA — provide data export/deletion for users; the schema keeps user data in a small number of tables to make this tractable.

## Operational controls

* Rate-limit login and order endpoints; alert on repeated `user.login_failed`.
* Monitor `trade.failed` audit events.
* Require MFA at the brokerage level for live accounts.
* Run `pytest` in CI — the approval-gate tests (`test_paper_broker_requires_approval`, `test_trade_approval_flow`) must stay green.
