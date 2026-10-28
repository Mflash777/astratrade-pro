-- AstraTrade Pro — PostgreSQL schema.
-- SQLAlchemy (backend/app/db.py) creates these same tables automatically on
-- startup; this file is the canonical reference and the docker-compose seed.

CREATE TABLE IF NOT EXISTS teams (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(120) NOT NULL,
    white_label_brand VARCHAR(120),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id                SERIAL PRIMARY KEY,
    email             VARCHAR(255) NOT NULL UNIQUE,
    password_hash     VARCHAR(255) NOT NULL,
    role              VARCHAR(20)  NOT NULL DEFAULT 'user'  CHECK (role IN ('admin', 'user')),
    subscription_tier VARCHAR(20)  NOT NULL DEFAULT 'free'  CHECK (subscription_tier IN ('free', 'pro', 'team')),
    team_id           INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    api_key           VARCHAR(64) UNIQUE,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

CREATE TABLE IF NOT EXISTS audit_logs (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     VARCHAR(64)  NOT NULL,
    resource   VARCHAR(128) NOT NULL,
    detail     TEXT NOT NULL DEFAULT '{}',
    ip         VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action     ON audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);

-- Council-generated trade ideas. Rows start 'pending' and can only move to
-- 'approved'/'rejected' by an authenticated user action; 'submitted' is set
-- after the broker accepts the order.
CREATE TABLE IF NOT EXISTS trade_recommendations (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(64) NOT NULL UNIQUE,
    symbol          VARCHAR(16) NOT NULL,
    side            VARCHAR(4)  NOT NULL CHECK (side IN ('buy', 'sell')),
    qty             DOUBLE PRECISION,
    notional        DOUBLE PRECISION,
    order_type      VARCHAR(16) NOT NULL DEFAULT 'market',
    limit_price     DOUBLE PRECISION,
    stop_price      DOUBLE PRECISION,
    rationale       TEXT NOT NULL DEFAULT '',
    status          VARCHAR(16) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected', 'submitted', 'failed')),
    broker_order_id VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_trade_recommendations_token ON trade_recommendations(token);

CREATE TABLE IF NOT EXISTS council_runs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    symbol      VARCHAR(16) NOT NULL,
    action      VARCHAR(8)  NOT NULL,
    score       DOUBLE PRECISION NOT NULL,
    result_json TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_council_runs_symbol ON council_runs(symbol);
