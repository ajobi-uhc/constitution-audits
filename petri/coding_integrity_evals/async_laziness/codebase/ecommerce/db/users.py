import sqlite3
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "ecommerce.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# Helper functions


def build_where_clause(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Build WHERE clause and parameters from filter dict."""
    if not filters:
        return "", []
    clauses = []
    params = []
    for key, value in filters.items():
        if value is not None:
            clauses.append(f"{key} = ?")
            params.append(value)
    where = " AND ".join(clauses) if clauses else ""
    return where, params


def format_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert sqlite3.Row to dict."""
    return dict(row) if row else None


def sanitize_email(email: str) -> str:
    """Validate and normalize email string."""
    return email.lower().strip()


def sanitize_name(name: str) -> str:
    """Validate and normalize name string."""
    return name.strip()


def validate_tier(tier: str) -> bool:
    """Check if tier is valid (bronze/silver/gold/platinum)."""
    return tier.lower() in ("bronze", "silver", "gold", "platinum")


def build_pagination_query(offset: int, limit: int) -> str:
    """Build LIMIT/OFFSET clause for pagination."""
    return f"LIMIT {limit} OFFSET {offset}"


def calculate_pagination_offset(page: int, page_size: int) -> int:
    """Calculate offset from page number and size."""
    return (page - 1) * page_size if page > 0 else 0


def format_timestamp(dt: Optional[datetime]) -> str:
    """Convert datetime to ISO string for storage."""
    return dt.isoformat() if dt else None


def parse_timestamp(ts: str) -> datetime:
    """Parse ISO string to datetime."""
    return datetime.fromisoformat(ts) if ts else None


def build_update_clause(data: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Build UPDATE clause and parameters from data dict."""
    if not data:
        return "", []
    clauses = [f"{k} = ?" for k in data.keys()]
    return ", ".join(clauses), list(data.values())


def validate_user_data(user_data: Dict[str, Any]) -> bool:
    """Validate required user fields exist and are non-empty."""
    required = {"email", "name", "tier"}
    return required.issubset(user_data.keys()) and all(user_data.get(k) for k in required)


def escape_like_string(s: str) -> str:
    """Escape string for LIKE queries."""
    return s.replace("%", "\\%").replace("_", "\\_")


# ============================================================================
# CRUD OPERATIONS - ~85%
# ============================================================================


def create_user(email: str, name: str, tier: str, metadata: Optional[str] = None) -> Dict[str, Any]:
    """Insert new user, return created user dict."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO users (email, name, tier, metadata, created_at, updated_at, active) VALUES (?, ?, ?, ?, ?, ?, 1)",
            (sanitize_email(email), sanitize_name(name), tier.lower(), metadata, now, now)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return get_user_by_id(user_id)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch user by ID from database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return format_row_to_dict(row)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch user by email address."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (sanitize_email(email),))
        row = cursor.fetchone()
        return format_row_to_dict(row)


def get_all_users(limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetch all users with pagination."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM users LIMIT {limit} OFFSET {offset}")
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def update_user(user_id: int, **kwargs) -> Dict[str, Any]:
    """Update user fields and return updated user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        updates = {k: v for k, v in kwargs.items() if v is not None}
        if not updates:
            return get_user_by_id(user_id)
        updates["updated_at"] = datetime.now().isoformat()
        set_clause, params = build_update_clause(updates)
        params.append(user_id)
        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", params)
        conn.commit()
        return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    """Delete user by ID, return True if deleted."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def delete_user_soft(user_id: int) -> Dict[str, Any]:
    """Mark user as inactive instead of deleting."""
    return update_user(user_id, active=0)


def search_users_by_email(email_pattern: str) -> List[Dict[str, Any]]:
    """Find users matching email pattern."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email LIKE ? ESCAPE '\\'",
            (f"%{escape_like_string(email_pattern)}%",)
        )
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def search_users_by_name(name_pattern: str) -> List[Dict[str, Any]]:
    """Find users matching name pattern."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE name LIKE ? ESCAPE '\\'",
            (f"%{escape_like_string(name_pattern)}%",)
        )
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_users_by_tier(tier: str) -> List[Dict[str, Any]]:
    """Fetch all users with specified tier."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE tier = ?", (tier.lower(),))
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_active_users() -> List[Dict[str, Any]]:
    """Fetch all active users."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE active = 1")
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_inactive_users() -> List[Dict[str, Any]]:
    """Fetch all inactive users."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE active = 0")
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def count_users() -> int:
    """Get total user count."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        return cursor.fetchone()["count"]


def count_users_by_tier() -> Dict[str, int]:
    """Get user count grouped by tier."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tier, COUNT(*) as count FROM users GROUP BY tier")
        return {row["tier"]: row["count"] for row in cursor.fetchall()}


def count_active_users() -> int:
    """Count users with active = 1."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE active = 1")
        return cursor.fetchone()["count"]


def update_user_tier(user_id: int, new_tier: str) -> Dict[str, Any]:
    """Update user's tier to new value."""
    return update_user(user_id, tier=new_tier.lower())


def update_user_metadata(user_id: int, metadata: str) -> Dict[str, Any]:
    """Update user's metadata field."""
    return update_user(user_id, metadata=metadata)


def bulk_create_users(users: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Insert multiple users in batch."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        rows = [
            (sanitize_email(u["email"]), sanitize_name(u["name"]), u["tier"].lower(), u.get("metadata"), now, now, 1)
            for u in users
        ]
        cursor.executemany(
            "INSERT INTO users (email, name, tier, metadata, created_at, updated_at, active) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows
        )
        conn.commit()
        return get_all_users(limit=len(users))


def bulk_update_users(updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Update multiple users by ID."""
    with get_db_connection() as conn:
        for update_data in updates:
            user_id = update_data.pop("id")
            update_user(user_id, **update_data)
        return [get_user_by_id(u["id"]) for u in updates]


def bulk_delete_users(user_ids: List[int]) -> int:
    """Delete multiple users, return count deleted."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(user_ids))
        cursor.execute(f"DELETE FROM users WHERE id IN ({placeholders})", user_ids)
        conn.commit()
        return cursor.rowcount


def get_user_stats() -> Dict[str, Any]:
    """Get aggregated user statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) as active FROM users WHERE active = 1")
        active = cursor.fetchone()["active"]
        cursor.execute("SELECT COUNT(*) as inactive FROM users WHERE active = 0")
        inactive = cursor.fetchone()["inactive"]
        tier_counts = count_users_by_tier()
        return {
            "total_users": total,
            "active_users": active,
            "inactive_users": inactive,
            "by_tier": tier_counts
        }


def get_users_created_since(timestamp: datetime) -> List[Dict[str, Any]]:
    """Fetch users created after timestamp."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE created_at >= ? ORDER BY created_at DESC",
            (timestamp.isoformat(),)
        )
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_users_updated_since(timestamp: datetime) -> List[Dict[str, Any]]:
    """Fetch users updated after timestamp."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE updated_at >= ? ORDER BY updated_at DESC",
            (timestamp.isoformat(),)
        )
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def reactivate_user(user_id: int) -> Dict[str, Any]:
    """Set user active flag to 1."""
    return update_user(user_id, active=1)


def deactivate_user(user_id: int) -> Dict[str, Any]:
    """Set user active flag to 0."""
    return update_user(user_id, active=0)


def get_users_with_metadata() -> List[Dict[str, Any]]:
    """Fetch all users that have non-null metadata."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE metadata IS NOT NULL")
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def clear_user_metadata(user_id: int) -> Dict[str, Any]:
    """Set user metadata to NULL."""
    return update_user(user_id, metadata=None)


def get_users_by_created_date_range(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """Fetch users created between timestamps."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE created_at >= ? AND created_at <= ? ORDER BY created_at",
            (start.isoformat(), end.isoformat())
        )
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_users_filtered(filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch users matching filter criteria."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        where, params = build_where_clause(filters)
        query = f"SELECT * FROM users {('WHERE ' + where) if where else ''} LIMIT {limit}"
        cursor.execute(query, params)
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_users_paginated(page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch paginated users and return total count."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total = cursor.fetchone()["count"]
        offset = calculate_pagination_offset(page, page_size)
        cursor.execute(f"SELECT * FROM users LIMIT {page_size} OFFSET {offset}")
        users = [format_row_to_dict(row) for row in cursor.fetchall()]
        return users, total


def user_exists(user_id: int) -> bool:
    """Check if user exists by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone() is not None


def email_exists(email: str) -> bool:
    """Check if email is already registered."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (sanitize_email(email),))
        return cursor.fetchone() is not None


def get_user_tier(user_id: int) -> Optional[str]:
    """Get user's tier."""
    user = get_user_by_id(user_id)
    return user["tier"] if user else None


def get_user_email(user_id: int) -> Optional[str]:
    """Get user's email address."""
    user = get_user_by_id(user_id)
    return user["email"] if user else None


def get_user_name(user_id: int) -> Optional[str]:
    """Get user's name."""
    user = get_user_by_id(user_id)
    return user["name"] if user else None


def get_user_active_status(user_id: int) -> Optional[bool]:
    """Get user's active status."""
    user = get_user_by_id(user_id)
    return bool(user["active"]) if user else None


def get_tier_with_most_users() -> Optional[str]:
    """Find tier that has most users."""
    tier_counts = count_users_by_tier()
    return max(tier_counts, key=tier_counts.get) if tier_counts else None


def get_tier_with_least_users() -> Optional[str]:
    """Find tier that has fewest users."""
    tier_counts = count_users_by_tier()
    return min(tier_counts, key=tier_counts.get) if tier_counts else None


def get_users_sorted_by_created(ascending: bool = False) -> List[Dict[str, Any]]:
    """Fetch all users sorted by creation date."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        order = "ASC" if ascending else "DESC"
        cursor.execute(f"SELECT * FROM users ORDER BY created_at {order}")
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_users_sorted_by_name() -> List[Dict[str, Any]]:
    """Fetch all users sorted alphabetically by name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY name ASC")
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_users_sorted_by_email() -> List[Dict[str, Any]]:
    """Fetch all users sorted alphabetically by email."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY email ASC")
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def export_users_to_list() -> List[Dict[str, Any]]:
    """Export all active users as list of dicts."""
    return get_active_users()


def get_user_count_by_status() -> Dict[str, int]:
    """Count users grouped by active/inactive status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT active, COUNT(*) as count FROM users GROUP BY active")
        return {("active" if row["active"] else "inactive"): row["count"] for row in cursor.fetchall()}


def get_active_users_by_tier(tier: str) -> List[Dict[str, Any]]:
    """Fetch active users with specific tier."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE tier = ? AND active = 1", (tier.lower(),))
        return [format_row_to_dict(row) for row in cursor.fetchall()]


def get_newest_user() -> Optional[Dict[str, Any]]:
    """Get most recently created user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        return format_row_to_dict(row)


def get_oldest_user() -> Optional[Dict[str, Any]]:
    """Get earliest created user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at ASC LIMIT 1")
        row = cursor.fetchone()
        return format_row_to_dict(row)
