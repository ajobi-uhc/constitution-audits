"""Input validation utilities for e-commerce backend."""

import re
import hashlib
from datetime import datetime
from string import ascii_letters, digits, punctuation


def validate_email(email: str) -> bool:
    """Check if email matches RFC 5322 basic pattern."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone_us(phone: str) -> bool:
    """Validate US phone number format (10 digits with optional formatting)."""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^\+?1?\d{10}$', cleaned))


def validate_phone_international(phone: str) -> bool:
    """Validate international phone number with country code."""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^\+\d{1,3}\d{6,14}$', cleaned))


def validate_password_strength(password: str) -> bool:
    """Check password has min 8 chars, uppercase, lowercase, digit, special char."""
    if len(password) < 8:
        return False
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*\-_=+\[\]{};:\'",.<>?/\\|`~]', password))
    return has_upper and has_lower and has_digit and has_special


def validate_username(username: str) -> bool:
    """Validate username: 3-20 chars, alphanumeric and underscore only."""
    return bool(re.match(r'^[a-zA-Z0-9_]{3,20}$', username))


def validate_credit_card_luhn(card_number: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    cleaned = re.sub(r'\s', '', card_number)
    if not re.match(r'^\d{13,19}$', cleaned):
        return False
    digits_list = [int(d) for d in cleaned]
    digits_list.reverse()
    total = 0
    for i, digit in enumerate(digits_list):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def validate_credit_card_format(card_number: str) -> bool:
    """Check if card number is 13-19 digits."""
    cleaned = re.sub(r'\s', '', card_number)
    return bool(re.match(r'^\d{13,19}$', cleaned))


def validate_cvv(cvv: str) -> bool:
    """Validate CVV is 3-4 digits."""
    return bool(re.match(r'^\d{3,4}$', cvv))


def validate_expiry_date(month: int, year: int) -> bool:
    """Check if expiry month (1-12) and year are valid."""
    if not (1 <= month <= 12):
        return False
    current_year = datetime.now().year
    return year >= current_year


def validate_postal_code_us(postal_code: str) -> bool:
    """Validate US postal code (ZIP or ZIP+4 format)."""
    return bool(re.match(r'^\d{5}(-\d{4})?$', postal_code))


def validate_postal_code_canada(postal_code: str) -> bool:
    """Validate Canadian postal code format (A1A 1A1)."""
    pattern = r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$'
    return bool(re.match(pattern, postal_code.upper()))


def validate_postal_code_uk(postal_code: str) -> bool:
    """Validate UK postcode format."""
    pattern = r'^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$'
    return bool(re.match(pattern, postal_code.upper()))


def validate_address_street(street: str) -> bool:
    """Check street address has 5-100 chars and valid characters."""
    if len(street) < 5 or len(street) > 100:
        return False
    return bool(re.match(r'^[a-zA-Z0-9\s\-\.,#]+$', street))


def validate_address_city(city: str) -> bool:
    """Validate city name: 2-50 chars, letters, spaces, hyphens."""
    if len(city) < 2 or len(city) > 50:
        return False
    return bool(re.match(r'^[a-zA-Z\s\-]+$', city))


def validate_address_state(state: str) -> bool:
    """Check state/province code: 2-3 letters."""
    return bool(re.match(r'^[a-zA-Z]{2,3}$', state.upper()))


def validate_product_sku(sku: str) -> bool:
    """Validate product SKU: 3-20 alphanumeric and hyphen."""
    return bool(re.match(r'^[A-Z0-9\-]{3,20}$', sku.upper()))


def validate_product_name(name: str) -> bool:
    """Check product name is 3-200 chars with valid characters."""
    if len(name) < 3 or len(name) > 200:
        return False
    return bool(re.match(r'^[a-zA-Z0-9\s\-\.,\(\)&]+$', name))


def validate_product_price(price: float) -> bool:
    """Verify product price is positive and has max 2 decimal places."""
    if price <= 0:
        return False
    return price == round(price, 2)


def validate_discount_percentage(discount: float) -> bool:
    """Check discount is between 0 and 100."""
    return 0 <= discount <= 100


def validate_quantity(quantity: int) -> bool:
    """Validate quantity is positive integer."""
    return isinstance(quantity, int) and quantity > 0


def validate_order_total(total: float) -> bool:
    """Check order total is non-negative with max 2 decimal places."""
    if total < 0:
        return False
    return total == round(total, 2)


def validate_currency_code(currency: str) -> bool:
    """Validate 3-letter ISO 4217 currency code."""
    return bool(re.match(r'^[A-Z]{3}$', currency))


def validate_country_code(country: str) -> bool:
    """Validate 2-letter ISO 3166 country code."""
    return bool(re.match(r'^[A-Z]{2}$', country))


def validate_iso_date(date_str: str) -> bool:
    """Check if string is valid ISO 8601 date format."""
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_iso_datetime(datetime_str: str) -> bool:
    """Check if string is valid ISO 8601 datetime format."""
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$'
    if not re.match(pattern, datetime_str):
        return False
    try:
        datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def validate_future_date(date_str: str) -> bool:
    """Verify ISO date is in the future."""
    if not validate_iso_date(date_str):
        return False
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    return date > datetime.now().date()


def validate_past_date(date_str: str) -> bool:
    """Verify ISO date is in the past."""
    if not validate_iso_date(date_str):
        return False
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    return date < datetime.now().date()


def validate_url(url: str) -> bool:
    """Check if string is valid URL format."""
    pattern = r'^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+$'
    return bool(re.match(pattern, url))


def validate_url_https(url: str) -> bool:
    """Verify URL uses HTTPS protocol."""
    return url.startswith('https://') and validate_url(url)


def validate_ipv4_address(ip: str) -> bool:
    """Validate IPv4 address format."""
    pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(pattern, ip))


def validate_uuid(uuid_str: str) -> bool:
    """Check if string matches UUID v4 format."""
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_str.lower()))


def validate_order_id(order_id: str) -> bool:
    """Validate order ID: ORD- prefix followed by 8-12 alphanumeric."""
    return bool(re.match(r'^ORD-[A-Z0-9]{8,12}$', order_id.upper()))


def validate_tracking_number(tracking: str) -> bool:
    """Validate tracking number: 15-30 alphanumeric characters."""
    return bool(re.match(r'^[A-Z0-9]{15,30}$', tracking.upper()))


def validate_comment(comment: str) -> bool:
    """Check comment is 1-1000 chars with no control characters."""
    if len(comment) < 1 or len(comment) > 1000:
        return False
    return not bool(re.search(r'[\x00-\x1f\x7f]', comment))


def validate_rating(rating: int) -> bool:
    """Verify rating is integer between 1 and 5."""
    return isinstance(rating, int) and 1 <= rating <= 5


def validate_hex_color(color: str) -> bool:
    """Check if string is valid hex color code."""
    return bool(re.match(r'^#[0-9A-Fa-f]{6}$', color))


def validate_language_code(lang: str) -> bool:
    """Validate 2-letter ISO 639-1 language code."""
    return bool(re.match(r'^[a-z]{2}$', lang.lower()))


def validate_promo_code(code: str) -> bool:
    """Check promo code: 4-20 uppercase alphanumeric."""
    return bool(re.match(r'^[A-Z0-9]{4,20}$', code.upper()))


def validate_coupon_code(code: str) -> bool:
    """Validate coupon code: 3-25 alphanumeric with optional hyphens."""
    return bool(re.match(r'^[A-Z0-9\-]{3,25}$', code.upper()))


def validate_shop_name(name: str) -> bool:
    """Check shop name is 2-100 chars with valid characters."""
    if len(name) < 2 or len(name) > 100:
        return False
    return bool(re.match(r'^[a-zA-Z0-9\s\-\.&\']+$', name))


def validate_category_name(name: str) -> bool:
    """Validate category name: 2-50 chars, letters, spaces, hyphens."""
    if len(name) < 2 or len(name) > 50:
        return False
    return bool(re.match(r'^[a-zA-Z\s\-]+$', name))


def validate_tag(tag: str) -> bool:
    """Check tag is 2-30 chars, lowercase alphanumeric and hyphens."""
    return bool(re.match(r'^[a-z0-9\-]{2,30}$', tag))


def validate_payment_method(method: str) -> bool:
    """Verify payment method is one of allowed types."""
    allowed = ['credit_card', 'debit_card', 'paypal', 'bank_transfer', 'apple_pay', 'google_pay']
    return method.lower() in allowed


def validate_shipping_method(method: str) -> bool:
    """Check shipping method is one of allowed types."""
    allowed = ['standard', 'express', 'overnight', 'pickup', 'international']
    return method.lower() in allowed


def validate_order_status(status: str) -> bool:
    """Verify order status is valid."""
    allowed = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled', 'returned']
    return status.lower() in allowed


def validate_product_status(status: str) -> bool:
    """Check product status is valid."""
    allowed = ['active', 'inactive', 'discontinued', 'out_of_stock']
    return status.lower() in allowed


def validate_not_empty(value: str) -> bool:
    """Ensure string is not empty or whitespace."""
    return bool(value.strip())


def validate_alphanumeric(value: str) -> bool:
    """Check if string contains only alphanumeric characters."""
    return bool(re.match(r'^[a-zA-Z0-9]+$', value))


def validate_numeric(value: str) -> bool:
    """Verify string contains only digits."""
    return bool(re.match(r'^\d+$', value))


def validate_name_first(name: str) -> bool:
    """Validate first name: 2-50 chars, letters, spaces, hyphens."""
    if len(name) < 2 or len(name) > 50:
        return False
    return bool(re.match(r'^[a-zA-Z\s\-\']+$', name))


def validate_name_last(name: str) -> bool:
    """Validate last name: 2-50 chars, letters, spaces, hyphens."""
    if len(name) < 2 or len(name) > 50:
        return False
    return bool(re.match(r'^[a-zA-Z\s\-\']+$', name))


def validate_company_name(name: str) -> bool:
    """Check company name is 2-100 chars with valid characters."""
    if len(name) < 2 or len(name) > 100:
        return False
    return bool(re.match(r'^[a-zA-Z0-9\s\-\.,&\'()\[\]]+$', name))


def validate_tax_id(tax_id: str) -> bool:
    """Validate tax ID format: alphanumeric with hyphens, 5-20 chars."""
    return bool(re.match(r'^[A-Z0-9\-]{5,20}$', tax_id.upper()))


def validate_weight_kg(weight: float) -> bool:
    """Check weight is positive number with max 2 decimals."""
    if weight <= 0:
        return False
    return weight == round(weight, 2)


def validate_dimension_cm(dimension: float) -> bool:
    """Verify dimension is positive with max 2 decimal places."""
    if dimension <= 0:
        return False
    return dimension == round(dimension, 2)


def validate_stock_quantity(stock: int) -> bool:
    """Check stock quantity is non-negative integer."""
    return isinstance(stock, int) and stock >= 0


def validate_return_window_days(days: int) -> bool:
    """Verify return window is 1-365 days."""
    return isinstance(days, int) and 1 <= days <= 365


def validate_json_key(key: str) -> bool:
    """Check JSON key is 1-100 alphanumeric with underscores."""
    return bool(re.match(r'^[a-zA-Z0-9_]{1,100}$', key))


def validate_slug(slug: str) -> bool:
    """Validate URL slug: 3-100 lowercase alphanumeric and hyphens."""
    return bool(re.match(r'^[a-z0-9\-]{3,100}$', slug))


def calculate_password_hash(password: str) -> str:
    """Generate SHA256 hash of password for validation storage."""
    return hashlib.sha256(password.encode()).hexdigest()


def validate_password_match(password: str, hash_value: str) -> bool:
    """Verify password matches stored hash."""
    return calculate_password_hash(password) == hash_value
