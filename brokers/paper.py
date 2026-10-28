"""Built-in paper broker: an in-memory brokerage used when no real broker is
configured, and by the forward-simulation engine. SIMULATION ONLY."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from data_sources.market_data import get_quote

from .base import Account, BrokerConnector, BrokerError, OrderRequest, OrderResult, Position


class PaperBroker(BrokerConnector):
    name = "paper"
    supports_fractional = True

    def __init__(self, starting_cash: float = 100_000.0) -> None:
        self.cash = starting_cash
        self.starting_cash = starting_cash
        self.holdings: dict[str, dict[str, float]] = {}  # symbol -> {qty, avg}
        self.orders: list[OrderResult] = []

    def price(self, symbol: str) -> float:
        return float(get_quote(symbol)["price"])

    def get_account(self) -> Account:
        equity = self.cash + sum(h["qty"] * self.price(s) for s, h in self.holdings.items())
        return Account(broker=self.name, account_id="PAPER-0001", cash=round(self.cash, 2),
                       buying_power=round(self.cash, 2), equity=round(equity, 2), paper=True)

    def get_positions(self) -> list[Position]:
        out = []
        for s, h in self.holdings.items():
            if h["qty"] == 0:
                continue
            px = self.price(s)
            mv = h["qty"] * px
            pl = (px - h["avg"]) * h["qty"]
            out.append(Position(symbol=s, qty=round(h["qty"], 4), avg_entry_price=round(h["avg"], 2), current_price=px,
                                market_value=round(mv, 2), unrealized_pl=round(pl, 2),
                                unrealized_pl_pct=round(pl / max(h["avg"] * h["qty"], 1e-9) * 100, 2)))
        return out

    def submit_order(self, order: OrderRequest) -> OrderResult:
        self.check_order(order)
        sym = order.symbol.upper()
        px = self.price(sym)
        if order.order_type == "limit" and order.limit_price is not None:
            if (order.side == "buy" and px > order.limit_price) or (order.side == "sell" and px < order.limit_price):
                res = self._result(order, "accepted", None)
                self.orders.append(res)
                return res
            px = order.limit_price
        if order.order_type in ("stop", "stop_limit") and order.stop_price is not None:
            res = self._result(order, "accepted", None)
            self.orders.append(res)
            return res
        qty = order.qty if order.qty is not None else float(order.notional) / px
        cost = qty * px
        h = self.holdings.setdefault(sym, {"qty": 0.0, "avg": 0.0})
        if order.side == "buy":
            if cost > self.cash:
                raise BrokerError("Insufficient paper cash")
            new_qty = h["qty"] + qty
            h["avg"] = (h["avg"] * h["qty"] + cost) / new_qty
            h["qty"] = new_qty
            self.cash -= cost
        else:
            if qty > h["qty"] + 1e-4:
                raise BrokerError("Insufficient paper position")
            qty = min(qty, h["qty"])
            cost = qty * px
            h["qty"] = max(0.0, h["qty"] - qty)
            self.cash += cost
        res = self._result(order, "filled", px)
        self.orders.append(res)
        return res

    def list_orders(self, status: str = "all", limit: int = 50) -> list[OrderResult]:
        rows = self.orders if status == "all" else [o for o in self.orders if o.status == status]
        return rows[-limit:]

    def cancel_order(self, order_id: str) -> bool:
        for o in self.orders:
            if o.order_id == order_id and o.status == "accepted":
                o.status = "canceled"
                return True
        return False

    def _result(self, order: OrderRequest, status: str, fill: float | None) -> OrderResult:
        return OrderResult(broker=self.name, order_id=str(uuid.uuid4()), status=status, symbol=order.symbol.upper(),
                           side=order.side, qty=order.qty, notional=order.notional, order_type=order.order_type,
                           filled_avg_price=fill, submitted_at=datetime.now(timezone.utc).isoformat(), paper=True)
