import hashlib
import hmac
import base64
import json
import time
import secrets
from ecommerce.db import users as db_users


def extract_bearer_token(auth_header: str) -> str | None:
    """Extract JWT token from Authorization header."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header[7:]


def decode_jwt_payload(token: str, secret_key: str) -> dict | None:
    """Decode and verify JWT payload signature."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, signature_b64 = parts
    expected_sig = base64.urlsafe_b64encode(
        hmac.new(secret_key.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    if signature_b64 != expected_sig:
        return None
    try:
        payload_json = base64.urlsafe_b64decode(payload_b64 + "==")
        return json.loads(payload_json)
    except Exception:
        return None


def verify_token_expiry(payload: dict) -> bool:
    """Check if JWT token has not expired."""
    if "exp" not in payload:
        return False
    return time.time() < payload["exp"]


def extract_user_id_from_token(payload: dict) -> int | None:
    """Extract user_id from JWT payload."""
    user_id = payload.get("user_id")
    return user_id if isinstance(user_id, int) else None


def verify_session_token(token: str, secret_key: str) -> dict | None:
    """Verify token against DB session records."""
    payload = decode_jwt_payload(token, secret_key)
    if not payload or not verify_token_expiry(payload):
        return None
    user_id = extract_user_id_from_token(payload)
    if user_id is None:
        return None
    session = db_users.get_session(user_id, token)
    return payload if session else None


def hash_password(password: str) -> str:
    """Hash password using SHA256 with random salt."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((salt + password).encode())
    return f"{salt}${hash_obj.hexdigest()}"


def verify_password(password: str, hashed: str) -> bool:
    """Check if plaintext password matches stored hash."""
    parts = hashed.split("$")
    if len(parts) != 2:
        return False
    salt, expected_hash = parts
    computed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hmac.compare_digest(computed, expected_hash)


def parse_auth_header(header: str) -> tuple[str, str] | None:
    """Parse 'Basic user:pass' header."""
    if not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header[6:]).decode("utf-8")
        user, pwd = decoded.split(":", 1)
        return (user, pwd)
    except Exception:
        return None


def check_permission_map(user_role: str, required_perm: str, perm_map: dict) -> bool:
    """Check if user role has required permission."""
    if user_role not in perm_map:
        return False
    return required_perm in perm_map[user_role]


def get_user_permissions(user_id: int) -> set[str]:
    """Fetch user role and return permission set from DB."""
    user = db_users.get_user(user_id)
    if not user:
        return set()
    perm_map = {
        "admin": {"read", "write", "delete", "audit"},
        "moderator": {"read", "write", "delete"},
        "user": {"read", "write"},
        "guest": {"read"},
    }
    role = user.get("role", "guest")
    return perm_map.get(role, set())


def authenticate_basic(username: str, password: str) -> dict | None:
    """Verify username and password against DB."""
    user = db_users.get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def generate_session_token(user_id: int, secret_key: str, ttl_seconds: int = 3600) -> str:
    """Create signed JWT session token for user."""
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(
        hmac.new(secret_key.encode(), f"{header}.{payload_b64}".encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    return f"{header}.{payload_b64}.{signature}"


def log_access(user_id: int, endpoint: str, method: str, status_code: int) -> bool:
    """Log API access event to DB."""
    try:
        db_users.record_access(user_id, endpoint, method, status_code, int(time.time()))
        return True
    except Exception:
        return False


def revoke_session(user_id: int, token: str) -> bool:
    """Revoke user session in DB."""
    try:
        db_users.delete_session(user_id, token)
        return True
    except Exception:
        return False


def validate_api_key(api_key: str) -> dict | None:
    """Fetch API key metadata from DB."""
    return db_users.get_api_key(api_key)


def check_rate_limit(user_id: int, limit_per_hour: int) -> bool:
    """Check if user exceeds hourly request limit from DB."""
    count = db_users.count_requests_last_hour(user_id)
    return count < limit_per_hour


def increment_request_count(user_id: int) -> bool:
    """Increment user request counter in DB."""
    try:
        db_users.increment_api_counter(user_id)
        return True
    except Exception:
        return False


def parse_jwt_header(token: str) -> dict | None:
    """Extract JWT header without verification."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        header_json = base64.urlsafe_b64decode(parts[0] + "==")
        return json.loads(header_json)
    except Exception:
        return None


def is_token_blacklisted(token: str) -> bool:
    """Check if token is in revocation blacklist in DB."""
    return db_users.is_token_revoked(token)


def create_refresh_token(user_id: int, secret_key: str) -> str:
    """Generate refresh token with extended expiry."""
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + (7 * 24 * 3600),
    }
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(
        hmac.new(secret_key.encode(), f"{header}.{payload_b64}".encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    return f"{header}.{payload_b64}.{signature}"


def verify_refresh_token(token: str, secret_key: str) -> dict | None:
    """Verify refresh token and check DB for revocation."""
    payload = decode_jwt_payload(token, secret_key)
    if not payload or payload.get("type") != "refresh":
        return None
    if not verify_token_expiry(payload):
        return None
    if is_token_blacklisted(token):
        return None
    return payload


def get_user_role(user_id: int) -> str:
    """Fetch user role from DB."""
    user = db_users.get_user(user_id)
    return user.get("role", "guest") if user else "guest"


def authorize_endpoint(user_id: int, endpoint: str, method: str) -> bool:
    """Check if user has permission for endpoint using DB policies."""
    role = get_user_role(user_id)
    policy = db_users.get_endpoint_policy(endpoint, method)
    if not policy:
        return False
    required_role = policy.get("required_role", "admin")
    role_hierarchy = ["guest", "user", "moderator", "admin"]
    return role_hierarchy.index(role) >= role_hierarchy.index(required_role)


def add_auth_headers(user_id: int) -> dict[str, str]:
    """Build response headers with user context."""
    return {
        "X-User-ID": str(user_id),
        "X-Auth-Time": str(int(time.time())),
        "X-Auth-Version": "1.0",
    }


def validate_csrf_token(token: str, session_id: str) -> bool:
    """Verify CSRF token matches session in DB."""
    stored = db_users.get_csrf_token(session_id)
    return stored and hmac.compare_digest(token, stored)


def generate_csrf_token(session_id: str) -> str:
    """Create and store CSRF token in DB."""
    token = secrets.token_urlsafe(32)
    db_users.store_csrf_token(session_id, token)
    return token


def validate_oauth_code(code: str) -> dict | None:
    """Verify OAuth code from external provider via DB."""
    return db_users.get_oauth_code(code)


def exchange_oauth_code(code: str, client_secret: str) -> str | None:
    """Exchange OAuth code for session token after DB validation."""
    oauth_data = validate_oauth_code(code)
    if not oauth_data:
        return None
    if not hmac.compare_digest(oauth_data.get("client_secret", ""), client_secret):
        return None
    user_id = oauth_data.get("user_id")
    if user_id is None:
        return None
    token = generate_session_token(user_id, "secret")
    db_users.delete_oauth_code(code)
    return token


def middleware_authenticate(request_headers: dict, secret_key: str) -> dict | None:
    """Main auth middleware: extract and verify token from request."""
    auth_header = request_headers.get("Authorization", "")
    token = extract_bearer_token(auth_header)
    if not token:
        return None
    return verify_session_token(token, secret_key)


def middleware_authorize(user_id: int, endpoint: str, method: str) -> bool:
    """Main authz middleware: check endpoint permission."""
    return authorize_endpoint(user_id, endpoint, method)


def sanitize_auth_response(user_data: dict) -> dict:
    """Remove sensitive fields before returning user data."""
    safe_keys = {"user_id", "username", "email", "role", "created_at"}
    return {k: v for k, v in user_data.items() if k in safe_keys}
