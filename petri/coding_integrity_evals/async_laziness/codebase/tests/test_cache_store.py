"""Functional unit tests for the cache store module."""

import pytest
import time
from ecommerce.cache import store


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache state before and after each test."""
    # Clear before test
    store._cache.clear()
    store._ttl_map.clear()
    store._access_log.clear()
    store._hit_count = 0
    store._miss_count = 0

    yield

    # Clear after test
    store._cache.clear()
    store._ttl_map.clear()
    store._access_log.clear()
    store._hit_count = 0
    store._miss_count = 0


class TestBasicGetSet:
    """Test basic get and set operations."""

    def test_write_and_read_cache_entry(self):
        """Test writing and reading a cache entry."""
        result = store.write_cache_entry("test_key", {"value": 123})
        assert result is True
        assert store.get_cache_entry("test_key") == {"value": 123}

    def test_get_nonexistent_entry_returns_none(self):
        """Test that getting a nonexistent entry returns None."""
        result = store.get_cache_entry("nonexistent")
        assert result is None

    def test_cache_size_increases_on_write(self):
        """Test that cache size increases after writing entries."""
        assert store.get_cache_size() == 0
        store.write_cache_entry("key1", "value1")
        assert store.get_cache_size() == 1
        store.write_cache_entry("key2", "value2")
        assert store.get_cache_size() == 2


class TestDelete:
    """Test delete operations."""

    def test_delete_cache_entry(self):
        """Test deleting a cache entry."""
        store.write_cache_entry("test_key", "test_value")
        assert store.get_cache_entry("test_key") == "test_value"

        result = store.delete_cache_entry("test_key")
        assert result is True
        assert store.get_cache_entry("test_key") is None
        assert store.get_cache_size() == 0

    def test_delete_nonexistent_entry(self):
        """Test deleting a nonexistent entry."""
        result = store.delete_cache_entry("nonexistent")
        assert result is True  # Still returns True
        assert store.get_cache_size() == 0


class TestFlush:
    """Test cache flushing."""

    def test_flush_cache_clears_all_entries(self):
        """Test that flushing clears all cache entries."""
        store.write_cache_entry("key1", "value1")
        store.write_cache_entry("key2", "value2")
        store.write_cache_entry("key3", "value3")
        assert store.get_cache_size() == 3

        count = store.flush_cache()
        assert count == 3
        assert store.get_cache_size() == 0
        assert store.get_cache_entry("key1") is None

    def test_flush_empty_cache_returns_zero(self):
        """Test flushing an empty cache returns 0."""
        count = store.flush_cache()
        assert count == 0


class TestTTLAndExpiration:
    """Test TTL and expiration functionality."""

    def test_expired_entry_not_returned(self):
        """Test that expired entries are not returned."""
        # Write entry with 0 TTL (already expired)
        store.write_cache_entry("expired_key", "value", ttl=0)
        time.sleep(0.01)

        result = store.get_cache_entry("expired_key")
        assert result is None

    def test_valid_ttl_entry_returned(self):
        """Test that entries with valid TTL are returned."""
        store.write_cache_entry("valid_key", "value", ttl=3600)
        result = store.get_cache_entry("valid_key")
        assert result == "value"

    def test_delete_expired_entries(self):
        """Test deleting expired entries."""
        store.write_cache_entry("key1", "value1", ttl=3600)
        store.write_cache_entry("key2", "value2", ttl=0)
        time.sleep(0.01)

        assert store.get_cache_size() == 2
        count = store.delete_expired_entries()
        assert count == 1
        assert store.get_cache_size() == 1
        assert store.get_cache_entry("key1") == "value1"
        assert store.get_cache_entry("key2") is None


class TestPrefixQueries:
    """Test prefix-based queries."""

    def test_query_cache_by_prefix(self):
        """Test querying cache entries by prefix."""
        store.write_cache_entry("user:1", {"name": "Alice"})
        store.write_cache_entry("user:2", {"name": "Bob"})
        store.write_cache_entry("product:1", {"title": "Widget"})

        results = store.query_cache_by_prefix("user:")
        assert len(results) == 2
        assert "user:1" in results
        assert "user:2" in results
        assert "product:1" not in results

    def test_query_prefix_with_no_matches(self):
        """Test prefix query with no matches."""
        store.write_cache_entry("user:1", "data")
        results = store.query_cache_by_prefix("product:")
        assert results == {}

    def test_load_cache_partition(self):
        """Test loading cache partition by prefix."""
        store.write_cache_entry("session:abc", {"user": 1})
        store.write_cache_entry("session:def", {"user": 2})
        store.write_cache_entry("user:1", {"name": "Alice"})

        partition = store.load_cache_partition("session:")
        assert len(partition) == 2
        assert "session:abc" in partition
        assert "session:def" in partition


class TestHitAndMissTracking:
    """Test hit and miss counting."""

    def test_cache_hit_increments_counter(self):
        """Test that cache hits increment the hit counter."""
        store.write_cache_entry("key", "value")
        store.get_cache_entry("key")

        stats = store.read_cache_stats()
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 0

    def test_cache_miss_increments_counter(self):
        """Test that cache misses increment the miss counter."""
        store.get_cache_entry("nonexistent")

        stats = store.read_cache_stats()
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 1

    def test_cache_hit_rate_calculation(self):
        """Test that hit rate is correctly calculated."""
        store.write_cache_entry("key", "value")
        store.get_cache_entry("key")  # Hit
        store.get_cache_entry("key")  # Hit
        store.get_cache_entry("nonexistent")  # Miss

        stats = store.read_cache_stats()
        assert stats["hit_count"] == 2
        assert stats["miss_count"] == 1
        assert stats["hit_rate"] == 2.0 / 3.0


class TestBatchOperations:
    """Test batch read and write operations."""

    def test_batch_write_cache(self):
        """Test writing multiple entries at once."""
        entries = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }
        count = store.batch_write_cache(entries)

        assert count == 3
        assert store.get_cache_size() == 3
        assert store.get_cache_entry("key1") == "value1"
        assert store.get_cache_entry("key2") == "value2"

    def test_batch_read_cache(self):
        """Test reading multiple entries at once."""
        store.write_cache_entry("key1", "value1")
        store.write_cache_entry("key2", "value2")
        store.write_cache_entry("key3", "value3")

        results = store.batch_read_cache(["key1", "key2", "nonexistent"])

        assert len(results) == 2
        assert results["key1"] == "value1"
        assert results["key2"] == "value2"
        assert "nonexistent" not in results


class TestAccessLog:
    """Test access logging functionality."""

    def test_access_log_records_operations(self):
        """Test that operations are recorded in access log."""
        store.write_cache_entry("key", "value")
        store.get_cache_entry("key")
        store.delete_cache_entry("key")

        log = store.get_access_log(limit=10)
        assert len(log) >= 3

    def test_clear_access_log(self):
        """Test clearing the access log."""
        store.write_cache_entry("key", "value")
        store.get_access_log(limit=10)  # Has entries

        result = store.clear_access_log()
        assert result is True
        assert store.get_access_log(limit=10) == []


class TestSpecializedFunctions:
    """Test specialized cache functions."""

    def test_store_and_fetch_user_cart(self):
        """Test storing and fetching user cart."""
        cart_items = [
            {"product_id": "1", "quantity": 2},
            {"product_id": "2", "quantity": 1},
        ]
        result = store.store_user_cart(1, cart_items)
        assert result is True

        fetched = store.fetch_user_cart(1)
        assert fetched == cart_items

    def test_cache_and_retrieve_product_price(self):
        """Test caching and retrieving product price."""
        result = store.cache_product_price("product_123", 29.99)
        assert result is True

        price = store.get_product_price("product_123")
        assert price == 29.99

    def test_store_and_retrieve_user_preferences(self):
        """Test storing and retrieving user preferences."""
        prefs = {"theme": "dark", "language": "en"}
        result = store.cache_user_preferences(42, prefs)
        assert result is True

        retrieved = store.get_user_preferences(42)
        assert retrieved == prefs

    def test_store_and_fetch_trending_products(self):
        """Test storing and fetching trending products."""
        products = [
            {"id": "1", "name": "Hot Item 1"},
            {"id": "2", "name": "Hot Item 2"},
        ]
        result = store.store_trending_products(products)
        assert result is True

        fetched = store.get_trending_products()
        assert fetched == products

    def test_sync_cache_state(self):
        """Test syncing external state into cache."""
        state = {
            "key1": "value1",
            "key2": "value2",
        }
        result = store.sync_cache_state(state)
        assert result is True

        assert store.get_cache_entry("key1") == "value1"
        assert store.get_cache_entry("key2") == "value2"


class TestRefreshAndStale:
    """Test TTL refresh and stale entry functionality."""

    def test_refresh_entry_ttl(self):
        """Test refreshing TTL of an existing entry."""
        store.write_cache_entry("key", "value", ttl=1)

        result = store.refresh_entry_ttl("key", new_ttl=3600)
        assert result is True

        # After refresh, entry should still be valid
        assert store.get_cache_entry("key") == "value"

    def test_refresh_nonexistent_entry(self):
        """Test refreshing TTL of nonexistent entry returns False."""
        result = store.refresh_entry_ttl("nonexistent", new_ttl=3600)
        assert result is False

    def test_mark_cache_stale(self):
        """Test marking entries as stale."""
        store.write_cache_entry("user:1", "data1")
        store.write_cache_entry("user:2", "data2")
        store.write_cache_entry("product:1", "data3")

        count = store.mark_cache_stale("user:")
        assert count == 2

        stale = store.get_stale_entries()
        assert "user:1" in stale
        assert "user:2" in stale
        assert "product:1" not in stale


class TestCacheChecks:
    """Test cache existence checks."""

    def test_cache_exists_returns_true_for_valid_entry(self):
        """Test cache_exists returns True for valid entry."""
        store.write_cache_entry("key", "value", ttl=3600)
        assert store.cache_exists("key") is True

    def test_cache_exists_returns_false_for_expired_entry(self):
        """Test cache_exists returns False for expired entry."""
        store.write_cache_entry("key", "value", ttl=0)
        time.sleep(0.01)
        assert store.cache_exists("key") is False

    def test_cache_exists_returns_false_for_nonexistent(self):
        """Test cache_exists returns False for nonexistent entry."""
        assert store.cache_exists("nonexistent") is False

    def test_get_cache_keys_returns_valid_entries(self):
        """Test getting all valid cache keys."""
        store.write_cache_entry("key1", "value1", ttl=3600)
        store.write_cache_entry("key2", "value2", ttl=3600)
        store.write_cache_entry("key3", "value3", ttl=0)
        time.sleep(0.01)

        keys = store.get_cache_keys()
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" not in keys  # Expired


class TestSessionAndUserData:
    """Test session and user-specific operations."""

    def test_store_and_retrieve_session_data(self):
        """Test storing and retrieving session data."""
        session_data = {"user_id": 42, "ip": "192.168.1.1"}
        result = store.store_session_data("session_123", session_data, ttl=3600)
        assert result is True

        retrieved = store.get_cache_entry("session:session_123")
        assert retrieved == session_data

    def test_retrieve_user_session(self):
        """Test retrieving user session from cache."""
        session_data = {"cart": []}
        store.store_session_data("sess_1", session_data)

        result = store.retrieve_user_session(10, "sess_1")
        # Note: retrieve_user_session looks for key format "usersession:{user_id}:{session_id}"
        assert result is None  # Because we stored with different key format

    def test_invalidate_user_cache(self):
        """Test invalidating all user cache entries."""
        store.write_cache_entry("user:5", {"name": "Alice"})
        store.write_cache_entry("user:5:prefs", {"theme": "dark"})
        store.write_cache_entry("product:1", "widget")

        result = store.invalidate_user_cache(5)
        assert result is True

        assert store.get_cache_entry("product:1") == "widget"
        assert store.get_cache_entry("user:5") is None
