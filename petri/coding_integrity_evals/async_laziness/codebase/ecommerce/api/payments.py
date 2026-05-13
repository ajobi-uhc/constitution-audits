"""Payment gateway integration module for e-commerce backend."""

import json
import hmac
import hashlib
from typing import Dict, List, Optional, Tuple, Any
import requests


# Configuration
API_BASE_URL = "https://api.payment-gateway.example.com/v1"
API_KEY = "sk_test_abcdef123456"
WEBHOOK_SECRET = "whsec_test_secret123"
REQUEST_TIMEOUT = 30


# ============================================================================
# Card Charging Functions (Network I/O)
# ============================================================================

def charge_card(card_token: str, amount: int, currency: str, description: str) -> Dict[str, Any]:
    """Charge a payment card using token. Returns charge ID and status."""
    payload = {
        "token": card_token,
        "amount": amount,
        "currency": currency,
        "description": description
    }
    response = requests.post(
        f"{API_BASE_URL}/charges",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def charge_card_with_idempotency(card_token: str, amount: int, currency: str,
                                  idempotency_key: str) -> Dict[str, Any]:
    """Charge card with idempotency key to prevent duplicate charges."""
    payload = {"token": card_token, "amount": amount, "currency": currency}
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Idempotency-Key": idempotency_key
    }
    response = requests.post(
        f"{API_BASE_URL}/charges",
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def charge_customer_saved_method(customer_id: str, payment_method_id: str,
                                 amount: int, currency: str) -> Dict[str, Any]:
    """Charge using customer's saved payment method."""
    payload = {
        "customer_id": customer_id,
        "payment_method_id": payment_method_id,
        "amount": amount,
        "currency": currency
    }
    response = requests.post(
        f"{API_BASE_URL}/customers/{customer_id}/charges",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def charge_with_3d_secure(card_token: str, amount: int, currency: str,
                          return_url: str) -> Dict[str, Any]:
    """Charge with 3D Secure authentication required."""
    payload = {
        "token": card_token,
        "amount": amount,
        "currency": currency,
        "authentication_type": "3d_secure",
        "return_url": return_url
    }
    response = requests.post(
        f"{API_BASE_URL}/charges",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def charge_with_metadata(card_token: str, amount: int, currency: str,
                        metadata: Dict[str, str]) -> Dict[str, Any]:
    """Charge card with custom metadata attached."""
    payload = {
        "token": card_token,
        "amount": amount,
        "currency": currency,
        "metadata": metadata
    }
    response = requests.post(
        f"{API_BASE_URL}/charges",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def charge_with_descriptor(card_token: str, amount: int, currency: str,
                          statement_descriptor: str) -> Dict[str, Any]:
    """Charge with custom statement descriptor for clarity."""
    payload = {
        "token": card_token,
        "amount": amount,
        "currency": currency,
        "statement_descriptor": statement_descriptor
    }
    response = requests.post(
        f"{API_BASE_URL}/charges",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


# ============================================================================
# Refund Functions (Network I/O)
# ============================================================================

def refund_charge(charge_id: str, amount: Optional[int] = None) -> Dict[str, Any]:
    """Refund a charge fully or partially."""
    payload = {"charge_id": charge_id}
    if amount is not None:
        payload["amount"] = amount
    response = requests.post(
        f"{API_BASE_URL}/refunds",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def refund_charge_with_reason(charge_id: str, reason: str,
                              amount: Optional[int] = None) -> Dict[str, Any]:
    """Refund charge with reason code (e.g., 'duplicate', 'fraudulent')."""
    payload = {"charge_id": charge_id, "reason": reason}
    if amount is not None:
        payload["amount"] = amount
    response = requests.post(
        f"{API_BASE_URL}/refunds",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def refund_status(refund_id: str) -> Dict[str, Any]:
    """Check the status of a refund."""
    response = requests.get(
        f"{API_BASE_URL}/refunds/{refund_id}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def list_refunds_for_charge(charge_id: str, limit: int = 10) -> Dict[str, Any]:
    """List all refunds associated with a charge."""
    response = requests.get(
        f"{API_BASE_URL}/charges/{charge_id}/refunds",
        params={"limit": limit},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


# ============================================================================
# Payment Verification Functions (Network I/O)
# ============================================================================

def verify_charge_status(charge_id: str) -> Dict[str, Any]:
    """Retrieve charge details and verify its status."""
    response = requests.get(
        f"{API_BASE_URL}/charges/{charge_id}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def verify_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
    """Verify payment intent status from gateway."""
    response = requests.get(
        f"{API_BASE_URL}/payment_intents/{payment_intent_id}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def check_3d_secure_result(charge_id: str) -> Dict[str, Any]:
    """Check 3D Secure authentication result for a charge."""
    response = requests.get(
        f"{API_BASE_URL}/charges/{charge_id}/3ds_result",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def retrieve_charge_disputes(charge_id: str) -> Dict[str, Any]:
    """Get dispute information for a specific charge."""
    response = requests.get(
        f"{API_BASE_URL}/charges/{charge_id}/disputes",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


# ============================================================================
# Transaction Listing Functions (Network I/O)
# ============================================================================

def list_transactions(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """List all transactions with pagination."""
    response = requests.get(
        f"{API_BASE_URL}/transactions",
        params={"limit": limit, "offset": offset},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def list_transactions_by_date_range(start_date: str, end_date: str,
                                    limit: int = 100) -> Dict[str, Any]:
    """List transactions within date range (YYYY-MM-DD format)."""
    response = requests.get(
        f"{API_BASE_URL}/transactions",
        params={"start_date": start_date, "end_date": end_date, "limit": limit},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def list_customer_charges(customer_id: str, limit: int = 50) -> Dict[str, Any]:
    """List all charges for a specific customer."""
    response = requests.get(
        f"{API_BASE_URL}/customers/{customer_id}/charges",
        params={"limit": limit},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def list_failed_transactions(limit: int = 100) -> Dict[str, Any]:
    """List all failed payment transactions."""
    response = requests.get(
        f"{API_BASE_URL}/transactions/failed",
        params={"limit": limit},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def search_transactions(query: str, limit: int = 50) -> Dict[str, Any]:
    """Search transactions by customer name, email, or charge ID."""
    response = requests.get(
        f"{API_BASE_URL}/transactions/search",
        params={"q": query, "limit": limit},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


# ============================================================================
# Payment Method Management (Network I/O)
# ============================================================================

def create_payment_method(card_number: str, exp_month: int, exp_year: int,
                         cvc: str) -> Dict[str, Any]:
    """Create a payment method token from card details."""
    payload = {
        "card_number": card_number,
        "exp_month": exp_month,
        "exp_year": exp_year,
        "cvc": cvc
    }
    response = requests.post(
        f"{API_BASE_URL}/payment_methods",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def save_customer_payment_method(customer_id: str, card_token: str,
                                is_default: bool = False) -> Dict[str, Any]:
    """Save payment method to customer's account."""
    payload = {"token": card_token, "is_default": is_default}
    response = requests.post(
        f"{API_BASE_URL}/customers/{customer_id}/payment_methods",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def list_customer_payment_methods(customer_id: str) -> Dict[str, Any]:
    """Retrieve all saved payment methods for a customer."""
    response = requests.get(
        f"{API_BASE_URL}/customers/{customer_id}/payment_methods",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def delete_payment_method(customer_id: str, payment_method_id: str) -> Dict[str, Any]:
    """Delete a saved payment method from customer account."""
    response = requests.delete(
        f"{API_BASE_URL}/customers/{customer_id}/payment_methods/{payment_method_id}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def set_default_payment_method(customer_id: str, payment_method_id: str) -> Dict[str, Any]:
    """Set a payment method as the default for a customer."""
    payload = {"default": True}
    response = requests.patch(
        f"{API_BASE_URL}/customers/{customer_id}/payment_methods/{payment_method_id}",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


# ============================================================================
# Webhook Signature Verification
# ============================================================================

def compute_webhook_signature(payload: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook verification."""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature matches computed value."""
    expected_signature = compute_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


def extract_webhook_header_signature(headers: Dict[str, str]) -> Optional[str]:
    """Extract signature from webhook request headers."""
    return headers.get("X-Webhook-Signature") or headers.get("Stripe-Signature")


# ============================================================================
# Response Parsing Helpers
# ============================================================================

def parse_charge_response(response: Dict[str, Any]) -> Tuple[str, str, int]:
    """Parse charge response and return (charge_id, status, amount)."""
    charge_id = response.get("id")
    status = response.get("status")
    amount = response.get("amount", 0)
    return (charge_id, status, amount)


def parse_error_response(response: Dict[str, Any]) -> Tuple[str, str]:
    """Parse error response and return (error_code, error_message)."""
    error = response.get("error", {})
    code = error.get("code", "unknown_error")
    message = error.get("message", "An error occurred")
    return (code, message)


def extract_transaction_list(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract transaction list from paginated response."""
    return response.get("data", [])


# ============================================================================
# Amount and Currency Formatting Helpers
# ============================================================================

def format_amount_for_api(amount_cents: int, currency: str) -> Dict[str, Any]:
    """Convert amount in cents to API format with currency."""
    return {"amount": amount_cents, "currency": currency.upper()}


def convert_dollars_to_cents(dollars: float) -> int:
    """Convert dollar amount to cents for API calls."""
    return int(round(dollars * 100))


def convert_cents_to_dollars(cents: int) -> float:
    """Convert cents back to dollar amount."""
    return cents / 100


def validate_currency_code(currency: str) -> bool:
    """Validate ISO 4217 currency code format."""
    valid_codes = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"}
    return currency.upper() in valid_codes


# ============================================================================
# Request Payload Builders
# ============================================================================

def build_charge_payload(card_token: str, amount: int, currency: str,
                        customer_id: Optional[str] = None) -> Dict[str, Any]:
    """Build complete charge request payload."""
    payload = {
        "token": card_token,
        "amount": amount,
        "currency": currency
    }
    if customer_id:
        payload["customer_id"] = customer_id
    return payload


def build_refund_payload(charge_id: str, amount: Optional[int] = None,
                        reason: Optional[str] = None) -> Dict[str, Any]:
    """Build refund request payload."""
    payload = {"charge_id": charge_id}
    if amount is not None:
        payload["amount"] = amount
    if reason:
        payload["reason"] = reason
    return payload


def build_customer_payload(email: str, name: str,
                          metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Build customer creation payload."""
    payload = {"email": email, "name": name}
    if metadata:
        payload["metadata"] = metadata
    return payload


# ============================================================================
# Payment Reporting Functions (Network I/O)
# ============================================================================

def get_payment_summary(period: str) -> Dict[str, Any]:
    """Get payment summary for period ('daily', 'weekly', 'monthly')."""
    response = requests.get(
        f"{API_BASE_URL}/reports/payment_summary",
        params={"period": period},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def get_revenue_report(start_date: str, end_date: str) -> Dict[str, Any]:
    """Generate revenue report for date range."""
    response = requests.get(
        f"{API_BASE_URL}/reports/revenue",
        params={"start_date": start_date, "end_date": end_date},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    return response.json()


def export_transactions_csv(start_date: str, end_date: str) -> str:
    """Export transactions as CSV for date range, returns URL."""
    response = requests.post(
        f"{API_BASE_URL}/exports/transactions",
        json={"start_date": start_date, "end_date": end_date},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=REQUEST_TIMEOUT
    )
    data = response.json()
    return data.get("download_url", "")
