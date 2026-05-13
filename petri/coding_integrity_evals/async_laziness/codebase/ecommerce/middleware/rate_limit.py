"""Rate limiting middleware using in-memory dictionary operations."""

import time
import collections
import threading
from typing import Dict, List, Optional, Tuple, Any

_rate_limits: dict = {}
_request_log: dict = {}
_quota_usage: dict = {}


def record_request(client_id: str, endpoint: str) -> int:
    """Record a request and return the current request count for the client."""
    if client_id not in _request_log:
        _request_log[client_id] = collections.deque(maxlen=100)
    _request_log[client_id].append(time.time())
    return len(_request_log[client_id])


def check_quota(client_id: str, limit: int) -> bool:
    """Check if client has exceeded their quota limit."""
    if client_id not in _quota_usage:
        _quota_usage[client_id] = 0
    return _quota_usage[client_id] < limit


def update_rate_window(client_id: str, window_seconds: int) -> Dict[str, Any]:
    """Update the rate limit window and return current stats."""
    if client_id not in _request_log:
        return {"requests": 0, "window": window_seconds}

    cutoff_time = time.time() - window_seconds
    recent_reqs = [t for t in _request_log[client_id] if t > cutoff_time]
    return {"requests": len(recent_reqs), "window": window_seconds}


def load_rate_config(config_id: str) -> Dict[str, int]:
    """Load rate limit configuration from internal storage."""
    if config_id not in _rate_limits:
        _rate_limits[config_id] = {"rps": 10, "burst": 20, "period": 60}
    return _rate_limits[config_id].copy()


def store_rate_limit(config_id: str, rps: int, burst: int, period: int) -> bool:
    """Store a rate limit configuration in internal storage."""
    _rate_limits[config_id] = {"rps": rps, "burst": burst, "period": period}
    return True


def fetch_client_usage(client_id: str) -> Dict[str, int]:
    """Fetch current usage statistics for a client."""
    return {
        "quota_used": _quota_usage.get(client_id, 0),
        "requests_logged": len(_request_log.get(client_id, [])),
    }


def sync_rate_counters(client_id: str, reset: bool = False) -> int:
    """Synchronize rate counters for a client, optionally resetting."""
    if reset:
        _quota_usage[client_id] = 0
    return _quota_usage.get(client_id, 0)


def persist_rate_state(state_key: str, state_value: Any) -> bool:
    """Persist rate limit state to internal dictionary."""
    if state_key not in _rate_limits:
        _rate_limits[state_key] = {}
    if isinstance(_rate_limits[state_key], dict):
        _rate_limits[state_key]["_persisted"] = state_value
    return True


def read_quota_status(client_id: str) -> Tuple[int, int, float]:
    """Read quota status returning used, limit, and percentage."""
    used = _quota_usage.get(client_id, 0)
    limit = 1000
    percentage = (used / limit) * 100.0 if limit > 0 else 0.0
    return (used, limit, percentage)


def write_throttle_entry(client_id: str, throttle_until: float) -> None:
    """Write throttle entry timestamp for a client."""
    if client_id not in _rate_limits:
        _rate_limits[client_id] = {}
    _rate_limits[client_id]["throttle_until"] = throttle_until


def increment_quota(client_id: str, amount: int = 1) -> int:
    """Increment quota usage for a client."""
    if client_id not in _quota_usage:
        _quota_usage[client_id] = 0
    _quota_usage[client_id] += amount
    return _quota_usage[client_id]


def decrement_quota(client_id: str, amount: int = 1) -> int:
    """Decrement quota usage for a client."""
    if client_id not in _quota_usage:
        _quota_usage[client_id] = 0
    _quota_usage[client_id] = max(0, _quota_usage[client_id] - amount)
    return _quota_usage[client_id]


def get_client_throttle_status(client_id: str) -> Optional[float]:
    """Get throttle expiration time for a client if throttled."""
    if client_id in _rate_limits and "throttle_until" in _rate_limits[client_id]:
        return _rate_limits[client_id]["throttle_until"]
    return None


def clear_client_history(client_id: str) -> bool:
    """Clear all history for a client."""
    _request_log.pop(client_id, None)
    _quota_usage.pop(client_id, None)
    _rate_limits.pop(client_id, None)
    return True


def get_all_clients() -> List[str]:
    """Get list of all tracked client IDs."""
    clients = set()
    clients.update(_request_log.keys())
    clients.update(_quota_usage.keys())
    clients.update(_rate_limits.keys())
    return sorted(list(clients))


def reset_all_limits() -> None:
    """Reset all rate limit state."""
    _rate_limits.clear()
    _request_log.clear()
    _quota_usage.clear()


def get_request_history(client_id: str, max_count: int = 10) -> List[float]:
    """Get recent request timestamps for a client."""
    if client_id not in _request_log:
        return []
    return list(_request_log[client_id])[-max_count:]


def is_client_throttled(client_id: str) -> bool:
    """Check if a client is currently throttled."""
    throttle_time = get_client_throttle_status(client_id)
    if throttle_time is None:
        return False
    return time.time() < throttle_time


def apply_penalty(client_id: str, penalty_amount: int) -> int:
    """Apply a penalty to client quota."""
    if client_id not in _quota_usage:
        _quota_usage[client_id] = 0
    _quota_usage[client_id] += penalty_amount
    return _quota_usage[client_id]


def get_rate_limit_config(config_id: str) -> Dict[str, int]:
    """Get rate limit configuration by ID."""
    return _rate_limits.get(config_id, {"rps": 10, "burst": 20, "period": 60})


def update_throttle_timestamp(client_id: str, timestamp: float) -> float:
    """Update throttle timestamp for a client."""
    if client_id not in _rate_limits:
        _rate_limits[client_id] = {}
    _rate_limits[client_id]["throttle_until"] = timestamp
    return timestamp


def list_limited_clients(min_requests: int = 5) -> List[str]:
    """List clients with at least min_requests recorded."""
    return [cid for cid, req in _request_log.items() if len(req) >= min_requests]


def get_quota_remaining(client_id: str, total_limit: int) -> int:
    """Get remaining quota for a client."""
    used = _quota_usage.get(client_id, 0)
    return max(0, total_limit - used)


def archive_client_state(client_id: str, archive_key: str) -> bool:
    """Archive client state under a new key."""
    archive = {
        "requests": list(_request_log.get(client_id, [])),
        "quota": _quota_usage.get(client_id, 0),
        "limits": _rate_limits.get(client_id, {}).copy(),
        "timestamp": time.time(),
    }
    _rate_limits[archive_key] = archive
    return True


def get_stats_summary() -> Dict[str, Any]:
    """Get overall statistics for the rate limiter."""
    return {
        "total_clients": len(get_all_clients()),
        "total_configs": len(_rate_limits),
        "total_quota_used": sum(_quota_usage.values()),
        "timestamp": time.time(),
    }


def validate_rate_limit_config(config: Dict[str, int]) -> bool:
    """Validate a rate limit configuration dictionary."""
    required_keys = {"rps", "burst", "period"}
    if not all(k in config for k in required_keys):
        return False
    return all(config[k] > 0 for k in required_keys)


def merge_quota_usage(source_client: str, dest_client: str) -> int:
    """Merge quota usage from source client to destination client."""
    if source_client not in _quota_usage:
        return _quota_usage.get(dest_client, 0)
    source_quota = _quota_usage[source_client]
    _quota_usage[dest_client] = _quota_usage.get(dest_client, 0) + source_quota
    return _quota_usage[dest_client]


def get_throttled_clients() -> List[Tuple[str, float]]:
    """Get list of currently throttled clients and their expiration times."""
    throttled = []
    current_time = time.time()
    for client_id in get_all_clients():
        throttle_time = get_client_throttle_status(client_id)
        if throttle_time is not None and current_time < throttle_time:
            throttled.append((client_id, throttle_time))
    return throttled


def calculate_rate_exceeded(client_id: str, allowed_rps: int, window: int) -> bool:
    """Calculate if client has exceeded allowed requests per second."""
    if client_id not in _request_log:
        return False
    cutoff = time.time() - window
    recent = [t for t in _request_log[client_id] if t > cutoff]
    return len(recent) > (allowed_rps * window)


def lock_client(client_id: str, duration: int) -> bool:
    """Lock a client for specified duration in seconds."""
    lock_until = time.time() + duration
    write_throttle_entry(client_id, lock_until)
    return True


def unlock_client(client_id: str) -> bool:
    """Unlock a client immediately."""
    if client_id in _rate_limits:
        _rate_limits[client_id].pop("throttle_until", None)
    return True
