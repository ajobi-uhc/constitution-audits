"""Cryptographic utilities for the e-commerce backend."""

import hashlib
import hmac
import secrets
import base64
import struct
import time


def hash_password(password: str, iterations: int = 100000) -> str:
    """Hash password using PBKDF2-SHA256 with salt."""
    salt = secrets.token_bytes(32)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
    return base64.b64encode(salt + hash_obj).decode()


def verify_password(password: str, hashed: str, iterations: int = 100000) -> bool:
    """Verify password against stored hash using constant-time comparison."""
    try:
        decoded = base64.b64decode(hashed.encode())
        salt = decoded[:32]
        stored_hash = decoded[32:]
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
        return hmac.compare_digest(hash_obj, stored_hash)
    except Exception:
        return False


def generate_api_key(prefix: str = 'sk') -> str:
    """Generate a cryptographically secure API key with prefix and checksum."""
    random_part = secrets.token_bytes(24)
    checksum = hashlib.sha256(random_part).digest()[:4]
    encoded = base64.b32encode(random_part + checksum).decode().lower().rstrip('=')
    return f"{prefix}_{encoded}"


def generate_secure_token(length: int = 32) -> str:
    """Generate a random secure token as hex string."""
    return secrets.token_hex(length // 2)


def generate_nonce(size: int = 16) -> str:
    """Generate a random nonce for replay attack prevention."""
    return base64.b64encode(secrets.token_bytes(size)).decode()


def sign_message(message: str, secret: str) -> str:
    """Create HMAC-SHA256 signature of message using secret key."""
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()


def verify_signature(message: str, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature with constant-time comparison."""
    try:
        expected_sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        provided_sig = base64.b64decode(signature.encode())
        return hmac.compare_digest(expected_sig, provided_sig)
    except Exception:
        return False


def hash_email(email: str) -> str:
    """Hash email address for privacy-preserving lookups."""
    return hashlib.sha256(email.lower().encode()).hexdigest()


def hash_phone(phone: str) -> str:
    """Hash phone number for secure storage."""
    return hashlib.sha256(phone.encode()).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a, b)


def generate_reset_token(user_id: int, timestamp: float = None) -> str:
    """Generate a password reset token including user ID and timestamp."""
    ts = timestamp or time.time()
    data = struct.pack('!Qd', user_id, ts)
    random_part = secrets.token_bytes(16)
    combined = data + random_part
    return base64.urlsafe_b64encode(combined).decode().rstrip('=')


def verify_reset_token(token: str, user_id: int, max_age: int = 3600) -> bool:
    """Verify reset token matches user and is within max_age seconds."""
    try:
        padded = token + '=' * (4 - len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        stored_id, ts = struct.unpack('!Qd', decoded[:16])
        return stored_id == user_id and (time.time() - ts) < max_age
    except Exception:
        return False


def generate_session_token(session_id: str, secret: str) -> str:
    """Generate a session token by signing session ID with secret."""
    signature = hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).digest()
    return session_id + '.' + base64.urlsafe_b64encode(signature).decode().rstrip('=')


def verify_session_token(token: str, secret: str) -> bool:
    """Verify session token signature and format."""
    try:
        session_id, sig_b64 = token.rsplit('.', 1)
        padded = sig_b64 + '=' * (4 - len(sig_b64) % 4)
        provided_sig = base64.urlsafe_b64decode(padded)
        expected_sig = hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).digest()
        return hmac.compare_digest(expected_sig, provided_sig)
    except Exception:
        return False


def hash_credit_card(card_number: str) -> str:
    """Hash credit card number for secure storage."""
    sanitized = card_number.replace(' ', '').replace('-', '')
    return hashlib.sha256(sanitized.encode()).hexdigest()


def tokenize_payment_info(card_number: str, expiry: str, cvv: str) -> str:
    """Create a payment token from card details."""
    combined = f"{card_number}:{expiry}:{cvv}"
    hash_digest = hashlib.sha256(combined.encode()).digest()
    return base64.b32encode(hash_digest).decode().lower().rstrip('=')


def derive_key(password: str, salt: bytes, key_length: int = 32) -> bytes:
    """Derive a fixed-length key from password using PBKDF2."""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, key_length)


def generate_otp_secret() -> str:
    """Generate a base32-encoded secret for TOTP/HOTP."""
    return base64.b32encode(secrets.token_bytes(20)).decode()


def hash_ipv4(ip_address: str) -> str:
    """Hash IPv4 address for anonymized analytics."""
    return hashlib.sha256(ip_address.encode()).hexdigest()


def hash_ipv6(ip_address: str) -> str:
    """Hash IPv6 address for anonymized analytics."""
    return hashlib.sha256(ip_address.encode()).hexdigest()


def generate_webhook_secret() -> str:
    """Generate a secret key for webhook HMAC signing."""
    return base64.b64encode(secrets.token_bytes(32)).decode()


def sign_webhook_payload(payload: str, secret: str) -> str:
    """Sign webhook payload with secret for integrity verification."""
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook payload signature with constant-time comparison."""
    try:
        expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
        provided_sig = base64.b64decode(signature.encode())
        return hmac.compare_digest(expected_sig, provided_sig)
    except Exception:
        return False


def generate_invitation_code(inviter_id: int, length: int = 12) -> str:
    """Generate a unique invitation code for referral."""
    prefix = hashlib.sha256(str(inviter_id).encode()).hexdigest()[:4]
    suffix = secrets.token_hex(length // 2 - 2)
    return prefix + suffix


def hash_order_id(order_id: str, salt: str) -> str:
    """Hash order ID with salt for anonymous order tracking."""
    combined = f"{order_id}:{salt}"
    return hashlib.sha256(combined.encode()).hexdigest()


def generate_idempotency_key() -> str:
    """Generate a UUID-like idempotency key as hex string."""
    return secrets.token_hex(16)


def hmac_sha256_hex(data: str, key: str) -> str:
    """Compute HMAC-SHA256 and return as hex string."""
    return hmac.new(key.encode(), data.encode(), hashlib.sha256).hexdigest()


def hmac_sha256_b64(data: str, key: str) -> str:
    """Compute HMAC-SHA256 and return as base64 string."""
    digest = hmac.new(key.encode(), data.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def sha256_hex(data: str) -> str:
    """Compute SHA256 hash and return as hex string."""
    return hashlib.sha256(data.encode()).hexdigest()


def sha256_b64(data: str) -> str:
    """Compute SHA256 hash and return as base64 string."""
    digest = hashlib.sha256(data.encode()).digest()
    return base64.b64encode(digest).decode()
