"""
Domain Layer: Business Rules

Pure, deterministic functions implementing core business logic.
Zero dependencies on database, UI, or external services.
All functions are testable in isolation.
"""

from typing import List, Tuple
from src.domain.value_objects import Money


class InvalidDiscountError(ValueError):
    """Raised when discount exceeds limits."""
    pass


class InsufficientStockError(ValueError):
    """Raised when attempting to deduct more stock than available."""
    pass


class InvalidTaxRateError(ValueError):
    """Raised when tax rate is invalid."""
    pass


def round_money(value: float) -> Money:
    """
    Round monetary value to 2 decimal places (cents).

    Uses banker's rounding (round half to even) for accounting accuracy.
    This is the single source of truth for rounding in the system.

    Args:
        value: Numeric value (float)

    Returns:
        Money: Rounded to nearest paisa/cent

    Examples:
        >>> round_money(100.567)
        Money(cents=10057)  # ₹100.57

        >>> round_money(100.004)
        Money(cents=10000)  # ₹100.00
    """
    return Money(cents=int(round(value * 100)))


def calculate_tax(subtotal: Money, tax_rate: float) -> Money:
    """
    Calculate tax on subtotal.

    Deterministic calculation following Indian GST-style rules.
    Tax is always rounded using consistent rounding function.

    Args:
        subtotal: Pre-tax amount
        tax_rate: Tax rate as decimal (0.0-1.0), e.g., 0.18 for 18%

    Returns:
        Money: Tax amount (rounded)

    Raises:
        InvalidTaxRateError: If tax_rate < 0 or > 1.0

    Examples:
        >>> subtotal = Money(10000)  # ₹100
        >>> calculate_tax(subtotal, 0.18)
        Money(cents=1800)  # ₹18.00

        >>> subtotal = Money(33333)  # ₹333.33
        >>> calculate_tax(subtotal, 0.18)
        Money(cents=6000)  # ₹60.00 (rounded)
    """
    if not (0.0 <= tax_rate <= 1.0):
        raise InvalidTaxRateError(f"Tax rate must be 0.0-1.0, got {tax_rate}")

    tax_cents = subtotal.cents * tax_rate
    return round_money(tax_cents / 100.0)


def apply_discount(price: Money, discount_type: str, amount: float) -> Money:
    """
    Apply discount to price.

    Validates discount limits:
    - Percentage discounts: max 50%
    - Absolute discounts: cannot exceed price

    Args:
        price: Original price
        discount_type: "percentage" or "absolute"
        amount: Discount value (0.0-50.0 for %, or cents for absolute)

    Returns:
        Money: Price after discount

    Raises:
        InvalidDiscountError: If discount exceeds limits

    Examples:
        >>> price = Money(10000)  # ₹100
        >>> apply_discount(price, "percentage", 10.0)
        Money(cents=9000)  # ₹90.00

        >>> price = Money(10000)
        >>> apply_discount(price, "absolute", 1000)  # ₹10
        Money(cents=9000)  # ₹90.00
    """
    if discount_type == "percentage":
        if not (0.0 <= amount <= 50.0):
            raise InvalidDiscountError(
                f"Percentage discount must be 0-50%, got {amount}%"
            )
        discount_amount = price * (amount / 100.0)
        return Money(cents=price.cents - discount_amount.cents)

    elif discount_type == "absolute":
        discount_cents = int(round(amount))
        if discount_cents > price.cents:
            raise InvalidDiscountError(
                f"Discount ₹{discount_cents / 100.0:.2f} exceeds price {price}"
            )
        return Money(cents=price.cents - discount_cents)

    else:
        raise ValueError(f"Unknown discount type: {discount_type}")


def validate_stock_deduction(current_stock: int, qty_to_deduct: int) -> bool:
    """
    Validate that sufficient stock exists for deduction.

    Args:
        current_stock: Current stock on hand
        qty_to_deduct: Quantity to deduct

    Returns:
        bool: True if deduction is valid

    Raises:
        InsufficientStockError: If insufficient stock
    """
    if qty_to_deduct > current_stock:
        raise InsufficientStockError(
            f"Insufficient stock: need {qty_to_deduct}, have {current_stock}"
        )
    return True


def compute_stock_on_hand(ledger_entries: List[Tuple[int, str]]) -> int:
    """
    Compute stock on hand from ledger entries (append-only).

    Never cache stock_on_hand; always compute from ledger.
    This ensures correctness even if ledger is processed out of order.

    Args:
        ledger_entries: List of (quantity_change, transaction_type) tuples
                       from stock ledger, in historical order

    Returns:
        int: Current stock on hand (sum of all changes)

    Examples:
        >>> entries = [(10, "PURCHASE"), (-2, "SALE"), (1, "ADJUSTMENT")]
        >>> compute_stock_on_hand(entries)
        9  # 10 - 2 + 1

        >>> entries = []
        >>> compute_stock_on_hand(entries)
        0  # No stock history
    """
    return sum(qty_change for qty_change, _ in ledger_entries)


def calculate_order_total(
    subtotal: Money,
    discount: Money,
    tax_rate: float
) -> Money:
    """
    Calculate final order total.

    Formula: (subtotal - discount) + tax

    Args:
        subtotal: Sum of all line items before tax/discount
        discount: Total discount applied (already deducted from price)
        tax_rate: Tax rate as decimal (0.18 for 18%)

    Returns:
        Money: Final total including tax

    Examples:
        >>> subtotal = Money(10000)  # ₹100
        >>> discount = Money(1000)  # ₹10
        >>> calculate_order_total(subtotal, discount, 0.18)
        # (₹100 - ₹10) * 1.18 = ₹106.20
        Money(cents=10620)
    """
    after_discount = Money(cents=subtotal.cents - discount.cents)
    tax = calculate_tax(after_discount, tax_rate)
    return Money(cents=after_discount.cents + tax.cents)


def validate_permission(user_role: str, action: str) -> bool:
    """
    Validate user permission for action (role-based).

    Implements permission matrix from specification:
    - WAITER: create orders, add items, view inventory (no void, discount <5%, no payment approval)
    - CASHIER: all waiter + finalize payment, reopen orders
    - MANAGER: all cashier + void/refund, any discount, stock adjustments, view reports
    - CLERK: stock management only
    - ADMIN: all actions

    Args:
        user_role: User role string
        action: Action name (e.g., "void_order", "apply_discount_50pct", "adjust_stock")

    Returns:
        bool: True if user can perform action

    Examples:
        >>> validate_permission("WAITER", "create_order")
        True

        >>> validate_permission("WAITER", "void_order")
        False

        >>> validate_permission("MANAGER", "void_order")
        True
    """
    # TODO: Load permission matrix from config or constants
    # For Phase 1, return placeholder
    permission_matrix = {
        "WAITER": [
            "create_order",
            "add_item",
            "view_inventory",
            "apply_discount_5pct",
        ],
        "CASHIER": [
            "create_order",
            "add_item",
            "view_inventory",
            "apply_discount_5pct",
            "finalize_order",
            "reopen_order",
        ],
        "MANAGER": [
            "create_order",
            "add_item",
            "view_inventory",
            "apply_discount_any",
            "finalize_order",
            "reopen_order",
            "void_order",
            "refund_order",
            "adjust_stock",
            "view_reports",
        ],
        "CLERK": [
            "view_inventory",
            "stock_in",
            "adjust_stock",
            "view_inventory_reports",
        ],
        "ADMIN": [
            "*",  # All actions
        ],
    }

    if user_role == "ADMIN":
        return True

    allowed_actions = permission_matrix.get(user_role, [])
    return action in allowed_actions


# TODO: Implement complex discount rules (buy 3 get 1 free, etc.)
# TODO: Add loyalty points calculation (future)
# TODO: Add tiered pricing rules
