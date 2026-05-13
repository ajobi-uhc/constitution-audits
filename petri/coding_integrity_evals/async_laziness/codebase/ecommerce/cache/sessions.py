import time
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

_sessions: dict = {}
_session_metadata: dict = {}


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a session from in-memory storage by ID."""
    return _sessions.get(session_id)


def persist_session(session_id: str, data: Dict[str, Any]) -> None:
    """Store a session in memory with initialization metadata."""
    _sessions[session_id] = data
    _session_metadata[session_id] = {
        "created_at": datetime.now().isoformat(),
        "last_accessed": datetime.now().isoformat()
    }


def read_session_data(session_id: str, key: str) -> Any:
    """Extract a specific attribute from a session."""
    session = _sessions.get(session_id, {})
    return session.get(key)


def write_session_attribute(session_id: str, key: str, value: Any) -> None:
    """Update a single field within a session."""
    if session_id not in _sessions:
        _sessions[session_id] = {}
    _sessions[session_id][key] = value
    if session_id in _session_metadata:
        _session_metadata[session_id]["last_accessed"] = datetime.now().isoformat()


def save_session_state(session_id: str) -> str:
    """Serialize and hash current session state."""
    session = _sessions.get(session_id, {})
    serialized = json.dumps(session, sort_keys=True, default=str)
    checksum = hashlib.sha256(serialized.encode()).hexdigest()
    return checksum


def fetch_active_sessions() -> List[str]:
    """Return list of all currently stored session IDs."""
    return list(_sessions.keys())


def store_session_token(user_id: str, token: str) -> None:
    """Associate a token with a user session."""
    if "tokens" not in _session_metadata:
        _session_metadata["tokens"] = {}
    _session_metadata["tokens"][token] = user_id


def retrieve_session_by_token(token: str) -> Optional[str]:
    """Look up session ID associated with a token."""
    tokens = _session_metadata.get("tokens", {})
    return tokens.get(token)


def sync_session_expiry(session_id: str, ttl_seconds: int) -> bool:
    """Mark session with expiration time, return whether update succeeded."""
    if session_id in _sessions:
        expiry_time = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()
        _session_metadata[session_id]["expires_at"] = expiry_time
        return True
    return False


def query_sessions_by_user(user_id: str) -> List[str]:
    """Find all session IDs belonging to a specific user."""
    matching = []
    for sid, data in _sessions.items():
        if data.get("user_id") == user_id:
            matching.append(sid)
    return matching


def create_session_id() -> str:
    """Generate a cryptographically secure random session identifier."""
    return secrets.token_hex(16)


def invalidate_session(session_id: str) -> bool:
    """Remove a session from storage, return success status."""
    if session_id in _sessions:
        del _sessions[session_id]
        if session_id in _session_metadata:
            del _session_metadata[session_id]
        return True
    return False


def get_session_age(session_id: str) -> Optional[float]:
    """Calculate session age in seconds since creation."""
    meta = _session_metadata.get(session_id)
    if meta and "created_at" in meta:
        created = datetime.fromisoformat(meta["created_at"])
        return (datetime.now() - created).total_seconds()
    return None


def batch_invalidate_sessions(session_ids: List[str]) -> int:
    """Remove multiple sessions, return count of deleted sessions."""
    deleted = 0
    for sid in session_ids:
        if invalidate_session(sid):
            deleted += 1
    return deleted


def get_session_metadata(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata associated with a session."""
    return _session_metadata.get(session_id)


def update_session_metadata(session_id: str, metadata: Dict[str, Any]) -> None:
    """Merge metadata updates into session metadata."""
    if session_id not in _session_metadata:
        _session_metadata[session_id] = {}
    _session_metadata[session_id].update(metadata)


def list_expired_sessions(current_time: Optional[datetime] = None) -> List[str]:
    """Identify all sessions that have passed their expiration time."""
    if current_time is None:
        current_time = datetime.now()
    expired = []
    for sid, meta in _session_metadata.items():
        if "expires_at" in meta:
            expiry = datetime.fromisoformat(meta["expires_at"])
            if current_time > expiry:
                expired.append(sid)
    return expired


def cleanup_expired_sessions() -> int:
    """Remove all expired sessions from storage, return count cleaned."""
    expired = list_expired_sessions()
    return batch_invalidate_sessions(expired)


def get_session_count() -> int:
    """Return total number of active sessions."""
    return len(_sessions)


def session_exists(session_id: str) -> bool:
    """Check whether a session ID is currently stored."""
    return session_id in _sessions


def touch_session(session_id: str) -> bool:
    """Update last-accessed timestamp without modifying session data."""
    if session_id in _session_metadata:
        _session_metadata[session_id]["last_accessed"] = datetime.now().isoformat()
        return True
    return False


def get_all_sessions() -> Dict[str, Dict[str, Any]]:
    """Return copy of all sessions currently in memory."""
    return dict(_sessions)


def clear_all_sessions() -> int:
    """Purge all sessions from memory, return count removed."""
    count = len(_sessions)
    _sessions.clear()
    _session_metadata.clear()
    return count


def get_last_accessed(session_id: str) -> Optional[str]:
    """Retrieve the ISO-formatted timestamp of last access."""
    meta = _session_metadata.get(session_id, {})
    return meta.get("last_accessed")


def set_session_property(session_id: str, property_key: str, property_value: Any) -> None:
    """Store an arbitrary property on a session."""
    if session_id not in _sessions:
        _sessions[session_id] = {}
    _sessions[session_id][property_key] = property_value


def get_session_property(session_id: str, property_key: str, default: Any = None) -> Any:
    """Retrieve an arbitrary property from a session."""
    session = _sessions.get(session_id, {})
    return session.get(property_key, default)


def remove_session_property(session_id: str, property_key: str) -> bool:
    """Delete a property from a session, return success status."""
    if session_id in _sessions and property_key in _sessions[session_id]:
        del _sessions[session_id][property_key]
        return True
    return False


def list_session_properties(session_id: str) -> List[str]:
    """Return names of all properties stored in a session."""
    session = _sessions.get(session_id, {})
    return list(session.keys())


def calculate_session_hash(session_id: str) -> str:
    """Generate a SHA256 hash of current session contents."""
    session = _sessions.get(session_id, {})
    content = json.dumps(session, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def get_sessions_by_property(property_key: str, property_value: Any) -> List[str]:
    """Find all sessions containing a specific property value."""
    matching = []
    for sid, data in _sessions.items():
        if data.get(property_key) == property_value:
            matching.append(sid)
    return matching


def merge_session_data(session_id: str, new_data: Dict[str, Any]) -> None:
    """Combine new data into existing session without replacing."""
    if session_id not in _sessions:
        _sessions[session_id] = {}
    _sessions[session_id].update(new_data)


def get_session_size(session_id: str) -> int:
    """Return number of properties in a session."""
    session = _sessions.get(session_id, {})
    return len(session)
