"""Redact Telegram credentials before any logging handler sees a record."""

import logging
import os
import re
import traceback
from urllib.parse import quote

SECRET_NAMES = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_OPERATOR_TOKEN",
    "TELEGRAM_WEBHOOK_PATH_SECRET",
    "TELEGRAM_WEBHOOK_SECRET",
)
TOKEN = re.compile(r"\b\d{5,}:[A-Za-z0-9_-]{20,}")
WEBHOOK = re.compile(r"(/telegram/webhook/)[^\s?\"<>]+")
BEARER = re.compile(r"Bearer\s+[^\s,\"']+", re.IGNORECASE)


def redact(text):
    text = str(text)
    text = WEBHOOK.sub(r"\1[REDACTED]", text)
    text = TOKEN.sub("[REDACTED]", text)
    text = BEARER.sub("Bearer [REDACTED]", text)
    for name in SECRET_NAMES:
        value = os.getenv(name)
        if value:
            text = text.replace(value, "[REDACTED]").replace(quote(value, safe=""), "[REDACTED]")
    return text


def install_log_redaction():
    previous = logging.getLogRecordFactory()
    if getattr(previous, "telegram_redaction", False):
        return

    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        if record.name == "uvicorn.access" and isinstance(record.args, tuple) and len(record.args) == 5:
            # AccessFormatter unpacks these arguments to build request_line.
            # Preserve numeric status codes and the tuple structure it requires.
            record.msg = redact(record.msg)
            record.args = tuple(value if isinstance(value, (int, float)) else redact(value) for value in record.args)
        else:
            # Format URL objects before arbitrary handlers see their raw values.
            record.msg = redact(record.getMessage())
            record.args = ()
        if record.exc_info:
            record.exc_text = redact("".join(traceback.format_exception(*record.exc_info)))
            record.exc_info = None
        if record.stack_info:
            record.stack_info = redact(record.stack_info)
        return record

    factory.telegram_redaction = True
    logging.setLogRecordFactory(factory)


def contains_credentials(value):
    if isinstance(value, str):
        return bool(TOKEN.search(value)) or any(os.getenv(name) and os.getenv(name) in value for name in SECRET_NAMES)
    if isinstance(value, dict):
        return any(contains_credentials(k) or contains_credentials(v) for k, v in value.items())
    if isinstance(value, list):
        return any(contains_credentials(v) for v in value)
    return False
