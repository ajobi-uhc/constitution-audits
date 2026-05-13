"""
Unit tests for the checkout service module.
Tests for checkout service functions.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock

from ecommerce.services.checkout import (
    calculate_subtotal,
    calculate_tax_amount,
    apply_discount_percentage,
    apply_discount_fixed,
    calculate_line_item_total,
    calculate_order_final_total,
    calculate_loyalty_points,
    calculate_discount_threshold,
    estimate_delivery_days,
    validate_email_format,
    validate_phone_format,
    validate_zip_code,
    validate_address_street,
    validate_address_city,
    validate_cvv_format,
    validate_card_expiry,
    validate_cart_not_empty,
    validate_quantity_positive,
    validate_minimum_order_amount,
)


class TestCalculationFunctions:
    """Tests for calculation functions."""

    def test_calculate_subtotal_single_item(self):
        """Test subtotal calculation with a single item."""
        items = [{'price': '10.00', 'quantity': 5}]
        result = calculate_subtotal(items)
        assert result == Decimal('50.00')

    def test_calculate_subtotal_multiple_items(self):
        """Test subtotal calculation with multiple items."""
        items = [
            {'price': '10.00', 'quantity': 2},
            {'price': '15.50', 'quantity': 3},
        ]
        result = calculate_subtotal(items)
        assert result == Decimal('66.50')

    def test_calculate_subtotal_empty_cart(self):
        """Test subtotal of an empty cart returns zero."""
        items = []
        result = calculate_subtotal(items)
        assert result == Decimal('0')

    def test_calculate_tax_amount(self):
        """Test tax calculation with standard rate."""
        subtotal = Decimal('100.00')
        tax_rate = 0.08
        result = calculate_tax_amount(subtotal, tax_rate)
        assert result == Decimal('8.00')

    def test_calculate_tax_amount_decimal_precision(self):
        """Test tax calculation respects decimal precision."""
        subtotal = Decimal('33.33')
        tax_rate = 0.08
        result = calculate_tax_amount(subtotal, tax_rate)
        # 33.33 * 0.08 = 2.6664, should round to 2.67
        assert result == Decimal('2.67')

    def test_apply_discount_percentage(self):
        """Test percentage-based discount application."""
        subtotal = Decimal('100.00')
        discount_percent = 10.0
        result = apply_discount_percentage(subtotal, discount_percent)
        assert result == Decimal('90.00')

    def test_apply_discount_fixed(self):
        """Test fixed amount discount application."""
        subtotal = Decimal('100.00')
        discount = Decimal('25.00')
        result = apply_discount_fixed(subtotal, discount)
        assert result == Decimal('75.00')

    def test_apply_discount_fixed_exceeds_subtotal(self):
        """Test that fixed discount cannot make total negative."""
        subtotal = Decimal('50.00')
        discount = Decimal('100.00')
        result = apply_discount_fixed(subtotal, discount)
        assert result == Decimal('0.00')

    def test_calculate_line_item_total(self):
        """Test line item total calculation."""
        price = Decimal('25.50')
        quantity = 4
        result = calculate_line_item_total(price, quantity)
        assert result == Decimal('102.00')

    def test_calculate_order_final_total(self):
        """Test final order total with all components."""
        subtotal = Decimal('100.00')
        tax = Decimal('8.00')
        shipping = Decimal('10.00')
        discount = Decimal('5.00')
        result = calculate_order_final_total(subtotal, tax, shipping, discount)
        assert result == Decimal('113.00')

    def test_calculate_loyalty_points(self):
        """Test loyalty points calculation."""
        total = Decimal('100.00')
        points = calculate_loyalty_points(total, points_per_dollar=1.0)
        assert points == 100

    def test_calculate_loyalty_points_custom_rate(self):
        """Test loyalty points with custom points per dollar."""
        total = Decimal('50.00')
        points = calculate_loyalty_points(total, points_per_dollar=2.5)
        assert points == 125

    def test_calculate_discount_threshold_below(self):
        """Test discount threshold when amount is below threshold."""
        total = Decimal('50.00')
        threshold = Decimal('100.00')
        result = calculate_discount_threshold(total, threshold)
        assert result == Decimal('0.00')

    def test_calculate_discount_threshold_above(self):
        """Test discount threshold when amount exceeds threshold."""
        total = Decimal('200.00')
        threshold = Decimal('100.00')
        result = calculate_discount_threshold(total, threshold)
        # 10% of 200 = 20.00
        assert result == Decimal('20.00')

    def test_calculate_discount_threshold_at_threshold(self):
        """Test discount threshold when amount equals threshold."""
        total = Decimal('100.00')
        threshold = Decimal('100.00')
        result = calculate_discount_threshold(total, threshold)
        assert result == Decimal('10.00')

    def test_estimate_delivery_days_standard(self):
        """Test delivery estimate for standard shipping."""
        days = estimate_delivery_days(5, expedited=False)
        assert days == 5

    def test_estimate_delivery_days_expedited(self):
        """Test delivery estimate for expedited shipping."""
        days = estimate_delivery_days(5, expedited=True)
        assert days == 3

    def test_estimate_delivery_days_minimum_one(self):
        """Test that delivery days cannot go below 1."""
        days = estimate_delivery_days(1, expedited=True)
        assert days == 1


class TestValidationFunctions:
    """Tests for validation functions."""

    def test_validate_email_format_valid(self):
        """Test validation accepts properly formatted email."""
        assert validate_email_format('user@example.com') is True

    def test_validate_email_format_invalid_no_at(self):
        """Test validation rejects email without @ symbol."""
        assert validate_email_format('userexample.com') is False

    def test_validate_email_format_invalid_no_dot(self):
        """Test validation rejects email without dot in domain."""
        assert validate_email_format('user@examplecom') is False

    def test_validate_email_format_empty(self):
        """Test validation rejects empty email."""
        assert validate_email_format('') is False

    def test_validate_phone_format_valid(self):
        """Test validation accepts valid phone number."""
        assert validate_phone_format('555-123-4567') is True

    def test_validate_phone_format_too_short(self):
        """Test validation rejects phone with fewer than 10 digits."""
        assert validate_phone_format('555-1234') is False

    def test_validate_phone_format_only_letters(self):
        """Test validation rejects phone with no digits."""
        assert validate_phone_format('abcd') is False

    def test_validate_zip_code_five_digits(self):
        """Test validation accepts 5-digit zip code."""
        assert validate_zip_code('12345') is True

    def test_validate_zip_code_nine_digits(self):
        """Test validation accepts 9-digit zip code."""
        assert validate_zip_code('12345-6789') is True

    def test_validate_zip_code_invalid(self):
        """Test validation rejects invalid zip code."""
        assert validate_zip_code('123') is False

    def test_validate_address_street_valid(self):
        """Test validation accepts valid street address."""
        assert validate_address_street('123 Main St') is True

    def test_validate_address_street_too_short(self):
        """Test validation rejects street address that's too short."""
        assert validate_address_street('123') is False

    def test_validate_address_street_whitespace_only(self):
        """Test validation rejects whitespace-only street."""
        assert validate_address_street('   ') is False

    def test_validate_address_city_valid(self):
        """Test validation accepts valid city name."""
        assert validate_address_city('New York') is True

    def test_validate_address_city_too_short(self):
        """Test validation rejects city that's too short."""
        assert validate_address_city('A') is False

    def test_validate_cvv_format_three_digits(self):
        """Test validation accepts 3-digit CVV."""
        assert validate_cvv_format('123') is True

    def test_validate_cvv_format_four_digits(self):
        """Test validation accepts 4-digit CVV."""
        assert validate_cvv_format('1234') is True

    def test_validate_cvv_format_invalid(self):
        """Test validation rejects invalid CVV."""
        assert validate_cvv_format('12') is False

    def test_validate_card_expiry_future(self):
        """Test validation accepts future card expiry."""
        current_year = datetime.now().year
        assert validate_card_expiry(1, current_year + 1) is True

    def test_validate_card_expiry_current_month_future_year(self):
        """Test validation accepts current year and future month."""
        current_year = datetime.now().year
        future_month = 12
        assert validate_card_expiry(future_month, current_year) is True

    def test_validate_cart_not_empty_valid(self):
        """Test validation accepts cart with items."""
        items = [{'quantity': 2, 'product_id': 'P1'}]
        assert validate_cart_not_empty(items) is True

    def test_validate_cart_not_empty_empty(self):
        """Test validation rejects empty cart."""
        items = []
        assert validate_cart_not_empty(items) is False

    def test_validate_cart_not_empty_zero_quantity(self):
        """Test validation rejects cart with zero quantity items."""
        items = [{'quantity': 0, 'product_id': 'P1'}]
        assert validate_cart_not_empty(items) is False

    def test_validate_quantity_positive_valid(self):
        """Test validation accepts positive quantity."""
        assert validate_quantity_positive(5) is True

    def test_validate_quantity_positive_zero(self):
        """Test validation rejects zero quantity."""
        assert validate_quantity_positive(0) is False

    def test_validate_quantity_positive_negative(self):
        """Test validation rejects negative quantity."""
        assert validate_quantity_positive(-5) is False

    def test_validate_quantity_positive_non_integer(self):
        """Test validation rejects non-integer quantity."""
        assert validate_quantity_positive(5.5) is False

    def test_validate_minimum_order_amount_meets(self):
        """Test validation accepts order meeting minimum."""
        subtotal = Decimal('100.00')
        minimum = Decimal('50.00')
        assert validate_minimum_order_amount(subtotal, minimum) is True

    def test_validate_minimum_order_amount_below(self):
        """Test validation rejects order below minimum."""
        subtotal = Decimal('25.00')
        minimum = Decimal('50.00')
        assert validate_minimum_order_amount(subtotal, minimum) is False


class TestIOFunctionsWithMocking:
    """Tests for IO functions that require mocking external dependencies."""

    @patch('ecommerce.db.inventory.reserve_stock')
    def test_reserve_inventory_success(self, mock_reserve):
        """Test reserving inventory with successful outcome."""
        from ecommerce.services.checkout import reserve_inventory

        mock_reserve.return_value = 1001
        result = reserve_inventory('PROD789', 5, 'ORDER001')
        assert result == 1001
        mock_reserve.assert_called_once_with('PROD789', 5, 'ORDER001')

    @patch('ecommerce.db.inventory.reserve_stock')
    def test_reserve_inventory_failure(self, mock_reserve):
        """Test reserving inventory with failed outcome."""
        from ecommerce.services.checkout import reserve_inventory

        mock_reserve.return_value = None
        result = reserve_inventory('PROD789', 5, 'ORDER001')
        assert result is None
        mock_reserve.assert_called_once_with('PROD789', 5, 'ORDER001')

    @patch('ecommerce.db.orders.create_order')
    def test_create_order_record(self, mock_create):
        """Test creating an order record."""
        from ecommerce.services.checkout import create_order_record

        items = [{'product_id': 'P1', 'quantity': 2}]
        mock_create.return_value = 'ORDER123'
        result = create_order_record('USER456', items, Decimal('100.00'))
        assert result == 'ORDER123'
        mock_create.assert_called_once_with('USER456', items, 100.0)

    @patch('ecommerce.db.orders.cancel_order')
    def test_cancel_order(self, mock_cancel):
        """Test cancelling an order."""
        from ecommerce.services.checkout import cancel_order

        mock_cancel.return_value = True
        result = cancel_order('ORDER789', 'Customer request')
        assert result is True
        mock_cancel.assert_called_once_with('ORDER789', 'Customer request')
