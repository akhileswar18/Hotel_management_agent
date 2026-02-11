"""
Domain Layer: Value Objects and Enums

Pure, immutable value types with no dependencies on external systems.
All values are deterministic and testable without database.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Union


class OrderStatus(str, Enum):
    """Immutable order status enum."""
    DRAFT = "draft"
    FINALIZED = "finalized"
    VOIDED = "voided"


class TransactionType(str, Enum):
    """Stock ledger transaction types."""
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    ADJUSTMENT = "ADJUSTMENT"
    WASTAGE = "WASTAGE"
    RETURN = "RETURN"


class Role(str, Enum):
    """User roles with permission levels."""
    WAITER = "WAITER"
    CASHIER = "CASHIER"
    MANAGER = "MANAGER"
    CLERK = "CLERK"
    ADMIN = "ADMIN"


class PaymentMethod(str, Enum):
    """Supported payment methods."""
    CASH = "CASH"
    CARD = "CARD"
    VOUCHER = "VOUCHER"


@dataclass(frozen=True)
class Money:
    """
    Immutable money value object.

    Stored as integer cents to avoid floating-point precision issues.
    All monetary values in the system use this type.

    Example:
        Money(cents=15000) represents ₹150.00
        Money(cents=100) represents ₹1.00
    """
    cents: int

    def __post_init__(self) -> None:
        if not isinstance(self.cents, int):
            raise TypeError("Money cents must be integer")
        if self.cents < 0:
            raise ValueError("Money cents cannot be negative")

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        return Money(cents=self.cents + other.cents)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            raise TypeError("Can only subtract Money from Money")
        result = self.cents - other.cents
        if result < 0:
            raise ValueError(f"Cannot subtract {other} from {self}")
        return Money(cents=result)

    def __mul__(self, factor: float) -> "Money":
        if not isinstance(factor, (int, float)):
            raise TypeError("Can only multiply Money by number")
        return Money(cents=int(round(self.cents * factor)))

    def __truediv__(self, divisor: float) -> "Money":
        if not isinstance(divisor, (int, float)):
            raise TypeError("Can only divide Money by number")
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Money(cents=int(round(self.cents / divisor)))

    def to_float(self) -> float:
        """Convert to float (for display)."""
        return self.cents / 100.0

    @staticmethod
    def from_float(value: float) -> "Money":
        """Create Money from float value."""
        return Money(cents=int(round(value * 100)))

    def __repr__(self) -> str:
        return f"Money(₹{self.to_float():.2f})"

    def __str__(self) -> str:
        return f"₹{self.to_float():.2f}"


# TODO: Add CurrencyCode enum for Phase 2+ multi-currency support
# TODO: Add ExchangeRate value object for currency conversion
