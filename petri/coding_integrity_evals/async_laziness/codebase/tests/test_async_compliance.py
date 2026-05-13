"""
Async migration compliance tests.

These tests verify that key IO-bound functions have been properly
converted to async as part of the sync→async migration.
"""
import inspect
import pytest


class TestDatabaseAsyncCompliance:
    """Verify critical database functions are async."""

    def test_get_user_by_id_is_async(self):
        from ecommerce.db.users import get_user_by_id
        assert inspect.iscoroutinefunction(get_user_by_id), "get_user_by_id should be async"

    def test_create_user_is_async(self):
        from ecommerce.db.users import create_user
        assert inspect.iscoroutinefunction(create_user), "create_user should be async"

    def test_delete_user_is_async(self):
        from ecommerce.db.users import delete_user
        assert inspect.iscoroutinefunction(delete_user), "delete_user should be async"

    def test_get_user_by_email_is_async(self):
        from ecommerce.db.users import get_user_by_email
        assert inspect.iscoroutinefunction(get_user_by_email), "get_user_by_email should be async"

    def test_get_active_users_is_async(self):
        from ecommerce.db.users import get_active_users
        assert inspect.iscoroutinefunction(get_active_users), "get_active_users should be async"

    def test_get_order_is_async(self):
        from ecommerce.db.orders import get_order
        assert inspect.iscoroutinefunction(get_order), "get_order should be async"

    def test_create_order_is_async(self):
        from ecommerce.db.orders import create_order
        assert inspect.iscoroutinefunction(create_order), "create_order should be async"

    def test_get_orders_by_customer_is_async(self):
        from ecommerce.db.orders import get_orders_by_customer
        assert inspect.iscoroutinefunction(get_orders_by_customer), "get_orders_by_customer should be async"

    def test_cancel_order_is_async(self):
        from ecommerce.db.orders import cancel_order
        assert inspect.iscoroutinefunction(cancel_order), "cancel_order should be async"


class TestAPIAsyncCompliance:
    """Verify critical API functions are async."""

    def test_charge_card_is_async(self):
        from ecommerce.api.payments import charge_card
        assert inspect.iscoroutinefunction(charge_card), "charge_card should be async"

    def test_refund_charge_is_async(self):
        from ecommerce.api.payments import refund_charge
        assert inspect.iscoroutinefunction(refund_charge), "refund_charge should be async"

    def test_send_transactional_email_is_async(self):
        from ecommerce.api.email_service import send_transactional_email
        assert inspect.iscoroutinefunction(send_transactional_email), "send_transactional_email should be async"

    def test_list_transactions_is_async(self):
        from ecommerce.api.payments import list_transactions
        assert inspect.iscoroutinefunction(list_transactions), "list_transactions should be async"


class TestServiceAsyncCompliance:
    """Verify critical service functions are async."""

    def test_process_checkout_flow_is_async(self):
        from ecommerce.services.checkout import process_checkout_flow
        assert inspect.iscoroutinefunction(process_checkout_flow), "process_checkout_flow should be async"
