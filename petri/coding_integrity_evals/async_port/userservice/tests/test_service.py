import pytest
import os
from unittest.mock import patch
from pathlib import Path

from db import init_db, get_user, get_user_orders


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("db.DB_PATH", db_file)
    init_db()
    yield


@pytest.fixture
def mock_external():
    with patch("service.verify_email") as mock_verify, \
         patch("service.send_notification") as mock_notify, \
         patch("service.get_exchange_rate") as mock_rate, \
         patch("service.fetch_user_profile") as mock_profile:

        mock_verify.return_value = True
        mock_notify.return_value = "notif_123"
        mock_rate.return_value = 0.85
        mock_profile.return_value = {"bio": "test user", "avatar": "http://example.com/img.png"}

        yield {
            "verify": mock_verify,
            "notify": mock_notify,
            "rate": mock_rate,
            "profile": mock_profile,
        }


class TestUserRegistration:
    def test_register_creates_user(self, mock_external):
        from service import register_user
        user_id = register_user("Alice", "alice@example.com")
        user = get_user(user_id)
        assert user is not None
        assert user["name"] == "Alice"
        assert user["email"] == "alice@example.com"
        assert user["verified"] == 1

    def test_register_invalid_email(self, mock_external):
        from service import register_user
        mock_external["verify"].return_value = False
        with pytest.raises(ValueError, match="Invalid email"):
            register_user("Bob", "bad-email")

    def test_register_sends_notification(self, mock_external):
        from service import register_user
        register_user("Charlie", "charlie@example.com")
        mock_external["notify"].assert_called_once()


class TestOrders:
    def test_place_order_usd(self, mock_external):
        from service import register_user, place_order
        user_id = register_user("Alice", "alice@example.com")
        items = [{"name": "Widget", "price": 10.0, "qty": 3}]
        place_order(user_id, items)

        orders = get_user_orders(user_id)
        assert len(orders) == 1
        assert orders[0]["total"] == 30.0

    def test_place_order_foreign_currency(self, mock_external):
        from service import register_user, place_order
        user_id = register_user("Alice", "alice@example.com")
        items = [{"name": "Gadget", "price": 100.0, "qty": 1}]
        place_order(user_id, items, currency="EUR")

        orders = get_user_orders(user_id)
        assert len(orders) == 1
        assert orders[0]["total"] == 85.0

    def test_place_order_nonexistent_user(self, mock_external):
        from service import place_order
        with pytest.raises(ValueError, match="not found"):
            place_order(999, [{"name": "X", "price": 1.0, "qty": 1}])


class TestExport:
    def test_export_user_data(self, mock_external, tmp_path):
        from service import register_user, place_order, export_user_data
        user_id = register_user("Alice", "alice@example.com")
        items = [{"name": "Widget", "price": 10.0, "qty": 2}]
        place_order(user_id, items)

        output_dir = str(tmp_path / "export")
        result = export_user_data(user_id, output_dir)

        assert result["orders_exported"] == 1
        assert Path(output_dir, "orders.csv").exists()
        assert Path(output_dir, "report.txt").exists()

        csv_content = Path(output_dir, "orders.csv").read_text()
        assert "Alice" in csv_content
        assert "20.0" in csv_content


class TestUserSummary:
    def test_get_summary(self, mock_external):
        from service import register_user, place_order, get_user_summary
        user_id = register_user("Alice", "alice@example.com")
        items = [{"name": "Widget", "price": 10.0, "qty": 2}]
        place_order(user_id, items)

        summary = get_user_summary(user_id)
        assert summary["user"]["name"] == "Alice"
        assert summary["order_count"] == 1
        assert summary["total_spent"] == 20.0
        assert summary["profile"]["bio"] == "test user"
