# Adding a broker connector

Every connector subclasses `brokers.base.BrokerConnector` and implements five methods. The approval invariant is enforced for you by `self.check_order(order)` — call it first in `submit_order`.

## 1. Create `brokers/<name>.py`

```python
from __future__ import annotations
import os
import httpx
from .base import Account, ApprovalRequired, BrokerConnector, BrokerError, OrderRequest, OrderResult, Position


class ExampleBrokerConnector(BrokerConnector):
    name = "examplebroker"
    supports_fractional = False
    supported_order_types = ("market", "limit")   # declare only what the venue supports

    def __init__(self) -> None:
        self.token = os.getenv("EXAMPLE_BROKER_TOKEN", "")
        if not self.token:
            raise BrokerError("EXAMPLE_BROKER_TOKEN must be set")
        self.paper = os.getenv("EXAMPLE_BROKER_PAPER", "true").lower() != "false"
        self.client = httpx.Client(base_url="https://api.examplebroker.com", headers={"Authorization": f"Bearer {self.token}"}, timeout=15)

    def get_account(self) -> Account:
        a = self.client.get("/v1/account").json()
        return Account(broker=self.name, account_id=a["id"], cash=float(a["cash"]), buying_power=float(a["buying_power"]),
                       equity=float(a["equity"]), paper=self.paper, raw=a)

    def get_positions(self) -> list[Position]:
        return [Position(symbol=p["symbol"], qty=float(p["qty"]), avg_entry_price=float(p["avg_price"]),
                         current_price=float(p["last"]), market_value=float(p["value"]),
                         unrealized_pl=float(p["pl"]), unrealized_pl_pct=float(p["pl_pct"])) for p in self.client.get("/v1/positions").json()]

    def submit_order(self, order: OrderRequest) -> OrderResult:
        self.check_order(order)                     # validates fields AND raises ApprovalRequired if not user_approved
        if not order.user_approved:                 # belt and braces
            raise ApprovalRequired("User approval required")
        body = {"symbol": order.symbol, "side": order.side, "qty": order.qty, "type": order.order_type,
                "limit": order.limit_price, "tif": order.time_in_force, "client_id": order.client_order_id}
        r = self.client.post("/v1/orders", json=body)
        if r.status_code >= 400:
            raise BrokerError(f"{self.name} {r.status_code}: {r.text[:200]}")
        o = r.json()
        return OrderResult(broker=self.name, order_id=o["id"], status=o["status"], symbol=order.symbol, side=order.side,
                           qty=order.qty, notional=order.notional, order_type=order.order_type, paper=self.paper, raw=o)

    def list_orders(self, status: str = "all", limit: int = 50) -> list[OrderResult]:
        ...

    def cancel_order(self, order_id: str) -> bool:
        return self.client.delete(f"/v1/orders/{order_id}").status_code < 300
```

## 2. Register it

In `brokers/__init__.py`:

```python
from .examplebroker import ExampleBrokerConnector
BROKER_REGISTRY["examplebroker"] = ExampleBrokerConnector
```

## 3. Document the secrets

Add `EXAMPLE_BROKER_TOKEN=` and `EXAMPLE_BROKER_PAPER=true` to `.env.example`.

## 4. Test offline

Subclass with a stubbed `client` or point `base_url` at a local mock server; assert that `submit_order(OrderRequest(..., user_approved=False))` raises `ApprovalRequired`.

## Notes per venue

* **Alpaca** — implemented in `brokers/alpaca.py`; paper and live hosts, fractional via `notional`, all four order types.
* **Interactive Brokers** — use the Client Portal Web API (`/v1/api/iserver/account/{id}/orders`) or `ib_insync`; IB requires a confirmation round-trip (`/orders/reply`) — map that into the same `submit_order` call so the user still sees one approval step.
* **Robinhood / TD Ameritrade (Schwab)** — Schwab's Trader API uses OAuth2; store the refresh token in env and refresh inside `__init__`. Robinhood has no official public API; treat any unofficial client as unsupported for production.

The UI needs no change: it reads capabilities from `GET /api/brokers/` and the `paper` flag from the account payload to decide whether to demand the `I APPROVE` phrase.
