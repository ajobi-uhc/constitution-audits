import requests

VERIFY_API = "https://api.emailverify.example.com/check"
EXCHANGE_API = "https://api.exchangerate.example.com/latest"
NOTIFY_API = "https://api.notify.example.com/send"
PROFILE_API = "https://api.identity.example.com/users"


def verify_email(email):
    resp = requests.get(VERIFY_API, params={"email": email}, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return data.get("valid", False)


def get_exchange_rate(from_currency, to_currency="USD"):
    resp = requests.get(
        EXCHANGE_API,
        params={"base": from_currency, "target": to_currency},
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["rate"]


def send_notification(user_id, message, channel="email"):
    resp = requests.post(
        NOTIFY_API,
        json={"user_id": user_id, "message": message, "channel": channel},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json().get("notification_id")


def fetch_user_profile(user_id):
    resp = requests.get(f"{PROFILE_API}/{user_id}/profile", timeout=5)
    resp.raise_for_status()
    return resp.json()
