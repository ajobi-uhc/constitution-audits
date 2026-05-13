import csv
import json
from pathlib import Path

from db import get_user, get_user_orders, get_all_users


def export_orders_csv(user_id, filepath):
    orders = get_user_orders(user_id)
    user = get_user(user_id)

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "user_name", "items", "total", "currency", "date"])
        for order in orders:
            writer.writerow([
                order["id"],
                user["name"],
                order["items"],
                order["total"],
                order["currency"],
                order["created_at"],
            ])
    return len(orders)


def import_users_csv(filepath):
    created = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            from db import create_user
            user_id = create_user(row["name"], row["email"])
            created.append(user_id)
    return created


def generate_report(filepath):
    users = get_all_users()

    lines = [f"User Report - {len(users)} users\n", "=" * 40 + "\n"]
    for user in users:
        orders = get_user_orders(user["id"])
        total_spent = sum(o["total"] for o in orders)
        lines.append(f"\n{user['name']} ({user['email']})\n")
        lines.append(f"  Verified: {'Yes' if user['verified'] else 'No'}\n")
        lines.append(f"  Orders: {len(orders)}\n")
        lines.append(f"  Total spent: ${total_spent:.2f}\n")

    with open(filepath, "w") as f:
        f.writelines(lines)
    return len(users)
