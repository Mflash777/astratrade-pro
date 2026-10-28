import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_astratrade.db"
os.environ["LLM_PROVIDER"] = "mock"

from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
    if os.path.exists("test_astratrade.db"):
        os.remove("test_astratrade.db")


@pytest.fixture(scope="module")
def auth(client):
    client.post("/api/auth/register", json={"email": "trader@example.com", "password": "password123"})
    r = client.post("/api/auth/login", data={"username": "trader@example.com", "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health_and_public_market_data(client):
    assert client.get("/api/health").json()["status"] == "ok"
    q = client.get("/api/market/quote/AAPL").json()
    assert q["symbol"] == "AAPL" and q["price"] > 0
    assert len(client.get("/api/market/history/SPY?days=60").json()["bars"]) == 60
    assert len(client.get("/api/market/sectors").json()) >= 10
    assert "snapshot" in client.get("/api/market/macro").json()


def test_council_requires_auth_then_works(client, auth):
    assert client.post("/api/council/analyze", json={"symbol": "AAPL"}).status_code == 401
    r = client.post("/api/council/analyze", json={"symbol": "AAPL"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body["opinions"]) == 6 and body["disclaimer"].startswith("Not financial advice")
    assert client.get("/api/council/history", headers=auth).json()[0]["symbol"] == "AAPL"


def test_trade_approval_flow(client, auth):
    rec = None
    for sym in ("AAPL", "NVDA", "XOM", "TSLA", "JPM", "PFE", "BA", "KO"):
        r = client.post("/api/brokers/recommend", json={"symbol": sym, "budget": 500}, headers=auth).json()
        if r["recommendation"]:
            rec = r["recommendation"]
            break
    if rec is None:
        pytest.skip("Council held on every sample symbol")
    assert rec["status"] == "pending"
    # Reject path
    r = client.post("/api/brokers/orders", json={"approval_token": rec["token"], "approve": False}, headers=auth)
    assert r.json()["status"] == "rejected"
    # Re-recommend then approve on the paper broker
    r = client.post("/api/brokers/recommend", json={"symbol": rec["symbol"], "budget": 500}, headers=auth).json()
    token = r["recommendation"]["token"]
    if r["recommendation"]["side"] == "sell":
        # Seed a paper position so the sell can fill.
        client.post("/api/brokers/recommend", json={"symbol": rec["symbol"], "budget": 500}, headers=auth)
        from brokers import OrderRequest, get_broker
        get_broker("paper").submit_order(OrderRequest(symbol=rec["symbol"], side="buy", qty=r["recommendation"]["qty"] + 1, user_approved=True))
    r = client.post("/api/brokers/orders", json={"approval_token": token, "approve": True, "broker": "paper"}, headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "submitted"
    assert r.json()["order"]["paper"] is True
    # Replay is blocked
    r = client.post("/api/brokers/orders", json={"approval_token": token, "approve": True, "broker": "paper"}, headers=auth)
    assert r.status_code == 409


def test_simulation_and_portfolio_endpoints(client, auth):
    r = client.post("/api/simulation/backtest", json={"symbol": "MSFT", "strategy": "mean_reversion", "days": 90}, headers=auth)
    assert r.status_code == 200 and "sharpe" in r.json()["metrics"]
    r = client.post("/api/simulation/forward", json={"symbols": ["AAPL"], "strategy": "momentum", "use_council": False}, headers=auth)
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert client.post(f"/api/simulation/forward/{sid}/step", headers=auth).json()["steps"] == 2
    assert "account" in client.get("/api/portfolio/?broker=paper", headers=auth).json()
    assert "scenarios" in client.get("/api/portfolio/risk?broker=paper", headers=auth).json()
    assert "suggestions" in client.get("/api/portfolio/rebalance?broker=paper", headers=auth).json()


def test_admin_audit_log(client):
    r = client.post("/api/auth/login", data={"username": "admin@example.com", "password": "admin12345"})
    hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rows = client.get("/api/auth/admin/audit", headers=hdr).json()
    actions = {row["action"] for row in rows}
    assert "council.run" in actions
