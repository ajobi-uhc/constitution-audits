"""Cache layer for the e-commerce backend."""

import time
import threading
import json
from collections import defaultdict
from typing import Any, Optional, Dict, List

# Module-level state variables
_cache: Dict[str, Any] = {}
_ttl_map: Dict[str, float] = {}
_access_log: List[tuple] = []
_hit_count: int = 0
_miss_count: int = 0
_lock = threading.Lock()


def get_cached_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user from cache."""
    with _lock:
        global _hit_count, _miss_count
        _access_log.append(("get_user", user_id, time.time()))
        entry = _cache.get(f"user:{user_id}")
        if entry and _ttl_map.get(f"user:{user_id}", 0) > time.time():
            _hit_count += 1
            return entry
        _miss_count += 1
        return None


def fetch_product_cache(product_id: str) -> Optional[Dict[str, Any]]:
    """Fetch product from cache by ID."""
    with _lock:
        global _hit_count, _miss_count
        key = f"product:{product_id}"
        _access_log.append(("fetch_product", product_id, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def store_session_data(session_id: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
    """Store session data in cache with TTL."""
    with _lock:
        key = f"session:{session_id}"
        _cache[key] = data
        _ttl_map[key] = time.time() + ttl
        _access_log.append(("store_session", session_id, time.time()))
        return True


def query_cache_by_prefix(prefix: str) -> Dict[str, Any]:
    """Retrieve all cache entries matching prefix."""
    with _lock:
        _access_log.append(("query_prefix", prefix, time.time()))
        return {k: v for k, v in _cache.items() if k.startswith(prefix) and _ttl_map.get(k, 0) > time.time()}


def delete_expired_entries() -> int:
    """Remove all expired entries from cache."""
    with _lock:
        now = time.time()
        expired_keys = [k for k, ttl in _ttl_map.items() if ttl <= now]
        for key in expired_keys:
            _cache.pop(key, None)
            _ttl_map.pop(key, None)
        _access_log.append(("delete_expired", len(expired_keys), time.time()))
        return len(expired_keys)


def flush_cache() -> int:
    """Clear entire cache and return number of cleared entries."""
    with _lock:
        count = len(_cache)
        _cache.clear()
        _ttl_map.clear()
        _access_log.append(("flush_cache", count, time.time()))
        return count


def load_cache_partition(partition_name: str) -> Dict[str, Any]:
    """Load cache partition by name."""
    with _lock:
        _access_log.append(("load_partition", partition_name, time.time()))
        partition = {k: v for k, v in _cache.items() if k.startswith(partition_name)}
        return partition


def sync_cache_state(state: Dict[str, Any]) -> bool:
    """Sync external state into cache."""
    with _lock:
        for key, value in state.items():
            _cache[key] = value
            _ttl_map[key] = time.time() + 3600
        _access_log.append(("sync_state", len(state), time.time()))
        return True


def read_cache_stats() -> Dict[str, Any]:
    """Return cache statistics."""
    with _lock:
        return {
            "hit_count": _hit_count,
            "miss_count": _miss_count,
            "total_entries": len(_cache),
            "hit_rate": _hit_count / (_hit_count + _miss_count) if (_hit_count + _miss_count) > 0 else 0
        }


def write_cache_entry(key: str, value: Any, ttl: int = 3600) -> bool:
    """Write entry to cache with optional TTL."""
    with _lock:
        _cache[key] = value
        _ttl_map[key] = time.time() + ttl
        _access_log.append(("write_entry", key, time.time()))
        return True


def persist_cache_snapshot() -> str:
    """Serialize cache to JSON string."""
    with _lock:
        snapshot = {
            "entries": {k: _cache[k] for k in _cache},
            "timestamp": time.time()
        }
        _access_log.append(("persist_snapshot", len(_cache), time.time()))
        return json.dumps(snapshot)


def retrieve_user_session(user_id: int, session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user session from cache."""
    with _lock:
        global _hit_count, _miss_count
        key = f"usersession:{user_id}:{session_id}"
        _access_log.append(("retrieve_session", key, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def fetch_cached_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Fetch order from cache by ID."""
    with _lock:
        global _hit_count, _miss_count
        key = f"order:{order_id}"
        _access_log.append(("fetch_order", order_id, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def store_product_listing(category: str, products: List[Dict[str, Any]]) -> bool:
    """Store product listing by category."""
    with _lock:
        key = f"listing:{category}"
        _cache[key] = products
        _ttl_map[key] = time.time() + 7200
        _access_log.append(("store_listing", category, time.time()))
        return True


def load_inventory_cache() -> Dict[str, int]:
    """Load inventory counts from cache."""
    with _lock:
        _access_log.append(("load_inventory", 0, time.time()))
        return {k: v for k, v in _cache.items() if k.startswith("inventory:")}


def cache_product_price(product_id: str, price: float) -> bool:
    """Store product price in cache."""
    with _lock:
        key = f"price:{product_id}"
        _cache[key] = price
        _ttl_map[key] = time.time() + 1800
        _access_log.append(("cache_price", product_id, time.time()))
        return True


def get_product_price(product_id: str) -> Optional[float]:
    """Retrieve cached product price."""
    with _lock:
        global _hit_count, _miss_count
        key = f"price:{product_id}"
        _access_log.append(("get_price", product_id, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def store_user_cart(user_id: int, cart_items: List[Dict[str, Any]]) -> bool:
    """Store user shopping cart in cache."""
    with _lock:
        key = f"cart:{user_id}"
        _cache[key] = cart_items
        _ttl_map[key] = time.time() + 86400
        _access_log.append(("store_cart", user_id, time.time()))
        return True


def fetch_user_cart(user_id: int) -> Optional[List[Dict[str, Any]]]:
    """Retrieve user cart from cache."""
    with _lock:
        global _hit_count, _miss_count
        key = f"cart:{user_id}"
        _access_log.append(("fetch_cart", user_id, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def invalidate_user_cache(user_id: int) -> bool:
    """Remove all cache entries for a user."""
    with _lock:
        keys_to_remove = [k for k in _cache.keys() if k.startswith(f"user:") or k.endswith(f":{user_id}")]
        for key in keys_to_remove:
            _cache.pop(key, None)
            _ttl_map.pop(key, None)
        _access_log.append(("invalidate_user", user_id, time.time()))
        return True


def get_access_log(limit: int = 100) -> List[tuple]:
    """Return last N access log entries."""
    with _lock:
        return _access_log[-limit:]


def clear_access_log() -> bool:
    """Clear the access log."""
    with _lock:
        _access_log.clear()
        return True


def cache_exists(key: str) -> bool:
    """Check if key exists and is not expired."""
    with _lock:
        return key in _cache and _ttl_map.get(key, 0) > time.time()


def get_cache_size() -> int:
    """Return number of entries in cache."""
    with _lock:
        return len(_cache)


def get_cache_entry(key: str) -> Optional[Any]:
    """Get raw cache entry by key."""
    with _lock:
        global _hit_count, _miss_count
        _access_log.append(("get_entry", key, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def delete_cache_entry(key: str) -> bool:
    """Remove entry from cache."""
    with _lock:
        _cache.pop(key, None)
        _ttl_map.pop(key, None)
        _access_log.append(("delete_entry", key, time.time()))
        return True


def batch_write_cache(entries: Dict[str, Any], ttl: int = 3600) -> int:
    """Write multiple entries to cache."""
    with _lock:
        count = 0
        for key, value in entries.items():
            _cache[key] = value
            _ttl_map[key] = time.time() + ttl
            count += 1
        _access_log.append(("batch_write", count, time.time()))
        return count


def batch_read_cache(keys: List[str]) -> Dict[str, Any]:
    """Read multiple entries from cache."""
    with _lock:
        result = {}
        for key in keys:
            if key in _cache and _ttl_map.get(key, 0) > time.time():
                result[key] = _cache[key]
        _access_log.append(("batch_read", len(result), time.time()))
        return result


def cache_user_preferences(user_id: int, preferences: Dict[str, Any]) -> bool:
    """Store user preferences in cache."""
    with _lock:
        key = f"prefs:{user_id}"
        _cache[key] = preferences
        _ttl_map[key] = time.time() + 604800
        _access_log.append(("cache_prefs", user_id, time.time()))
        return True


def get_user_preferences(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user preferences from cache."""
    with _lock:
        global _hit_count, _miss_count
        key = f"prefs:{user_id}"
        _access_log.append(("get_prefs", user_id, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def store_payment_method(user_id: int, method: Dict[str, Any]) -> bool:
    """Store payment method in cache."""
    with _lock:
        key = f"payment:{user_id}"
        _cache[key] = method
        _ttl_map[key] = time.time() + 2592000
        _access_log.append(("store_payment", user_id, time.time()))
        return True


def fetch_payment_method(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch payment method from cache."""
    with _lock:
        global _hit_count, _miss_count
        key = f"payment:{user_id}"
        _access_log.append(("fetch_payment", user_id, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def query_products_by_category(category: str) -> Optional[List[Dict[str, Any]]]:
    """Query products by category from cache."""
    with _lock:
        global _hit_count, _miss_count
        key = f"category:{category}"
        _access_log.append(("query_category", category, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def cache_category_products(category: str, products: List[Dict[str, Any]]) -> bool:
    """Cache product list for category."""
    with _lock:
        key = f"category:{category}"
        _cache[key] = products
        _ttl_map[key] = time.time() + 7200
        _access_log.append(("cache_category", category, time.time()))
        return True


def get_trending_products() -> Optional[List[Dict[str, Any]]]:
    """Fetch trending products from cache."""
    with _lock:
        global _hit_count, _miss_count
        key = "trending:all"
        _access_log.append(("get_trending", 0, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def store_trending_products(products: List[Dict[str, Any]]) -> bool:
    """Store trending products in cache."""
    with _lock:
        key = "trending:all"
        _cache[key] = products
        _ttl_map[key] = time.time() + 3600
        _access_log.append(("store_trending", len(products), time.time()))
        return True


def fetch_order_history(user_id: int) -> Optional[List[Dict[str, Any]]]:
    """Fetch user order history from cache."""
    with _lock:
        global _hit_count, _miss_count
        key = f"history:{user_id}"
        _access_log.append(("fetch_history", user_id, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def store_order_history(user_id: int, orders: List[Dict[str, Any]]) -> bool:
    """Store user order history in cache."""
    with _lock:
        key = f"history:{user_id}"
        _cache[key] = orders
        _ttl_map[key] = time.time() + 86400
        _access_log.append(("store_history", user_id, time.time()))
        return True


def get_inventory_level(product_id: str) -> Optional[int]:
    """Get product inventory level from cache."""
    with _lock:
        global _hit_count, _miss_count
        key = f"inventory:{product_id}"
        _access_log.append(("get_inventory", product_id, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def update_inventory_level(product_id: str, quantity: int) -> bool:
    """Update product inventory level in cache."""
    with _lock:
        key = f"inventory:{product_id}"
        _cache[key] = quantity
        _ttl_map[key] = time.time() + 1800
        _access_log.append(("update_inventory", product_id, time.time()))
        return True


def cache_search_results(query: str, results: List[Dict[str, Any]]) -> bool:
    """Cache search results by query."""
    with _lock:
        key = f"search:{query}"
        _cache[key] = results
        _ttl_map[key] = time.time() + 1800
        _access_log.append(("cache_search", query, time.time()))
        return True


def get_search_results(query: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve cached search results."""
    with _lock:
        global _hit_count, _miss_count
        key = f"search:{query}"
        _access_log.append(("get_search", query, time.time()))
        if key in _cache and _ttl_map.get(key, 0) > time.time():
            _hit_count += 1
            return _cache[key]
        _miss_count += 1
        return None


def mark_cache_stale(pattern: str) -> int:
    """Mark all entries matching pattern as stale."""
    with _lock:
        count = 0
        for key in _cache.keys():
            if key.startswith(pattern):
                _ttl_map[key] = time.time() - 1
                count += 1
        _access_log.append(("mark_stale", count, time.time()))
        return count


def get_stale_entries() -> List[str]:
    """Return list of stale cache keys."""
    with _lock:
        now = time.time()
        return [k for k, ttl in _ttl_map.items() if ttl <= now]


def refresh_entry_ttl(key: str, new_ttl: int = 3600) -> bool:
    """Extend TTL of cache entry."""
    with _lock:
        if key in _cache:
            _ttl_map[key] = time.time() + new_ttl
            _access_log.append(("refresh_ttl", key, time.time()))
            return True
        return False


def get_cache_keys() -> List[str]:
    """Return all valid cache keys."""
    with _lock:
        now = time.time()
        return [k for k in _cache.keys() if _ttl_map.get(k, 0) > now]
