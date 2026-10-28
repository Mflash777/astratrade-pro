import pytest

from brokers import ApprovalRequired, BrokerError, OrderRequest, PaperBroker
from simulation import STRATEGIES, ForwardSimulator, run_backtest


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_backtest_every_strategy(strategy):
    r = run_backtest("AAPL", strategy, days=120, initial_cash=50_000)
    assert r["label"].startswith("SIMULATION ONLY")
    assert r["final_equity"] > 0
    assert len(r["equity_curve"]) == 120
    assert "sharpe" in r["metrics"] and "max_drawdown" in r["metrics"]
    assert r["metrics"]["max_drawdown"] <= 0


def test_forward_simulation_steps():
    sim = ForwardSimulator()
    report = sim.create(["AAPL", "MSFT"], "momentum", 20_000, use_council=False, steps=2)
    assert report["steps"] == 2
    assert report["account"]["paper"] is True
    again = sim.step(report["session_id"], 1)
    assert again["steps"] == 3
    assert len(sim.list()) == 1


def test_paper_broker_requires_approval():
    b = PaperBroker(10_000)
    with pytest.raises(ApprovalRequired):
        b.submit_order(OrderRequest(symbol="AAPL", side="buy", qty=1))


def test_paper_broker_round_trip():
    b = PaperBroker(10_000)
    buy = b.submit_order(OrderRequest(symbol="AAPL", side="buy", notional=1000, user_approved=True))
    assert buy.status == "filled"
    pos = b.get_positions()
    assert pos[0].symbol == "AAPL" and pos[0].qty > 0
    sell = b.submit_order(OrderRequest(symbol="AAPL", side="sell", qty=pos[0].qty, user_approved=True))
    assert sell.status == "filled"
    assert abs(b.get_account().equity - 10_000) < 1.0
    with pytest.raises(BrokerError):
        b.submit_order(OrderRequest(symbol="AAPL", side="sell", qty=5, user_approved=True))


def test_limit_order_rests_when_not_marketable():
    b = PaperBroker(10_000)
    res = b.submit_order(OrderRequest(symbol="AAPL", side="buy", qty=1, order_type="limit", limit_price=1.0, user_approved=True))
    assert res.status == "accepted"
    assert b.cancel_order(res.order_id) is True
