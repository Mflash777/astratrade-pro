from ai_council import DISCLAIMER, CouncilOrchestrator
from ai_council.llm import MockLLM
from data_sources import IntelligenceAggregator


def test_aggregator_returns_normalized_signals():
    signals = IntelligenceAggregator().collect("AAPL")
    assert len(signals) >= 8
    for s in signals:
        assert -1.0 <= s.score <= 1.0
        assert 0.0 <= s.confidence <= 1.0
        assert s.symbol == "AAPL"
    cats = {s.category for s in signals}
    for required in ("technical", "fundamental", "macro", "news", "social", "political", "prediction", "analyst", "sector"):
        assert required in cats


def test_council_runs_seven_personas_and_votes():
    council = CouncilOrchestrator(llm=MockLLM())
    result = council.analyze_symbol("MSFT")
    assert len(result["opinions"]) == 6
    assert result["final"]["persona"] == "Optimizer"
    assert sum(result["votes"].values()) == 6
    assert result["recommendation"]["action"] in ("BUY", "HOLD", "SELL")
    assert result["recommendation"]["requires_user_approval"] is True
    assert result["disclaimer"] == DISCLAIMER
    assert len(result["debate"]) == 6
    for o in result["opinions"]:
        assert o["rationale"]
        assert o["vote"] in ("BUY", "HOLD", "SELL")


def test_council_is_deterministic_with_mock_llm():
    council = CouncilOrchestrator(llm=MockLLM())
    a = council.analyze_symbol("NVDA")["final"]["score"]
    b = council.analyze_symbol("NVDA")["final"]["score"]
    assert a == b


def test_portfolio_health():
    council = CouncilOrchestrator(llm=MockLLM())
    report = council.portfolio_health([{"symbol": "AAPL", "market_value": 5000}, {"symbol": "XOM", "market_value": 3000}])
    assert report["health"] in ("healthy", "watch", "at risk")
    assert len(report["holdings"]) == 2
    assert abs(sum(h["weight"] for h in report["holdings"]) - 1.0) < 1e-6
