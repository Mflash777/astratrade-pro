"""Forward (walk-forward / live-paper) simulation driven by strategies and the
AI Council. Each session owns its own PaperBroker. SIMULATION ONLY."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from ai_council import CouncilOrchestrator
from brokers.paper import PaperBroker
from brokers.base import OrderRequest
from data_sources.fundamentals import get_fundamentals
from data_sources.market_data import get_history

from .backtester import SIMULATION_LABEL
from .metrics import performance_metrics
from .strategies import get_strategy


class ForwardSession:
    def __init__(self, symbols: list[str], strategy_key: str, initial_cash: float, use_council: bool) -> None:
        self.id = str(uuid.uuid4())
        self.symbols = [s.upper() for s in symbols]
        self.strategy_key = strategy_key
        self.use_council = use_council
        self.broker = PaperBroker(initial_cash)
        self.council = CouncilOrchestrator() if use_council else None
        self.log: list[dict[str, Any]] = []
        self.equity_history: list[dict[str, Any]] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.steps = 0

    def step(self) -> dict[str, Any]:
        """Advance one decision cycle: evaluate every symbol and rebalance the paper book."""
        self.steps += 1
        actions = []
        equity = self.broker.get_account().equity
        per_symbol = equity / len(self.symbols)
        for sym in self.symbols:
            df = get_history(sym, 300).reset_index(drop=True)
            context: dict[str, Any] = {"fundamentals": get_fundamentals(sym), "council_score": 0.0}
            council_note = None
            if self.council:
                verdict = self.council.analyze_symbol(sym)
                context["council_score"] = verdict["final"]["score"]
                council_note = {"action": verdict["recommendation"]["action"], "score": verdict["final"]["score"],
                                "votes": verdict["votes"]}
            target = float(get_strategy(self.strategy_key).signals(df, context).iloc[-1])
            px = self.broker.price(sym)
            held = self.broker.holdings.get(sym, {"qty": 0.0})["qty"]
            desired = per_symbol * target / px
            delta = desired - held
            if abs(delta * px) > max(50.0, equity * 0.005):
                side = "buy" if delta > 0 else "sell"
                order = OrderRequest(symbol=sym, side=side, qty=round(abs(delta), 4), user_approved=True,
                                     approval_token="simulation")
                res = self.broker.submit_order(order)
                actions.append({"symbol": sym, "side": side, "qty": order.qty, "price": res.filled_avg_price,
                                "target_exposure": round(target, 3), "council": council_note})
            else:
                actions.append({"symbol": sym, "side": "hold", "target_exposure": round(target, 3), "council": council_note})
        acct = self.broker.get_account()
        entry = {"step": self.steps, "timestamp": datetime.now(timezone.utc).isoformat(), "equity": acct.equity,
                 "cash": acct.cash, "actions": actions}
        self.log.append(entry)
        self.equity_history.append({"step": self.steps, "equity": acct.equity})
        return entry

    def report(self) -> dict[str, Any]:
        acct = self.broker.get_account()
        eq = pd.Series([e["equity"] for e in self.equity_history] or [acct.equity])
        return {
            "label": SIMULATION_LABEL,
            "session_id": self.id,
            "symbols": self.symbols,
            "strategy": self.strategy_key,
            "use_council": self.use_council,
            "created_at": self.created_at,
            "steps": self.steps,
            "account": acct.to_dict(),
            "positions": [p.to_dict() for p in self.broker.get_positions()],
            "metrics": performance_metrics(eq, periods=252),
            "equity_history": self.equity_history,
            "log": self.log,
            "orders": [o.to_dict() for o in self.broker.list_orders()],
        }


class ForwardSimulator:
    def __init__(self) -> None:
        self.sessions: dict[str, ForwardSession] = {}

    def create(self, symbols: list[str], strategy_key: str = "ai_hybrid", initial_cash: float = 100_000.0,
               use_council: bool = True, steps: int = 1) -> dict[str, Any]:
        s = ForwardSession(symbols, strategy_key, initial_cash, use_council)
        self.sessions[s.id] = s
        for _ in range(max(1, steps)):
            s.step()
        return s.report()

    def step(self, session_id: str, steps: int = 1) -> dict[str, Any]:
        s = self.sessions[session_id]
        for _ in range(max(1, steps)):
            s.step()
        return s.report()

    def get(self, session_id: str) -> dict[str, Any]:
        return self.sessions[session_id].report()

    def list(self) -> list[dict[str, Any]]:
        return [{"session_id": s.id, "symbols": s.symbols, "strategy": s.strategy_key, "steps": s.steps,
                 "equity": s.broker.get_account().equity} for s in self.sessions.values()]
