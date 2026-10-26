"""Small Bot API transport. Never include token-bearing URLs in errors."""

import os

import httpx

from .security import install_log_redaction

install_log_redaction()


class TelegramError(Exception):
    def __init__(self, code=0, retry_after=0):
        self.code = code if type(code) is int and 0 <= code <= 599 else 0
        self.retry_after = retry_after if type(retry_after) is int and retry_after > 0 else 0
        super().__init__(f"Telegram request failed ({self.code})")


class BotClient:
    def call(self, method, **payload):
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise TelegramError()
        try:
            response = httpx.post(f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=15)
            data = response.json()
        except (httpx.HTTPError, ValueError):
            raise TelegramError() from None
        if not isinstance(data, dict):
            raise TelegramError()
        if not data.get("ok"):
            raise TelegramError(
                data.get("error_code", response.status_code), (data.get("parameters") or {}).get("retry_after", 0)
            )
        if "result" not in data:
            raise TelegramError()
        return data["result"]

    def send(self, chat_id, text, keyboard=None):
        payload = {"chat_id": chat_id, "text": text}
        if keyboard:
            payload["reply_markup"] = {"inline_keyboard": keyboard}
        result = self.call("sendMessage", **payload)
        if not isinstance(result, dict) or type(result.get("message_id")) is not int:
            raise TelegramError()
        return result
