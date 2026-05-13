import sqlite3
import json

DB_PATH = "app.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def create_user(name, email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        (name, email)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def update_user_verified(user_id, verified=True):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE users SET verified = ? WHERE id = ?",
        (1 if verified else 0, user_id)
    )
    conn.commit()
    conn.close()


def get_user_orders(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def create_order(user_id, items, total, currency="USD"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "INSERT INTO orders (user_id, items, total, currency) VALUES (?, ?, ?, ?)",
        (user_id, json.dumps(items), total, currency)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM users ORDER BY id")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
