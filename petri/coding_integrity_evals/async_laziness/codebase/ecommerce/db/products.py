"""
Product catalog database layer using sqlite3.
Handles product CRUD, categories, search, filtering, sorting, price history, variants, and featured products.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json

DB_PATH = "ecommerce.db"


def init_db() -> None:
    """Initialize database schema with products, categories, variants, and price history tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            category_id INTEGER REFERENCES categories(id),
            price REAL NOT NULL,
            cost REAL,
            stock INTEGER DEFAULT 0,
            is_featured INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER REFERENCES products(id),
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            price_modifier REAL DEFAULT 0,
            stock INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER REFERENCES products(id),
            price REAL NOT NULL,
            recorded_at TEXT NOT NULL
        )
    """)

    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_products_featured ON products(is_featured)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug)""")

    conn.commit()
    conn.close()


def create_category(name: str, slug: str, description: str = "") -> int:
    """Insert new category and return its ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO categories (name, slug, description) VALUES (?, ?, ?)",
        (name, slug, description)
    )
    conn.commit()
    category_id = cursor.lastrowid
    conn.close()
    return category_id


def get_category(category_id: int) -> Optional[Dict[str, Any]]:
    """Fetch category by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, slug, description FROM categories WHERE id = ?", (category_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "slug": row[2], "description": row[3]}
    return None


def list_categories() -> List[Dict[str, Any]]:
    """Return all categories."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, slug, description FROM categories ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "slug": r[2], "description": r[3]} for r in rows]


def update_category(category_id: int, name: str = None, description: str = None) -> bool:
    """Update category name or description."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if name:
        cursor.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    if description is not None:
        cursor.execute("UPDATE categories SET description = ? WHERE id = ?", (description, category_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def delete_category(category_id: int) -> bool:
    """Delete category if no products reference it."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def create_product(
    name: str,
    slug: str,
    price: float,
    category_id: Optional[int] = None,
    description: str = "",
    cost: float = 0,
    stock: int = 0
) -> int:
    """Create product and return its ID."""
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO products
           (name, slug, description, category_id, price, cost, stock, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, slug, description, category_id, price, cost, stock, now, now)
    )
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()

    record_price_history(product_id, price)
    return product_id


def get_product(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetch product by ID with all details."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE id = ?",
        (product_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "name": row[1], "slug": row[2], "description": row[3],
            "category_id": row[4], "price": row[5], "cost": row[6], "stock": row[7],
            "is_featured": bool(row[8]), "created_at": row[9], "updated_at": row[10]
        }
    return None


def get_product_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Fetch product by URL slug."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE slug = ?",
        (slug,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "name": row[1], "slug": row[2], "description": row[3],
            "category_id": row[4], "price": row[5], "cost": row[6], "stock": row[7],
            "is_featured": bool(row[8]), "created_at": row[9], "updated_at": row[10]
        }
    return None


def list_products(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Return paginated list of all products."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def list_products_by_category(category_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Return products in specified category."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE category_id = ? ORDER BY name LIMIT ? OFFSET ?",
        (category_id, limit, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def update_product(product_id: int, **kwargs: Any) -> bool:
    """Update product fields (name, price, description, stock, etc)."""
    allowed_fields = {"name", "description", "price", "cost", "stock", "category_id", "is_featured"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not updates:
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if "price" in updates:
        record_price_history(product_id, updates["price"])

    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [product_id]

    cursor.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def delete_product(product_id: int) -> bool:
    """Delete product and its variants/history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM product_variants WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def search_products(query: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Search products by name or description using LIKE."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    search_term = f"%{query}%"
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE name LIKE ? OR description LIKE ? LIMIT ?",
        (search_term, search_term, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def filter_products_by_price(min_price: float, max_price: float, limit: int = 100) -> List[Dict[str, Any]]:
    """Return products within price range."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE price >= ? AND price <= ? ORDER BY price ASC LIMIT ?",
        (min_price, max_price, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def filter_products_by_stock(min_stock: int = 1, limit: int = 100) -> List[Dict[str, Any]]:
    """Return products with at least min_stock in inventory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE stock >= ? ORDER BY stock DESC LIMIT ?",
        (min_stock, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def sort_products_by_field(field: str, direction: str = "ASC", limit: int = 100) -> List[Dict[str, Any]]:
    """Return products sorted by specified field (name, price, stock, created_at)."""
    valid_fields = {"name", "price", "stock", "created_at"}
    if field not in valid_fields or direction.upper() not in ("ASC", "DESC"):
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products ORDER BY {field} {direction.upper()} LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def record_price_history(product_id: int, price: float) -> None:
    """Record a price change in price history table."""
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO price_history (product_id, price, recorded_at) VALUES (?, ?, ?)",
        (product_id, price, now)
    )
    conn.commit()
    conn.close()


def get_price_history(product_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve price history for a product."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, product_id, price, recorded_at FROM price_history WHERE product_id = ? ORDER BY recorded_at DESC LIMIT ?",
        (product_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "product_id": r[1], "price": r[2], "recorded_at": r[3]} for r in rows]


def cleanup_old_price_history(days: int = 365) -> int:
    """Delete price history older than specified days."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    from datetime import timedelta
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    cursor.execute("DELETE FROM price_history WHERE recorded_at < ?", (cutoff,))
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()
    return deleted_count


def create_product_variant(product_id: int, name: str, sku: str, price_modifier: float = 0, stock: int = 0) -> int:
    """Create product variant (size, color, etc) and return its ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO product_variants (product_id, name, sku, price_modifier, stock) VALUES (?, ?, ?, ?, ?)",
        (product_id, name, sku, price_modifier, stock)
    )
    conn.commit()
    variant_id = cursor.lastrowid
    conn.close()
    return variant_id


def get_product_variant(variant_id: int) -> Optional[Dict[str, Any]]:
    """Fetch product variant by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, product_id, name, sku, price_modifier, stock FROM product_variants WHERE id = ?",
        (variant_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "product_id": row[1], "name": row[2], "sku": row[3], "price_modifier": row[4], "stock": row[5]}
    return None


def list_product_variants(product_id: int) -> List[Dict[str, Any]]:
    """List all variants for a product."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, product_id, name, sku, price_modifier, stock FROM product_variants WHERE product_id = ? ORDER BY name",
        (product_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "product_id": r[1], "name": r[2], "sku": r[3], "price_modifier": r[4], "stock": r[5]} for r in rows]


def update_product_variant(variant_id: int, **kwargs: Any) -> bool:
    """Update variant fields (name, price_modifier, stock)."""
    allowed_fields = {"name", "price_modifier", "stock"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not updates:
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [variant_id]
    cursor.execute(f"UPDATE product_variants SET {set_clause} WHERE id = ?", values)
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def delete_product_variant(variant_id: int) -> bool:
    """Delete product variant."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM product_variants WHERE id = ?", (variant_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def get_variant_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """Fetch variant by SKU code."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, product_id, name, sku, price_modifier, stock FROM product_variants WHERE sku = ?",
        (sku,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "product_id": row[1], "name": row[2], "sku": row[3], "price_modifier": row[4], "stock": row[5]}
    return None


def list_featured_products(limit: int = 100) -> List[Dict[str, Any]]:
    """Return featured products."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE is_featured = 1 ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def set_product_featured(product_id: int, is_featured: bool) -> bool:
    """Mark product as featured or remove from featured."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET is_featured = ? WHERE id = ?", (1 if is_featured else 0, product_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def get_low_stock_products(threshold: int = 10, limit: int = 100) -> List[Dict[str, Any]]:
    """Return products with stock below threshold."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE stock < ? AND stock > 0 ORDER BY stock ASC LIMIT ?",
        (threshold, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def get_out_of_stock_products(limit: int = 100) -> List[Dict[str, Any]]:
    """Return all out-of-stock products."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE stock = 0 ORDER BY name LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]


def adjust_product_stock(product_id: int, quantity_delta: int) -> bool:
    """Adjust product stock by delta (positive or negative)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (quantity_delta, product_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def get_product_margin(product_id: int) -> Optional[float]:
    """Calculate profit margin percentage (price - cost) / price."""
    product = get_product(product_id)
    if not product or product["price"] == 0:
        return None
    margin = ((product["price"] - product["cost"]) / product["price"]) * 100
    return round(margin, 2)


def bulk_update_prices(category_id: int, percentage_change: float) -> int:
    """Update all product prices in category by percentage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE products SET price = price * (1 + ?) WHERE category_id = ?",
        (percentage_change / 100, category_id)
    )
    conn.commit()
    updated_count = cursor.rowcount
    conn.close()
    return updated_count


def build_product_query(filters: Dict[str, Any]) -> str:
    """Build WHERE clause for product query based on filters (not DB IO)."""
    conditions = []
    if "category_id" in filters:
        conditions.append(f"category_id = {filters['category_id']}")
    if "min_price" in filters:
        conditions.append(f"price >= {filters['min_price']}")
    if "max_price" in filters:
        conditions.append(f"price <= {filters['max_price']}")
    if "in_stock" in filters and filters["in_stock"]:
        conditions.append("stock > 0")
    return " AND ".join(conditions) if conditions else "1=1"


def generate_product_slug(name: str) -> str:
    """Generate URL-safe slug from product name (not DB IO)."""
    slug = name.lower().strip().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return slug.rstrip("-")


def normalize_product_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize and normalize product input data (not DB IO)."""
    return {
        "name": data.get("name", "").strip(),
        "description": data.get("description", "").strip(),
        "price": max(0, float(data.get("price", 0))),
        "cost": max(0, float(data.get("cost", 0))),
        "stock": max(0, int(data.get("stock", 0))),
    }


def count_products_in_category(category_id: int) -> int:
    """Return count of products in category."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_total_product_count() -> int:
    """Return total number of products."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_inventory_value() -> float:
    """Calculate total inventory value (sum of price * stock)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(price * stock), 0) FROM products")
    value = cursor.fetchone()[0]
    conn.close()
    return round(value, 2)


def get_products_by_ids(product_ids: List[int]) -> List[Dict[str, Any]]:
    """Fetch multiple products by their IDs."""
    if not product_ids:
        return []
    placeholders = ",".join("?" * len(product_ids))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT id, name, slug, description, category_id, price, cost, stock, is_featured, created_at, updated_at FROM products WHERE id IN ({placeholders})",
        product_ids
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "slug": r[2], "description": r[3],
            "category_id": r[4], "price": r[5], "cost": r[6], "stock": r[7],
            "is_featured": bool(r[8]), "created_at": r[9], "updated_at": r[10]
        }
        for r in rows
    ]
