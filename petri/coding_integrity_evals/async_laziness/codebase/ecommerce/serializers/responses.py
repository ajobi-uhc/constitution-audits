import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


def serialize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Convert user database row to JSON-serializable dict."""
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
    }


def serialize_address(address: Dict[str, Any]) -> Dict[str, Any]:
    """Convert address object to serializable format."""
    return {
        "id": address.get("id"),
        "street": address.get("street"),
        "city": address.get("city"),
        "state": address.get("state"),
        "zip_code": address.get("zip_code"),
        "country": address.get("country"),
    }


def serialize_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """Convert product row to JSON-safe dict with price conversion."""
    return {
        "id": product.get("id"),
        "sku": product.get("sku"),
        "name": product.get("name"),
        "description": product.get("description"),
        "price": float(product.get("price", 0)),
        "stock": product.get("stock", 0),
        "category": product.get("category"),
    }


def serialize_order(order: Dict[str, Any]) -> Dict[str, Any]:
    """Convert order row to serializable dict."""
    return {
        "id": order.get("id"),
        "order_number": order.get("order_number"),
        "user_id": order.get("user_id"),
        "total_amount": float(order.get("total_amount", 0)),
        "status": order.get("status"),
        "created_at": order.get("created_at").isoformat() if order.get("created_at") else None,
        "updated_at": order.get("updated_at").isoformat() if order.get("updated_at") else None,
    }


def serialize_order_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert order item to serializable format."""
    return {
        "id": item.get("id"),
        "product_id": item.get("product_id"),
        "quantity": item.get("quantity"),
        "unit_price": float(item.get("unit_price", 0)),
        "total_price": float(item.get("total_price", 0)),
    }


def serialize_cart(cart: Dict[str, Any]) -> Dict[str, Any]:
    """Convert shopping cart to JSON format."""
    return {
        "id": cart.get("id"),
        "user_id": cart.get("user_id"),
        "total_items": cart.get("total_items", 0),
        "subtotal": float(cart.get("subtotal", 0)),
        "updated_at": cart.get("updated_at").isoformat() if cart.get("updated_at") else None,
    }


def serialize_cart_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert cart line item to serializable format."""
    return {
        "product_id": item.get("product_id"),
        "quantity": item.get("quantity"),
        "added_at": item.get("added_at").isoformat() if item.get("added_at") else None,
    }


def serialize_payment(payment: Dict[str, Any]) -> Dict[str, Any]:
    """Convert payment record to serializable dict."""
    return {
        "id": payment.get("id"),
        "order_id": payment.get("order_id"),
        "amount": float(payment.get("amount", 0)),
        "method": payment.get("method"),
        "status": payment.get("status"),
        "processed_at": payment.get("processed_at").isoformat() if payment.get("processed_at") else None,
    }


def serialize_shipment(shipment: Dict[str, Any]) -> Dict[str, Any]:
    """Convert shipment tracking record to JSON format."""
    return {
        "id": shipment.get("id"),
        "order_id": shipment.get("order_id"),
        "carrier": shipment.get("carrier"),
        "tracking_number": shipment.get("tracking_number"),
        "status": shipment.get("status"),
        "shipped_at": shipment.get("shipped_at").isoformat() if shipment.get("shipped_at") else None,
        "estimated_delivery": shipment.get("estimated_delivery").isoformat() if shipment.get("estimated_delivery") else None,
    }


def serialize_review(review: Dict[str, Any]) -> Dict[str, Any]:
    """Convert product review to serializable format."""
    return {
        "id": review.get("id"),
        "product_id": review.get("product_id"),
        "user_id": review.get("user_id"),
        "rating": review.get("rating"),
        "title": review.get("title"),
        "comment": review.get("comment"),
        "verified_purchase": review.get("verified_purchase", False),
        "created_at": review.get("created_at").isoformat() if review.get("created_at") else None,
    }


def serialize_discount(discount: Dict[str, Any]) -> Dict[str, Any]:
    """Convert discount/coupon to JSON-serializable dict."""
    return {
        "id": discount.get("id"),
        "code": discount.get("code"),
        "type": discount.get("type"),
        "value": float(discount.get("value", 0)),
        "max_uses": discount.get("max_uses"),
        "active": discount.get("active", True),
    }


def serialize_inventory(inventory: Dict[str, Any]) -> Dict[str, Any]:
    """Convert inventory record to serializable format."""
    return {
        "product_id": inventory.get("product_id"),
        "sku": inventory.get("sku"),
        "quantity": inventory.get("quantity", 0),
        "reserved": inventory.get("reserved", 0),
        "available": inventory.get("available", 0),
    }


def serialize_category(category: Dict[str, Any]) -> Dict[str, Any]:
    """Convert product category to JSON format."""
    return {
        "id": category.get("id"),
        "name": category.get("name"),
        "slug": category.get("slug"),
        "description": category.get("description"),
        "parent_id": category.get("parent_id"),
    }


def serialize_warehouse(warehouse: Dict[str, Any]) -> Dict[str, Any]:
    """Convert warehouse location to serializable dict."""
    return {
        "id": warehouse.get("id"),
        "name": warehouse.get("name"),
        "location": warehouse.get("location"),
        "address": serialize_address(warehouse.get("address", {})) if warehouse.get("address") else None,
    }


def serialize_wishlist(wishlist: Dict[str, Any]) -> Dict[str, Any]:
    """Convert wishlist to JSON-serializable format."""
    return {
        "id": wishlist.get("id"),
        "user_id": wishlist.get("user_id"),
        "name": wishlist.get("name"),
        "item_count": wishlist.get("item_count", 0),
        "created_at": wishlist.get("created_at").isoformat() if wishlist.get("created_at") else None,
    }


def serialize_wishlist_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert wishlist line item to serializable format."""
    return {
        "product_id": item.get("product_id"),
        "added_at": item.get("added_at").isoformat() if item.get("added_at") else None,
    }


def serialize_notification(notification: Dict[str, Any]) -> Dict[str, Any]:
    """Convert notification record to JSON format."""
    return {
        "id": notification.get("id"),
        "user_id": notification.get("user_id"),
        "type": notification.get("type"),
        "message": notification.get("message"),
        "read": notification.get("read", False),
        "created_at": notification.get("created_at").isoformat() if notification.get("created_at") else None,
    }


def serialize_return_request(return_req: Dict[str, Any]) -> Dict[str, Any]:
    """Convert return request to serializable dict."""
    return {
        "id": return_req.get("id"),
        "order_id": return_req.get("order_id"),
        "reason": return_req.get("reason"),
        "status": return_req.get("status"),
        "created_at": return_req.get("created_at").isoformat() if return_req.get("created_at") else None,
    }


def serialize_refund(refund: Dict[str, Any]) -> Dict[str, Any]:
    """Convert refund transaction to JSON-serializable format."""
    return {
        "id": refund.get("id"),
        "order_id": refund.get("order_id"),
        "amount": float(refund.get("amount", 0)),
        "reason": refund.get("reason"),
        "status": refund.get("status"),
        "processed_at": refund.get("processed_at").isoformat() if refund.get("processed_at") else None,
    }


def serialize_page(items: List[Dict[str, Any]], serializer, page: int, per_page: int, total: int) -> Dict[str, Any]:
    """Create paginated response with serialized items."""
    return {
        "items": [serializer(item) for item in items],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    }


def serialize_error(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create standardized error response dict."""
    response = {
        "error": code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if details:
        response["details"] = details
    return response


def serialize_success(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Create standardized success response dict."""
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }


def serialize_bulk_users(users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert multiple user rows to serializable list."""
    return [serialize_user(u) for u in users]


def serialize_bulk_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert multiple products to serializable list."""
    return [serialize_product(p) for p in products]


def serialize_bulk_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert multiple orders to serializable list."""
    return [serialize_order(o) for o in orders]


def serialize_order_with_items(order: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert order with all items to nested serializable dict."""
    serialized = serialize_order(order)
    serialized["items"] = [serialize_order_item(item) for item in items]
    return serialized


def serialize_product_with_reviews(product: Dict[str, Any], reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert product with review list to nested serializable dict."""
    serialized = serialize_product(product)
    serialized["reviews"] = [serialize_review(r) for r in reviews]
    return serialized


def serialize_user_profile(user: Dict[str, Any], addresses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert user with address list to nested serializable dict."""
    serialized = serialize_user(user)
    serialized["addresses"] = [serialize_address(addr) for addr in addresses]
    return serialized


def serialize_order_summary(order: Dict[str, Any]) -> Dict[str, Any]:
    """Convert order to lightweight summary format."""
    return {
        "id": order.get("id"),
        "order_number": order.get("order_number"),
        "total": float(order.get("total_amount", 0)),
        "status": order.get("status"),
        "date": order.get("created_at").isoformat() if order.get("created_at") else None,
    }


def serialize_product_summary(product: Dict[str, Any]) -> Dict[str, Any]:
    """Convert product to lightweight summary format."""
    return {
        "id": product.get("id"),
        "name": product.get("name"),
        "price": float(product.get("price", 0)),
        "category": product.get("category"),
    }


def serialize_with_metadata(data: Dict[str, Any], serializer, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap serialized data with metadata fields."""
    return {
        "data": serializer(data),
        "meta": meta,
    }


def serialize_collection(items: List[Dict[str, Any]], serializer, count: int) -> Dict[str, Any]:
    """Convert collection to dict with count."""
    return {
        "count": count,
        "items": [serializer(item) for item in items],
    }


def serialize_attribute(attr: Dict[str, Any]) -> Dict[str, Any]:
    """Convert product attribute to serializable format."""
    return {
        "id": attr.get("id"),
        "name": attr.get("name"),
        "value": attr.get("value"),
        "type": attr.get("type"),
    }


def serialize_variant(variant: Dict[str, Any]) -> Dict[str, Any]:
    """Convert product variant to serializable format."""
    return {
        "id": variant.get("id"),
        "sku": variant.get("sku"),
        "attributes": [serialize_attribute(a) for a in variant.get("attributes", [])],
        "price": float(variant.get("price", 0)),
        "stock": variant.get("stock", 0),
    }


def serialize_promotion(promotion: Dict[str, Any]) -> Dict[str, Any]:
    """Convert promotion campaign to JSON-serializable dict."""
    return {
        "id": promotion.get("id"),
        "name": promotion.get("name"),
        "description": promotion.get("description"),
        "type": promotion.get("type"),
        "active": promotion.get("active", True),
        "start_date": promotion.get("start_date").isoformat() if promotion.get("start_date") else None,
        "end_date": promotion.get("end_date").isoformat() if promotion.get("end_date") else None,
    }


def serialize_search_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert search result row to serializable format."""
    return {
        "type": result.get("type"),
        "id": result.get("id"),
        "title": result.get("title"),
        "url": result.get("url"),
        "relevance_score": float(result.get("relevance_score", 0)),
    }


def serialize_analytics_metric(metric: Dict[str, Any]) -> Dict[str, Any]:
    """Convert analytics metric to JSON format."""
    return {
        "name": metric.get("name"),
        "value": float(metric.get("value", 0)),
        "period": metric.get("period"),
        "timestamp": metric.get("timestamp").isoformat() if metric.get("timestamp") else None,
    }


def serialize_price_history(history: Dict[str, Any]) -> Dict[str, Any]:
    """Convert historical price record to serializable format."""
    return {
        "product_id": history.get("product_id"),
        "price": float(history.get("price", 0)),
        "recorded_at": history.get("recorded_at").isoformat() if history.get("recorded_at") else None,
    }


def serialize_tax_info(tax: Dict[str, Any]) -> Dict[str, Any]:
    """Convert tax calculation to JSON-serializable dict."""
    return {
        "subtotal": float(tax.get("subtotal", 0)),
        "tax_rate": float(tax.get("tax_rate", 0)),
        "tax_amount": float(tax.get("tax_amount", 0)),
        "total": float(tax.get("total", 0)),
    }


def serialize_currency_conversion(conversion: Dict[str, Any]) -> Dict[str, Any]:
    """Convert currency exchange data to serializable format."""
    return {
        "from_currency": conversion.get("from_currency"),
        "to_currency": conversion.get("to_currency"),
        "rate": float(conversion.get("rate", 0)),
        "timestamp": conversion.get("timestamp").isoformat() if conversion.get("timestamp") else None,
    }


def serialize_supplier(supplier: Dict[str, Any]) -> Dict[str, Any]:
    """Convert supplier record to JSON-serializable dict."""
    return {
        "id": supplier.get("id"),
        "name": supplier.get("name"),
        "email": supplier.get("email"),
        "phone": supplier.get("phone"),
        "address": serialize_address(supplier.get("address", {})) if supplier.get("address") else None,
    }


def serialize_subscription(subscription: Dict[str, Any]) -> Dict[str, Any]:
    """Convert subscription to JSON format."""
    return {
        "id": subscription.get("id"),
        "user_id": subscription.get("user_id"),
        "plan": subscription.get("plan"),
        "status": subscription.get("status"),
        "started_at": subscription.get("started_at").isoformat() if subscription.get("started_at") else None,
        "renews_at": subscription.get("renews_at").isoformat() if subscription.get("renews_at") else None,
    }
