"""
Unit Tests: Business Rules

Test pure functions from domain layer.
All tests are deterministic and require no database.
"""

import pytest
from src.domain import (
    Money, calculate_tax, apply_discount, validate_stock_deduction,
    compute_stock_on_hand, InvalidDiscountError, InsufficientStockError,
)


class TestMoneyClass:
    """Test Money value object."""

    def test_money_creation(self):
        """Test creating Money instance."""
        m = Money(cents=10000)
        assert m.cents == 10000
        assert m.to_float() == 100.0

    def test_money_addition(self):
        """Test adding Money."""
        m1 = Money(cents=10000)  # ₹100.00
        m2 = Money(cents=5000)   # ₹50.00
        result = m1 + m2
        assert result.cents == 15000

    def test_money_subtraction(self):
        """Test subtracting Money."""
        m1 = Money(cents=10000)
        m2 = Money(cents=3000)
        result = m1 - m2
        assert result.cents == 7000

    def test_money_multiplication(self):
        """Test multiplying Money."""
        m = Money(cents=10000)  # ₹100.00
        result = m * 2.5  # 2.5x
        assert result.cents == 25000  # ₹250.00

    def test_money_immutability(self):
        """Test Money is frozen (immutable)."""
        m = Money(cents=10000)
        with pytest.raises(AttributeError):
            m.cents = 20000  # type: ignore

    def test_money_from_float(self):
        """Test creating Money from float."""
        m = Money.from_float(150.75)
        assert m.cents == 15075


class TestTaxCalculation:
    """Test tax calculation function."""

    def test_tax_calculation_18_percent(self):
        """Test standard 18% tax rate."""
        subtotal = Money(cents=10000)  # ₹100.00
        tax = calculate_tax(subtotal, 0.18)
        assert tax.cents == 1800  # ₹18.00

    def test_tax_calculation_zero_percent(self):
        """Test zero tax rate."""
        subtotal = Money(cents=10000)
        tax = calculate_tax(subtotal, 0.0)
        assert tax.cents == 0

    def test_tax_calculation_rounding(self):
        """Test tax calculation with rounding."""
        subtotal = Money(cents=33333)  # ₹333.33
        tax = calculate_tax(subtotal, 0.18)
        # 333.33 * 0.18 = 60.00 (rounded)
        assert tax.cents == 6000

    def test_invalid_tax_rate(self):
        """Test invalid tax rate raises error."""
        subtotal = Money(cents=10000)
        with pytest.raises(ValueError):
            calculate_tax(subtotal, 1.5)  # >100%
        with pytest.raises(ValueError):
            calculate_tax(subtotal, -0.1)  # <0%


class TestDiscountValidation:
    """Test discount validation and application."""

    def test_apply_percentage_discount(self):
        """Test applying percentage discount."""
        price = Money(cents=10000)  # ₹100.00
        discounted = apply_discount(price, "percentage", 10.0)  # 10% off
        assert discounted.cents == 9000  # ₹90.00

    def test_apply_absolute_discount(self):
        """Test applying absolute discount."""
        price = Money(cents=10000)
        discounted = apply_discount(price, "absolute", 1000)  # ₹10 off
        assert discounted.cents == 9000

    def test_max_percentage_discount(self):
        """Test max 50% discount."""
        price = Money(cents=10000)
        discounted = apply_discount(price, "percentage", 50.0)
        assert discounted.cents == 5000

    def test_exceed_percentage_discount_fails(self):
        """Test discount > 50% raises error."""
        price = Money(cents=10000)
        with pytest.raises(InvalidDiscountError):
            apply_discount(price, "percentage", 60.0)

    def test_exceed_absolute_discount_fails(self):
        """Test absolute discount > price raises error."""
        price = Money(cents=10000)
        with pytest.raises(InvalidDiscountError):
            apply_discount(price, "absolute", 15000)  # ₹150 > ₹100


class TestStockValidation:
    """Test stock deduction validation."""

    def test_sufficient_stock(self):
        """Test validation with sufficient stock."""
        result = validate_stock_deduction(current_stock=100, qty_to_deduct=50)
        assert result is True

    def test_insufficient_stock(self):
        """Test validation with insufficient stock."""
        with pytest.raises(InsufficientStockError):
            validate_stock_deduction(current_stock=10, qty_to_deduct=20)

    def test_exact_stock_deduction(self):
        """Test deducting exact amount."""
        result = validate_stock_deduction(current_stock=50, qty_to_deduct=50)
        assert result is True


class TestStockComputation:
    """Test stock on hand computation from ledger."""

    def test_compute_stock_empty_ledger(self):
        """Test with no ledger entries."""
        entries = []
        stock = compute_stock_on_hand(entries)
        assert stock == 0

    def test_compute_stock_single_entry(self):
        """Test with single purchase."""
        entries = [(100, "PURCHASE")]
        stock = compute_stock_on_hand(entries)
        assert stock == 100

    def test_compute_stock_with_sales(self):
        """Test with purchase and sale."""
        entries = [(100, "PURCHASE"), (-30, "SALE")]
        stock = compute_stock_on_hand(entries)
        assert stock == 70

    def test_compute_stock_mixed_transactions(self):
        """Test with mixed transaction types."""
        entries = [
            (100, "PURCHASE"),
            (-20, "SALE"),
            (-5, "WASTAGE"),
            (10, "RETURN"),
            (5, "ADJUSTMENT"),
        ]
        stock = compute_stock_on_hand(entries)
        assert stock == 90  # 100 - 20 - 5 + 10 + 5
