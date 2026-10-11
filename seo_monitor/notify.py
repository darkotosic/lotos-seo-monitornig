"""Optional Telegram notifications. No webhook, no incoming commands, no customer data."""

from __future__ import annotations

import os

import httpx


def send_telegram(message: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False
    # Limit Telegram length and avoid exposing token in exceptions/logs.
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with httpx.Client(timeout=12) as client:
            response = client.post(endpoint, json={"chat_id": chat_id, "text": message[:3500],
                                                   "disable_web_page_preview": True})
            response.raise_for_status()
            return bool(response.json().get("ok", False))
    except (httpx.HTTPError, ValueError):
        return False
