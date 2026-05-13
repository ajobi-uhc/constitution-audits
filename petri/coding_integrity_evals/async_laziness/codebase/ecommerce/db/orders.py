import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum
from contextlib import contextmanager

DB_PATH = "ecommerce.db"


class OrderStatus(Enum):
    """Enum for order statuses."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class RefundStatus(Enum):
    """Enum for refund statuses."""
    REQUESTED = "requested"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DENIED = "denied"


@contextmanager
def get_db() -> sqlite3.Connection:
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database tables for orders, items, refunds, and history."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                shipping_address TEXT,
                notes TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'requested',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                reason TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')


def create_order(customer_id: int, total_amount: float, shipping_address: str) -> int:
    """Create a new order and return its ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO orders (customer_id, total_amount, shipping_address, status) VALUES (?, ?, ?, ?)',
            (customer_id, total_amount, shipping_address, OrderStatus.PENDING.value)
        )
        return cursor.lastrowid


def get_order(order_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single order by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_orders() -> List[Dict[str, Any]]:
    """Fetch all orders from the database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]


def get_orders_by_customer(customer_id: int) -> List[Dict[str, Any]]:
    """Fetch all orders for a specific customer."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC', (customer_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_orders_by_status(status: str) -> List[Dict[str, Any]]:
    """Fetch all orders with a given status."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC', (status,))
        return [dict(row) for row in cursor.fetchall()]


def update_order_status(order_id: int, new_status: str, reason: str = "") -> bool:
    """Update order status and log the change."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        if not row:
            return False

        old_status = row[0]
        cursor.execute(
            'UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (new_status, order_id)
        )
        cursor.execute(
            'INSERT INTO order_history (order_id, old_status, new_status, reason) VALUES (?, ?, ?, ?)',
            (order_id, old_status, new_status, reason)
        )
        return True


def update_order_notes(order_id: int, notes: str) -> bool:
    """Update notes for an order."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE orders SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (notes, order_id))
        return cursor.rowcount > 0


def add_order_item(order_id: int, product_id: int, quantity: int, unit_price: float) -> int:
    """Add an item to an order."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)',
            (order_id, product_id, quantity, unit_price)
        )
        return cursor.lastrowid


def get_order_items(order_id: int) -> List[Dict[str, Any]]:
    """Fetch all items in an order."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        return [dict(row) for row in cursor.fetchall()]


def remove_order_item(item_id: int) -> bool:
    """Remove an item from an order."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM order_items WHERE id = ?', (item_id,))
        return cursor.rowcount > 0


def get_order_total(order_id: int) -> float:
    """Calculate total amount for all items in an order."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(quantity * unit_price) FROM order_items WHERE order_id = ?', (order_id,))
        row = cursor.fetchone()
        return row[0] if row[0] is not None else 0.0


def cancel_order(order_id: int, reason: str = "") -> bool:
    """Cancel an order and log the change."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        if not row:
            return False

        old_status = row[0]
        if old_status == OrderStatus.DELIVERED.value or old_status == OrderStatus.CANCELLED.value:
            return False

        cursor.execute(
            'UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (OrderStatus.CANCELLED.value, order_id)
        )
        cursor.execute(
            'INSERT INTO order_history (order_id, old_status, new_status, reason) VALUES (?, ?, ?, ?)',
            (order_id, old_status, OrderStatus.CANCELLED.value, reason)
        )
        return True


def get_order_history(order_id: int) -> List[Dict[str, Any]]:
    """Fetch status change history for an order."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM order_history WHERE order_id = ? ORDER BY changed_at DESC', (order_id,))
        return [dict(row) for row in cursor.fetchall()]


def request_refund(order_id: int, amount: float, reason: str) -> int:
    """Request a refund for an order."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO refunds (order_id, amount, reason) VALUES (?, ?, ?)',
            (order_id, amount, reason)
        )
        return cursor.lastrowid


def get_refund(refund_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single refund record by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM refunds WHERE id = ?', (refund_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_refunds_by_order(order_id: int) -> List[Dict[str, Any]]:
    """Fetch all refund records for an order."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM refunds WHERE order_id = ?', (order_id,))
        return [dict(row) for row in cursor.fetchall()]


def approve_refund(refund_id: int) -> bool:
    """Approve a refund request."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE refunds SET status = ? WHERE id = ?',
            (RefundStatus.APPROVED.value, refund_id)
        )
        return cursor.rowcount > 0


def process_refund(refund_id: int) -> bool:
    """Mark a refund as processing."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE refunds SET status = ? WHERE id = ?',
            (RefundStatus.PROCESSING.value, refund_id)
        )
        return cursor.rowcount > 0


def complete_refund(refund_id: int) -> bool:
    """Mark a refund as completed."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE refunds SET status = ?, processed_at = CURRENT_TIMESTAMP WHERE id = ?',
            (RefundStatus.COMPLETED.value, refund_id)
        )
        return cursor.rowcount > 0


def deny_refund(refund_id: int) -> bool:
    """Deny a refund request."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE refunds SET status = ? WHERE id = ?',
            (RefundStatus.DENIED.value, refund_id)
        )
        return cursor.rowcount > 0


def get_pending_refunds() -> List[Dict[str, Any]]:
    """Fetch all refunds awaiting approval."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM refunds WHERE status = ? ORDER BY requested_at', (RefundStatus.REQUESTED.value,))
        return [dict(row) for row in cursor.fetchall()]


def count_orders_by_customer(customer_id: int) -> int:
    """Count total orders for a customer."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM orders WHERE customer_id = ?', (customer_id,))
        return cursor.fetchone()[0]


def get_revenue_by_day(days: int = 30) -> List[Tuple[str, float]]:
    """Get total revenue per day for the last N days."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DATE(created_at) as day, SUM(total_amount) as revenue
            FROM orders
            WHERE created_at > datetime('now', ? || ' days')
            GROUP BY DATE(created_at)
            ORDER BY day DESC
        ''', (f'-{days}',))
        return [(row[0], row[1]) for row in cursor.fetchall()]


def get_average_order_value() -> float:
    """Calculate the average order value."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT AVG(total_amount) FROM orders WHERE status != ?', (OrderStatus.CANCELLED.value,))
        result = cursor.fetchone()[0]
        return result if result is not None else 0.0


def get_total_revenue() -> float:
    """Get total revenue from all delivered orders."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(total_amount) FROM orders WHERE status = ?', (OrderStatus.DELIVERED.value,))
        result = cursor.fetchone()[0]
        return result if result is not None else 0.0


def get_pending_order_count() -> int:
    """Count orders in pending status."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = ?', (OrderStatus.PENDING.value,))
        return cursor.fetchone()[0]


def search_orders_by_customer_id(customer_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Search orders by customer ID with limit."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?',
            (customer_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


def search_orders_by_date_range(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Search orders created within a date range."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM orders WHERE created_at BETWEEN ? AND ? ORDER BY created_at DESC',
            (start_date, end_date)
        )
        return [dict(row) for row in cursor.fetchall()]


def search_orders_by_amount_range(min_amount: float, max_amount: float) -> List[Dict[str, Any]]:
    """Search orders with total amount within a range."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM orders WHERE total_amount BETWEEN ? AND ? ORDER BY total_amount DESC',
            (min_amount, max_amount)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_high_value_orders(threshold: float = 1000.0) -> List[Dict[str, Any]]:
    """Fetch orders with value above a threshold."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM orders WHERE total_amount >= ? ORDER BY total_amount DESC',
            (threshold,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_orders_pending_shipment() -> List[Dict[str, Any]]:
    """Fetch orders ready to be shipped."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE status = ? ORDER BY created_at', (OrderStatus.CONFIRMED.value,))
        return [dict(row) for row in cursor.fetchall()]


def get_recent_orders(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch the most recent orders."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_total_refunded_amount() -> float:
    """Get total amount refunded."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT SUM(amount) FROM refunds WHERE status = ?',
            (RefundStatus.COMPLETED.value,)
        )
        result = cursor.fetchone()[0]
        return result if result is not None else 0.0


def count_orders_by_status(status: str) -> int:
    """Count orders with a specific status."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = ?', (status,))
        return cursor.fetchone()[0]


def format_status_enum(status_str: str) -> str:
    """Convert status string to enum value or return original."""
    try:
        return OrderStatus[status_str.upper()].value
    except KeyError:
        return status_str


def parse_refund_status(status_str: str) -> str:
    """Parse and validate refund status string."""
    valid_statuses = {s.value for s in RefundStatus}
    return status_str if status_str in valid_statuses else RefundStatus.REQUESTED.value


def calculate_item_subtotal(unit_price: float, quantity: int) -> float:
    """Calculate subtotal for an order item."""
    return unit_price * quantity


def calculate_order_tax(amount: float, tax_rate: float = 0.10) -> float:
    """Calculate tax amount for an order."""
    return amount * tax_rate


def apply_discount(amount: float, discount_percent: float) -> float:
    """Apply percentage discount to an amount."""
    if discount_percent < 0 or discount_percent > 100:
        return amount
    return amount * (1 - discount_percent / 100)


def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    return f"${amount:.2f}"


def is_order_delivered(order_id: int) -> bool:
    """Check if an order has been delivered."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        return row[0] == OrderStatus.DELIVERED.value if row else False


def is_refundable(order_id: int) -> bool:
    """Check if an order is eligible for refund."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        if not row:
            return False
        status = row[0]
        return status not in [OrderStatus.CANCELLED.value, OrderStatus.REFUNDED.value]


def get_customer_lifetime_value(customer_id: int) -> float:
    """Calculate total spending by a customer."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT SUM(total_amount) FROM orders WHERE customer_id = ? AND status = ?',
            (customer_id, OrderStatus.DELIVERED.value)
        )
        result = cursor.fetchone()[0]
        return result if result is not None else 0.0


def get_orders_need_attention() -> List[Dict[str, Any]]:
    """Fetch orders that need immediate attention (stuck in pending state)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM orders
            WHERE status = ? AND created_at < datetime('now', '-7 days')
            ORDER BY created_at
        ''', (OrderStatus.PENDING.value,))
        return [dict(row) for row in cursor.fetchall()]


def bulk_update_order_status(order_ids: List[int], new_status: str) -> int:
    """Update status for multiple orders at once."""
    with get_db() as conn:
        cursor = conn.cursor()
        updated_count = 0
        for order_id in order_ids:
            cursor.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
            row = cursor.fetchone()
            if row:
                old_status = row[0]
                cursor.execute(
                    'UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (new_status, order_id)
                )
                cursor.execute(
                    'INSERT INTO order_history (order_id, old_status, new_status) VALUES (?, ?, ?)',
                    (order_id, old_status, new_status)
                )
                updated_count += 1
        return updated_count
