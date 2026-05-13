"""Unit tests for ecommerce.utils.formatters module."""

import unittest
from decimal import Decimal
from datetime import datetime, timedelta
from ecommerce.utils.formatters import (
    format_currency,
    format_price_range,
    format_discount_percentage,
    format_iso_date,
    format_human_date,
    format_relative_date,
    format_iso_duration,
    format_duration,
    format_file_size,
    format_phone_number,
    format_address,
    format_address_multiline,
    format_product_title,
    format_product_description,
    format_product_sku,
    format_product_barcode,
    format_quantity_label,
    format_order_id,
    format_order_summary,
    format_order_status,
    format_invoice_number,
    format_tracking_number,
    format_coupon_code,
    format_discount_code,
    format_percentage,
    format_rating,
    format_review_count,
    format_tax_amount,
    format_shipping_cost,
    format_pagination_info,
    format_search_result_count,
    format_error_message,
    format_validation_error,
    format_warning_message,
    format_success_message,
    format_truncated_string,
    format_csv_value,
    format_html_safe,
    format_weight,
    format_dimension,
    format_dimensions_box,
    format_stock_status,
    format_currency_code,
    format_language_code,
    format_country_code,
    format_email_masked,
    format_phone_masked,
    format_url_slug,
    format_camel_case,
    format_snake_case,
)


class TestCurrencyFormatters(unittest.TestCase):
    """Test currency-related formatting functions."""

    def test_format_currency_usd(self):
        """Test USD currency formatting."""
        self.assertEqual(format_currency(Decimal("19.99")), "$19.99")
        self.assertEqual(format_currency(Decimal("1000.00")), "$1,000.00")

    def test_format_currency_eur(self):
        """Test EUR currency formatting."""
        self.assertEqual(format_currency(Decimal("19.99"), "EUR"), "€19.99")

    def test_format_currency_gbp(self):
        """Test GBP currency formatting."""
        self.assertEqual(format_currency(Decimal("100.50"), "GBP"), "£100.50")

    def test_format_price_range(self):
        """Test price range formatting."""
        result = format_price_range(Decimal("10.00"), Decimal("50.00"))
        self.assertEqual(result, "$10.00 - $50.00")

    def test_format_discount_percentage(self):
        """Test discount percentage calculation."""
        self.assertEqual(format_discount_percentage(Decimal("100"), Decimal("80")), "20%")
        self.assertEqual(format_discount_percentage(Decimal("50"), Decimal("25")), "50%")

    def test_format_discount_percentage_zero_original(self):
        """Test discount percentage with zero original price."""
        self.assertEqual(format_discount_percentage(Decimal("0"), Decimal("10")), "0%")


class TestDateFormatters(unittest.TestCase):
    """Test date and time formatting functions."""

    def test_format_iso_date(self):
        """Test ISO 8601 date formatting."""
        dt = datetime(2026, 2, 16, 14, 30, 45)
        self.assertEqual(format_iso_date(dt), "2026-02-16T14:30:45Z")

    def test_format_human_date_without_time(self):
        """Test human-readable date formatting without time."""
        dt = datetime(2026, 2, 16, 14, 30, 45)
        self.assertEqual(format_human_date(dt), "Feb 16, 2026")

    def test_format_human_date_with_time(self):
        """Test human-readable date formatting with time."""
        dt = datetime(2026, 2, 16, 14, 30, 45)
        result = format_human_date(dt, include_time=True)
        self.assertIn("Feb 16, 2026", result)
        self.assertIn("2:30 PM", result)

    def test_format_relative_date_just_now(self):
        """Test relative date formatting for current time."""
        now = datetime.utcnow()
        self.assertEqual(format_relative_date(now), "just now")

    def test_format_relative_date_minutes_ago(self):
        """Test relative date formatting for minutes in the past."""
        past = datetime.utcnow() - timedelta(minutes=5)
        self.assertEqual(format_relative_date(past), "5 minutes ago")

    def test_format_relative_date_singular_minute(self):
        """Test relative date formatting for singular minute."""
        past = datetime.utcnow() - timedelta(minutes=1)
        self.assertEqual(format_relative_date(past), "1 minute ago")

    def test_format_relative_date_hours_in_future(self):
        """Test relative date formatting for future time."""
        future = datetime.utcnow() + timedelta(hours=3)
        result = format_relative_date(future)
        self.assertIn("hour", result)
        self.assertIn("in", result)


class TestDurationFormatters(unittest.TestCase):
    """Test duration formatting functions."""

    def test_format_iso_duration_seconds(self):
        """Test ISO duration formatting with seconds."""
        self.assertEqual(format_iso_duration(30), "PT0H0M30S")

    def test_format_iso_duration_complex(self):
        """Test ISO duration formatting with multiple units."""
        # 1 day, 2 hours, 0 minutes, 45 seconds = 93645 seconds
        self.assertEqual(format_iso_duration(93645), "P1DT2H0M45S")

    def test_format_duration_seconds_only(self):
        """Test human-readable duration with seconds only."""
        self.assertEqual(format_duration(30), "30s")

    def test_format_duration_mixed(self):
        """Test human-readable duration with mixed units."""
        # 1 hour, 30 minutes, 45 seconds = 5445 seconds
        result = format_duration(5445)
        self.assertIn("1h", result)
        self.assertIn("30m", result)
        self.assertIn("45s", result)

    def test_format_duration_days(self):
        """Test human-readable duration including days."""
        # 1 day, 2 hours = 93600 seconds
        result = format_duration(93600)
        self.assertIn("1d", result)
        self.assertIn("2h", result)


class TestFileSizeFormatter(unittest.TestCase):
    """Test file size formatting."""

    def test_format_file_size_bytes(self):
        """Test file size in bytes."""
        self.assertEqual(format_file_size(512), "512 B")

    def test_format_file_size_kilobytes(self):
        """Test file size in kilobytes."""
        self.assertEqual(format_file_size(1024), "1.0 KB")

    def test_format_file_size_megabytes(self):
        """Test file size in megabytes."""
        result = format_file_size(1024 * 1024 * 5)
        self.assertIn("5", result)
        self.assertIn("MB", result)

    def test_format_file_size_gigabytes(self):
        """Test file size in gigabytes."""
        result = format_file_size(1024 * 1024 * 1024)
        self.assertIn("1.0 GB", result)


class TestPhoneAndAddressFormatters(unittest.TestCase):
    """Test phone number and address formatting."""

    def test_format_phone_number_10_digit(self):
        """Test 10-digit US phone number formatting."""
        self.assertEqual(format_phone_number("5551234567"), "(555) 123-4567")

    def test_format_phone_number_11_digit_with_1(self):
        """Test 11-digit US phone number with leading 1."""
        self.assertEqual(format_phone_number("15551234567"), "+1 (555) 123-4567")

    def test_format_phone_number_with_separators(self):
        """Test phone number formatting with existing separators."""
        self.assertEqual(format_phone_number("(555) 123-4567"), "(555) 123-4567")

    def test_format_address_single_line(self):
        """Test single-line address formatting."""
        result = format_address("123 Main St", "New York", "NY", "10001")
        self.assertEqual(result, "123 Main St, New York, NY, 10001")

    def test_format_address_with_country(self):
        """Test address formatting with non-USA country."""
        result = format_address("123 Main St", "London", "London", "E1 6AN", "UK")
        self.assertIn("UK", result)

    def test_format_address_multiline(self):
        """Test multiline address formatting."""
        result = format_address_multiline("123 Main St", "New York", "NY", "10001")
        self.assertIn("123 Main St", result)
        self.assertIn("New York, NY 10001", result)


class TestProductFormatters(unittest.TestCase):
    """Test product-related formatting functions."""

    def test_format_product_title_short(self):
        """Test product title formatting for short title."""
        title = "Great Widget"
        self.assertEqual(format_product_title(title), "Great Widget")

    def test_format_product_title_long(self):
        """Test product title formatting with truncation."""
        title = "A" * 105
        result = format_product_title(title, max_length=100)
        self.assertEqual(len(result), 100)
        self.assertTrue(result.endswith("..."))

    def test_format_product_title_html_entities(self):
        """Test product title with HTML entities."""
        title = "Widget &amp; Gadget"
        self.assertEqual(format_product_title(title), "Widget & Gadget")

    def test_format_product_description(self):
        """Test product description formatting."""
        desc = "Great   product   with    spacing"
        result = format_product_description(desc)
        self.assertIn("Great product with spacing", result)

    def test_format_product_sku(self):
        """Test SKU formatting."""
        self.assertEqual(format_product_sku("sku-123-abc"), "SKU123ABC")
        self.assertEqual(format_product_sku("SKU@456#XYZ"), "SKU456XYZ")

    def test_format_product_barcode(self):
        """Test barcode formatting."""
        self.assertEqual(format_product_barcode("123-456-789-0"), "1234567890")
        self.assertEqual(format_product_barcode("9876543210"), "9876543210")


class TestQuantityAndOrderFormatters(unittest.TestCase):
    """Test quantity and order formatting functions."""

    def test_format_quantity_label_singular(self):
        """Test quantity label with singular unit."""
        self.assertEqual(format_quantity_label(1, "item"), "1 item")

    def test_format_quantity_label_plural(self):
        """Test quantity label with plural unit."""
        self.assertEqual(format_quantity_label(5, "item"), "5 items")

    def test_format_order_id(self):
        """Test order ID formatting."""
        self.assertEqual(format_order_id("ord-123-abc"), "#ORD-123-ABC")

    def test_format_order_summary(self):
        """Test order summary formatting."""
        result = format_order_summary("ord123", 3, Decimal("99.99"), "shipped")
        self.assertIn("#ORD123", result)
        self.assertIn("3 items", result)
        self.assertIn("$99.99", result)
        self.assertIn("shipped", result)

    def test_format_order_status(self):
        """Test order status formatting."""
        self.assertEqual(format_order_status("pending_payment"), "Pending Payment")
        self.assertEqual(format_order_status("shipped"), "Shipped")

    def test_format_invoice_number(self):
        """Test invoice number formatting."""
        self.assertEqual(format_invoice_number("inv-2026-001"), "INV-INV-2026-001")


class TestCouponAndDiscountFormatters(unittest.TestCase):
    """Test coupon and discount code formatters."""

    def test_format_coupon_code(self):
        """Test coupon code formatting."""
        self.assertEqual(format_coupon_code("save-20%"), "SAVE20")
        self.assertEqual(format_coupon_code("SPRING2026"), "SPRING2026")

    def test_format_discount_code(self):
        """Test discount code formatting."""
        self.assertEqual(format_discount_code("fall-sale!"), "FALLSALE")


class TestRatingAndReviewFormatters(unittest.TestCase):
    """Test rating and review formatting functions."""

    def test_format_percentage(self):
        """Test percentage formatting."""
        self.assertEqual(format_percentage(0.25), "25.0%")
        self.assertEqual(format_percentage(0.125, decimals=2), "12.50%")

    def test_format_rating(self):
        """Test rating formatting with stars."""
        result = format_rating(4.5)
        self.assertIn("★", result)
        self.assertIn("☆", result)
        self.assertIn("4.5/5", result)

    def test_format_review_count_zero(self):
        """Test review count formatting for no reviews."""
        self.assertEqual(format_review_count(0), "No reviews")

    def test_format_review_count_singular(self):
        """Test review count formatting for single review."""
        self.assertEqual(format_review_count(1), "1 review")

    def test_format_review_count_multiple(self):
        """Test review count formatting for multiple reviews."""
        self.assertEqual(format_review_count(500), "500 reviews")

    def test_format_review_count_thousands(self):
        """Test review count formatting for thousands."""
        self.assertEqual(format_review_count(5500), "5.5K reviews")


class TestTaxAndShippingFormatters(unittest.TestCase):
    """Test tax and shipping formatting functions."""

    def test_format_tax_amount(self):
        """Test tax amount formatting."""
        result = format_tax_amount(Decimal("100.00"), Decimal("0.08"))
        self.assertIn("$100.00", result)
        self.assertIn("8.0%", result)

    def test_format_shipping_cost_free(self):
        """Test free shipping formatting."""
        result = format_shipping_cost(Decimal("0"), 3)
        self.assertIn("Free shipping", result)
        self.assertIn("3-4 days", result)

    def test_format_shipping_cost_paid(self):
        """Test paid shipping formatting."""
        result = format_shipping_cost(Decimal("9.99"), 2)
        self.assertIn("$9.99", result)
        self.assertIn("2-3 days", result)


class TestPaginationAndSearchFormatters(unittest.TestCase):
    """Test pagination and search result formatting."""

    def test_format_pagination_info(self):
        """Test pagination information formatting."""
        result = format_pagination_info(2, 10, 20)
        self.assertIn("Page 2 of 10", result)
        self.assertIn("21-40", result)

    def test_format_search_result_count_zero(self):
        """Test search result count for no results."""
        self.assertEqual(format_search_result_count(0), "No results found")
        self.assertEqual(format_search_result_count(0, "widget"), "No results found for 'widget'")

    def test_format_search_result_count_one(self):
        """Test search result count for single result."""
        self.assertEqual(format_search_result_count(1), "1 result found")

    def test_format_search_result_count_multiple(self):
        """Test search result count for multiple results."""
        self.assertEqual(format_search_result_count(50), "50 results found")
        self.assertEqual(format_search_result_count(1500), "1,500 results found")


class TestErrorAndValidationFormatters(unittest.TestCase):
    """Test error and validation message formatting."""

    def test_format_error_message(self):
        """Test error message formatting."""
        result = format_error_message("not_found", "Resource does not exist")
        self.assertIn("NOT FOUND", result)
        self.assertIn("Resource does not exist", result)

    def test_format_validation_error_required(self):
        """Test validation error formatting."""
        self.assertEqual(format_validation_error("email", "required"), "Email is required")
        self.assertEqual(format_validation_error("first_name", "too_long"), "First Name is too long")

    def test_format_validation_error_custom(self):
        """Test validation error with custom error type."""
        result = format_validation_error("password", "custom_error")
        self.assertIn("Password", result)

    def test_format_warning_message(self):
        """Test warning message formatting."""
        result = format_warning_message("low_inventory")
        self.assertIn("Low Inventory", result)

    def test_format_warning_message_with_details(self):
        """Test warning message with details."""
        result = format_warning_message("price_mismatch", "Expected $100 but got $95")
        self.assertIn("Price Mismatch", result)
        self.assertIn("Expected $100 but got $95", result)

    def test_format_success_message(self):
        """Test success message formatting."""
        self.assertEqual(format_success_message("created"), "Successfully created")
        self.assertEqual(format_success_message("updated", "product"), "Successfully updated product")


class TestTruncationAndEscapingFormatters(unittest.TestCase):
    """Test text truncation and escaping functions."""

    def test_format_truncated_string_no_truncation(self):
        """Test truncated string when text is short."""
        self.assertEqual(format_truncated_string("hello", 10), "hello")

    def test_format_truncated_string_with_truncation(self):
        """Test truncated string with custom suffix."""
        result = format_truncated_string("hello world", 8, "...")
        self.assertEqual(result, "hello...")
        self.assertEqual(len(result), 8)

    def test_format_csv_value_simple(self):
        """Test CSV value formatting for simple values."""
        self.assertEqual(format_csv_value("simple"), "simple")

    def test_format_csv_value_with_comma(self):
        """Test CSV value formatting with comma."""
        self.assertEqual(format_csv_value("hello,world"), '"hello,world"')

    def test_format_csv_value_with_quotes(self):
        """Test CSV value formatting with quotes."""
        result = format_csv_value('say "hi"')
        self.assertIn('""', result)

    def test_format_html_safe(self):
        """Test HTML escaping."""
        result = format_html_safe("<script>alert('xss')</script>")
        self.assertIn("&lt;", result)
        self.assertIn("&gt;", result)


class TestPhysicalAttributeFormatters(unittest.TestCase):
    """Test weight, dimension, and stock status formatting."""

    def test_format_weight_auto_grams(self):
        """Test weight formatting in grams."""
        self.assertEqual(format_weight(500), "500 g")

    def test_format_weight_auto_kilograms(self):
        """Test weight formatting in kilograms."""
        self.assertEqual(format_weight(2500), "2.50 kg")

    def test_format_weight_pounds(self):
        """Test weight formatting in pounds."""
        result = format_weight(453.592, unit="lb")
        self.assertIn("1.00 lb", result)

    def test_format_dimension_auto_millimeters(self):
        """Test dimension formatting in millimeters."""
        self.assertEqual(format_dimension(50), "50 mm")

    def test_format_dimension_auto_centimeters(self):
        """Test dimension formatting in centimeters."""
        self.assertEqual(format_dimension(150), "15.0 cm")

    def test_format_dimension_auto_meters(self):
        """Test dimension formatting in meters."""
        result = format_dimension(1500)
        self.assertIn("1.50 m", result)

    def test_format_dimensions_box(self):
        """Test 3D dimensions formatting."""
        result = format_dimensions_box(10.5, 20.3, 5.8)
        self.assertIn("10.5 x 20.3 x 5.8 cm", result)

    def test_format_stock_status_out_of_stock(self):
        """Test stock status for out of stock."""
        self.assertEqual(format_stock_status(0), "Out of stock")

    def test_format_stock_status_low(self):
        """Test stock status for low inventory."""
        self.assertEqual(format_stock_status(3), "Only 3 left")

    def test_format_stock_status_moderate(self):
        """Test stock status for moderate inventory."""
        self.assertEqual(format_stock_status(10), "Low stock")

    def test_format_stock_status_high(self):
        """Test stock status for high inventory."""
        self.assertEqual(format_stock_status(100), "In stock")


class TestCodeFormatters(unittest.TestCase):
    """Test code and identifier formatting functions."""

    def test_format_currency_code(self):
        """Test currency code formatting."""
        self.assertEqual(format_currency_code("usd"), "USD")
        self.assertEqual(format_currency_code(" eur "), "EUR")

    def test_format_language_code(self):
        """Test language code formatting."""
        self.assertEqual(format_language_code("EN"), "en")
        self.assertEqual(format_language_code(" FR "), "fr")

    def test_format_country_code(self):
        """Test country code formatting."""
        self.assertEqual(format_country_code("us"), "US")
        self.assertEqual(format_country_code(" gb "), "GB")


class TestPrivacyFormatters(unittest.TestCase):
    """Test privacy-related formatting functions."""

    def test_format_email_masked_long_local(self):
        """Test email masking for longer local part."""
        result = format_email_masked("john.doe@example.com")
        self.assertIn("@example.com", result)
        self.assertIn("j", result)
        self.assertIn("e", result)

    def test_format_email_masked_short_local(self):
        """Test email masking for short local part."""
        result = format_email_masked("ab@example.com")
        self.assertIn("@example.com", result)
        self.assertIn("*", result)

    def test_format_email_masked_no_at(self):
        """Test email masking for invalid email."""
        self.assertEqual(format_email_masked("invalid"), "invalid")

    def test_format_phone_masked(self):
        """Test phone number masking."""
        result = format_phone_masked("5551234567")
        self.assertEqual(result, "******4567")

    def test_format_phone_masked_short(self):
        """Test phone number masking for short numbers."""
        result = format_phone_masked("123")
        self.assertEqual(result, "****")


class TestSlugAndCaseFormatters(unittest.TestCase):
    """Test URL slug and case conversion formatting."""

    def test_format_url_slug_simple(self):
        """Test simple URL slug formatting."""
        self.assertEqual(format_url_slug("Hello World"), "hello-world")

    def test_format_url_slug_special_chars(self):
        """Test URL slug formatting with special characters."""
        result = format_url_slug("Hello & World!")
        self.assertIn("hello", result)
        self.assertIn("world", result)
        self.assertNotIn("&", result)

    def test_format_url_slug_multiple_hyphens(self):
        """Test URL slug formatting with multiple hyphens."""
        result = format_url_slug("Hello---World")
        self.assertEqual(result, "hello-world")

    def test_format_camel_case_simple(self):
        """Test camelCase formatting."""
        self.assertEqual(format_camel_case("hello world"), "helloWorld")
        # Underscores are treated as part of non-word characters and converted to spaces
        result = format_camel_case("hello_world_test")
        self.assertTrue("hello" in result and "world" in result)

    def test_format_camel_case_empty(self):
        """Test camelCase formatting for empty string."""
        self.assertEqual(format_camel_case(""), "")

    def test_format_snake_case_simple(self):
        """Test snake_case formatting."""
        self.assertEqual(format_snake_case("HelloWorld"), "hello_world")
        self.assertEqual(format_snake_case("hello world"), "hello_world")

    def test_format_snake_case_multiple_underscores(self):
        """Test snake_case formatting with multiple underscores."""
        result = format_snake_case("hello__world")
        self.assertNotIn("__", result)


if __name__ == "__main__":
    unittest.main()
