import requests
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any


# ============================================================================
# SENDGRID-LIKE EMAIL SERVICE
# ============================================================================

def send_transactional_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    from_email: str = "noreply@example.com",
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a single transactional email via SendGrid API."""
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }
    if reply_to:
        payload["reply_to"] = {"email": reply_to}

    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=payload,
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"status_code": resp.status_code, "message_id": resp.headers.get("X-Message-ID")}


def send_bulk_marketing_emails(
    recipient_list: List[Dict[str, str]],
    campaign_id: str,
    template_id: str,
    sender_name: str = "Marketing Team",
) -> Dict[str, Any]:
    """Send marketing campaign emails to multiple recipients via batch endpoint."""
    personalizations = [
        {
            "to": [{"email": r["email"]}],
            "dynamic_template_data": r.get("data", {}),
        }
        for r in recipient_list
    ]

    payload = {
        "personalizations": personalizations,
        "from": {"email": "marketing@example.com", "name": sender_name},
        "template_id": template_id,
        "custom_args": {"campaign_id": campaign_id},
    }

    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=payload,
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=30,
    )
    return {"batch_status": "queued", "recipient_count": len(recipient_list), "code": resp.status_code}


def render_email_template(
    template_name: str,
    context: Dict[str, Any],
) -> str:
    """Render an HTML email template with context variables."""
    templates = {
        "welcome": "<h1>Welcome {name}!</h1><p>Thanks for joining us.</p>",
        "order_confirmation": "<h2>Order #{order_id}</h2><p>Total: ${total}</p>",
        "password_reset": '<a href="{reset_link}">Reset Password</a>',
        "promotion": "<h2>{promo_title}</h2><p>{promo_body}</p>",
    }

    template_html = templates.get(template_name, "")
    for key, value in context.items():
        template_html = template_html.replace(f"{{{key}}}", str(value))
    return template_html


def validate_email_address(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def format_email_subject(
    template: str,
    variables: Dict[str, str],
) -> str:
    """Format an email subject line with variables."""
    subject = template
    for key, value in variables.items():
        subject = subject.replace(f"{{{key}}}", value)
    return subject[:78]  # Enforce 78-char limit


def convert_html_to_plaintext(html_content: str) -> str:
    """Convert HTML email to plain text."""
    text = re.sub(r"<[^>]+>", "", html_content)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def verify_email_ownership(
    email: str,
    verification_token: str,
    user_id: str,
) -> Dict[str, Any]:
    """Verify email ownership by checking verification link clicked in API."""
    resp = requests.post(
        "https://api.sendgrid.com/v3/verified_senders",
        json={"email": email, "verification_token": verification_token, "user_id": user_id},
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"verified": resp.status_code == 200, "timestamp": datetime.now().isoformat()}


def send_verification_email(
    email: str,
    verification_link: str,
) -> Dict[str, Any]:
    """Send email verification link to user."""
    html_body = f'<a href="{verification_link}">Verify Email</a>'
    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json={
            "personalizations": [{"to": [{"email": email}]}],
            "from": {"email": "verify@example.com"},
            "subject": "Verify Your Email",
            "content": [{"type": "text/html", "value": html_body}],
        },
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"sent": resp.status_code == 202, "email": email}


def process_bounce_event(
    event_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Process an email bounce webhook event from SendGrid."""
    bounce_type = event_data.get("event", "unknown")
    email = event_data.get("email", "")
    reason = event_data.get("reason", "")

    resp = requests.post(
        "https://api.example.com/bounces",
        json={"email": email, "bounce_type": bounce_type, "reason": reason},
        timeout=5,
    )
    return {"processed": resp.status_code == 200, "email": email}


def handle_unsubscribe_request(
    email: str,
    unsubscribe_group_id: int,
) -> Dict[str, Any]:
    """Mark email as unsubscribed from a mailing list."""
    resp = requests.post(
        "https://api.sendgrid.com/v3/asm/groups/{}/suppressions".format(unsubscribe_group_id),
        json={"emails": [email]},
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"unsubscribed": resp.status_code == 201, "email": email}


def log_email_analytics(
    message_id: str,
    event_type: str,
    timestamp: str,
    recipient_email: str,
) -> Dict[str, Any]:
    """Log email event to analytics backend."""
    resp = requests.post(
        "https://api.example.com/email-analytics",
        json={
            "message_id": message_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "recipient": recipient_email,
        },
        timeout=5,
    )
    return {"logged": resp.status_code == 200}


def get_email_template_by_id(template_id: str) -> Dict[str, Any]:
    """Retrieve email template metadata from SendGrid."""
    resp = requests.get(
        f"https://api.sendgrid.com/v3/templates/{template_id}",
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {}


def list_all_templates() -> List[Dict[str, str]]:
    """Fetch all email templates available in SendGrid."""
    resp = requests.get(
        "https://api.sendgrid.com/v3/templates?generations=dynamic",
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    templates = resp.json().get("templates", []) if resp.status_code == 200 else []
    return [{"id": t.get("id"), "name": t.get("name")} for t in templates]


def create_dynamic_template(
    name: str,
    subject: str,
    html_template: str,
) -> Dict[str, Any]:
    """Create a new dynamic email template in SendGrid."""
    resp = requests.post(
        "https://api.sendgrid.com/v3/templates",
        json={"name": name, "generation": "dynamic"},
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    if resp.status_code == 201:
        template_id = resp.json().get("id")
        resp2 = requests.post(
            f"https://api.sendgrid.com/v3/templates/{template_id}/versions",
            json={"subject": subject, "html_content": html_template, "active": 1},
            headers={"Authorization": "Bearer SENDGRID_API_KEY"},
            timeout=10,
        )
        return {"created": True, "template_id": template_id, "version_status": resp2.status_code}
    return {"created": False}


def send_email_with_attachment(
    to_email: str,
    subject: str,
    html_body: str,
    attachment_base64: str,
    filename: str,
) -> Dict[str, Any]:
    """Send email with a file attachment encoded in base64."""
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": "noreply@example.com"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}],
        "attachments": [{"content": attachment_base64, "filename": filename, "type": "application/octet-stream"}],
    }

    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=payload,
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"sent": resp.status_code == 202, "filename": filename}


def get_bounce_list() -> List[Dict[str, Any]]:
    """Retrieve list of bounced email addresses from SendGrid."""
    resp = requests.get(
        "https://api.sendgrid.com/v3/suppression/bounces",
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return resp.json().get("results", []) if resp.status_code == 200 else []


def get_invalid_emails() -> List[Dict[str, Any]]:
    """Fetch invalid email addresses from suppression list."""
    resp = requests.get(
        "https://api.sendgrid.com/v3/suppression/invalid_emails",
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return resp.json().get("results", []) if resp.status_code == 200 else []


def delete_bounce_record(email: str) -> Dict[str, Any]:
    """Remove an email from bounce suppression list."""
    resp = requests.delete(
        "https://api.sendgrid.com/v3/suppression/bounces",
        json={"emails": [email]},
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"deleted": resp.status_code == 204}


def send_transactional_sms(
    phone_number: str,
    message: str,
) -> Dict[str, Any]:
    """Send transactional SMS via Twilio-like API."""
    resp = requests.post(
        "https://api.twilio.com/2010-04-01/Accounts/ACCOUNT_SID/Messages.json",
        data={"From": "+1234567890", "To": phone_number, "Body": message},
        auth=("ACCOUNT_SID", "AUTH_TOKEN"),
        timeout=10,
    )
    return {"sent": resp.status_code == 201, "phone": phone_number}


def get_email_stats_by_date(
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """Fetch email statistics (opens, clicks, sends) for date range."""
    resp = requests.get(
        "https://api.sendgrid.com/v3/stats",
        params={
            "start_date": start_date,
            "end_date": end_date,
            "aggregated_by": "day",
        },
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=15,
    )
    return resp.json() if resp.status_code == 200 else {}


def get_email_stats_by_campaign(campaign_id: str) -> Dict[str, Any]:
    """Fetch statistics for a specific marketing campaign."""
    resp = requests.get(
        "https://api.sendgrid.com/v3/stats",
        params={"custom_args_campaign_id": campaign_id},
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {}


def validate_sender_email(email: str) -> bool:
    """Validate email format."""
    if not validate_email_address(email):
        return False
    banned_domains = ["gmail.com", "yahoo.com", "hotmail.com"]
    domain = email.split("@")[1]
    return domain not in banned_domains


def build_html_email_body(
    header_text: str,
    body_text: str,
    footer_text: str,
    brand_color: str = "#0066cc",
) -> str:
    """Build HTML email structure with header, body, footer."""
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: {brand_color}; padding: 20px; color: white;">
                <h1>{header_text}</h1>
            </div>
            <div style="padding: 20px;">
                <p>{body_text}</p>
            </div>
            <div style="background-color: #f5f5f5; padding: 10px; text-align: center;">
                <p style="font-size: 12px;">{footer_text}</p>
            </div>
        </body>
    </html>
    """
    return html.strip()


def send_password_reset_email(
    email: str,
    reset_link: str,
    expiry_hours: int = 24,
) -> Dict[str, Any]:
    """Send password reset email with expiration warning."""
    html_body = render_email_template(
        "password_reset",
        {"reset_link": reset_link, "expiry_hours": expiry_hours},
    )
    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json={
            "personalizations": [{"to": [{"email": email}]}],
            "from": {"email": "security@example.com"},
            "subject": "Reset Your Password",
            "content": [{"type": "text/html", "value": html_body}],
        },
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"sent": resp.status_code == 202}


def send_order_confirmation(
    email: str,
    order_id: str,
    total_amount: float,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Send order confirmation email with itemized details."""
    items_html = "".join([
        f"<li>{item['name']} x{item['quantity']} = ${item['price']}</li>"
        for item in items
    ])
    html_body = f"""
    <h2>Order Confirmation #{order_id}</h2>
    <ul>{items_html}</ul>
    <p><strong>Total: ${total_amount:.2f}</strong></p>
    """

    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json={
            "personalizations": [{"to": [{"email": email}]}],
            "from": {"email": "orders@example.com"},
            "subject": f"Order Confirmation #{order_id}",
            "content": [{"type": "text/html", "value": html_body}],
        },
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"sent": resp.status_code == 202, "order_id": order_id}


def schedule_email_send(
    email: str,
    subject: str,
    html_body: str,
    send_at_timestamp: int,
) -> Dict[str, Any]:
    """Schedule an email to be sent at future time."""
    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json={
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "send_at": send_at_timestamp,
                }
            ],
            "from": {"email": "noreply@example.com"},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        },
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"scheduled": resp.status_code == 202}


def get_email_delivery_status(message_id: str) -> Dict[str, Any]:
    """Check delivery status of a specific email message."""
    resp = requests.get(
        "https://api.sendgrid.com/v3/messages",
        params={"query": f"msg_id={message_id}"},
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    messages = resp.json().get("messages", []) if resp.status_code == 200 else []
    return messages[0] if messages else {}


def batch_verify_emails(email_list: List[str]) -> Dict[str, Any]:
    """Verify multiple email addresses in batch."""
    resp = requests.post(
        "https://api.example.com/email-verify/batch",
        json={"emails": email_list},
        timeout=30,
    )
    return resp.json() if resp.status_code == 200 else {"verified": [], "invalid": email_list}


def get_email_engagement_metrics(email: str) -> Dict[str, Any]:
    """Fetch engagement metrics (opens, clicks) for a recipient."""
    resp = requests.get(
        "https://api.sendgrid.com/v3/suppression/bounce_classifications",
        params={"email": email},
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {}


def update_contact_preferences(
    email: str,
    preferences: Dict[str, bool],
) -> Dict[str, Any]:
    """Update email preferences for a contact (opt-in/opt-out)."""
    resp = requests.patch(
        "https://api.sendgrid.com/v3/marketing/contacts",
        json={"email": email, "custom_fields": preferences},
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    return {"updated": resp.status_code == 200}


def check_email_domain_reputation(domain: str) -> Dict[str, Any]:
    """Check domain reputation score for email deliverability."""
    resp = requests.get(
        "https://api.sendgrid.com/v3/mail_settings/domain_whitelabel",
        headers={"Authorization": "Bearer SENDGRID_API_KEY"},
        timeout=10,
    )
    domain_data = resp.json() if resp.status_code == 200 else {}
    return {"domain": domain, "valid": domain_data.get("valid", False)}


def parse_email_recipient_string(recipient_string: str) -> Tuple[str, str]:
    """Parse email recipient string into name and email."""
    if "<" in recipient_string and ">" in recipient_string:
        name = recipient_string.split("<")[0].strip()
        email = recipient_string.split("<")[1].split(">")[0].strip()
        return (name, email)
    return ("", recipient_string.strip())


def sanitize_email_content(html_content: str) -> str:
    """Remove potentially dangerous HTML tags from email content."""
    dangerous_tags = ["script", "iframe", "style", "embed"]
    result = html_content
    for tag in dangerous_tags:
        result = re.sub(f"<{tag}[^>]*>.*?</{tag}>", "", result, flags=re.IGNORECASE | re.DOTALL)
    return result.strip()
