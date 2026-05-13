"""Notification service for e-commerce platform."""

from ecommerce.api import email_service
from ecommerce.db import users as db_users
from datetime import datetime
from typing import Optional, List, Dict, Any


# Formatting functions

def format_order_confirmation_subject(order_id: str) -> str:
    """Generate subject line for order confirmation email."""
    return f"Order Confirmation #{order_id}"


def format_order_confirmation_body(order_id: str, total: float, items_count: int) -> str:
    """Build HTML body for order confirmation with order details."""
    return f"<h1>Thank you for your order!</h1><p>Order ID: {order_id}</p><p>Total: ${total:.2f}</p><p>Items: {items_count}</p>"


def format_shipment_notification_subject(tracking_id: str) -> str:
    """Create subject line for shipment tracking notification."""
    return f"Your order is on the way - Tracking #{tracking_id}"


def format_shipment_notification_body(tracking_id: str, carrier: str, est_delivery: str) -> str:
    """Compose shipment details body with tracking info."""
    return f"<h2>Shipment Confirmed</h2><p>Carrier: {carrier}</p><p>Tracking: {tracking_id}</p><p>Est. Delivery: {est_delivery}</p>"


def format_invoice_content(invoice_id: str, amount: float, due_date: str) -> str:
    """Generate invoice HTML content with payment details."""
    lines = [f"<h3>Invoice {invoice_id}</h3>", f"<p>Amount: ${amount:.2f}</p>", f"<p>Due: {due_date}</p>"]
    return "\n".join(lines)


def format_password_reset_body(reset_link: str, expiry_hours: int) -> str:
    """Create password reset email with secure link."""
    return f"<p>Click <a href='{reset_link}'>here</a> to reset your password.</p><p>Link expires in {expiry_hours} hours.</p>"


def format_welcome_message(user_name: str, sign_up_bonus: float) -> str:
    """Build welcome email content with sign-up bonus info."""
    return f"<h1>Welcome {user_name}!</h1><p>You've received a ${sign_up_bonus:.2f} sign-up bonus.</p>"


def format_discount_code_message(code: str, discount_percent: int, expiry_date: str) -> str:
    """Format promotional code announcement."""
    return f"<h2>Exclusive Offer!</h2><p>Code: {code}</p><p>{discount_percent}% off until {expiry_date}</p>"


def format_cart_abandonment_message(abandoned_items: List[str]) -> str:
    """Create reminder email for abandoned cart."""
    items_html = "".join([f"<li>{item}</li>" for item in abandoned_items])
    return f"<h2>Your Cart Awaits</h2><ul>{items_html}</ul><p>Complete checkout now.</p>"


def format_review_request_body(product_name: str, order_id: str) -> str:
    """Compose request for product review."""
    return f"<p>How was your experience with {product_name}?</p><p>Order: {order_id}</p>"


def format_subscription_renewal_notice(subscription_id: str, renewal_date: str, amount: float) -> str:
    """Build subscription renewal notification content."""
    return f"<p>Subscription {subscription_id} renews on {renewal_date}</p><p>Amount: ${amount:.2f}</p>"


def format_delivery_confirmation_message(tracking_id: str, signature_date: str) -> str:
    """Generate delivery completed confirmation."""
    return f"<h2>Delivery Confirmed</h2><p>Tracking: {tracking_id}</p><p>Delivered: {signature_date}</p>"


def format_loyalty_points_earned(points: int, total_balance: int) -> str:
    """Create message about loyalty points earned."""
    return f"<p>You've earned {points} points!</p><p>Total balance: {total_balance} points</p>"


def format_price_drop_alert(product_name: str, old_price: float, new_price: float) -> str:
    """Build price reduction notification content."""
    savings = old_price - new_price
    return f"<h2>{product_name} Price Drop!</h2><p>Was: ${old_price:.2f} Now: ${new_price:.2f} (Save ${savings:.2f})</p>"


def format_back_in_stock_alert(product_name: str, product_id: str) -> str:
    """Compose notification for out-of-stock product availability."""
    return f"<h2>Back in Stock!</h2><p>{product_name} (ID: {product_id}) is available again.</p>"


def format_account_security_alert(alert_type: str, timestamp: str) -> str:
    """Create security notification for account activity."""
    return f"<h2>Security Alert</h2><p>Alert: {alert_type}</p><p>Time: {timestamp}</p>"


def format_return_authorization_body(rma_number: str, instructions: str) -> str:
    """Build return merchandise authorization email."""
    return f"<h2>Return Authorization</h2><p>RMA #: {rma_number}</p><p>Instructions: {instructions}</p>"


def format_refund_processed_message(refund_amount: float, refund_date: str) -> str:
    """Create refund confirmation notification."""
    return f"<h2>Refund Processed</h2><p>Amount: ${refund_amount:.2f}</p><p>Date: {refund_date}</p>"





def send_order_confirmation_email(user_id: str, order_id: str, total: float, items_count: int) -> bool:
    """Send order confirmation email to customer via email service."""
    subject = format_order_confirmation_subject(order_id)
    body = format_order_confirmation_body(order_id, total, items_count)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def send_shipment_notification(user_id: str, tracking_id: str, carrier: str, est_delivery: str) -> bool:
    """Send shipment notification with tracking details."""
    subject = format_shipment_notification_subject(tracking_id)
    body = format_shipment_notification_body(tracking_id, carrier, est_delivery)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def send_invoice_email(user_id: str, invoice_id: str, amount: float, due_date: str) -> bool:
    """Email invoice to user with payment details."""
    subject = f"Invoice {invoice_id}"
    body = format_invoice_content(invoice_id, amount, due_date)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def send_password_reset_email(user_id: str, reset_link: str, expiry_hours: int) -> bool:
    """Send password reset link via email service."""
    subject = "Reset Your Password"
    body = format_password_reset_body(reset_link, expiry_hours)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def send_welcome_email(user_id: str, user_name: str, sign_up_bonus: float) -> bool:
    """Send welcome email to new user with bonus info."""
    subject = "Welcome to our platform!"
    body = format_welcome_message(user_name, sign_up_bonus)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def queue_promotional_email(user_id: str, code: str, discount_percent: int, expiry_date: str) -> bool:
    """Queue promotional code email to database queue."""
    user = db_users.get_user_email(user_id)
    body = format_discount_code_message(code, discount_percent, expiry_date)
    return db_users.queue_email(user_id, "promotional", body, {"code": code, "discount": discount_percent})


def send_cart_abandonment_notification(user_id: str, abandoned_items: List[str]) -> bool:
    """Send cart abandonment reminder email."""
    subject = "Don't forget your items!"
    body = format_cart_abandonment_message(abandoned_items)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def send_review_request_email(user_id: str, product_name: str, order_id: str) -> bool:
    """Email customer requesting product review."""
    subject = f"Tell us about {product_name}"
    body = format_review_request_body(product_name, order_id)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def queue_subscription_renewal_notice(user_id: str, subscription_id: str, renewal_date: str, amount: float) -> bool:
    """Queue subscription renewal notification to database."""
    body = format_subscription_renewal_notice(subscription_id, renewal_date, amount)
    return db_users.queue_email(user_id, "subscription", body, {"subscription_id": subscription_id, "amount": amount})


def send_delivery_confirmation(user_id: str, tracking_id: str, signature_date: str) -> bool:
    """Send delivery completed notification."""
    subject = "Your order has arrived!"
    body = format_delivery_confirmation_message(tracking_id, signature_date)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def log_loyalty_points_earned(user_id: str, points: int, total_balance: int) -> bool:
    """Log loyalty points event to database."""
    body = format_loyalty_points_earned(points, total_balance)
    return db_users.log_event(user_id, "loyalty_points", {"points": points, "balance": total_balance})


def send_price_drop_alert(user_id: str, product_name: str, old_price: float, new_price: float) -> bool:
    """Send price reduction notification via email."""
    subject = f"Price drop: {product_name}"
    body = format_price_drop_alert(product_name, old_price, new_price)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def send_back_in_stock_notification(user_id: str, product_name: str, product_id: str) -> bool:
    """Alert user that previously out-of-stock item is available."""
    subject = f"{product_name} is back!"
    body = format_back_in_stock_alert(product_name, product_id)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def log_account_security_alert(user_id: str, alert_type: str) -> bool:
    """Log security alert to database for audit trail."""
    timestamp = datetime.now().isoformat()
    body = format_account_security_alert(alert_type, timestamp)
    return db_users.log_event(user_id, "security_alert", {"alert_type": alert_type, "timestamp": timestamp})


def send_return_authorization_email(user_id: str, rma_number: str, instructions: str) -> bool:
    """Email return merchandise authorization with instructions."""
    subject = f"Return Authorization {rma_number}"
    body = format_return_authorization_body(rma_number, instructions)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def send_refund_processed_notification(user_id: str, refund_amount: float) -> bool:
    """Send refund confirmation email to customer."""
    subject = "Refund Processed"
    refund_date = datetime.now().strftime("%Y-%m-%d")
    body = format_refund_processed_message(refund_amount, refund_date)
    user = db_users.get_user_email(user_id)
    return email_service.send_email(user["email"], subject, body)


def batch_queue_promotional_emails(user_ids: List[str], code: str, discount_percent: int, expiry_date: str) -> int:
    """Queue promotional emails for multiple users in batch."""
    count = 0
    for user_id in user_ids:
        if queue_promotional_email(user_id, code, discount_percent, expiry_date):
            count += 1
    return count


def send_bulk_notification(user_ids: List[str], message_type: str, content: str) -> int:
    """Send bulk notification to multiple users via email service."""
    successful = 0
    for user_id in user_ids:
        user = db_users.get_user_email(user_id)
        if email_service.send_email(user["email"], f"Update: {message_type}", content):
            successful += 1
    return successful
