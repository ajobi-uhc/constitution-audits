"""Unit tests for ecommerce.db.users module."""

import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest

from ecommerce.db.users import (
    # Helpers
    build_where_clause,
    format_row_to_dict,
    sanitize_email,
    sanitize_name,
    validate_tier,
    build_pagination_query,
    calculate_pagination_offset,
    format_timestamp,
    parse_timestamp,
    build_update_clause,
    validate_user_data,
    escape_like_string,
    # CRUD operations
    create_user,
    get_user_by_id,
    get_user_by_email,
    get_all_users,
    update_user,
    delete_user,
    delete_user_soft,
    search_users_by_email,
    search_users_by_name,
    get_users_by_tier,
    get_active_users,
    get_inactive_users,
    count_users,
    count_users_by_tier,
    count_active_users,
    user_exists,
    email_exists,
    get_user_tier,
    get_newest_user,
    get_oldest_user,
)


# ============================================================================
# Helper function tests
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_sanitize_email_lowercase(self):
        """Email should be lowercased and stripped."""
        assert sanitize_email("  ALICE@EXAMPLE.COM  ") == "alice@example.com"

    def test_sanitize_email_already_clean(self):
        """Already clean email should be returned as-is."""
        assert sanitize_email("bob@example.com") == "bob@example.com"

    def test_sanitize_name_strips_whitespace(self):
        """Name should have whitespace stripped."""
        assert sanitize_name("  John Doe  ") == "John Doe"

    def test_sanitize_name_preserves_case(self):
        """Name should preserve case."""
        assert sanitize_name("JoHn DoE") == "JoHn DoE"

    def test_validate_tier_accepts_valid_tiers(self):
        """Should accept bronze, silver, gold, platinum."""
        assert validate_tier("bronze") is True
        assert validate_tier("SILVER") is True
        assert validate_tier("Gold") is True
        assert validate_tier("platinum") is True

    def test_validate_tier_rejects_invalid_tiers(self):
        """Should reject invalid tier values."""
        assert validate_tier("diamond") is False
        assert validate_tier("") is False
        assert validate_tier("admin") is False

    def test_build_pagination_query_generates_limit_offset(self):
        """Should generate correct LIMIT/OFFSET clause."""
        result = build_pagination_query(offset=10, limit=20)
        assert result == "LIMIT 20 OFFSET 10"

    def test_calculate_pagination_offset_page_1(self):
        """Page 1 should have offset 0."""
        assert calculate_pagination_offset(page=1, page_size=10) == 0

    def test_calculate_pagination_offset_page_3(self):
        """Page 3 with size 10 should have offset 20."""
        assert calculate_pagination_offset(page=3, page_size=10) == 20

    def test_calculate_pagination_offset_invalid_page(self):
        """Page 0 or negative should return 0."""
        assert calculate_pagination_offset(page=0, page_size=10) == 0
        assert calculate_pagination_offset(page=-1, page_size=10) == 0

    def test_format_timestamp_with_datetime(self):
        """Should convert datetime to ISO format string."""
        dt = datetime(2025, 2, 16, 10, 30, 45)
        result = format_timestamp(dt)
        assert result == "2025-02-16T10:30:45"

    def test_format_timestamp_with_none(self):
        """Should return None for None input."""
        assert format_timestamp(None) is None

    def test_parse_timestamp_valid_string(self):
        """Should parse ISO format string to datetime."""
        ts = "2025-02-16T10:30:45"
        result = parse_timestamp(ts)
        assert result == datetime(2025, 2, 16, 10, 30, 45)

    def test_parse_timestamp_none(self):
        """Should return None for None input."""
        assert parse_timestamp(None) is None

    def test_build_where_clause_empty_filters(self):
        """Empty filters should return empty string and list."""
        where, params = build_where_clause({})
        assert where == ""
        assert params == []

    def test_build_where_clause_single_filter(self):
        """Single filter should build correct clause."""
        where, params = build_where_clause({"tier": "gold"})
        assert where == "tier = ?"
        assert params == ["gold"]

    def test_build_where_clause_multiple_filters(self):
        """Multiple filters should be joined with AND."""
        where, params = build_where_clause({"tier": "gold", "active": 1})
        assert "tier = ?" in where
        assert "active = ?" in where
        assert "AND" in where
        assert "gold" in params
        assert 1 in params

    def test_build_where_clause_ignores_none_values(self):
        """Filters with None values should be excluded."""
        where, params = build_where_clause({"tier": "gold", "email": None})
        assert where == "tier = ?"
        assert params == ["gold"]

    def test_build_update_clause_empty_dict(self):
        """Empty dict should return empty clause."""
        set_clause, params = build_update_clause({})
        assert set_clause == ""
        assert params == []

    def test_build_update_clause_single_field(self):
        """Single field should build correct UPDATE clause."""
        set_clause, params = build_update_clause({"name": "Alice"})
        assert set_clause == "name = ?"
        assert params == ["Alice"]

    def test_build_update_clause_multiple_fields(self):
        """Multiple fields should be joined by commas."""
        set_clause, params = build_update_clause({"name": "Alice", "tier": "gold"})
        assert "name = ?" in set_clause
        assert "tier = ?" in set_clause
        assert set_clause.count(",") == 1
        assert "Alice" in params
        assert "gold" in params

    def test_validate_user_data_valid(self):
        """Valid user data with required fields should return True."""
        data = {"email": "alice@example.com", "name": "Alice", "tier": "gold"}
        assert validate_user_data(data) is True

    def test_validate_user_data_missing_field(self):
        """Missing required field should return False."""
        data = {"email": "alice@example.com", "name": "Alice"}
        assert validate_user_data(data) is False

    def test_validate_user_data_empty_field(self):
        """Empty required field should return False."""
        data = {"email": "", "name": "Alice", "tier": "gold"}
        assert validate_user_data(data) is False

    def test_escape_like_string_percent(self):
        """Should escape percent signs."""
        result = escape_like_string("alice%test")
        assert result == "alice\\%test"

    def test_escape_like_string_underscore(self):
        """Should escape underscores."""
        result = escape_like_string("alice_test")
        assert result == "alice\\_test"

    def test_escape_like_string_both(self):
        """Should escape both percent and underscore."""
        result = escape_like_string("alice_%test")
        assert result == "alice\\_\\%test"

    def test_format_row_to_dict_with_row(self):
        """Should convert sqlite3.Row to dict."""
        mock_row = MagicMock()
        mock_row.keys.return_value = ["id", "name"]
        mock_row.__iter__ = MagicMock(return_value=iter([("id", 1), ("name", "Alice")]))
        result = format_row_to_dict(mock_row)
        assert isinstance(result, dict)

    def test_format_row_to_dict_with_none(self):
        """Should return None for None input."""
        assert format_row_to_dict(None) is None


# ============================================================================
# CRUD OPERATION TESTS (WITH MOCKING)
# ============================================================================


class TestGetUserById:
    """Tests for get_user_by_id function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_get_user_by_id_found(self, mock_get_conn):
        """Should return user dict when user exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        # Setup mock chain
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_row

        # Mock format_row_to_dict behavior
        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.return_value = {"id": 1, "name": "Alice", "email": "alice@example.com"}
            result = get_user_by_id(1)

            mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = ?", (1,))
            assert result == {"id": 1, "name": "Alice", "email": "alice@example.com"}

    @patch('ecommerce.db.users.get_db_connection')
    def test_get_user_by_id_not_found(self, mock_get_conn):
        """Should return None when user not found."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.return_value = None
            result = get_user_by_id(999)

            assert result is None


class TestGetUserByEmail:
    """Tests for get_user_by_email function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_get_user_by_email_found(self, mock_get_conn):
        """Should return user when email is found."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_row

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.return_value = {"id": 1, "email": "alice@example.com"}
            result = get_user_by_email("  ALICE@EXAMPLE.COM  ")

            # Should sanitize the email
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "alice@example.com" in call_args[0][1]


class TestCreateUser:
    """Tests for create_user function."""

    @patch('ecommerce.db.users.get_user_by_id')
    @patch('ecommerce.db.users.get_db_connection')
    def test_create_user_success(self, mock_get_conn, mock_get_user):
        """Should create user and return user dict."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 1

        mock_get_user.return_value = {"id": 1, "email": "alice@example.com", "name": "Alice", "tier": "gold"}

        result = create_user("alice@example.com", "Alice", "gold")

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        assert result == {"id": 1, "email": "alice@example.com", "name": "Alice", "tier": "gold"}
        mock_get_user.assert_called_once_with(1)


class TestUpdateUser:
    """Tests for update_user function."""

    @patch('ecommerce.db.users.get_user_by_id')
    @patch('ecommerce.db.users.get_db_connection')
    def test_update_user_with_changes(self, mock_get_conn, mock_get_user):
        """Should update user with provided fields."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_get_user.return_value = {"id": 1, "name": "Bob", "tier": "silver"}

        result = update_user(1, name="Bob", tier="silver")

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        assert result == {"id": 1, "name": "Bob", "tier": "silver"}

    @patch('ecommerce.db.users.get_user_by_id')
    @patch('ecommerce.db.users.get_db_connection')
    def test_update_user_no_changes(self, mock_get_conn, mock_get_user):
        """Should return current user if no non-None updates."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_get_user.return_value = {"id": 1, "name": "Alice"}

        result = update_user(1, name=None, tier=None)

        # Should not execute INSERT when all updates are None
        assert result == {"id": 1, "name": "Alice"}


class TestDeleteUser:
    """Tests for delete_user function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_delete_user_success(self, mock_get_conn):
        """Should delete user and return True."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1

        result = delete_user(1)

        mock_cursor.execute.assert_called_once_with("DELETE FROM users WHERE id = ?", (1,))
        mock_conn.commit.assert_called_once()
        assert result is True

    @patch('ecommerce.db.users.get_db_connection')
    def test_delete_user_not_found(self, mock_get_conn):
        """Should return False when user not found."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 0

        result = delete_user(999)

        assert result is False


class TestDeleteUserSoft:
    """Tests for delete_user_soft function."""

    @patch('ecommerce.db.users.update_user')
    def test_delete_user_soft_sets_inactive(self, mock_update):
        """Should call update_user with active=0."""
        mock_update.return_value = {"id": 1, "active": 0}

        result = delete_user_soft(1)

        mock_update.assert_called_once_with(1, active=0)
        assert result == {"id": 1, "active": 0}


class TestSearchUsers:
    """Tests for search_users_by_email and search_users_by_name."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_search_users_by_email_found(self, mock_get_conn):
        """Should find users matching email pattern."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row1 = MagicMock(spec=sqlite3.Row)
        mock_row2 = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [mock_row1, mock_row2]

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.side_effect = [
                {"id": 1, "email": "alice@example.com"},
                {"id": 2, "email": "alice2@example.com"}
            ]
            result = search_users_by_email("alice")

            assert len(result) == 2
            assert result[0]["email"] == "alice@example.com"

    @patch('ecommerce.db.users.get_db_connection')
    def test_search_users_by_name_found(self, mock_get_conn):
        """Should find users matching name pattern."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [mock_row]

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.return_value = {"id": 1, "name": "John Doe"}
            result = search_users_by_name("John")

            assert len(result) == 1
            assert result[0]["name"] == "John Doe"


class TestGetUsersByTier:
    """Tests for get_users_by_tier function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_get_users_by_tier(self, mock_get_conn):
        """Should return all users with specified tier."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row1 = MagicMock(spec=sqlite3.Row)
        mock_row2 = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [mock_row1, mock_row2]

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.side_effect = [
                {"id": 1, "tier": "gold"},
                {"id": 2, "tier": "gold"}
            ]
            result = get_users_by_tier("GOLD")

            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert ("gold",) in call_args[0]
            assert len(result) == 2


class TestGetActiveUsers:
    """Tests for get_active_users function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_get_active_users(self, mock_get_conn):
        """Should return only active users."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [mock_row]

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.return_value = {"id": 1, "active": 1}
            result = get_active_users()

            mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE active = 1")
            assert result[0]["active"] == 1


class TestGetInactiveUsers:
    """Tests for get_inactive_users function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_get_inactive_users(self, mock_get_conn):
        """Should return only inactive users."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [mock_row]

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.return_value = {"id": 1, "active": 0}
            result = get_inactive_users()

            mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE active = 0")
            assert result[0]["active"] == 0


class TestCountUsers:
    """Tests for count_users function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_count_users(self, mock_get_conn):
        """Should return total user count."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)
        mock_row.__getitem__ = lambda self, key: 42 if key == "count" else None

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_row

        result = count_users()

        mock_cursor.execute.assert_called_once_with("SELECT COUNT(*) as count FROM users")
        assert result == 42


class TestCountUsersByTier:
    """Tests for count_users_by_tier function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_count_users_by_tier(self, mock_get_conn):
        """Should return user count grouped by tier."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_row1 = MagicMock(spec=sqlite3.Row)
        mock_row1.__getitem__ = lambda self, key: "gold" if key == "tier" else 10

        mock_row2 = MagicMock(spec=sqlite3.Row)
        mock_row2.__getitem__ = lambda self, key: "silver" if key == "tier" else 5

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [mock_row1, mock_row2]

        result = count_users_by_tier()

        assert result["gold"] == 10
        assert result["silver"] == 5


class TestCountActiveUsers:
    """Tests for count_active_users function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_count_active_users(self, mock_get_conn):
        """Should return count of active users."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)
        mock_row.__getitem__ = lambda self, key: 25 if key == "count" else None

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_row

        result = count_active_users()

        assert result == 25


class TestUserExists:
    """Tests for user_exists function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_user_exists_true(self, mock_get_conn):
        """Should return True when user exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_row

        result = user_exists(1)

        assert result is True

    @patch('ecommerce.db.users.get_db_connection')
    def test_user_exists_false(self, mock_get_conn):
        """Should return False when user does not exist."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        result = user_exists(999)

        assert result is False


class TestEmailExists:
    """Tests for email_exists function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_email_exists_true(self, mock_get_conn):
        """Should return True when email exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_row

        result = email_exists("alice@example.com")

        assert result is True

    @patch('ecommerce.db.users.get_db_connection')
    def test_email_exists_false(self, mock_get_conn):
        """Should return False when email does not exist."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        result = email_exists("nonexistent@example.com")

        assert result is False


class TestGetUserTier:
    """Tests for get_user_tier function."""

    @patch('ecommerce.db.users.get_user_by_id')
    def test_get_user_tier_found(self, mock_get_user):
        """Should return user's tier."""
        mock_get_user.return_value = {"id": 1, "tier": "gold"}

        result = get_user_tier(1)

        assert result == "gold"

    @patch('ecommerce.db.users.get_user_by_id')
    def test_get_user_tier_not_found(self, mock_get_user):
        """Should return None when user not found."""
        mock_get_user.return_value = None

        result = get_user_tier(999)

        assert result is None


class TestGetNewestUser:
    """Tests for get_newest_user function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_get_newest_user(self, mock_get_conn):
        """Should return most recently created user."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_row

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.return_value = {"id": 100, "name": "Latest User"}
            result = get_newest_user()

            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "ORDER BY created_at DESC" in call_args[0][0]
            assert result["id"] == 100


class TestGetOldestUser:
    """Tests for get_oldest_user function."""

    @patch('ecommerce.db.users.get_db_connection')
    def test_get_oldest_user(self, mock_get_conn):
        """Should return earliest created user."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = MagicMock(spec=sqlite3.Row)

        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = mock_row

        with patch('ecommerce.db.users.format_row_to_dict') as mock_format:
            mock_format.return_value = {"id": 1, "name": "First User"}
            result = get_oldest_user()

            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "ORDER BY created_at ASC" in call_args[0][0]
            assert result["id"] == 1
