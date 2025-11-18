import random

import requests

from src.core.settings import JWT_TOKEN, NOTIFICATIONS_API_URL, OWNER_ID


def generate_confirmation_code() -> str:
    return f"{random.randint(100000, 999999)}"


def send_confirmation_email(msg_id: str, email: str, full_name: str, code: str) -> bool:
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "id": str(msg_id),
        "owner_id": str(OWNER_ID),
        "email": email,
        "message": f"Здравствуйте, {full_name}!\nВаш код подтверждения: {code}",
    }

    try:
        resp = requests.post(
            f"{NOTIFICATIONS_API_URL}", json=payload, headers=headers, timeout=(5, 10)
        )

        if 200 <= resp.status_code < 300:
            return True
        if resp.status_code in (409, 422):
            return True
        return False

    except requests.RequestException:
        return False
