"""Functional unit tests for the pricing module."""

import pytest
from decimal import Decimal
from ecommerce.services.pricing import (
    get_tier_multiplier,
    calculate_base_price,
    apply_percentage_discount,
    apply_fixed_discount,
    calculate_loyalty_discount,
    apply_bulk_quantity_discount,
    calculate_bulk_pricing,
    evaluate_promotional_rules,
    apply_coupon_discount,
    apply_seasonal_adjustment,
    calculate_tax_amount,
    calculate_total_with_tax,
    convert_currency,
    calculate_margin,
    calculate_markup,
    calculate_break_even_price,
    apply_tiered_pricing,
    calculate_volume_rebate,
    apply_student_discount,
    apply_senior_discount,
    calculate_subscription_discount,
    calculate_bundle_discount,
    calculate_cumulative_discounts,
    calculate_gift_card_balance_after_purchase,
    calculate_reward_points,
    calculate_points_discount,
    calculate_member_exclusive_price,
    calculate_price_with_insurance,
    calculate_handling_fee,
    calculate_price_after_fees,
    calculate_wholesale_price,
    calculate_reseller_tier_price,
    calculate_vip_customer_price,
    price_round_to_nearest_cent,
    price_round_to_nearest_dollar,
    calculate_average_item_price,
    calculate_price_after_maximum_discount,
    calculate_price_with_surcharge,
    calculate_financing_monthly_payment,
    calculate_total_financing_cost,
    calculate_financing_interest_paid,
)


class TestBasePricing:
    """Test basic pricing calculations."""

    def test_calculate_base_price_simple(self):
        """Test simple base price calculation."""
        unit_price = Decimal("10.00")
        quantity = 5
        result = calculate_base_price(unit_price, quantity)
        assert result == Decimal("50.00")

    def test_calculate_base_price_zero_quantity(self):
        """Test base price with zero quantity."""
        unit_price = Decimal("10.00")
        quantity = 0
        result = calculate_base_price(unit_price, quantity)
        assert result == Decimal("0.00")

    def test_calculate_base_price_decimal_price(self):
        """Test base price with decimal unit price."""
        unit_price = Decimal("12.99")
        quantity = 3
        result = calculate_base_price(unit_price, quantity)
        assert result == Decimal("38.97")


class TestDiscounts:
    """Test various discount calculations."""

    def test_apply_percentage_discount_simple(self):
        """Test simple percentage discount."""
        price = Decimal("100.00")
        discount_percent = 10.0
        result = apply_percentage_discount(price, discount_percent)
        assert result == Decimal("90.00")

    def test_apply_percentage_discount_large(self):
        """Test large percentage discount."""
        price = Decimal("1000.00")
        discount_percent = 50.0
        result = apply_percentage_discount(price, discount_percent)
        assert result == Decimal("500.00")

    def test_apply_fixed_discount_simple(self):
        """Test simple fixed discount."""
        price = Decimal("100.00")
        discount_amount = Decimal("25.00")
        result = apply_fixed_discount(price, discount_amount)
        assert result == Decimal("75.00")

    def test_apply_fixed_discount_zero_result(self):
        """Test fixed discount with result clamped to zero."""
        price = Decimal("50.00")
        discount_amount = Decimal("100.00")
        result = apply_fixed_discount(price, discount_amount)
        assert result == Decimal("0.00")

    def test_calculate_cumulative_discounts(self):
        """Test applying multiple discounts sequentially."""
        price = Decimal("1000.00")
        discounts = [10.0, 20.0, 5.0]
        result = calculate_cumulative_discounts(price, discounts)
        # 1000 * 0.9 * 0.8 * 0.95 = 684.00
        assert result == Decimal("684.00")

    def test_apply_student_discount(self):
        """Test student discount application."""
        price = Decimal("100.00")
        result = apply_student_discount(price)
        assert result == Decimal("90.00")

    def test_apply_senior_discount(self):
        """Test senior discount application."""
        price = Decimal("100.00")
        result = apply_senior_discount(price)
        assert result == Decimal("85.00")


class TestLoyaltyTiers:
    """Test loyalty tier calculations."""

    def test_get_tier_multiplier_bronze(self):
        """Test bronze tier multiplier."""
        result = get_tier_multiplier("bronze")
        assert result == Decimal("0.95")

    def test_get_tier_multiplier_platinum(self):
        """Test platinum tier multiplier."""
        result = get_tier_multiplier("platinum")
        assert result == Decimal("0.80")

    def test_calculate_loyalty_discount_gold(self):
        """Test loyalty discount for gold tier."""
        price = Decimal("100.00")
        result = calculate_loyalty_discount(price, "gold")
        assert result == Decimal("85.00")

    def test_calculate_loyalty_discount_silver(self):
        """Test loyalty discount for silver tier."""
        price = Decimal("200.00")
        result = calculate_loyalty_discount(price, "silver")
        assert result == Decimal("180.00")


class TestBulkPricing:
    """Test bulk and tiered pricing calculations."""

    def test_apply_bulk_quantity_discount_threshold_10(self):
        """Test bulk discount at 10 unit threshold."""
        base_price = Decimal("1000.00")
        quantity = 10
        result = apply_bulk_quantity_discount(base_price, quantity)
        assert result == Decimal("950.00")

    def test_apply_bulk_quantity_discount_threshold_50(self):
        """Test bulk discount at 50 unit threshold."""
        base_price = Decimal("5000.00")
        quantity = 50
        result = apply_bulk_quantity_discount(base_price, quantity)
        assert result == Decimal("4250.00")

    def test_apply_bulk_quantity_discount_threshold_250(self):
        """Test bulk discount at 250 unit threshold (highest tier)."""
        base_price = Decimal("25000.00")
        quantity = 250
        result = apply_bulk_quantity_discount(base_price, quantity)
        assert result == Decimal("18750.00")

    def test_apply_bulk_quantity_discount_below_threshold(self):
        """Test no discount below threshold."""
        base_price = Decimal("500.00")
        quantity = 5
        result = apply_bulk_quantity_discount(base_price, quantity)
        assert result == Decimal("500.00")

    def test_calculate_bulk_pricing(self):
        """Test full bulk pricing calculation."""
        unit_price = Decimal("10.00")
        quantity = 25
        result = calculate_bulk_pricing(unit_price, quantity)
        # Base: 10 * 25 = 250, then apply 25-unit discount (0.90)
        assert result == Decimal("225.00")

    def test_apply_tiered_pricing(self):
        """Test tiered pricing based on quantity."""
        unit_price = Decimal("100.00")
        quantity = 50
        tiers = [(10, Decimal("90")), (50, Decimal("80")), (100, Decimal("70"))]
        result = apply_tiered_pricing(unit_price, quantity, tiers)
        # Quantity 50 matches tier 50, so price is 80 per unit * 50 = 4000
        assert result == Decimal("4000.00")


class TestTaxCalculations:
    """Test tax computations."""

    def test_calculate_tax_amount_us(self):
        """Test US tax calculation."""
        price = Decimal("100.00")
        tax = calculate_tax_amount(price, "US")
        assert tax == Decimal("8.00")

    def test_calculate_tax_amount_eu(self):
        """Test EU tax calculation."""
        price = Decimal("100.00")
        tax = calculate_tax_amount(price, "EU")
        assert tax == Decimal("19.00")

    def test_calculate_tax_amount_uk(self):
        """Test UK tax calculation."""
        price = Decimal("100.00")
        tax = calculate_tax_amount(price, "UK")
        assert tax == Decimal("20.00")

    def test_calculate_total_with_tax_us(self):
        """Test total price with US tax."""
        price = Decimal("100.00")
        total = calculate_total_with_tax(price, "US")
        assert total == Decimal("108.00")

    def test_calculate_total_with_tax_eu(self):
        """Test total price with EU tax."""
        price = Decimal("100.00")
        total = calculate_total_with_tax(price, "EU")
        assert total == Decimal("119.00")

    def test_calculate_tax_amount_unknown_region(self):
        """Test tax for unknown region defaults to zero."""
        price = Decimal("100.00")
        tax = calculate_tax_amount(price, "ZZ")
        assert tax == Decimal("0.00")


class TestCurrencyConversion:
    """Test currency conversion calculations."""

    def test_convert_currency_usd_to_eur(self):
        """Test USD to EUR conversion."""
        amount = Decimal("100.00")
        result = convert_currency(amount, "USD", "EUR")
        # 100 / 1.0 * 1.10 = 110.00
        assert result == Decimal("110.00")

    def test_convert_currency_eur_to_gbp(self):
        """Test EUR to GBP conversion."""
        amount = Decimal("100.00")
        result = convert_currency(amount, "EUR", "GBP")
        # 100 / 1.10 * 1.27 ≈ 115.45
        assert abs(result - Decimal("115.45")) < Decimal("0.01")

    def test_convert_currency_same_currency(self):
        """Test conversion to same currency."""
        amount = Decimal("100.00")
        result = convert_currency(amount, "USD", "USD")
        assert result == Decimal("100.00")

    def test_convert_currency_to_jpy(self):
        """Test conversion to Japanese Yen."""
        amount = Decimal("100.00")
        result = convert_currency(amount, "USD", "JPY")
        # 100 / 1.0 * 0.0067 = 0.67
        assert result == Decimal("0.67")


class TestMarginAndMarkup:
    """Test margin and markup calculations."""

    def test_calculate_margin_standard(self):
        """Test standard margin calculation."""
        cost = Decimal("50.00")
        selling_price = Decimal("100.00")
        margin = calculate_margin(cost, selling_price)
        # (100 - 50) / 100 * 100 = 50.00%
        assert margin == Decimal("50.00")

    def test_calculate_margin_zero_selling_price(self):
        """Test margin with zero selling price."""
        cost = Decimal("50.00")
        selling_price = Decimal("0.00")
        margin = calculate_margin(cost, selling_price)
        assert margin == Decimal("0.00")

    def test_calculate_margin_low_margin(self):
        """Test low margin calculation."""
        cost = Decimal("100.00")
        selling_price = Decimal("110.00")
        margin = calculate_margin(cost, selling_price)
        # (110 - 100) / 110 * 100 = 9.09%
        assert abs(margin - Decimal("9.09")) < Decimal("0.01")

    def test_calculate_markup_standard(self):
        """Test standard markup calculation."""
        cost = Decimal("50.00")
        markup_percent = 100.0
        result = calculate_markup(cost, markup_percent)
        # 50 * (1 + 1.0) = 100.00
        assert result == Decimal("100.00")

    def test_calculate_markup_20_percent(self):
        """Test 20% markup calculation."""
        cost = Decimal("100.00")
        markup_percent = 20.0
        result = calculate_markup(cost, markup_percent)
        assert result == Decimal("120.00")

    def test_calculate_break_even_price(self):
        """Test break even price calculation."""
        cost = Decimal("50.00")
        target_margin_percent = 40.0
        result = calculate_break_even_price(cost, target_margin_percent)
        # 50 / (1 - 0.40) = 50 / 0.60 ≈ 83.33
        assert abs(result - Decimal("83.33")) < Decimal("0.01")

    def test_calculate_break_even_price_zero_margin(self):
        """Test break even with zero margin."""
        cost = Decimal("50.00")
        target_margin_percent = 0.0
        result = calculate_break_even_price(cost, target_margin_percent)
        assert result == Decimal("50.00")


class TestPromotionalRules:
    """Test promotional rule evaluation."""

    def test_evaluate_promotional_rules_percentage(self):
        """Test promotional rules with percentage discount."""
        price = Decimal("100.00")
        rules = [{"type": "percentage", "value": 10.0}]
        result = evaluate_promotional_rules(price, rules)
        assert result == Decimal("90.00")

    def test_evaluate_promotional_rules_fixed(self):
        """Test promotional rules with fixed discount."""
        price = Decimal("100.00")
        rules = [{"type": "fixed", "value": 25.0}]
        result = evaluate_promotional_rules(price, rules)
        assert result == Decimal("75.00")

    def test_evaluate_promotional_rules_multiplier(self):
        """Test promotional rules with multiplier."""
        price = Decimal("100.00")
        rules = [{"type": "multiplier", "value": 0.8}]
        result = evaluate_promotional_rules(price, rules)
        assert result == Decimal("80.00")

    def test_evaluate_promotional_rules_multiple(self):
        """Test multiple promotional rules applied sequentially."""
        price = Decimal("100.00")
        rules = [
            {"type": "percentage", "value": 10.0},
            {"type": "fixed", "value": 5.0},
            {"type": "multiplier", "value": 0.9}
        ]
        result = evaluate_promotional_rules(price, rules)
        # 100 * 0.9 = 90, then 90 - 5 = 85, then 85 * 0.9 = 76.5
        assert result == Decimal("76.50")


class TestCouponDiscounts:
    """Test coupon discount application."""

    def test_apply_coupon_discount_percentage(self):
        """Test percentage coupon discount."""
        price = Decimal("100.00")
        coupon = {
            "type": "percentage",
            "value": 10.0,
            "min_purchase": 50.0
        }
        result = apply_coupon_discount(price, coupon)
        assert result == Decimal("90.00")

    def test_apply_coupon_discount_fixed(self):
        """Test fixed coupon discount."""
        price = Decimal("100.00")
        coupon = {
            "type": "fixed",
            "value": 20.0,
            "min_purchase": 50.0
        }
        result = apply_coupon_discount(price, coupon)
        assert result == Decimal("80.00")

    def test_apply_coupon_discount_below_minimum(self):
        """Test coupon not applied when minimum not met."""
        price = Decimal("40.00")
        coupon = {
            "type": "percentage",
            "value": 10.0,
            "min_purchase": 50.0
        }
        result = apply_coupon_discount(price, coupon)
        assert result == Decimal("40.00")


class TestSeasonalAndSubscription:
    """Test seasonal and subscription-based pricing."""

    def test_apply_seasonal_adjustment_peak(self):
        """Test peak season adjustment."""
        price = Decimal("100.00")
        result = apply_seasonal_adjustment(price, "peak")
        assert result == Decimal("120.00")

    def test_apply_seasonal_adjustment_low(self):
        """Test low season adjustment."""
        price = Decimal("100.00")
        result = apply_seasonal_adjustment(price, "low")
        assert result == Decimal("85.00")

    def test_apply_seasonal_adjustment_holiday(self):
        """Test holiday season adjustment."""
        price = Decimal("100.00")
        result = apply_seasonal_adjustment(price, "holiday")
        assert result == Decimal("135.00")

    def test_calculate_subscription_discount_12_months(self):
        """Test 12-month subscription discount."""
        price = Decimal("100.00")
        result = calculate_subscription_discount(price, 12)
        assert result == Decimal("75.00")

    def test_calculate_subscription_discount_6_months(self):
        """Test 6-month subscription discount."""
        price = Decimal("100.00")
        result = calculate_subscription_discount(price, 6)
        assert result == Decimal("85.00")

    def test_calculate_subscription_discount_3_months(self):
        """Test 3-month subscription discount."""
        price = Decimal("100.00")
        result = calculate_subscription_discount(price, 3)
        assert result == Decimal("92.00")

    def test_calculate_subscription_discount_no_discount(self):
        """Test subscription discount below 3 months."""
        price = Decimal("100.00")
        result = calculate_subscription_discount(price, 1)
        assert result == Decimal("100.00")


class TestBundlesAndRewards:
    """Test bundle and reward calculations."""

    def test_calculate_bundle_discount(self):
        """Test bundle discount calculation."""
        items_prices = [Decimal("20.00"), Decimal("30.00"), Decimal("50.00")]
        result = calculate_bundle_discount(items_prices, 10.0)
        # Sum: 100, apply 10% discount: 90.00
        assert result == Decimal("90.00")

    def test_calculate_reward_points_standard(self):
        """Test standard reward points calculation."""
        purchase_amount = Decimal("100.00")
        points = calculate_reward_points(purchase_amount, 1.0)
        assert points == 100

    def test_calculate_reward_points_custom_rate(self):
        """Test custom reward points rate."""
        purchase_amount = Decimal("100.00")
        points = calculate_reward_points(purchase_amount, 2.0)
        assert points == 200

    def test_calculate_points_discount(self):
        """Test points redemption discount."""
        current_price = Decimal("100.00")
        points_to_redeem = 50
        points_value = Decimal("1.00")
        result = calculate_points_discount(current_price, points_to_redeem, points_value)
        assert result == Decimal("50.00")

    def test_calculate_gift_card_balance_after_purchase(self):
        """Test gift card balance after purchase."""
        balance = Decimal("100.00")
        purchase_amount = Decimal("30.00")
        result = calculate_gift_card_balance_after_purchase(balance, purchase_amount)
        assert result == Decimal("70.00")


class TestMemberAndSpecialCustomers:
    """Test member and VIP pricing."""

    def test_calculate_member_exclusive_price(self):
        """Test member exclusive pricing."""
        regular_price = Decimal("100.00")
        result = calculate_member_exclusive_price(regular_price, 15.0)
        assert result == Decimal("85.00")

    def test_calculate_vip_customer_price_default(self):
        """Test VIP customer price with default discount."""
        price = Decimal("100.00")
        result = calculate_vip_customer_price(price)
        assert result == Decimal("80.00")

    def test_calculate_vip_customer_price_custom(self):
        """Test VIP customer price with custom discount."""
        price = Decimal("200.00")
        result = calculate_vip_customer_price(price, 25.0)
        assert result == Decimal("150.00")

    def test_calculate_reseller_tier_price(self):
        """Test reseller tier pricing."""
        base_price = Decimal("100.00")
        # Tier 1 = no discount
        result1 = calculate_reseller_tier_price(base_price, 1)
        assert result1 == Decimal("100.00")
        # Tier 5 = 20% discount
        result5 = calculate_reseller_tier_price(base_price, 5)
        assert result5 == Decimal("80.00")

    def test_calculate_wholesale_price(self):
        """Test wholesale price calculation."""
        retail_price = Decimal("100.00")
        wholesale_margin_percent = 40.0
        result = calculate_wholesale_price(retail_price, wholesale_margin_percent)
        # 100 * (1 - 0.40) = 60.00
        assert result == Decimal("60.00")


class TestFeesAndCharges:
    """Test fees and charges calculations."""

    def test_calculate_price_with_insurance(self):
        """Test price with insurance fee."""
        product_price = Decimal("100.00")
        insurance_percent = 5.0
        result = calculate_price_with_insurance(product_price, insurance_percent)
        assert result == Decimal("105.00")

    def test_calculate_handling_fee(self):
        """Test handling fee calculation."""
        subtotal = Decimal("100.00")
        fee_percent = 2.5
        result = calculate_handling_fee(subtotal, fee_percent)
        assert result == Decimal("2.50")

    def test_calculate_price_after_fees(self):
        """Test price after adding multiple fees."""
        subtotal = Decimal("100.00")
        fee_list = [2.5, 5.0]
        result = calculate_price_after_fees(subtotal, fee_list)
        assert result == Decimal("107.50")

    def test_calculate_price_with_surcharge(self):
        """Test price with surcharge."""
        base_price = Decimal("100.00")
        surcharge_percent = 10.0
        result = calculate_price_with_surcharge(base_price, surcharge_percent)
        assert result == Decimal("110.00")


class TestPriceRounding:
    """Test price rounding operations."""

    def test_price_round_to_nearest_cent(self):
        """Test rounding to nearest cent."""
        price = Decimal("10.126")
        result = price_round_to_nearest_cent(price)
        assert result == Decimal("10.13")

    def test_price_round_to_nearest_cent_down(self):
        """Test rounding down to nearest cent."""
        price = Decimal("10.124")
        result = price_round_to_nearest_cent(price)
        assert result == Decimal("10.12")

    def test_price_round_to_nearest_dollar(self):
        """Test rounding to nearest dollar."""
        price = Decimal("10.51")
        result = price_round_to_nearest_dollar(price)
        assert result == Decimal("11")

    def test_price_round_to_nearest_dollar_down(self):
        """Test rounding down to nearest dollar."""
        price = Decimal("10.49")
        result = price_round_to_nearest_dollar(price)
        assert result == Decimal("10")


class TestAverageAndMaximum:
    """Test average and maximum discount calculations."""

    def test_calculate_average_item_price(self):
        """Test average item price calculation."""
        total_price = Decimal("100.00")
        item_count = 4
        result = calculate_average_item_price(total_price, item_count)
        assert result == Decimal("25.00")

    def test_calculate_average_item_price_zero_items(self):
        """Test average with zero items."""
        total_price = Decimal("100.00")
        item_count = 0
        result = calculate_average_item_price(total_price, item_count)
        assert result == Decimal("0.00")

    def test_calculate_price_after_maximum_discount(self):
        """Test price with maximum discount cap."""
        price = Decimal("1000.00")
        discounts = [20.0, 20.0, 20.0]
        max_discount = 40.0
        result = calculate_price_after_maximum_discount(price, discounts, max_discount)
        # Cumulative: 1000 * 0.8 * 0.8 * 0.8 = 512.00
        # Actual discount: (1000 - 512) / 1000 * 100 = 48.8%
        # Capped at 40%: 1000 * 0.6 = 600.00
        assert result == Decimal("600.00")


class TestVolumeRebate:
    """Test volume rebate calculations."""

    def test_calculate_volume_rebate(self):
        """Test volume rebate calculation."""
        base_price = Decimal("1000.00")
        units_sold = 100
        rebate_percent = 5.0
        result = calculate_volume_rebate(base_price, units_sold, rebate_percent)
        assert result == Decimal("50.00")


class TestFinancing:
    """Test financing calculations."""

    def test_calculate_financing_monthly_payment_no_interest(self):
        """Test monthly payment with zero interest."""
        total_price = Decimal("1200.00")
        months = 12
        interest_rate_percent = 0.0
        result = calculate_financing_monthly_payment(total_price, months, interest_rate_percent)
        assert result == Decimal("100.00")

    def test_calculate_financing_monthly_payment_with_interest(self):
        """Test monthly payment with interest rate."""
        total_price = Decimal("10000.00")
        months = 12
        interest_rate_percent = 12.0
        result = calculate_financing_monthly_payment(total_price, months, interest_rate_percent)
        # Should be greater than 10000/12 = 833.33 due to interest
        assert result > Decimal("833.33")

    def test_calculate_total_financing_cost(self):
        """Test total financing cost calculation."""
        monthly_payment = Decimal("100.00")
        months = 12
        result = calculate_total_financing_cost(monthly_payment, months)
        assert result == Decimal("1200.00")

    def test_calculate_financing_interest_paid(self):
        """Test financing interest paid calculation."""
        total_price = Decimal("10000.00")
        monthly_payment = Decimal("858.00")
        months = 12
        result = calculate_financing_interest_paid(total_price, monthly_payment, months)
        # Total paid: 858 * 12 = 10296, interest = 10296 - 10000 = 296
        assert result == Decimal("296.00")

    def test_calculate_financing_monthly_payment_zero_months(self):
        """Test financing with zero months returns original price."""
        total_price = Decimal("1000.00")
        months = 0
        interest_rate_percent = 10.0
        result = calculate_financing_monthly_payment(total_price, months, interest_rate_percent)
        assert result == Decimal("1000.00")
