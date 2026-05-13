"""Data formatting utilities for the e-commerce backend."""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from textwrap import wrap
import html


def format_currency(amount: Decimal, currency_code: str = "USD") -> str:
    """Format decimal amount as currency string with locale-aware symbols."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    symbol = symbols.get(currency_code, currency_code)
    return f"{symbol}{amount:,.2f}"


def format_price_range(min_price: Decimal, max_price: Decimal) -> str:
    """Format min and max prices as readable range."""
    return f"{format_currency(min_price)} - {format_currency(max_price)}"


def format_discount_percentage(original: Decimal, discounted: Decimal) -> str:
    """Calculate and format percentage discount between two prices."""
    if original == 0:
        return "0%"
    percent = ((original - discounted) / original) * 100
    return f"{percent:.0f}%"


def format_iso_date(date_obj: datetime) -> str:
    """Convert datetime object to ISO 8601 format string."""
    return date_obj.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_human_date(date_obj: datetime, include_time: bool = False) -> str:
    """Format datetime as human-readable string (e.g., 'Jan 15, 2026')."""
    fmt = "%b %d, %Y" if not include_time else "%b %d, %Y at %I:%M %p"
    return date_obj.strftime(fmt)


def format_relative_date(date_obj: datetime) -> str:
    """Format datetime relative to now (e.g., '2 days ago', 'in 3 hours')."""
    now = datetime.utcnow()
    delta = date_obj - now
    seconds = delta.total_seconds()

    if abs(seconds) < 60:
        return "just now"
    minutes = int(abs(seconds) / 60)
    if minutes < 60:
        suffix = "ago" if seconds < 0 else "in"
        return f"{minutes} minute{'s' if minutes != 1 else ''} {suffix}"

    hours = minutes // 60
    if hours < 24:
        suffix = "ago" if seconds < 0 else "in"
        return f"{hours} hour{'s' if hours != 1 else ''} {suffix}"

    days = hours // 24
    if days < 30:
        suffix = "ago" if seconds < 0 else "in"
        return f"{days} day{'s' if days != 1 else ''} {suffix}"

    return "long ago" if seconds < 0 else "far in future"


def format_iso_duration(seconds: int) -> str:
    """Format seconds as ISO 8601 duration (e.g., 'PT5H30M')."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}D")
    return f"P{''.join(parts)}T{hours}H{minutes}M{secs}S"


def format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration (e.g., '2h 30m 15s')."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts[:3]) if parts else "0s"


def format_file_size(bytes_count: int) -> str:
    """Convert byte count to human-readable file size (e.g., '1.5 MB')."""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_count)

    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}" if size < 10 else f"{size:.0f} {unit}"
        size /= 1024

    return f"{size:.1f} PB"


def format_phone_number(phone: str) -> str:
    """Format phone number string to standardized format."""
    digits = re.sub(r"\D", "", phone)

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    elif len(digits) >= 10:
        return f"+{digits[0]} {digits[1:]} " if digits[0] != "1" else digits

    return phone


def format_address(street: str, city: str, state: str, zip_code: str, country: str = "USA") -> str:
    """Format address components into single-line address string."""
    parts = [street, city, state, zip_code]
    if country and country != "USA":
        parts.append(country)
    return ", ".join(p for p in parts if p)


def format_address_multiline(street: str, city: str, state: str, zip_code: str, country: str = "USA") -> str:
    """Format address components as multiline string."""
    lines = [street, f"{city}, {state} {zip_code}"]
    if country and country != "USA":
        lines.append(country)
    return "\n".join(lines)


def format_product_title(title: str, max_length: int = 100) -> str:
    """Normalize and truncate product title with ellipsis if needed."""
    title = html.unescape(title).strip()
    if len(title) > max_length:
        return title[:max_length - 3] + "..."
    return title


def format_product_description(description: str, max_length: int = 500) -> str:
    """Clean and truncate product description."""
    text = html.unescape(description).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text


def format_product_sku(sku: str) -> str:
    """Format product SKU to uppercase alphanumeric only."""
    return re.sub(r"[^A-Z0-9]", "", sku.upper())


def format_product_barcode(barcode: str) -> str:
    """Format barcode to digits only."""
    return re.sub(r"\D", "", barcode)


def format_quantity_label(quantity: int, unit: str = "item") -> str:
    """Format quantity with proper singular/plural unit."""
    plural = "s" if quantity != 1 else ""
    return f"{quantity} {unit}{plural}"


def format_order_id(order_id: str) -> str:
    """Format order ID with '#' prefix and uppercase."""
    return f"#{order_id.upper()}"


def format_order_summary(order_id: str, item_count: int, total: Decimal, status: str) -> str:
    """Format compact order summary line."""
    return f"Order {format_order_id(order_id)}: {item_count} items, {format_currency(total)}, {status}"


def format_order_status(status: str) -> str:
    """Format order status to title case with proper spacing."""
    return status.replace("_", " ").title()


def format_invoice_number(invoice_id: str) -> str:
    """Format invoice number with prefix and checksum-like formatting."""
    return f"INV-{invoice_id.upper()}"


def format_tracking_number(tracking: str) -> str:
    """Format tracking number with consistent spacing."""
    clean = re.sub(r"\s", "", tracking.upper())
    if len(clean) > 20:
        return clean[:20]
    return clean


def format_coupon_code(code: str) -> str:
    """Format coupon code to uppercase alphanumeric only."""
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def format_discount_code(code: str) -> str:
    """Format discount code for display."""
    return format_coupon_code(code)


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format decimal as percentage string."""
    return f"{value * 100:.{decimals}f}%"


def format_rating(rating: float, max_rating: int = 5) -> str:
    """Format rating with stars or numeric display."""
    stars = "★" * int(rating) + "☆" * (max_rating - int(rating))
    return f"{stars} {rating:.1f}/{max_rating}"


def format_review_count(count: int) -> str:
    """Format review count as readable string."""
    if count == 0:
        return "No reviews"
    elif count == 1:
        return "1 review"
    elif count < 1000:
        return f"{count} reviews"
    else:
        return f"{count / 1000:.1f}K reviews"


def format_tax_amount(amount: Decimal, tax_rate: Decimal) -> str:
    """Format tax calculation as readable string."""
    return f"{format_currency(amount)} ({format_percentage(float(tax_rate))})"


def format_shipping_cost(cost: Decimal, delivery_days: int) -> str:
    """Format shipping cost with delivery estimate."""
    if cost == 0:
        return f"Free shipping ({delivery_days}-{delivery_days + 1} days)"
    return f"{format_currency(cost)} ({delivery_days}-{delivery_days + 1} days)"


def format_pagination_info(current_page: int, total_pages: int, items_per_page: int) -> str:
    """Format pagination details for display."""
    start_item = (current_page - 1) * items_per_page + 1
    end_item = current_page * items_per_page
    return f"Page {current_page} of {total_pages} ({start_item}-{end_item})"


def format_search_result_count(total: int, query: str = "") -> str:
    """Format search result count as readable message."""
    if total == 0:
        return f"No results found" + (f" for '{query}'" if query else "")
    elif total == 1:
        return "1 result found"
    elif total < 100:
        return f"{total} results found"
    else:
        return f"{total:,} results found"


def format_error_message(code: str, message: str) -> str:
    """Format error details as user-friendly message."""
    code_upper = code.upper().replace("_", " ")
    return f"Error ({code_upper}): {message}"


def format_validation_error(field: str, error_type: str) -> str:
    """Format field validation error message."""
    field_label = field.replace("_", " ").title()
    error_msgs = {
        "required": f"{field_label} is required",
        "invalid": f"{field_label} format is invalid",
        "too_long": f"{field_label} is too long",
        "too_short": f"{field_label} is too short",
        "unique": f"{field_label} is already in use",
    }
    return error_msgs.get(error_type, f"{field_label}: {error_type}")


def format_warning_message(warning_type: str, details: str = "") -> str:
    """Format warning message with type classification."""
    warning_label = warning_type.replace("_", " ").title()
    if details:
        return f"Warning - {warning_label}: {details}"
    return f"Warning - {warning_label}"


def format_success_message(action: str, subject: str = "") -> str:
    """Format success confirmation message."""
    if subject:
        return f"Successfully {action} {subject}"
    return f"Successfully {action}"


def format_truncated_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to max length and append suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_csv_value(value: str) -> str:
    """Format string value for safe CSV inclusion."""
    if "," in value or '"' in value or "\n" in value:
        return f'"{value.replace(chr(34), chr(34) + chr(34))}"'
    return value


def format_html_safe(text: str) -> str:
    """Escape HTML special characters in text."""
    return html.escape(text, quote=True)


def format_weight(grams: float, unit: str = "auto") -> str:
    """Format weight in grams to readable unit (g, kg, lb, oz)."""
    if unit == "auto":
        if grams >= 1000:
            return f"{grams / 1000:.2f} kg"
        return f"{grams:.0f} g"
    elif unit == "lb":
        return f"{grams / 453.592:.2f} lb"
    elif unit == "oz":
        return f"{grams / 28.35:.2f} oz"
    return f"{grams:.0f} g"


def format_dimension(mm: float, unit: str = "auto") -> str:
    """Format dimension in millimeters to readable unit."""
    if unit == "auto":
        if mm >= 1000:
            return f"{mm / 1000:.2f} m"
        elif mm >= 100:
            return f"{mm / 10:.1f} cm"
        return f"{mm:.0f} mm"
    elif unit == "in":
        return f"{mm / 25.4:.2f} in"
    return f"{mm:.0f} mm"


def format_dimensions_box(length: float, width: float, height: float) -> str:
    """Format 3D dimensions as readable string."""
    return f"{length:.1f} x {width:.1f} x {height:.1f} cm"


def format_stock_status(quantity: int) -> str:
    """Format stock quantity as status message."""
    if quantity == 0:
        return "Out of stock"
    elif quantity < 5:
        return f"Only {quantity} left"
    elif quantity < 20:
        return "Low stock"
    return "In stock"


def format_currency_code(code: str) -> str:
    """Format currency code to uppercase ISO 4217 format."""
    return code.upper().strip()


def format_language_code(code: str) -> str:
    """Format language code to lowercase ISO 639-1 format."""
    return code.lower().strip()


def format_country_code(code: str) -> str:
    """Format country code to uppercase ISO 3166-1 alpha-2 format."""
    return code.upper().strip()


def format_email_masked(email: str) -> str:
    """Format email with domain visible but local part partially masked."""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def format_phone_masked(phone: str) -> str:
    """Format phone number with last 4 digits visible only."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "****"
    return "*" * (len(digits) - 4) + digits[-4:]


def format_url_slug(text: str) -> str:
    """Format text as URL-safe slug (lowercase, hyphens, alphanumeric)."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug


def format_camel_case(text: str) -> str:
    """Format text as camelCase identifier."""
    words = re.sub(r"[^\w\s]", " ", text).split()
    if not words:
        return ""
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def format_snake_case(text: str) -> str:
    """Format text as snake_case identifier."""
    text = re.sub(r"([A-Z])", r"_\1", text).lower()
    text = re.sub(r"[^\w_]", "_", text)
    return re.sub(r"_+", "_", text).strip("_")
