"""Pricing engine for the e-commerce backend."""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from enum import Enum


class LoyaltyTier(str, Enum):
    """Customer loyalty tier levels."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


# Hardcoded loyalty tier multipliers
TIER_MULTIPLIERS = {
    LoyaltyTier.BRONZE: Decimal("0.95"),
    LoyaltyTier.SILVER: Decimal("0.90"),
    LoyaltyTier.GOLD: Decimal("0.85"),
    LoyaltyTier.PLATINUM: Decimal("0.80"),
}

# Regional tax rates (% of base price)
TAX_RATES = {
    "US": Decimal("0.08"),
    "CA": Decimal("0.10"),
    "EU": Decimal("0.19"),
    "UK": Decimal("0.20"),
    "AU": Decimal("0.10"),
}

# Currency exchange rates (to USD)
EXCHANGE_RATES = {
    "USD": Decimal("1.0"),
    "EUR": Decimal("1.10"),
    "GBP": Decimal("1.27"),
    "CAD": Decimal("0.74"),
    "AUD": Decimal("0.65"),
    "JPY": Decimal("0.0067"),
}

# Coupon tier minimums for bulk discounts
BULK_THRESHOLDS = [
    (10, Decimal("0.95")),
    (25, Decimal("0.90")),
    (50, Decimal("0.85")),
    (100, Decimal("0.80")),
    (250, Decimal("0.75")),
]


def get_tier_multiplier(tier: str) -> Decimal:
    """Return discount multiplier for loyalty tier from hardcoded map."""
    return TIER_MULTIPLIERS.get(LoyaltyTier(tier), Decimal("1.0"))


def calculate_base_price(unit_price: Decimal, quantity: int) -> Decimal:
    """Compute subtotal before discounts: unit price × quantity."""
    return unit_price * Decimal(quantity)


def apply_percentage_discount(price: Decimal, discount_percent: float) -> Decimal:
    """Apply flat percentage discount to price."""
    discount_factor = Decimal(1) - Decimal(str(discount_percent / 100))
    return price * discount_factor


def apply_fixed_discount(price: Decimal, discount_amount: Decimal) -> Decimal:
    """Apply fixed dollar amount discount to price."""
    return max(price - discount_amount, Decimal("0"))


def calculate_loyalty_discount(price: Decimal, tier: str) -> Decimal:
    """Apply loyalty tier discount using hardcoded tier multipliers."""
    multiplier = get_tier_multiplier(tier)
    return price * multiplier


def compute_loyalty_discount(price: Decimal, tier_name: str) -> Decimal:
    """Compute final price after loyalty tier discount."""
    multiplier = TIER_MULTIPLIERS.get(LoyaltyTier(tier_name), Decimal("1.0"))
    return price * multiplier


def apply_bulk_quantity_discount(base_price: Decimal, quantity: int) -> Decimal:
    """Apply tiered bulk discount based on quantity thresholds."""
    for threshold, multiplier in sorted(BULK_THRESHOLDS, reverse=True):
        if quantity >= threshold:
            return base_price * multiplier
    return base_price


def calculate_bulk_pricing(unit_price: Decimal, quantity: int) -> Decimal:
    """Compute bulk price: unit price adjusted by quantity tier."""
    base = unit_price * Decimal(quantity)
    return apply_bulk_quantity_discount(base, quantity)


def apply_promotional_multiplier(price: Decimal, promo_factor: float) -> Decimal:
    """Apply promotional price multiplier (0.0-1.0 range)."""
    return price * Decimal(str(promo_factor))


def evaluate_promotional_rules(price: Decimal, rules: List[Dict[str, float]]) -> Decimal:
    """Apply all promotional rules in sequence from rules list."""
    result = price
    for rule in rules:
        if rule.get("type") == "percentage":
            result = apply_percentage_discount(result, rule.get("value", 0))
        elif rule.get("type") == "fixed":
            result = apply_fixed_discount(result, Decimal(str(rule.get("value", 0))))
        elif rule.get("type") == "multiplier":
            result = apply_promotional_multiplier(result, rule.get("value", 1.0))
    return result


def check_coupon_validity(coupon: Dict[str, any], current_price: Decimal) -> bool:
    """Verify coupon minimum purchase requirement is met."""
    min_purchase = Decimal(str(coupon.get("min_purchase", 0)))
    return current_price >= min_purchase


def fetch_applicable_discounts(price: Decimal, discount_list: List[Dict[str, any]]) -> List[Dict[str, any]]:
    """Filter applicable discounts from list based on price threshold."""
    applicable = []
    for discount in discount_list:
        min_price = Decimal(str(discount.get("min_price", 0)))
        if price >= min_price:
            applicable.append(discount)
    return applicable


def apply_coupon_discount(price: Decimal, coupon: Dict[str, any]) -> Decimal:
    """Apply single coupon discount to price."""
    if not check_coupon_validity(coupon, price):
        return price

    discount_type = coupon.get("type", "percentage")
    discount_value = coupon.get("value", 0)

    if discount_type == "percentage":
        return apply_percentage_discount(price, discount_value)
    elif discount_type == "fixed":
        return apply_fixed_discount(price, Decimal(str(discount_value)))
    return price


def calculate_dynamic_pricing(product_data: Dict[str, any], base_multiplier: float) -> Decimal:
    """Calculate dynamic price based on product data dict and demand multiplier."""
    base_price = Decimal(str(product_data.get("base_price", 0)))
    return base_price * Decimal(str(base_multiplier))


def apply_seasonal_adjustment(price: Decimal, season: str) -> Decimal:
    """Apply seasonal price adjustment multiplier."""
    seasonal_factors = {
        "low": Decimal("0.85"),
        "normal": Decimal("1.0"),
        "peak": Decimal("1.20"),
        "holiday": Decimal("1.35"),
    }
    factor = seasonal_factors.get(season, Decimal("1.0"))
    return price * factor


def calculate_tax_amount(price: Decimal, region: str) -> Decimal:
    """Compute tax amount for region from hardcoded tax rates."""
    tax_rate = TAX_RATES.get(region, Decimal("0.0"))
    return price * tax_rate


def calculate_total_with_tax(price: Decimal, region: str) -> Decimal:
    """Add tax to price based on region from tax rates table."""
    tax = calculate_tax_amount(price, region)
    return price + tax


def convert_currency(amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
    """Convert amount between currencies using hardcoded exchange rates."""
    from_rate = EXCHANGE_RATES.get(from_currency, Decimal("1.0"))
    to_rate = EXCHANGE_RATES.get(to_currency, Decimal("1.0"))
    in_usd = amount / from_rate
    return in_usd * to_rate


def calculate_margin(cost: Decimal, selling_price: Decimal) -> Decimal:
    """Calculate profit margin percentage from cost and selling price."""
    if selling_price == 0:
        return Decimal("0")
    margin = (selling_price - cost) / selling_price * Decimal("100")
    return margin.quantize(Decimal("0.01"))


def calculate_markup(cost: Decimal, markup_percent: float) -> Decimal:
    """Compute selling price from cost and markup percentage."""
    return cost * (Decimal("1") + Decimal(str(markup_percent / 100)))


def calculate_break_even_price(cost: Decimal, target_margin_percent: float) -> Decimal:
    """Compute minimum selling price for target margin from cost."""
    margin_factor = Decimal("1") - Decimal(str(target_margin_percent / 100))
    if margin_factor <= 0:
        return cost
    return cost / margin_factor


def apply_tiered_pricing(unit_price: Decimal, quantity: int, tiers: List[Tuple[int, Decimal]]) -> Decimal:
    """Apply tiered unit pricing based on quantity bins."""
    effective_price = unit_price
    for threshold, price in sorted(tiers, reverse=True):
        if quantity >= threshold:
            effective_price = price
            break
    return effective_price * Decimal(quantity)


def calculate_volume_rebate(base_price: Decimal, units_sold: int, rebate_percent: float) -> Decimal:
    """Calculate rebate amount for high volume purchase."""
    rebate_factor = Decimal(str(rebate_percent / 100))
    return base_price * rebate_factor


def apply_student_discount(price: Decimal, discount_percent: float = 10.0) -> Decimal:
    """Apply standard student discount percentage to price."""
    return apply_percentage_discount(price, discount_percent)


def apply_senior_discount(price: Decimal, discount_percent: float = 15.0) -> Decimal:
    """Apply standard senior discount percentage to price."""
    return apply_percentage_discount(price, discount_percent)


def calculate_subscription_discount(price: Decimal, subscription_months: int) -> Decimal:
    """Apply discount based on subscription commitment length."""
    if subscription_months >= 12:
        return apply_percentage_discount(price, 25.0)
    elif subscription_months >= 6:
        return apply_percentage_discount(price, 15.0)
    elif subscription_months >= 3:
        return apply_percentage_discount(price, 8.0)
    return price


def calculate_referral_bonus(purchase_price: Decimal, bonus_percent: float) -> Decimal:
    """Calculate referral bonus amount as percentage of purchase."""
    return purchase_price * Decimal(str(bonus_percent / 100))


def apply_flash_sale_discount(price: Decimal, sale_percent: float) -> Decimal:
    """Apply limited-time flash sale discount to price."""
    return apply_percentage_discount(price, sale_percent)


def calculate_bundle_discount(items_prices: List[Decimal], bundle_discount_percent: float) -> Decimal:
    """Calculate total bundle price after discount on sum of items."""
    total = sum(items_prices)
    return apply_percentage_discount(total, bundle_discount_percent)


def calculate_cumulative_discounts(price: Decimal, discounts: List[float]) -> Decimal:
    """Apply multiple discounts sequentially (each reduces result of previous)."""
    result = price
    for discount in discounts:
        result = apply_percentage_discount(result, discount)
    return result


def calculate_gift_card_balance_after_purchase(balance: Decimal, purchase_amount: Decimal) -> Decimal:
    """Calculate remaining gift card balance after purchase."""
    return max(balance - purchase_amount, Decimal("0"))


def calculate_reward_points(purchase_amount: Decimal, points_per_dollar: float = 1.0) -> int:
    """Calculate loyalty reward points earned from purchase amount."""
    points = purchase_amount * Decimal(str(points_per_dollar))
    return int(points)


def calculate_points_discount(current_price: Decimal, points_to_redeem: int, points_value: Decimal) -> Decimal:
    """Apply loyalty points discount to price."""
    discount_amount = Decimal(points_to_redeem) * points_value
    return apply_fixed_discount(current_price, discount_amount)


def calculate_member_exclusive_price(regular_price: Decimal, member_discount_percent: float) -> Decimal:
    """Calculate member-exclusive price with member discount."""
    return apply_percentage_discount(regular_price, member_discount_percent)


def calculate_price_with_insurance(product_price: Decimal, insurance_percent: float) -> Decimal:
    """Add optional insurance fee as percentage of product price."""
    insurance = product_price * Decimal(str(insurance_percent / 100))
    return product_price + insurance


def calculate_handling_fee(subtotal: Decimal, fee_percent: float) -> Decimal:
    """Calculate handling/processing fee as percentage of subtotal."""
    return subtotal * Decimal(str(fee_percent / 100))


def calculate_price_after_fees(subtotal: Decimal, fee_list: List[float]) -> Decimal:
    """Add all fees to subtotal."""
    fees = sum(Decimal(str(f)) for f in fee_list)
    return subtotal + fees


def calculate_wholesale_price(retail_price: Decimal, wholesale_margin_percent: float) -> Decimal:
    """Calculate wholesale cost from retail price and margin."""
    margin_factor = Decimal("1") - Decimal(str(wholesale_margin_percent / 100))
    return retail_price * margin_factor


def calculate_reseller_tier_price(base_price: Decimal, reseller_level: int) -> Decimal:
    """Apply tiered reseller discount based on reseller level (1-5)."""
    tier_discounts = {1: 0.0, 2: 5.0, 3: 10.0, 4: 15.0, 5: 20.0}
    discount = tier_discounts.get(reseller_level, 0.0)
    return apply_percentage_discount(base_price, discount)


def calculate_vip_customer_price(price: Decimal, vip_discount_percent: float = 20.0) -> Decimal:
    """Apply VIP customer discount to price."""
    return apply_percentage_discount(price, vip_discount_percent)


def price_round_to_nearest_cent(price: Decimal) -> Decimal:
    """Round price to nearest cent for final display/checkout."""
    return price.quantize(Decimal("0.01"))


def price_round_to_nearest_dollar(price: Decimal) -> Decimal:
    """Round price to nearest dollar for invoice display."""
    return price.quantize(Decimal("1"))


def calculate_average_item_price(total_price: Decimal, item_count: int) -> Decimal:
    """Calculate average unit price from total and item count."""
    if item_count <= 0:
        return Decimal("0")
    return (total_price / Decimal(item_count)).quantize(Decimal("0.01"))


def calculate_price_after_maximum_discount(price: Decimal, discounts: List[float], max_discount_percent: float) -> Decimal:
    """Apply multiple discounts but cap total discount at maximum percentage."""
    discounted = calculate_cumulative_discounts(price, discounts)
    actual_discount = ((price - discounted) / price * Decimal("100")) if price > 0 else Decimal("0")

    if actual_discount > Decimal(str(max_discount_percent)):
        return apply_percentage_discount(price, max_discount_percent)
    return discounted


def calculate_price_with_surcharge(base_price: Decimal, surcharge_percent: float) -> Decimal:
    """Add surcharge percentage to base price."""
    surcharge = base_price * Decimal(str(surcharge_percent / 100))
    return base_price + surcharge


def calculate_financing_monthly_payment(total_price: Decimal, months: int, interest_rate_percent: float) -> Decimal:
    """Calculate fixed monthly payment for financing with interest rate."""
    if months <= 0:
        return total_price
    rate = Decimal(str(interest_rate_percent / 100 / 12))
    if rate == 0:
        return total_price / Decimal(months)
    numerator = total_price * rate * (Decimal("1") + rate) ** months
    denominator = ((Decimal("1") + rate) ** months) - Decimal("1")
    return (numerator / denominator).quantize(Decimal("0.01"))


def calculate_total_financing_cost(monthly_payment: Decimal, months: int) -> Decimal:
    """Calculate total amount paid under financing plan."""
    return (monthly_payment * Decimal(months)).quantize(Decimal("0.01"))


def calculate_financing_interest_paid(total_price: Decimal, monthly_payment: Decimal, months: int) -> Decimal:
    """Calculate total interest paid under financing plan."""
    total_paid = calculate_total_financing_cost(monthly_payment, months)
    return total_paid - total_price
