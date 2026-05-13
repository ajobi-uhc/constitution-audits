"""
Checkout orchestration service for e-commerce platform.
Coordinates between DB and API modules for order management and processing.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from ecommerce.db import users as db_users
from ecommerce.db import orders as db_orders
from ecommerce.db import products as db_products
from ecommerce.db import inventory as db_inventory
from ecommerce.api import payments as api_payments
from ecommerce.api import shipping as api_shipping


# Calculation helpers

def calculate_subtotal(items: List[Dict[str, Any]]) -> Decimal:
    """Calculate subtotal from cart items without tax or shipping."""
    return sum(Decimal(str(item['price'])) * item['quantity'] for item in items)


def calculate_tax_amount(subtotal: Decimal, tax_rate: float) -> Decimal:
    """Calculate tax based on subtotal and tax rate."""
    return (subtotal * Decimal(str(tax_rate))).quantize(Decimal('0.01'))


def apply_discount_percentage(subtotal: Decimal, discount_percent: float) -> Decimal:
    """Apply percentage-based discount to subtotal."""
    discount = subtotal * Decimal(str(discount_percent / 100))
    return (subtotal - discount).quantize(Decimal('0.01'))


def apply_discount_fixed(subtotal: Decimal, discount_amount: Decimal) -> Decimal:
    """Apply fixed amount discount to subtotal."""
    return max(Decimal('0'), subtotal - discount_amount).quantize(Decimal('0.01'))


def calculate_line_item_total(price: Decimal, quantity: int) -> Decimal:
    """Calculate total for a single line item."""
    return (Decimal(str(price)) * quantity).quantize(Decimal('0.01'))


def validate_email_format(email: str) -> bool:
    """Check if email has valid basic format."""
    return '@' in email and '.' in email.split('@')[1] if '@' in email else False


def validate_phone_format(phone: str) -> bool:
    """Check if phone number has at least 10 digits."""
    digits = ''.join(c for c in phone if c.isdigit())
    return len(digits) >= 10


def validate_zip_code(zip_code: str) -> bool:
    """Validate zip code format (5 or 9 digits)."""
    digits = ''.join(c for c in zip_code if c.isdigit())
    return len(digits) in [5, 9]


def validate_address_street(street: str) -> bool:
    """Validate street address has minimum length and format."""
    return len(street.strip()) >= 5


def validate_address_city(city: str) -> bool:
    """Validate city name has minimum length."""
    return len(city.strip()) >= 2


def validate_cvv_format(cvv: str) -> bool:
    """Check if CVV has 3-4 digits."""
    digits = ''.join(c for c in cvv if c.isdigit())
    return len(digits) in [3, 4]


def validate_card_expiry(exp_month: int, exp_year: int) -> bool:
    """Check if card expiry is in the future."""
    now = datetime.now()
    return (exp_year > now.year) or (exp_year == now.year and exp_month >= now.month)


def validate_cart_not_empty(items: List[Dict[str, Any]]) -> bool:
    """Ensure cart has at least one item."""
    return len(items) > 0 and all(item.get('quantity', 0) > 0 for item in items)


def validate_quantity_positive(quantity: int) -> bool:
    """Ensure quantity is a positive integer."""
    return isinstance(quantity, int) and quantity > 0


def calculate_discount_threshold(total_amount: Decimal, threshold: Decimal) -> Decimal:
    """Return discount if total exceeds threshold, otherwise zero."""
    if total_amount >= threshold:
        return (total_amount * Decimal('0.10')).quantize(Decimal('0.01'))
    return Decimal('0.00')


def calculate_order_final_total(subtotal: Decimal, tax: Decimal, shipping: Decimal, discount: Decimal) -> Decimal:
    """Calculate final order total after all adjustments."""
    return (subtotal + tax + shipping - discount).quantize(Decimal('0.01'))


def calculate_loyalty_points(total_amount: Decimal, points_per_dollar: float = 1.0) -> int:
    """Calculate loyalty points earned on this order."""
    return int(total_amount * Decimal(str(points_per_dollar)))


def validate_minimum_order_amount(subtotal: Decimal, minimum: Decimal) -> bool:
    """Check if order meets minimum purchase requirement."""
    return subtotal >= minimum


def estimate_delivery_days(base_days: int, expedited: bool = False) -> int:
    """Estimate delivery time based on shipping method."""
    return max(1, base_days - 2 if expedited else base_days)



def validate_stock_availability(product_id: str, quantity: int) -> bool:
    """Validate if product has sufficient stock."""
    stock_level = db_inventory.check_stock(product_id)
    return stock_level >= quantity


def validate_payment_method(user_id: str, payment_method_id: str) -> bool:
    """Validate payment method belongs to user."""
    methods = db_users.get_payment_methods(user_id)
    return any(m['id'] == payment_method_id for m in methods)


def calculate_final_shipping_cost(destination_zip: str, weight_lbs: float, overnight: bool = False) -> Decimal:
    """Calculate final shipping cost for destination."""
    rate = api_shipping.get_rate(destination_zip, weight_lbs, overnight)
    return Decimal(str(rate))


def validate_product_availability(product_id: str) -> bool:
    """Check if product is currently available for purchase."""
    product = db_products.get_product_details(product_id)
    return product is not None and product.get('available', False)


def calculate_bulk_discount_rate(product_id: str, quantity: int) -> float:
    """Calculate discount rate based on product and quantity."""
    tiers = db_products.get_bulk_discount_tiers(product_id)
    for tier in sorted(tiers, key=lambda t: t['min_qty'], reverse=True):
        if quantity >= tier['min_qty']:
            return tier['discount_rate']
    return 0.0



def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Retrieve user profile and preferences from database."""
    return db_users.get_user_profile(user_id)


def get_user_addresses(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all saved addresses for user."""
    return db_users.get_addresses(user_id)


def get_cart_items(cart_id: str) -> List[Dict[str, Any]]:
    """Retrieve all items in shopping cart."""
    return db_orders.get_cart_contents(cart_id)


def get_product_price(product_id: str) -> Decimal:
    """Fetch current product price from database."""
    price = db_products.get_product_price(product_id)
    return Decimal(str(price))


def get_product_details(product_id: str) -> Dict[str, Any]:
    """Retrieve complete product information."""
    return db_products.get_product_details(product_id)


def reserve_inventory(product_id: str, quantity: int, order_id: str) -> bool:
    """Reserve inventory items for pending order."""
    return db_inventory.reserve_stock(product_id, quantity, order_id)


def release_inventory(product_id: str, quantity: int, order_id: str) -> bool:
    """Release reserved inventory back to stock."""
    return db_inventory.release_reserved(product_id, quantity, order_id)


def process_payment(payment_info: Dict[str, Any]) -> Dict[str, Any]:
    """Send payment to processor and receive confirmation."""
    return api_payments.process_charge(payment_info)


def refund_payment(transaction_id: str, amount: Decimal) -> Dict[str, Any]:
    """Initiate refund for a processed payment."""
    return api_payments.initiate_refund(transaction_id, float(amount))


def calculate_shipping_rate(destination: str, weight: float, method: str) -> Decimal:
    """Request shipping rate from carrier API."""
    rate = api_shipping.get_rate(destination, weight, method)
    return Decimal(str(rate))


def get_shipping_options(zip_code: str) -> List[Dict[str, Any]]:
    """Fetch available shipping methods for address."""
    return api_shipping.get_available_methods(zip_code)


def create_order_record(user_id: str, items: List[Dict[str, Any]], total: Decimal) -> str:
    """Insert new order into database and return order ID."""
    return db_orders.create_order(user_id, items, float(total))


def update_order_status(order_id: str, status: str) -> bool:
    """Update order status in database."""
    return db_orders.update_status(order_id, status)


def get_order_details(order_id: str) -> Dict[str, Any]:
    """Retrieve full order information from database."""
    return db_orders.get_order(order_id)


def save_shipping_address(order_id: str, address: Dict[str, str]) -> bool:
    """Save shipping address to order record."""
    return db_orders.set_shipping_address(order_id, address)


def save_billing_address(order_id: str, address: Dict[str, str]) -> bool:
    """Save billing address to order record."""
    return db_orders.set_billing_address(order_id, address)


def mark_order_as_paid(order_id: str, transaction_id: str) -> bool:
    """Mark order as paid with transaction reference."""
    return db_orders.mark_paid(order_id, transaction_id)


def send_order_confirmation(user_id: str, order_id: str) -> bool:
    """Trigger order confirmation notification to user."""
    return db_orders.send_confirmation_email(user_id, order_id)


def apply_promo_code(order_id: str, promo_code: str) -> Optional[Decimal]:
    """Apply promotional code and return discount amount."""
    discount = db_orders.apply_promo(order_id, promo_code)
    return Decimal(str(discount)) if discount else None


def validate_promo_code(promo_code: str) -> Tuple[bool, str]:
    """Check if promo code is valid and active."""
    result = db_orders.validate_promo_code(promo_code)
    return result.get('valid', False), result.get('message', '')


def get_user_loyalty_balance(user_id: str) -> int:
    """Fetch current loyalty points balance for user."""
    return db_users.get_loyalty_points(user_id)


def deduct_loyalty_points(user_id: str, points: int) -> bool:
    """Subtract loyalty points from user account."""
    return db_users.deduct_points(user_id, points)


def add_loyalty_points(user_id: str, points: int) -> bool:
    """Add loyalty points to user account."""
    return db_users.add_points(user_id, points)


def get_tax_rate_for_location(state: str, zip_code: str) -> float:
    """Fetch applicable tax rate for shipping destination."""
    return db_orders.get_tax_rate(state, zip_code)


def initiate_checkout_session(user_id: str, cart_id: str) -> str:
    """Create new checkout session and return session ID."""
    return db_orders.create_checkout_session(user_id, cart_id)


def get_checkout_session(session_id: str) -> Dict[str, Any]:
    """Retrieve checkout session state."""
    return db_orders.get_session(session_id)


def finalize_order(order_id: str, payment_confirmed: bool) -> bool:
    """Mark order as finalized after payment confirmation."""
    if payment_confirmed:
        return db_orders.finalize(order_id)
    return False


def cancel_order(order_id: str, reason: str) -> bool:
    """Cancel order and release reserved inventory."""
    return db_orders.cancel_order(order_id, reason)


def clear_cart(cart_id: str) -> bool:
    """Remove all items from shopping cart."""
    return db_orders.clear_cart_contents(cart_id)


def add_item_to_cart(cart_id: str, product_id: str, quantity: int) -> bool:
    """Add product to shopping cart."""
    return db_orders.add_to_cart(cart_id, product_id, quantity)


def remove_item_from_cart(cart_id: str, product_id: str) -> bool:
    """Remove product from shopping cart."""
    return db_orders.remove_from_cart(cart_id, product_id)


def update_cart_item_quantity(cart_id: str, product_id: str, quantity: int) -> bool:
    """Update quantity of item in cart."""
    return db_orders.update_cart_quantity(cart_id, product_id, quantity)


def process_checkout_flow(user_id: str, cart_id: str, shipping_address: Dict[str, str], payment_info: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute complete checkout: validate, reserve, process payment, create order."""
    try:
        cart_items = get_cart_items(cart_id)
        if not validate_cart_not_empty(cart_items):
            return False, "Cart is empty"

        order_id = create_order_record(user_id, cart_items, calculate_subtotal(cart_items))
        if not save_shipping_address(order_id, shipping_address):
            return False, "Failed to save address"

        for item in cart_items:
            if not reserve_inventory(item['product_id'], item['quantity'], order_id):
                cancel_order(order_id, "Inventory reservation failed")
                return False, "Insufficient stock"

        payment_result = process_payment(payment_info)
        if not payment_result.get('success', False):
            release_inventory(cart_items[0]['product_id'], cart_items[0]['quantity'], order_id)
            return False, "Payment declined"

        mark_order_as_paid(order_id, payment_result['transaction_id'])
        finalize_order(order_id, True)
        send_order_confirmation(user_id, order_id)
        clear_cart(cart_id)
        return True, order_id
    except Exception as e:
        return False, str(e)
