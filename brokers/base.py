"""Broker connector interface.

Safety invariants enforced here and in the API layer:
* The platform never custodies funds — connectors only call the user's own brokerage.
* ``submit_order`` must only be called with an :class:`OrderRequest` whose
  ``user_approved`` flag is True and whose ``approval_token`` matches a pending
  recommendation. Connectors raise :class:`ApprovalRequired` otherwise.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop", "stop_limit"]
TimeInForce = Literal["day", "gtc", "ioc", "fok"]


class BrokerError(Exception):
    pass


class ApprovalRequired(BrokerError):
    pass


@dataclass
class Account:
    broker: str
    account_id: str
    cash: float
    buying_power: float
    equity: float
    currency: str = "USD"
    paper: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_pl_pct: float
    side: str = "long"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    qty: float | None = None
    notional: float | None = None  # dollar amount for fractional orders
    order_type: OrderType = "market"
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: TimeInForce = "day"
    user_approved: bool = False
    approval_token: str | None = None
    client_order_id: str | None = None

    def validate(self) -> None:
        if not self.symbol:
            raise BrokerError("symbol is required")
        if self.qty is None and self.notional is None:
            raise BrokerError("qty or notional is required")
        if self.qty is not None and self.qty <= 0:
            raise BrokerError("qty must be positive")
        if self.notional is not None and self.notional <= 0:
            raise BrokerError("notional must be positive")
        if self.order_type in ("limit", "stop_limit") and self.limit_price is None:
            raise BrokerError("limit_price required for limit orders")
        if self.order_type in ("stop", "stop_limit") and self.stop_price is None:
            raise BrokerError("stop_price required for stop orders")
        if not self.user_approved:
            raise ApprovalRequired("Order has not been approved by the user")


@dataclass
class OrderResult:
    broker: str
    order_id: str
    status: str
    symbol: str
    side: str
    qty: float | None
    notional: float | None
    order_type: str
    filled_avg_price: float | None = None
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    paper: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BrokerConnector(ABC):
    name: str = "base"
    supports_fractional: bool = False
    supported_order_types: tuple[str, ...] = ("market", "limit", "stop", "stop_limit")

    @abstractmethod
    def get_account(self) -> Account: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def submit_order(self, order: OrderRequest) -> OrderResult: ...

    @abstractmethod
    def list_orders(self, status: str = "all", limit: int = 50) -> list[OrderResult]: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    def check_order(self, order: OrderRequest) -> None:
        order.validate()
        if order.order_type not in self.supported_order_types:
            raise BrokerError(f"{self.name} does not support {order.order_type} orders")
        if order.notional is not None and not self.supports_fractional:
            raise BrokerError(f"{self.name} does not support fractional/notional orders")
