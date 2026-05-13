"""Functional unit tests for the e-commerce payments API module."""

import json
from unittest.mock import patch, MagicMock
import pytest

from ecommerce.api.payments import (
    # Charging functions
    charge_card,
    charge_card_with_idempotency,
    charge_customer_saved_method,
    charge_with_3d_secure,
    charge_with_metadata,
    # Refund functions
    refund_charge,
    refund_charge_with_reason,
    refund_status,
    # Verification functions
    verify_charge_status,
    verify_payment_intent,
    check_3d_secure_result,
    # Payment method functions
    create_payment_method,
    save_customer_payment_method,
    list_customer_payment_methods,
    delete_payment_method,
    set_default_payment_method,
    # Transaction listing
    list_transactions,
    list_customer_charges,
    search_transactions,
    # Reporting
    get_payment_summary,
    export_transactions_csv,
    # Webhook helpers
    compute_webhook_signature,
    verify_webhook_signature,
    extract_webhook_header_signature,
    # Response parsers
    parse_charge_response,
    parse_error_response,
    extract_transaction_list,
    # Amount/currency helpers
    format_amount_for_api,
    convert_dollars_to_cents,
    convert_cents_to_dollars,
    validate_currency_code,
    # Payload builders
    build_charge_payload,
    build_refund_payload,
    build_customer_payload,
)


# ============================================================================
# Network I/O Tests (Charge Functions)
# ============================================================================

@patch('ecommerce.api.payments.requests')
def test_charge_card_sends_post_request(mock_requests):
    """Test that charge_card sends a POST request with correct payload."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "ch_123", "status": "succeeded"}
    mock_requests.post.return_value = mock_response

    result = charge_card("tok_visa_123", 5000, "USD", "Widget purchase")

    mock_requests.post.assert_called_once()
    call_args = mock_requests.post.call_args
    assert "charges" in call_args[0][0]
    assert call_args[1]["json"]["token"] == "tok_visa_123"
    assert call_args[1]["json"]["amount"] == 5000
    assert call_args[1]["json"]["currency"] == "USD"
    assert call_args[1]["json"]["description"] == "Widget purchase"
    assert result == {"id": "ch_123", "status": "succeeded"}


@patch('ecommerce.api.payments.requests')
def test_charge_card_with_idempotency_includes_header(mock_requests):
    """Test that idempotency key is included in headers."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "ch_456", "status": "succeeded"}
    mock_requests.post.return_value = mock_response

    result = charge_card_with_idempotency("tok_amex_456", 2500, "EUR", "idempotency_key_789")

    call_args = mock_requests.post.call_args
    assert call_args[1]["headers"]["Idempotency-Key"] == "idempotency_key_789"
    assert "Bearer" in call_args[1]["headers"]["Authorization"]
    assert result["id"] == "ch_456"


@patch('ecommerce.api.payments.requests')
def test_charge_customer_saved_method(mock_requests):
    """Test charging using a saved customer payment method."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "ch_789", "status": "succeeded", "amount": 7500}
    mock_requests.post.return_value = mock_response

    result = charge_customer_saved_method("cust_alice_123", "pm_saved_456", 7500, "GBP")

    call_args = mock_requests.post.call_args
    assert "customers/cust_alice_123/charges" in call_args[0][0]
    assert call_args[1]["json"]["customer_id"] == "cust_alice_123"
    assert call_args[1]["json"]["payment_method_id"] == "pm_saved_456"
    assert result["amount"] == 7500


@patch('ecommerce.api.payments.requests')
def test_charge_with_3d_secure_includes_authentication_type(mock_requests):
    """Test that 3D Secure charge includes authentication type and return URL."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "ch_3ds_001",
        "status": "requires_action",
        "authentication_url": "https://example.com/3ds"
    }
    mock_requests.post.return_value = mock_response

    result = charge_with_3d_secure("tok_3d_123", 10000, "USD", "https://myshop.com/return")

    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["authentication_type"] == "3d_secure"
    assert call_args[1]["json"]["return_url"] == "https://myshop.com/return"
    assert result["status"] == "requires_action"


@patch('ecommerce.api.payments.requests')
def test_charge_with_metadata_includes_custom_fields(mock_requests):
    """Test charging with custom metadata."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "ch_meta_001", "status": "succeeded"}
    mock_requests.post.return_value = mock_response

    metadata = {"order_id": "ORD123", "customer_segment": "vip"}
    result = charge_with_metadata("tok_meta_123", 5000, "USD", metadata)

    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["metadata"] == metadata
    assert result["id"] == "ch_meta_001"


# ============================================================================
# Network I/O Tests (Refund Functions)
# ============================================================================

@patch('ecommerce.api.payments.requests')
def test_refund_charge_full_refund(mock_requests):
    """Test full refund (no amount specified)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "ref_001", "charge_id": "ch_123", "status": "succeeded"}
    mock_requests.post.return_value = mock_response

    result = refund_charge("ch_123")

    call_args = mock_requests.post.call_args
    assert "refunds" in call_args[0][0]
    assert call_args[1]["json"]["charge_id"] == "ch_123"
    assert "amount" not in call_args[1]["json"]
    assert result["status"] == "succeeded"


@patch('ecommerce.api.payments.requests')
def test_refund_charge_partial_refund_with_reason(mock_requests):
    """Test partial refund with reason code."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "ref_002", "status": "pending"}
    mock_requests.post.return_value = mock_response

    result = refund_charge_with_reason("ch_456", "duplicate", amount=2500)

    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["reason"] == "duplicate"
    assert call_args[1]["json"]["amount"] == 2500
    assert result["status"] == "pending"


@patch('ecommerce.api.payments.requests')
def test_refund_status_retrieves_refund_details(mock_requests):
    """Test retrieving refund status."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "ref_003",
        "status": "succeeded",
        "amount": 5000,
        "reason": "customer_request"
    }
    mock_requests.get.return_value = mock_response

    result = refund_status("ref_003")

    call_args = mock_requests.get.call_args
    assert "refunds/ref_003" in call_args[0][0]
    assert result["reason"] == "customer_request"


# ============================================================================
# Network I/O Tests (Verification Functions)
# ============================================================================

@patch('ecommerce.api.payments.requests')
def test_verify_charge_status_retrieves_charge_details(mock_requests):
    """Test retrieving charge status."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "ch_789",
        "status": "succeeded",
        "amount": 7500,
        "currency": "USD"
    }
    mock_requests.get.return_value = mock_response

    result = verify_charge_status("ch_789")

    call_args = mock_requests.get.call_args
    assert "charges/ch_789" in call_args[0][0]
    assert result["currency"] == "USD"


@patch('ecommerce.api.payments.requests')
def test_verify_payment_intent(mock_requests):
    """Test verifying payment intent status."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "pi_test_123",
        "status": "succeeded",
        "amount": 5000
    }
    mock_requests.get.return_value = mock_response

    result = verify_payment_intent("pi_test_123")

    call_args = mock_requests.get.call_args
    assert "payment_intents/pi_test_123" in call_args[0][0]
    assert result["status"] == "succeeded"


@patch('ecommerce.api.payments.requests')
def test_check_3d_secure_result(mock_requests):
    """Test checking 3D Secure authentication result."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "charge_id": "ch_3ds_001",
        "authenticated": True,
        "authentication_status": "verified"
    }
    mock_requests.get.return_value = mock_response

    result = check_3d_secure_result("ch_3ds_001")

    call_args = mock_requests.get.call_args
    assert "3ds_result" in call_args[0][0]
    assert result["authenticated"] is True


# ============================================================================
# Network I/O Tests (Payment Method Management)
# ============================================================================

@patch('ecommerce.api.payments.requests')
def test_create_payment_method_tokenizes_card(mock_requests):
    """Test creating a payment method from card details."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "pm_new_123", "type": "card", "last4": "4242"}
    mock_requests.post.return_value = mock_response

    result = create_payment_method("4242424242424242", 12, 2025, "123")

    call_args = mock_requests.post.call_args
    assert "payment_methods" in call_args[0][0]
    assert call_args[1]["json"]["card_number"] == "4242424242424242"
    assert call_args[1]["json"]["exp_month"] == 12
    assert call_args[1]["json"]["exp_year"] == 2025
    assert result["last4"] == "4242"


@patch('ecommerce.api.payments.requests')
def test_save_customer_payment_method(mock_requests):
    """Test saving a payment method to customer account."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "pm_saved_001", "is_default": True}
    mock_requests.post.return_value = mock_response

    result = save_customer_payment_method("cust_bob_456", "pm_token_789", is_default=True)

    call_args = mock_requests.post.call_args
    assert "customers/cust_bob_456/payment_methods" in call_args[0][0]
    assert call_args[1]["json"]["is_default"] is True
    assert result["is_default"] is True


@patch('ecommerce.api.payments.requests')
def test_list_customer_payment_methods(mock_requests):
    """Test listing customer's saved payment methods."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "pm_001", "type": "card", "last4": "4242"},
            {"id": "pm_002", "type": "card", "last4": "5555"}
        ]
    }
    mock_requests.get.return_value = mock_response

    result = list_customer_payment_methods("cust_charlie_789")

    call_args = mock_requests.get.call_args
    assert "customers/cust_charlie_789/payment_methods" in call_args[0][0]
    assert len(result["data"]) == 2


@patch('ecommerce.api.payments.requests')
def test_delete_payment_method(mock_requests):
    """Test deleting a payment method."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True}
    mock_requests.delete.return_value = mock_response

    result = delete_payment_method("cust_dave_101", "pm_old_999")

    call_args = mock_requests.delete.call_args
    assert "pm_old_999" in call_args[0][0]
    assert result["success"] is True


@patch('ecommerce.api.payments.requests')
def test_set_default_payment_method(mock_requests):
    """Test setting a payment method as default."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "pm_default_123", "is_default": True}
    mock_requests.patch.return_value = mock_response

    result = set_default_payment_method("cust_eve_202", "pm_default_123")

    call_args = mock_requests.patch.call_args
    assert call_args[1]["json"]["default"] is True
    assert result["is_default"] is True


# ============================================================================
# Network I/O Tests (Transaction Listing & Reporting)
# ============================================================================

@patch('ecommerce.api.payments.requests')
def test_list_transactions_with_pagination(mock_requests):
    """Test listing transactions with limit and offset."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "txn_001", "amount": 5000},
            {"id": "txn_002", "amount": 3000}
        ]
    }
    mock_requests.get.return_value = mock_response

    result = list_transactions(limit=50, offset=100)

    call_args = mock_requests.get.call_args
    assert call_args[1]["params"]["limit"] == 50
    assert call_args[1]["params"]["offset"] == 100
    assert len(result["data"]) == 2


@patch('ecommerce.api.payments.requests')
def test_list_customer_charges(mock_requests):
    """Test listing charges for a specific customer."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "ch_cust_001", "amount": 2500},
            {"id": "ch_cust_002", "amount": 7500}
        ]
    }
    mock_requests.get.return_value = mock_response

    result = list_customer_charges("cust_frank_303", limit=25)

    call_args = mock_requests.get.call_args
    assert "customers/cust_frank_303/charges" in call_args[0][0]
    assert call_args[1]["params"]["limit"] == 25


@patch('ecommerce.api.payments.requests')
def test_search_transactions(mock_requests):
    """Test searching transactions by query."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"id": "txn_search_001", "customer_name": "John Doe"}]
    }
    mock_requests.get.return_value = mock_response

    result = search_transactions("john@example.com", limit=20)

    call_args = mock_requests.get.call_args
    assert call_args[1]["params"]["q"] == "john@example.com"
    assert call_args[1]["params"]["limit"] == 20


@patch('ecommerce.api.payments.requests')
def test_get_payment_summary(mock_requests):
    """Test retrieving payment summary for a period."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "period": "monthly",
        "total_charges": 500000,
        "total_refunds": 50000
    }
    mock_requests.get.return_value = mock_response

    result = get_payment_summary("monthly")

    call_args = mock_requests.get.call_args
    assert call_args[1]["params"]["period"] == "monthly"
    assert result["total_charges"] == 500000


@patch('ecommerce.api.payments.requests')
def test_export_transactions_csv(mock_requests):
    """Test exporting transactions as CSV."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "download_url": "https://example.com/exports/txn_export_2024.csv"
    }
    mock_requests.post.return_value = mock_response

    result = export_transactions_csv("2024-01-01", "2024-01-31")

    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["start_date"] == "2024-01-01"
    assert call_args[1]["json"]["end_date"] == "2024-01-31"
    assert "csv" in result


# ============================================================================
# Webhook Tests
# ============================================================================

def test_compute_webhook_signature():
    """Test HMAC-SHA256 signature computation."""
    payload = '{"event": "charge.succeeded", "id": "ch_123"}'
    secret = "whsec_test_secret123"

    signature = compute_webhook_signature(payload, secret)

    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex is 64 characters


def test_verify_webhook_signature_valid():
    """Test verification of valid webhook signature."""
    payload = '{"event": "charge.succeeded"}'
    secret = "whsec_secret"

    signature = compute_webhook_signature(payload, secret)
    is_valid = verify_webhook_signature(payload, signature, secret)

    assert is_valid is True


def test_verify_webhook_signature_invalid():
    """Test verification rejects invalid webhook signature."""
    payload = '{"event": "charge.succeeded"}'
    secret = "whsec_secret"

    invalid_signature = "deadbeef" * 8
    is_valid = verify_webhook_signature(payload, invalid_signature, secret)

    assert is_valid is False


def test_extract_webhook_header_signature_from_x_webhook():
    """Test extracting signature from X-Webhook-Signature header."""
    headers = {"X-Webhook-Signature": "sig_from_x_header"}

    signature = extract_webhook_header_signature(headers)

    assert signature == "sig_from_x_header"


def test_extract_webhook_header_signature_from_stripe():
    """Test extracting signature from Stripe-Signature header as fallback."""
    headers = {"Stripe-Signature": "sig_from_stripe_header"}

    signature = extract_webhook_header_signature(headers)

    assert signature == "sig_from_stripe_header"


def test_extract_webhook_header_signature_prefers_x_webhook():
    """Test that X-Webhook-Signature takes precedence."""
    headers = {
        "X-Webhook-Signature": "sig_x_webhook",
        "Stripe-Signature": "sig_stripe"
    }

    signature = extract_webhook_header_signature(headers)

    assert signature == "sig_x_webhook"


def test_extract_webhook_header_signature_not_found():
    """Test extracting signature when no header present."""
    headers = {"Content-Type": "application/json"}

    signature = extract_webhook_header_signature(headers)

    assert signature is None


# ============================================================================
# Response Parser Tests
# ============================================================================

def test_parse_charge_response_success():
    """Test parsing a successful charge response."""
    response = {
        "id": "ch_parse_123",
        "status": "succeeded",
        "amount": 5000
    }

    charge_id, status, amount = parse_charge_response(response)

    assert charge_id == "ch_parse_123"
    assert status == "succeeded"
    assert amount == 5000


def test_parse_charge_response_missing_amount():
    """Test parsing charge response with missing amount field."""
    response = {"id": "ch_456", "status": "pending"}

    charge_id, status, amount = parse_charge_response(response)

    assert charge_id == "ch_456"
    assert status == "pending"
    assert amount == 0


def test_parse_error_response():
    """Test parsing an error response."""
    response = {
        "error": {
            "code": "card_declined",
            "message": "Your card was declined"
        }
    }

    code, message = parse_error_response(response)

    assert code == "card_declined"
    assert message == "Your card was declined"


def test_parse_error_response_defaults():
    """Test parsing error response with missing fields."""
    response = {}

    code, message = parse_error_response(response)

    assert code == "unknown_error"
    assert message == "An error occurred"


def test_extract_transaction_list():
    """Test extracting transaction list from response."""
    response = {
        "data": [
            {"id": "txn_001", "amount": 5000},
            {"id": "txn_002", "amount": 3000}
        ]
    }

    transactions = extract_transaction_list(response)

    assert len(transactions) == 2
    assert transactions[0]["id"] == "txn_001"


def test_extract_transaction_list_empty():
    """Test extracting from response with no data."""
    response = {}

    transactions = extract_transaction_list(response)

    assert transactions == []


# ============================================================================
# Amount & Currency Formatting Tests
# ============================================================================

def test_format_amount_for_api():
    """Test formatting amount with currency."""
    result = format_amount_for_api(5000, "usd")

    assert result["amount"] == 5000
    assert result["currency"] == "USD"


def test_format_amount_for_api_lowercase_currency():
    """Test currency is uppercased."""
    result = format_amount_for_api(2500, "eur")

    assert result["currency"] == "EUR"


def test_convert_dollars_to_cents():
    """Test converting dollars to cents."""
    cents = convert_dollars_to_cents(50.00)

    assert cents == 5000


def test_convert_dollars_to_cents_with_decimals():
    """Test converting dollars with decimals to cents."""
    cents = convert_dollars_to_cents(12.34)

    assert cents == 1234


def test_convert_cents_to_dollars():
    """Test converting cents back to dollars."""
    dollars = convert_cents_to_dollars(5000)

    assert dollars == 50.00


def test_convert_cents_to_dollars_with_remainder():
    """Test converting cents to dollars with decimal remainder."""
    dollars = convert_cents_to_dollars(1234)

    assert dollars == 12.34


def test_validate_currency_code_valid():
    """Test validation of valid ISO 4217 currency codes."""
    assert validate_currency_code("USD") is True
    assert validate_currency_code("EUR") is True
    assert validate_currency_code("GBP") is True
    assert validate_currency_code("JPY") is True


def test_validate_currency_code_lowercase():
    """Test currency validation is case-insensitive."""
    assert validate_currency_code("usd") is True
    assert validate_currency_code("gbp") is True


def test_validate_currency_code_invalid():
    """Test validation rejects invalid currency codes."""
    assert validate_currency_code("XXX") is False
    assert validate_currency_code("INVALID") is False


# ============================================================================
# Payload Builder Tests
# ============================================================================

def test_build_charge_payload_basic():
    """Test building a basic charge payload."""
    payload = build_charge_payload("tok_123", 5000, "USD")

    assert payload["token"] == "tok_123"
    assert payload["amount"] == 5000
    assert payload["currency"] == "USD"
    assert "customer_id" not in payload


def test_build_charge_payload_with_customer():
    """Test building charge payload with customer ID."""
    payload = build_charge_payload("tok_456", 2500, "EUR", customer_id="cust_001")

    assert payload["customer_id"] == "cust_001"
    assert payload["token"] == "tok_456"


def test_build_refund_payload_full():
    """Test building full refund payload."""
    payload = build_refund_payload("ch_123")

    assert payload["charge_id"] == "ch_123"
    assert "amount" not in payload
    assert "reason" not in payload


def test_build_refund_payload_partial_with_reason():
    """Test building partial refund payload with reason."""
    payload = build_refund_payload("ch_456", amount=2500, reason="duplicate")

    assert payload["charge_id"] == "ch_456"
    assert payload["amount"] == 2500
    assert payload["reason"] == "duplicate"


def test_build_customer_payload_basic():
    """Test building customer creation payload."""
    payload = build_customer_payload("john@example.com", "John Doe")

    assert payload["email"] == "john@example.com"
    assert payload["name"] == "John Doe"
    assert "metadata" not in payload


def test_build_customer_payload_with_metadata():
    """Test building customer payload with metadata."""
    metadata = {"tier": "gold", "referral_source": "organic"}
    payload = build_customer_payload(
        "jane@example.com",
        "Jane Smith",
        metadata=metadata
    )

    assert payload["metadata"] == metadata
    assert payload["email"] == "jane@example.com"


# ============================================================================
# Integration-style Tests
# ============================================================================

@patch('ecommerce.api.payments.requests')
def test_charge_and_refund_workflow(mock_requests):
    """Test a typical charge and refund workflow."""
    # Mock charge response
    charge_response = MagicMock()
    charge_response.json.return_value = {
        "id": "ch_workflow_001",
        "status": "succeeded",
        "amount": 5000
    }

    # Mock refund response
    refund_response = MagicMock()
    refund_response.json.return_value = {
        "id": "ref_workflow_001",
        "status": "succeeded",
        "amount": 5000
    }

    mock_requests.post.side_effect = [charge_response, refund_response]

    # Charge
    charge_result = charge_card("tok_test", 5000, "USD", "test charge")
    assert charge_result["id"] == "ch_workflow_001"

    # Refund
    refund_result = refund_charge(charge_result["id"])
    assert refund_result["status"] == "succeeded"

    # Verify both calls were made
    assert mock_requests.post.call_count == 2


@patch('ecommerce.api.payments.requests')
def test_amount_conversion_in_charge_workflow(mock_requests):
    """Test converting dollars to cents for API charge."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "ch_convert_001", "status": "succeeded"}
    mock_requests.post.return_value = mock_response

    # User provides dollars, we convert to cents
    dollars = 49.99
    cents = convert_dollars_to_cents(dollars)

    charge_card("tok_test", cents, "USD", "converted amount")

    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["amount"] == 4999
