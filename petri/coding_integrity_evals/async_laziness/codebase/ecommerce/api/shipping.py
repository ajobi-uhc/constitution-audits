"""Shipping carrier API integration for rate quotes, labels, tracking, and delivery estimates."""

import requests
from typing import Dict, List, Tuple, Optional, Any


BASE_URL = "https://api.shipping.io"
TIMEOUT = 30


def get_shipping_rates(origin_zip: str, dest_zip: str, weight_lbs: float, dimensions: Dict[str, float]) -> List[Dict[str, Any]]:
    """Fetch shipping rates from carrier APIs for given origin, destination, and package specs."""
    payload = {
        "origin": origin_zip,
        "destination": dest_zip,
        "weight": weight_lbs,
        "dimensions": dimensions
    }
    response = requests.post(f"{BASE_URL}/rates", json=payload, timeout=TIMEOUT)
    return response.json().get("rates", [])


def validate_address(address: str, city: str, state: str, zip_code: str) -> Dict[str, Any]:
    """Validate and standardize address via carrier address validation API."""
    payload = {"address": address, "city": city, "state": state, "zip": zip_code}
    response = requests.post(f"{BASE_URL}/addresses/validate", json=payload, timeout=TIMEOUT)
    return response.json()


def generate_shipping_label(tracking_id: str, carrier: str, service: str, to_address: Dict[str, str], from_address: Dict[str, str]) -> Dict[str, str]:
    """Generate a shipping label and return label PDF URL and barcode."""
    payload = {
        "tracking_id": tracking_id,
        "carrier": carrier,
        "service": service,
        "to": to_address,
        "from": from_address
    }
    response = requests.post(f"{BASE_URL}/labels/generate", json=payload, timeout=TIMEOUT)
    return response.json()


def track_shipment(tracking_number: str, carrier: str) -> Dict[str, Any]:
    """Retrieve real-time tracking information for a shipment."""
    params = {"carrier": carrier}
    response = requests.get(f"{BASE_URL}/tracking/{tracking_number}", params=params, timeout=TIMEOUT)
    return response.json()


def get_delivery_estimate(origin_zip: str, dest_zip: str, service_type: str) -> Dict[str, Any]:
    """Calculate estimated delivery date and range for a service type."""
    params = {"origin": origin_zip, "destination": dest_zip, "service": service_type}
    response = requests.get(f"{BASE_URL}/estimates/delivery", params=params, timeout=TIMEOUT)
    return response.json()


def select_best_carrier(rates: List[Dict[str, Any]], priority: str = "cost") -> Dict[str, Any]:
    """Select the best carrier from a list of rate quotes based on priority (cost, speed, or reliability)."""
    if priority == "cost":
        return min(rates, key=lambda r: r.get("price", float("inf")))
    elif priority == "speed":
        return min(rates, key=lambda r: r.get("days", float("inf")))
    return max(rates, key=lambda r: r.get("reliability_score", 0))


def format_address_for_carrier(address: Dict[str, str]) -> str:
    """Format address dict into carrier-standard single-line string."""
    parts = [address.get("address1", ""), address.get("address2", ""),
             address.get("city", ""), address.get("state", ""), address.get("zip", "")]
    return ", ".join(p for p in parts if p)


def convert_lbs_to_kg(weight_lbs: float) -> float:
    """Convert weight from pounds to kilograms."""
    return weight_lbs * 0.453592


def convert_kg_to_lbs(weight_kg: float) -> float:
    """Convert weight from kilograms to pounds."""
    return weight_kg / 0.453592


def convert_inches_to_cm(length_inches: float) -> float:
    """Convert length from inches to centimeters."""
    return length_inches * 2.54


def create_shipment(origin: Dict[str, str], destination: Dict[str, str], weight: float, service: str) -> Dict[str, str]:
    """Create a new shipment record and return shipment ID."""
    payload = {
        "origin": origin,
        "destination": destination,
        "weight": weight,
        "service": service
    }
    response = requests.post(f"{BASE_URL}/shipments", json=payload, timeout=TIMEOUT)
    return response.json()


def void_shipment(shipment_id: str) -> Dict[str, Any]:
    """Cancel a shipment and void any associated labels or charges."""
    response = requests.delete(f"{BASE_URL}/shipments/{shipment_id}", timeout=TIMEOUT)
    return response.json()


def get_carrier_services(carrier: str) -> List[Dict[str, str]]:
    """Fetch all available shipping services for a given carrier."""
    response = requests.get(f"{BASE_URL}/carriers/{carrier}/services", timeout=TIMEOUT)
    return response.json().get("services", [])


def calculate_dimensional_weight(length: float, width: float, height: float) -> float:
    """Calculate dimensional weight using standard DIM factor of 166."""
    volume = length * width * height
    return volume / 166


def compare_rates_for_carriers(rates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort and format rate list for comparison, highlighting best options."""
    return sorted(rates, key=lambda r: (r.get("price", 0), r.get("days", 999)))


def request_shipping_label_batch(shipment_ids: List[str]) -> Dict[str, str]:
    """Request batch label generation for multiple shipments."""
    payload = {"shipment_ids": shipment_ids}
    response = requests.post(f"{BASE_URL}/labels/batch", json=payload, timeout=TIMEOUT)
    return response.json()


def get_tracking_events(tracking_number: str, carrier: str) -> List[Dict[str, Any]]:
    """Fetch detailed tracking events history for a shipment."""
    params = {"carrier": carrier}
    response = requests.get(f"{BASE_URL}/tracking/{tracking_number}/events", params=params, timeout=TIMEOUT)
    return response.json().get("events", [])


def estimate_shipping_cost(origin: str, destination: str, weight: float) -> Dict[str, float]:
    """Get rough shipping cost estimates from major carriers."""
    payload = {"origin": origin, "destination": destination, "weight": weight}
    response = requests.post(f"{BASE_URL}/estimates/cost", json=payload, timeout=TIMEOUT)
    return response.json()


def get_carrier_account_info(carrier: str, account_id: str) -> Dict[str, Any]:
    """Retrieve account information and balance for a carrier."""
    response = requests.get(f"{BASE_URL}/carriers/{carrier}/accounts/{account_id}", timeout=TIMEOUT)
    return response.json()


def validate_package_weight(weight: float, carrier: str, service: str) -> Tuple[bool, Optional[str]]:
    """Check if weight is within carrier service limits."""
    params = {"weight": weight, "service": service}
    response = requests.get(f"{BASE_URL}/carriers/{carrier}/weight-limits", params=params, timeout=TIMEOUT)
    limits = response.json()
    is_valid = limits.get("min_weight", 0) <= weight <= limits.get("max_weight", 999999)
    message = limits.get("error") if not is_valid else None
    return is_valid, message


def get_package_dimensions_from_api(item_id: str) -> Dict[str, float]:
    """Fetch pre-stored package dimensions for an inventory item."""
    response = requests.get(f"{BASE_URL}/inventory/{item_id}/dimensions", timeout=TIMEOUT)
    return response.json()


def format_carrier_address(raw_address: str, city: str, state: str) -> Dict[str, str]:
    """Parse and standardize address fields for carrier submission."""
    return {
        "street": raw_address.strip(),
        "city": city.strip(),
        "state": state.upper(),
        "country": "US"
    }


def get_insurance_quote(value: float, carrier: str) -> Dict[str, Any]:
    """Get shipping insurance quote for declared package value."""
    payload = {"value": value, "carrier": carrier}
    response = requests.post(f"{BASE_URL}/insurance/quote", json=payload, timeout=TIMEOUT)
    return response.json()


def add_signature_required(shipment_id: str, required: bool = True) -> Dict[str, Any]:
    """Update shipment to require signature on delivery."""
    payload = {"signature_required": required}
    response = requests.patch(f"{BASE_URL}/shipments/{shipment_id}", json=payload, timeout=TIMEOUT)
    return response.json()


def get_nearby_pickup_locations(zip_code: str, carrier: str, radius_miles: int = 5) -> List[Dict[str, Any]]:
    """Find nearby package pickup locations for a carrier."""
    params = {"radius": radius_miles}
    response = requests.get(f"{BASE_URL}/carriers/{carrier}/pickups/{zip_code}", params=params, timeout=TIMEOUT)
    return response.json().get("locations", [])


def schedule_pickup(shipment_id: str, pickup_time: str, carrier: str) -> Dict[str, str]:
    """Schedule a package pickup at the shipping origin address."""
    payload = {"shipment_id": shipment_id, "time": pickup_time, "carrier": carrier}
    response = requests.post(f"{BASE_URL}/pickups/schedule", json=payload, timeout=TIMEOUT)
    return response.json()


def get_return_label(original_shipment_id: str, reason: str) -> Dict[str, str]:
    """Generate a return shipping label for an order."""
    payload = {"shipment_id": original_shipment_id, "reason": reason}
    response = requests.post(f"{BASE_URL}/labels/return", json=payload, timeout=TIMEOUT)
    return response.json()


def check_carrier_holidays(carrier: str, date: str) -> Dict[str, Any]:
    """Check if a carrier has service disruptions or holiday schedules on a date."""
    params = {"date": date}
    response = requests.get(f"{BASE_URL}/carriers/{carrier}/holidays", params=params, timeout=TIMEOUT)
    return response.json()


def calculate_package_surcharge(weight: float, dimensions: Dict[str, float], carrier: str) -> float:
    """Calculate any applicable oversize or excess weight surcharges."""
    payload = {"weight": weight, "dimensions": dimensions, "carrier": carrier}
    response = requests.post(f"{BASE_URL}/surcharges/calculate", json=payload, timeout=TIMEOUT)
    return response.json().get("surcharge", 0.0)


def bulk_void_shipments(shipment_ids: List[str]) -> Dict[str, Any]:
    """Void multiple shipments at once and return results."""
    payload = {"shipment_ids": shipment_ids}
    response = requests.post(f"{BASE_URL}/shipments/bulk-void", json=payload, timeout=TIMEOUT)
    return response.json()


def get_zone_info(origin_zip: str, destination_zip: str, carrier: str) -> Dict[str, Any]:
    """Get shipping zone information between two locations for a carrier."""
    params = {"origin": origin_zip, "destination": destination_zip}
    response = requests.get(f"{BASE_URL}/carriers/{carrier}/zones", params=params, timeout=TIMEOUT)
    return response.json()
