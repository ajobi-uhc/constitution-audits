from db import (
    init_db,
    create_user,
    get_user,
    update_user_verified,
    create_order,
    get_user_orders,
)
from external import verify_email, get_exchange_rate, send_notification, fetch_user_profile
from export import export_orders_csv, generate_report
from pathlib import Path


def register_user(name, email):
    is_valid = verify_email(email)
    if not is_valid:
        raise ValueError(f"Invalid email: {email}")

    user_id = create_user(name, email)
    update_user_verified(user_id, True)

    send_notification(user_id, f"Welcome {name}! Your account is ready.")

    return user_id


def place_order(user_id, items, currency="USD"):
    user = get_user(user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    if currency != "USD":
        rate = get_exchange_rate(currency)
        total = sum(item["price"] * item["qty"] for item in items) * rate
    else:
        total = sum(item["price"] * item["qty"] for item in items)

    order_id = create_order(user_id, items, round(total, 2), currency)

    send_notification(user_id, f"Order #{order_id} confirmed: ${round(total, 2)}")

    return order_id


def get_user_summary(user_id):
    user = get_user(user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    profile = fetch_user_profile(user_id)
    orders = get_user_orders(user_id)

    return {
        "user": user,
        "profile": profile,
        "orders": orders,
        "total_spent": sum(o["total"] for o in orders),
        "order_count": len(orders),
    }


def export_user_data(user_id, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    orders_path = str(Path(output_dir) / "orders.csv")
    report_path = str(Path(output_dir) / "report.txt")

    num_orders = export_orders_csv(user_id, orders_path)
    num_users = generate_report(report_path)

    return {"orders_exported": num_orders, "report_users": num_users}
