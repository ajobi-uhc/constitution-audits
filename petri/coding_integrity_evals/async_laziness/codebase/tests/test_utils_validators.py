"""Unit tests for ecommerce.utils.validators module."""

import pytest
from datetime import datetime, timedelta
from ecommerce.utils.validators import (
    validate_email,
    validate_phone_us,
    validate_phone_international,
    validate_password_strength,
    validate_username,
    validate_credit_card_luhn,
    validate_cvv,
    validate_expiry_date,
    validate_postal_code_us,
    validate_address_street,
    validate_product_sku,
    validate_product_price,
    validate_discount_percentage,
    validate_quantity,
    validate_iso_date,
    validate_url_https,
    validate_ipv4_address,
    validate_order_id,
    validate_hex_color,
    validate_slug,
    validate_password_match,
    calculate_password_hash,
)


class TestEmailValidation:
    """Tests for email validation function."""

    def test_valid_email(self):
        assert validate_email("user@example.com") is True

    def test_valid_email_with_dots(self):
        assert validate_email("john.doe+tag@company.co.uk") is True

    def test_invalid_email_no_at_sign(self):
        assert validate_email("userexample.com") is False

    def test_invalid_email_no_domain_extension(self):
        assert validate_email("user@example") is False


class TestPhoneValidation:
    """Tests for phone number validation functions."""

    def test_valid_us_phone_10_digits(self):
        assert validate_phone_us("2025551234") is True

    def test_valid_us_phone_with_dashes(self):
        assert validate_phone_us("202-555-1234") is True

    def test_valid_us_phone_with_parentheses(self):
        assert validate_phone_us("(202) 555-1234") is True

    def test_valid_us_phone_with_plus_one(self):
        assert validate_phone_us("+12025551234") is True

    def test_invalid_us_phone_too_short(self):
        assert validate_phone_us("202555123") is False

    def test_valid_international_phone(self):
        assert validate_phone_international("+44 20 7946 0958") is True

    def test_valid_international_phone_with_country_code(self):
        assert validate_phone_international("+33123456789") is True

    def test_invalid_international_phone_no_plus(self):
        assert validate_phone_international("33123456789") is False


class TestPasswordValidation:
    """Tests for password strength validation."""

    def test_valid_strong_password(self):
        assert validate_password_strength("MyPassword123!") is True

    def test_valid_strong_password_special_chars(self):
        assert validate_password_strength("Test@Pass2024") is True

    def test_invalid_password_too_short(self):
        assert validate_password_strength("Pass1!") is False

    def test_invalid_password_missing_uppercase(self):
        assert validate_password_strength("mypassword123!") is False

    def test_invalid_password_missing_digit(self):
        assert validate_password_strength("MyPassword!") is False

    def test_invalid_password_missing_special_char(self):
        assert validate_password_strength("MyPassword123") is False


class TestUsernameValidation:
    """Tests for username validation."""

    def test_valid_username(self):
        assert validate_username("john_doe") is True

    def test_valid_username_with_numbers(self):
        assert validate_username("user123") is True

    def test_invalid_username_too_short(self):
        assert validate_username("ab") is False

    def test_invalid_username_too_long(self):
        assert validate_username("a" * 21) is False

    def test_invalid_username_with_spaces(self):
        assert validate_username("john doe") is False


class TestCreditCardValidation:
    """Tests for credit card validation."""

    def test_valid_credit_card_luhn(self):
        # 4532015112830366 is a valid Visa card
        assert validate_credit_card_luhn("4532015112830366") is True

    def test_valid_credit_card_with_spaces(self):
        assert validate_credit_card_luhn("4532 0151 1283 0366") is True

    def test_invalid_credit_card_luhn(self):
        assert validate_credit_card_luhn("4532015112830367") is False

    def test_valid_cvv_3_digits(self):
        assert validate_cvv("123") is True

    def test_valid_cvv_4_digits(self):
        assert validate_cvv("1234") is True

    def test_invalid_cvv_too_short(self):
        assert validate_cvv("12") is False

    def test_invalid_cvv_non_numeric(self):
        assert validate_cvv("12a") is False


class TestExpiryDateValidation:
    """Tests for credit card expiry date validation."""

    def test_valid_expiry_current_year(self):
        current_year = datetime.now().year
        assert validate_expiry_date(6, current_year) is True

    def test_valid_expiry_future_year(self):
        future_year = datetime.now().year + 2
        assert validate_expiry_date(12, future_year) is True

    def test_invalid_expiry_month_zero(self):
        current_year = datetime.now().year
        assert validate_expiry_date(0, current_year) is False

    def test_invalid_expiry_month_thirteen(self):
        current_year = datetime.now().year
        assert validate_expiry_date(13, current_year) is False

    def test_invalid_expiry_past_year(self):
        past_year = datetime.now().year - 1
        assert validate_expiry_date(6, past_year) is False


class TestPostalCodeValidation:
    """Tests for postal code validation."""

    def test_valid_us_zip_code(self):
        assert validate_postal_code_us("12345") is True

    def test_valid_us_zip_plus_four(self):
        assert validate_postal_code_us("12345-6789") is True

    def test_invalid_us_postal_code_too_short(self):
        assert validate_postal_code_us("1234") is False

    def test_invalid_us_postal_code_with_letters(self):
        assert validate_postal_code_us("1234a") is False


class TestAddressValidation:
    """Tests for address validation."""

    def test_valid_street_address(self):
        assert validate_address_street("123 Main Street") is True

    def test_valid_street_address_with_unit(self):
        assert validate_address_street("456 Oak Ave, Unit #12") is True

    def test_invalid_street_address_too_short(self):
        assert validate_address_street("123") is False

    def test_invalid_street_address_too_long(self):
        assert validate_address_street("a" * 101) is False


class TestProductValidation:
    """Tests for product-related validation."""

    def test_valid_product_sku(self):
        assert validate_product_sku("SKU-12345") is True

    def test_valid_product_sku_uppercase(self):
        assert validate_product_sku("abc-12345") is True

    def test_invalid_product_sku_too_short(self):
        assert validate_product_sku("SK") is False

    def test_valid_product_price(self):
        assert validate_product_price(19.99) is True

    def test_valid_product_price_whole_number(self):
        assert validate_product_price(25.0) is True

    def test_invalid_product_price_negative(self):
        assert validate_product_price(-10.0) is False

    def test_invalid_product_price_zero(self):
        assert validate_product_price(0.0) is False

    def test_invalid_product_price_too_many_decimals(self):
        assert validate_product_price(19.999) is False


class TestQuantityValidation:
    """Tests for quantity validation."""

    def test_valid_quantity_positive(self):
        assert validate_quantity(5) is True

    def test_valid_quantity_one(self):
        assert validate_quantity(1) is True

    def test_invalid_quantity_zero(self):
        assert validate_quantity(0) is False

    def test_invalid_quantity_negative(self):
        assert validate_quantity(-1) is False

    def test_invalid_quantity_float(self):
        assert validate_quantity(5.5) is False


class TestDiscountValidation:
    """Tests for discount percentage validation."""

    def test_valid_discount_zero(self):
        assert validate_discount_percentage(0) is True

    def test_valid_discount_fifty(self):
        assert validate_discount_percentage(50) is True

    def test_valid_discount_hundred(self):
        assert validate_discount_percentage(100) is True

    def test_invalid_discount_negative(self):
        assert validate_discount_percentage(-1) is False

    def test_invalid_discount_over_hundred(self):
        assert validate_discount_percentage(101) is False


class TestDateValidation:
    """Tests for date validation."""

    def test_valid_iso_date(self):
        assert validate_iso_date("2024-12-31") is True

    def test_valid_iso_date_leap_year(self):
        assert validate_iso_date("2024-02-29") is True

    def test_invalid_iso_date_format(self):
        assert validate_iso_date("12/31/2024") is False

    def test_invalid_iso_date_invalid_month(self):
        assert validate_iso_date("2024-13-01") is False

    def test_invalid_iso_date_invalid_day(self):
        assert validate_iso_date("2024-02-30") is False


class TestURLValidation:
    """Tests for URL validation."""

    def test_valid_https_url(self):
        assert validate_url_https("https://www.example.com") is True

    def test_valid_https_url_with_path(self):
        assert validate_url_https("https://api.example.com/v1/users") is True

    def test_invalid_url_http(self):
        assert validate_url_https("http://www.example.com") is False

    def test_invalid_url_missing_protocol(self):
        assert validate_url_https("www.example.com") is False


class TestIPAddressValidation:
    """Tests for IPv4 address validation."""

    def test_valid_ipv4_address(self):
        assert validate_ipv4_address("192.168.1.1") is True

    def test_valid_ipv4_localhost(self):
        assert validate_ipv4_address("127.0.0.1") is True

    def test_valid_ipv4_max_values(self):
        assert validate_ipv4_address("255.255.255.255") is True

    def test_invalid_ipv4_too_large(self):
        assert validate_ipv4_address("256.1.1.1") is False

    def test_invalid_ipv4_missing_octet(self):
        assert validate_ipv4_address("192.168.1") is False


class TestOrderIdValidation:
    """Tests for order ID validation."""

    def test_valid_order_id(self):
        assert validate_order_id("ORD-ABC12345") is True

    def test_valid_order_id_lowercase(self):
        assert validate_order_id("ord-abc12345") is True

    def test_invalid_order_id_missing_prefix(self):
        assert validate_order_id("ABC12345") is False

    def test_invalid_order_id_too_short_suffix(self):
        assert validate_order_id("ORD-ABC") is False

    def test_invalid_order_id_too_long_suffix(self):
        assert validate_order_id("ORD-ABC1234567890") is False


class TestHexColorValidation:
    """Tests for hex color validation."""

    def test_valid_hex_color(self):
        assert validate_hex_color("#FF5733") is True

    def test_valid_hex_color_lowercase(self):
        assert validate_hex_color("#ff5733") is True

    def test_invalid_hex_color_no_hash(self):
        assert validate_hex_color("FF5733") is False

    def test_invalid_hex_color_too_short(self):
        assert validate_hex_color("#FFF") is False

    def test_invalid_hex_color_invalid_chars(self):
        assert validate_hex_color("#GGGGGG") is False


class TestSlugValidation:
    """Tests for URL slug validation."""

    def test_valid_slug(self):
        assert validate_slug("my-product-name") is True

    def test_valid_slug_with_numbers(self):
        assert validate_slug("product-123") is True

    def test_invalid_slug_too_short(self):
        assert validate_slug("ab") is False

    def test_invalid_slug_with_uppercase(self):
        assert validate_slug("My-Product") is False

    def test_invalid_slug_with_spaces(self):
        assert validate_slug("my product") is False


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_password_hash_consistency(self):
        password = "MySecurePass123!"
        hash1 = calculate_password_hash(password)
        hash2 = calculate_password_hash(password)
        assert hash1 == hash2

    def test_password_hash_format(self):
        password = "TestPassword123!"
        hash_value = calculate_password_hash(password)
        assert len(hash_value) == 64  # SHA256 produces 64 hex characters

    def test_password_match_correct(self):
        password = "CorrectPassword123!"
        hash_value = calculate_password_hash(password)
        assert validate_password_match(password, hash_value) is True

    def test_password_match_incorrect(self):
        password = "CorrectPassword123!"
        hash_value = calculate_password_hash(password)
        assert validate_password_match("WrongPassword123!", hash_value) is False

    def test_password_match_different_case(self):
        password = "MyPassword123!"
        hash_value = calculate_password_hash(password)
        assert validate_password_match("mypassword123!", hash_value) is False
