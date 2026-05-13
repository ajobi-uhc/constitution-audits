import sqlite3
import datetime
from typing import List, Dict, Tuple, Optional, Any

DB_PATH = "ecommerce.db"


def init_inventory_db() -> None:
    """Initialize inventory database schema if not exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            product_id INTEGER PRIMARY KEY,
            warehouse_id TEXT NOT NULL,
            stock_level INTEGER NOT NULL,
            reserved INTEGER NOT NULL DEFAULT 0,
            reorder_point INTEGER NOT NULL,
            max_stock INTEGER NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            warehouse_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            order_id TEXT UNIQUE,
            status TEXT DEFAULT 'active'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            warehouse_id TEXT NOT NULL,
            action TEXT NOT NULL,
            quantity_change INTEGER,
            reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warehouse_config (
            warehouse_id TEXT PRIMARY KEY,
            warehouse_name TEXT NOT NULL,
            location TEXT,
            capacity INTEGER,
            active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def add_warehouse(warehouse_id: str, warehouse_name: str, location: str, capacity: int) -> bool:
    """Insert a new warehouse into the system."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO warehouse_config (warehouse_id, warehouse_name, location, capacity) VALUES (?, ?, ?, ?)",
            (warehouse_id, warehouse_name, location, capacity)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_warehouse_info(warehouse_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve warehouse configuration details by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT warehouse_id, warehouse_name, location, capacity, active FROM warehouse_config WHERE warehouse_id = ?",
        (warehouse_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "warehouse_id": row[0],
            "warehouse_name": row[1],
            "location": row[2],
            "capacity": row[3],
            "active": row[4]
        }
    return None


def list_all_warehouses() -> List[Dict[str, Any]]:
    """Retrieve all active warehouses in the system."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT warehouse_id, warehouse_name, location, capacity FROM warehouse_config WHERE active = 1 ORDER BY warehouse_id"
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"warehouse_id": r[0], "warehouse_name": r[1], "location": r[2], "capacity": r[3]} for r in rows]


def add_stock(product_id: int, warehouse_id: str, quantity: int, reorder_point: int, max_stock: int) -> bool:
    """Add inventory entry for product in warehouse."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO inventory (product_id, warehouse_id, stock_level, reorder_point, max_stock) VALUES (?, ?, ?, ?, ?)",
            (product_id, warehouse_id, quantity, reorder_point, max_stock)
        )
        cursor.execute(
            "INSERT INTO audit_log (product_id, warehouse_id, action, quantity_change, reason) VALUES (?, ?, ?, ?, ?)",
            (product_id, warehouse_id, "initial_stock", quantity, "Initial stock entry")
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_stock_level(product_id: int, warehouse_id: str) -> Optional[int]:
    """Get current stock level for product in warehouse."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT stock_level FROM inventory WHERE product_id = ? AND warehouse_id = ?",
        (product_id, warehouse_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def get_available_stock(product_id: int, warehouse_id: str) -> Optional[int]:
    """Get available stock after accounting for reservations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT stock_level, reserved FROM inventory WHERE product_id = ? AND warehouse_id = ?",
        (product_id, warehouse_id)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0] - row[1]
    return None


def increment_stock(product_id: int, warehouse_id: str, quantity: int, reason: str) -> bool:
    """Increase stock level and log the transaction."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE inventory SET stock_level = stock_level + ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?",
            (quantity, product_id, warehouse_id)
        )
        cursor.execute(
            "INSERT INTO audit_log (product_id, warehouse_id, action, quantity_change, reason) VALUES (?, ?, ?, ?, ?)",
            (product_id, warehouse_id, "increment", quantity, reason)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def decrement_stock(product_id: int, warehouse_id: str, quantity: int, reason: str) -> bool:
    """Decrease stock level and log the transaction."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT stock_level FROM inventory WHERE product_id = ? AND warehouse_id = ?",
            (product_id, warehouse_id)
        )
        row = cursor.fetchone()
        if not row or row[0] < quantity:
            return False
        cursor.execute(
            "UPDATE inventory SET stock_level = stock_level - ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?",
            (quantity, product_id, warehouse_id)
        )
        cursor.execute(
            "INSERT INTO audit_log (product_id, warehouse_id, action, quantity_change, reason) VALUES (?, ?, ?, ?, ?)",
            (product_id, warehouse_id, "decrement", -quantity, reason)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def reserve_stock(product_id: int, warehouse_id: str, quantity: int, order_id: str) -> Optional[int]:
    """Reserve stock for an order and return reservation ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT stock_level, reserved FROM inventory WHERE product_id = ? AND warehouse_id = ?",
            (product_id, warehouse_id)
        )
        row = cursor.fetchone()
        if not row or (row[0] - row[1]) < quantity:
            return None
        cursor.execute(
            "INSERT INTO reservations (product_id, warehouse_id, quantity, order_id, status) VALUES (?, ?, ?, ?, ?)",
            (product_id, warehouse_id, quantity, order_id, "active")
        )
        cursor.execute(
            "UPDATE inventory SET reserved = reserved + ? WHERE product_id = ? AND warehouse_id = ?",
            (quantity, product_id, warehouse_id)
        )
        reservation_id = cursor.lastrowid
        conn.commit()
        return reservation_id
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def release_reservation(reservation_id: int) -> bool:
    """Release a stock reservation and update inventory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT product_id, warehouse_id, quantity FROM reservations WHERE reservation_id = ? AND status = 'active'",
            (reservation_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False
        product_id, warehouse_id, quantity = row
        cursor.execute(
            "UPDATE reservations SET status = 'cancelled' WHERE reservation_id = ?",
            (reservation_id,)
        )
        cursor.execute(
            "UPDATE inventory SET reserved = reserved - ? WHERE product_id = ? AND warehouse_id = ?",
            (quantity, product_id, warehouse_id)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def confirm_reservation(reservation_id: int) -> bool:
    """Convert reservation to actual stock deduction."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT product_id, warehouse_id, quantity FROM reservations WHERE reservation_id = ? AND status = 'active'",
            (reservation_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False
        product_id, warehouse_id, quantity = row
        cursor.execute(
            "UPDATE inventory SET stock_level = stock_level - ?, reserved = reserved - ? WHERE product_id = ? AND warehouse_id = ?",
            (quantity, quantity, product_id, warehouse_id)
        )
        cursor.execute(
            "UPDATE reservations SET status = 'confirmed' WHERE reservation_id = ?",
            (reservation_id,)
        )
        cursor.execute(
            "INSERT INTO audit_log (product_id, warehouse_id, action, quantity_change, reason) VALUES (?, ?, ?, ?, ?)",
            (product_id, warehouse_id, "order_fulfillment", -quantity, f"Reservation {reservation_id} confirmed")
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def get_reservations(product_id: int, warehouse_id: str) -> List[Dict[str, Any]]:
    """Get all active reservations for a product in a warehouse."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reservation_id, quantity, reserved_at, order_id FROM reservations WHERE product_id = ? AND warehouse_id = ? AND status = 'active' ORDER BY reserved_at",
        (product_id, warehouse_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"reservation_id": r[0], "quantity": r[1], "reserved_at": r[2], "order_id": r[3]} for r in rows]


def calculate_reorder_point(avg_daily_usage: int, lead_time_days: int, safety_stock: int) -> int:
    """Calculate reorder point based on usage and lead time."""
    return (avg_daily_usage * lead_time_days) + safety_stock


def classify_stock_level(current: int, reorder_point: int, max_stock: int) -> str:
    """Classify stock level as optimal, low, critical, or overstocked."""
    if current <= 0:
        return "critical"
    elif current < reorder_point:
        return "low"
    elif current > max_stock:
        return "overstocked"
    else:
        return "optimal"


def format_warehouse_code(location: str, sequence: int) -> str:
    """Generate formatted warehouse code from location and sequence number."""
    location_code = "".join([c.upper() for c in location.split() if c.isalpha()])[:3]
    return f"{location_code}-{sequence:04d}"


def get_low_stock_products(warehouse_id: str) -> List[Dict[str, Any]]:
    """Retrieve all products below reorder point in a warehouse."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT product_id, stock_level, reorder_point, max_stock FROM inventory WHERE warehouse_id = ? AND stock_level < reorder_point ORDER BY stock_level",
        (warehouse_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"product_id": r[0], "stock_level": r[1], "reorder_point": r[2], "max_stock": r[3]} for r in rows]


def get_critical_stock_products(warehouse_id: str) -> List[Dict[str, Any]]:
    """Retrieve products at critical stock levels (0 or below reorder point)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT product_id, stock_level FROM inventory WHERE warehouse_id = ? AND stock_level <= 0 ORDER BY stock_level",
        (warehouse_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"product_id": r[0], "stock_level": r[1]} for r in rows]


def get_overstocked_products(warehouse_id: str) -> List[Dict[str, Any]]:
    """Retrieve products exceeding max stock level."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT product_id, stock_level, max_stock FROM inventory WHERE warehouse_id = ? AND stock_level > max_stock ORDER BY stock_level DESC",
        (warehouse_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"product_id": r[0], "stock_level": r[1], "max_stock": r[2]} for r in rows]


def get_warehouse_total_stock(warehouse_id: str) -> int:
    """Get total stock units across all products in a warehouse."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(stock_level) FROM inventory WHERE warehouse_id = ?",
        (warehouse_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row[0] else 0


def get_warehouse_reserved_stock(warehouse_id: str) -> int:
    """Get total reserved stock units in a warehouse."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(reserved) FROM inventory WHERE warehouse_id = ?",
        (warehouse_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row[0] else 0


def get_audit_history(product_id: int, warehouse_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get audit log entries for a product in a warehouse."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT audit_id, action, quantity_change, reason, timestamp FROM audit_log WHERE product_id = ? AND warehouse_id = ? ORDER BY timestamp DESC LIMIT ?",
        (product_id, warehouse_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"audit_id": r[0], "action": r[1], "quantity_change": r[2], "reason": r[3], "timestamp": r[4]} for r in rows]


def get_warehouse_audit_log(warehouse_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """Get audit log for all products in a warehouse from the past N days."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    cursor.execute(
        "SELECT audit_id, product_id, action, quantity_change, reason, timestamp FROM audit_log WHERE warehouse_id = ? AND timestamp > ? ORDER BY timestamp DESC",
        (warehouse_id, cutoff_date)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"audit_id": r[0], "product_id": r[1], "action": r[2], "quantity_change": r[3], "reason": r[4], "timestamp": r[5]} for r in rows]


def update_reorder_levels(product_id: int, warehouse_id: str, reorder_point: int, max_stock: int) -> bool:
    """Update reorder point and max stock for a product."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE inventory SET reorder_point = ?, max_stock = ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?",
            (reorder_point, max_stock, product_id, warehouse_id)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def transfer_stock(product_id: int, from_warehouse: str, to_warehouse: str, quantity: int) -> bool:
    """Transfer stock between warehouses."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT stock_level FROM inventory WHERE product_id = ? AND warehouse_id = ?",
            (product_id, from_warehouse)
        )
        row = cursor.fetchone()
        if not row or row[0] < quantity:
            return False
        cursor.execute(
            "UPDATE inventory SET stock_level = stock_level - ? WHERE product_id = ? AND warehouse_id = ?",
            (quantity, product_id, from_warehouse)
        )
        cursor.execute(
            "UPDATE inventory SET stock_level = stock_level + ? WHERE product_id = ? AND warehouse_id = ?",
            (quantity, product_id, to_warehouse)
        )
        cursor.execute(
            "INSERT INTO audit_log (product_id, warehouse_id, action, quantity_change, reason) VALUES (?, ?, ?, ?, ?)",
            (product_id, from_warehouse, "transfer_out", -quantity, f"Transfer to {to_warehouse}")
        )
        cursor.execute(
            "INSERT INTO audit_log (product_id, warehouse_id, action, quantity_change, reason) VALUES (?, ?, ?, ?, ?)",
            (product_id, to_warehouse, "transfer_in", quantity, f"Transfer from {from_warehouse}")
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def get_inventory_summary(warehouse_id: str) -> Dict[str, Any]:
    """Get complete inventory summary for a warehouse."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*), SUM(stock_level), SUM(reserved) FROM inventory WHERE warehouse_id = ?",
        (warehouse_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return {
        "product_count": row[0] if row[0] else 0,
        "total_stock": row[1] if row[1] else 0,
        "total_reserved": row[2] if row[2] else 0
    }


def count_products_by_status(warehouse_id: str) -> Dict[str, int]:
    """Count products in each status category (low, critical, optimal, overstocked)."""
    low = len(get_low_stock_products(warehouse_id))
    critical = len(get_critical_stock_products(warehouse_id))
    overstocked = len(get_overstocked_products(warehouse_id))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM inventory WHERE warehouse_id = ?",
        (warehouse_id,)
    )
    total = cursor.fetchone()[0]
    conn.close()
    optimal = total - low - critical - overstocked
    return {"optimal": optimal, "low": low, "critical": critical, "overstocked": overstocked}


def get_product_across_warehouses(product_id: int) -> List[Dict[str, Any]]:
    """Get inventory levels for a product across all warehouses."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT warehouse_id, stock_level, reserved, reorder_point FROM inventory WHERE product_id = ? ORDER BY warehouse_id",
        (product_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"warehouse_id": r[0], "stock_level": r[1], "reserved": r[2], "reorder_point": r[3]} for r in rows]


def get_total_product_stock(product_id: int) -> int:
    """Get total stock for a product across all warehouses."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(stock_level) FROM inventory WHERE product_id = ?",
        (product_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row[0] else 0


def delete_warehouse(warehouse_id: str) -> bool:
    """Deactivate a warehouse by setting active flag to 0."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE warehouse_config SET active = 0 WHERE warehouse_id = ?",
            (warehouse_id,)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def list_active_reservations() -> List[Dict[str, Any]]:
    """Get all active reservations across the system."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reservation_id, product_id, warehouse_id, quantity, order_id, reserved_at FROM reservations WHERE status = 'active' ORDER BY reserved_at DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"reservation_id": r[0], "product_id": r[1], "warehouse_id": r[2], "quantity": r[3], "order_id": r[4], "reserved_at": r[5]} for r in rows]


def get_inventory_by_product_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Get primary warehouse inventory record for a product."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT product_id, warehouse_id, stock_level, reserved, reorder_point, max_stock FROM inventory WHERE product_id = ? LIMIT 1",
        (product_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"product_id": row[0], "warehouse_id": row[1], "stock_level": row[2], "reserved": row[3], "reorder_point": row[4], "max_stock": row[5]}
    return None
