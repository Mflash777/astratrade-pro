"""Alpaca connector (https://docs.alpaca.markets/reference/).

Paper trading by default (``ALPACA_PAPER=true``). Live trading additionally
requires ``ALPACA_LIVE_TRADING_ENABLED=true`` as a deliberate second switch.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from .base import (Account, ApprovalRequired, BrokerConnector, BrokerError, OrderRequest, OrderResult,
                   Position)

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"


class AlpacaConnector(BrokerConnector):
    name = "alpaca"
    supports_fractional = True
    supported_order_types = ("market", "limit", "stop", "stop_limit")

    def __init__(self, api_key: str | None = None, secret_key: str | None = None, paper: bool | None = None) -> None:
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")
        if paper is None:
            paper = os.getenv("ALPACA_PAPER", "true").lower() != "false"
        if not paper and os.getenv("ALPACA_LIVE_TRADING_ENABLED", "false").lower() != "true":
            raise BrokerError("Live trading requested but ALPACA_LIVE_TRADING_ENABLED is not true")
        self.paper = paper
        self.base_url = PAPER_URL if paper else LIVE_URL
        if not self.api_key or not self.secret_key:
            raise BrokerError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.secret_key, "Content-Type": "application/json"},
            timeout=15,
        )

    def _req(self, method: str, path: str, **kw: Any) -> Any:
        try:
            r = self.client.request(method, path, **kw)
            if r.status_code >= 400:
                raise BrokerError(f"Alpaca {r.status_code}: {r.text[:300]}")
            return r.json() if r.content else {}
        except httpx.HTTPError as exc:
            raise BrokerError(f"Alpaca request failed: {exc}") from exc

    def get_account(self) -> Account:
        a = self._req("GET", "/v2/account")
        return Account(broker=self.name, account_id=a["account_number"], cash=float(a["cash"]),
                       buying_power=float(a["buying_power"]), equity=float(a["equity"]), currency=a.get("currency", "USD"),
                       paper=self.paper, raw=a)

    def get_positions(self) -> list[Position]:
        rows = self._req("GET", "/v2/positions")
        return [Position(symbol=p["symbol"], qty=float(p["qty"]), avg_entry_price=float(p["avg_entry_price"]),
                         current_price=float(p["current_price"]), market_value=float(p["market_value"]),
                         unrealized_pl=float(p["unrealized_pl"]), unrealized_pl_pct=float(p["unrealized_plpc"]) * 100,
                         side=p.get("side", "long")) for p in rows]

    def submit_order(self, order: OrderRequest) -> OrderResult:
        self.check_order(order)
        if not order.user_approved:
            raise ApprovalRequired("User approval required")
        body: dict[str, Any] = {"symbol": order.symbol.upper(), "side": order.side, "type": order.order_type,
                                "time_in_force": order.time_in_force}
        if order.qty is not None:
            body["qty"] = str(order.qty)
        else:
            body["notional"] = str(order.notional)
        if order.limit_price is not None:
            body["limit_price"] = str(order.limit_price)
        if order.stop_price is not None:
            body["stop_price"] = str(order.stop_price)
        if order.client_order_id:
            body["client_order_id"] = order.client_order_id
        o = self._req("POST", "/v2/orders", json=body)
        return self._to_result(o)

    def list_orders(self, status: str = "all", limit: int = 50) -> list[OrderResult]:
        rows = self._req("GET", "/v2/orders", params={"status": status, "limit": limit})
        return [self._to_result(o) for o in rows]

    def cancel_order(self, order_id: str) -> bool:
        self._req("DELETE", f"/v2/orders/{order_id}")
        return True

    def _to_result(self, o: dict[str, Any]) -> OrderResult:
        return OrderResult(broker=self.name, order_id=o["id"], status=o["status"], symbol=o["symbol"], side=o["side"],
                           qty=float(o["qty"]) if o.get("qty") else None,
                           notional=float(o["notional"]) if o.get("notional") else None, order_type=o["type"],
                           filled_avg_price=float(o["filled_avg_price"]) if o.get("filled_avg_price") else None,
                           submitted_at=o.get("submitted_at", ""), paper=self.paper, raw=o)
