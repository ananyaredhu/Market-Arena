from __future__ import annotations
"""Person C routes: Telegram campaigns (opt-in, approval, A/B send, results) and webhook.

Stubs return canned data when MOCK=1. Real version: consent log, /start and /stop, human approval
gate, A/B split, frequency cap, click/button tracking.
"""
from fastapi import APIRouter

from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled, not_built

router = APIRouter(tags=["telegram (C)"])


@router.post("/telegram/campaigns")
def create_campaign(body: dict | None = None):
    if mock_enabled():
        return {"id": "cmp_1", "subscribe_link": "https://t.me/example_bot?start=cmp_1",
                "variants": load_fixture("kit")["assets"]["telegram_variants"], "approved": False}
    raise not_built("POST /telegram/campaigns")


@router.post("/telegram/campaigns/{campaign_id}/send")
def send_campaign(campaign_id: str):
    if mock_enabled():
        return {"id": campaign_id, "status": "sent", "recipients": 0}
    raise not_built("POST /telegram/campaigns/{id}/send")


@router.get("/telegram/campaigns/{campaign_id}/results")
def campaign_results(campaign_id: str):
    if mock_enabled():
        return {"id": campaign_id, "variants": [
            {"variant": "A", "sent": 10, "clicks": 3, "interested": 2, "too_expensive": 1},
            {"variant": "B", "sent": 10, "clicks": 5, "interested": 4, "too_expensive": 0}]}
    raise not_built("GET /telegram/campaigns/{id}/results")


@router.post("/telegram/webhook/{secret}")
def webhook(secret: str, update: dict | None = None):
    if mock_enabled():
        return {"ok": True}
    raise not_built("POST /telegram/webhook/{secret}")
