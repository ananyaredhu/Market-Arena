"""Person C routes: Telegram campaigns (opt-in, approval, A/B send, results) and webhook.

Stubs return canned data when MOCK=1. Real version: consent log, /start and /stop, human approval
gate, A/B split, frequency cap, click/button tracking.
"""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Header, HTTPException

from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled

from . import service

router = APIRouter(tags=["telegram (C)"])


@router.post("/telegram/campaigns")
def create_campaign(body: dict | None = None, authorization: str | None = Header(default=None)):
    operator(authorization)
    if mock_enabled():
        return {
            "id": "cmp_1",
            "subscribe_link": "https://t.me/example_bot?start=cmp_1",
            "variants": load_fixture("kit")["assets"]["telegram_variants"],
            "approved": False,
        }
    return service.create(body or {})


@router.post("/telegram/campaigns/{campaign_id}/send")
def send_campaign(
    campaign_id: str,
    authorization: str | None = Header(default=None),
    project_id: str | None = None,
    run_id: str | None = None,
):
    operator(authorization)
    if mock_enabled():
        return {"id": campaign_id, "status": "sent", "recipients": 0}
    return service.send(campaign_id, project_id, run_id)


@router.get("/telegram/campaigns/{campaign_id}/results")
def campaign_results(
    campaign_id: str,
    authorization: str | None = Header(default=None),
    project_id: str | None = None,
    run_id: str | None = None,
):
    operator(authorization)
    if mock_enabled():
        return {
            "id": campaign_id,
            "variants": [
                {"variant": "A", "sent": 10, "clicks": 3, "interested": 2, "too_expensive": 1},
                {"variant": "B", "sent": 10, "clicks": 5, "interested": 4, "too_expensive": 0},
            ],
        }
    return service.results(campaign_id, project_id, run_id)


@router.post("/telegram/webhook/{secret}")
def webhook(
    secret: str,
    update: dict | None = None,
    token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    if mock_enabled():
        return {"ok": True}
    check(secret, "TELEGRAM_WEBHOOK_PATH_SECRET")
    check(token, "TELEGRAM_WEBHOOK_SECRET")
    return service.receive(update or {})


def check(value, name):
    expected = os.getenv(name, "")
    if not expected:
        raise HTTPException(503, "Telegram configuration incomplete")
    if not value or not hmac.compare_digest(value.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(401, "Invalid credentials")


def operator(authorization):
    if not mock_enabled():
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Operator authentication required")
        check(authorization[7:], "TELEGRAM_OPERATOR_TOKEN")


@router.post("/telegram/campaigns/{campaign_id}/approve")
def approve_campaign(
    campaign_id: str,
    authorization: str | None = Header(default=None),
    project_id: str | None = None,
    run_id: str | None = None,
):
    operator(authorization)
    if mock_enabled():
        return {"id": campaign_id, "approved": True}
    return service.approve(campaign_id, project_id, run_id)
