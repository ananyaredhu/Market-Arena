"""Consent, scoped approval, durable send claims and response attribution."""

import hashlib
import json
import os
import time
import uuid

from fastapi import HTTPException

from .client import BotClient, TelegramError
from .provenance import check_scope, source_for
from .security import contains_credentials
from .store import database


def get(db, identifier, project_id=None, run_id=None):
    row = db.execute("SELECT * FROM campaigns WHERE id=?", (identifier,)).fetchone()
    if row is None:
        raise HTTPException(404, "Campaign not found")
    check_scope(row, project_id, run_id)
    return row


def link(identifier):
    name = os.getenv("TELEGRAM_BOT_USERNAME", "")
    return f"https://t.me/{name}?start={identifier}" if name else None


def assignment(identifier, chat):
    return int(hashlib.sha256(f"{identifier}:{chat}".encode()).hexdigest(), 16) % 2


def create(body):
    variants = body.get("variants")
    if (
        not isinstance(variants, list)
        or len(variants) != 2
        or any(not isinstance(t, str) or not t.strip() or len(t) > 3900 for t in variants)
    ):
        raise HTTPException(422, "Supply exactly two variants, each 1 to 3900 characters")
    source = source_for(body)
    if contains_credentials({"body": body, "source": source}):
        raise HTTPException(422, "Campaign content must not contain credentials")
    identifier = "cmp_" + uuid.uuid4().hex[:20]
    with database() as db:
        db.execute(
            "INSERT INTO campaigns(id,variants,created,run_id,project_id,kit_source) VALUES(?,?,?,?,?,?)",
            (identifier, json.dumps(variants), time.time(), body["run_id"], body["project_id"], json.dumps(source)),
        )
    return {
        "id": identifier,
        "variants": variants,
        "approved": False,
        "subscribe_link": link(identifier),
        "project_id": body["project_id"],
        "run_id": body["run_id"],
        "kit_source": source,
    }


def approve(identifier, project_id=None, run_id=None):
    with database() as db:
        get(db, identifier, project_id, run_id)
        db.execute("UPDATE campaigns SET approved=1 WHERE id=?", (identifier,))
    return {"id": identifier, "approved": True}


def eligible(db, identifier, chat):
    return db.execute(
        "SELECT s.generation,s.last_command_id FROM subscribers s JOIN memberships m ON m.chat=s.chat "
        "WHERE s.chat=? AND s.active=1 AND m.campaign=?",
        (chat, identifier),
    ).fetchone()


def setting(db, key):
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else 0


def set_max(db, key, value):
    db.execute(
        "INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=max(value,excluded.value)", (key, value)
    )


def claim(identifier, chat):
    """Atomically reserve cap capacity and a bot-wide paced slot; no network."""
    now = time.time()
    with database() as db:
        consent = eligible(db, identifier, chat)
        if not consent:
            return None
        old = db.execute("SELECT * FROM deliveries WHERE campaign=? AND chat=?", (identifier, chat)).fetchone()
        if old and (old["status"] != "deferred" or old["retry_at"] > now):
            return None
        recent = db.execute(
            "SELECT at FROM deliveries WHERE chat=? AND at>? AND status IN ('sent','sending','unknown') ORDER BY at",
            (chat, now - 604800),
        ).fetchall()
        cooldown = setting(db, "cooldown_until")
        reason = "frequency_cap" if len(recent) >= 2 else ("bot_cooldown" if cooldown > now else None)
        retry_at = recent[-2][0] + 604800 if len(recent) >= 2 else cooldown
        status = "deferred" if reason else "sending"
        delivery = old["id"] if old else uuid.uuid4().hex[:24]
        variant = assignment(identifier, chat)
        db.execute(
            "INSERT INTO deliveries(id,campaign,chat,variant,status,at,retry_at,reason,consent_generation) "
            "VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(campaign,chat) DO UPDATE SET "
            "status=excluded.status,at=excluded.at,retry_at=excluded.retry_at,reason=excluded.reason,"
            "consent_generation=excluded.consent_generation",
            (delivery, identifier, chat, variant, status, now, retry_at if reason else 0, reason, consent[0]),
        )
        slot = max(now, setting(db, "next_slot"))
        if not reason:
            set_max(db, "next_slot", slot + 0.05)
        return {
            "id": delivery,
            "chat": chat,
            "variant": variant,
            "generation": consent[0],
            "command_id": consent[1],
            "status": status,
            "slot": slot,
        }


def ready(identifier, delivery):
    """Final short transaction immediately before dispatch. Stop never waits on HTTP."""
    with database() as db:
        consent = eligible(db, identifier, delivery["chat"])
        if not consent or consent[0] != delivery["generation"]:
            db.execute(
                "UPDATE deliveries SET status='cancelled',reason='consent_revoked' WHERE id=?", (delivery["id"],)
            )
            return "cancelled"
        cooldown = setting(db, "cooldown_until")
        if cooldown > time.time():
            db.execute(
                "UPDATE deliveries SET status='deferred',reason='bot_cooldown',retry_at=? WHERE id=?",
                (cooldown, delivery["id"]),
            )
            return "deferred"
        return "sending"


def complete(identifier, delivery, result=None, error=None):
    now = time.time()
    with database() as db:
        if error is None:
            db.execute(
                "UPDATE deliveries SET status='sent',message_id=?,at=?,reason=NULL WHERE id=?",
                (result["message_id"], now, delivery["id"]),
            )
            consent = eligible(db, identifier, delivery["chat"])
            if not consent or consent[0] != delivery["generation"]:
                db.execute("INSERT OR IGNORE INTO events VALUES(?,?,?)", (delivery["id"], "unsubscribes", now))
            return "sent"
        status = "deferred" if error.code == 429 else ("failed" if 400 <= error.code < 500 else "unknown")
        retry_at = now + max(error.retry_after, 1) if status == "deferred" else 0
        db.execute(
            "UPDATE deliveries SET status=?,retry_at=?,reason=? WHERE id=?",
            (status, retry_at, "telegram_429" if error.code == 429 else f"telegram_{error.code}", delivery["id"]),
        )
        if error.code == 429:
            set_max(db, "cooldown_until", retry_at)
        if error.code == 403:
            # A transport response must not overwrite a newer explicit /start.
            db.execute(
                "UPDATE subscribers SET active=0,generation=generation+1 "
                "WHERE chat=? AND generation=? AND last_command_id=?",
                (delivery["chat"], delivery["generation"], delivery["command_id"]),
            )
            if db.execute("SELECT changes()").fetchone()[0]:
                db.execute("DELETE FROM memberships WHERE chat=?", (delivery["chat"],))
                db.execute("INSERT INTO consent_log VALUES(?,?,?,?)", (delivery["chat"], 0, identifier, now))
        return status


def send(identifier, project_id=None, run_id=None):
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise HTTPException(503, "Telegram bot is not configured")
    counts = dict(sent=0, failed=0, unknown=0, deferred=0, cancelled=0)
    with database() as db:
        row = get(db, identifier, project_id, run_id)
        if not row["approved"]:
            raise HTTPException(409, "Campaign requires human approval")
        texts = json.loads(row["variants"])
        audience = [
            r[0]
            for r in db.execute(
                "SELECT m.chat FROM memberships m JOIN subscribers s ON s.chat=m.chat "
                "WHERE m.campaign=? AND s.active=1 ORDER BY m.chat",
                (identifier,),
            )
        ]
    for chat in audience:
        delivery = claim(identifier, chat)
        if delivery is None:
            continue
        if delivery["status"] == "deferred":
            counts["deferred"] += 1
            continue
        time.sleep(max(0, delivery["slot"] - time.time()))
        state = ready(identifier, delivery)
        if state != "sending":
            counts[state] += 1
            continue
        keyboard = [
            [{"text": label, "callback_data": f"{delivery['id']}:{kind}"}]
            for label, kind in [
                ("Interested", "interested"),
                ("Too expensive", "too_expensive"),
                ("Learn more", "clicks"),
            ]
        ]
        # No SQLite transaction is alive here. An opt-out after ready() can race
        # with this irreversible HTTP request; do not promise message recall.
        try:
            result = BotClient().send(chat, texts[delivery["variant"]] + "\n\nReply /stop to unsubscribe.", keyboard)
        except TelegramError as error:
            state = complete(identifier, delivery, error=error)
        else:
            state = complete(identifier, delivery, result=result)
        counts[state] += 1
    return {"id": identifier, "status": "processed", "recipients": counts["sent"], **counts}


def consent_command(db, msg, command, parts):
    chat = msg["chat"]["id"]
    message_id = msg.get("message_id")
    if type(message_id) is not int or message_id <= 0:
        raise HTTPException(422, "Consent commands require a positive Telegram message_id")
    previous = db.execute("SELECT * FROM subscribers WHERE chat=?", (chat,)).fetchone()
    # Telegram update_id can reset after inactivity. Private-chat message_id is
    # the per-chat ordering key; replayed/older commands never mutate consent.
    if previous and message_id <= previous["last_command_id"]:
        return None
    if command == "/start":
        if len(parts) != 2:
            return None
        identifier = parts[1]
        row = db.execute("SELECT * FROM campaigns WHERE id=?", (identifier,)).fetchone()
        if not row or not row["project_id"] or not row["kit_source"]:
            return None
        db.execute(
            "INSERT INTO subscribers(chat,active,consent,last_command_id) VALUES(?,1,?,?) "
            "ON CONFLICT(chat) DO UPDATE SET active=1,consent=excluded.consent,"
            "last_command_id=excluded.last_command_id",
            (chat, time.time(), message_id),
        )
        db.execute("INSERT OR IGNORE INTO memberships VALUES(?,?)", (identifier, chat))
        db.execute("INSERT INTO consent_log VALUES(?,?,?,?)", (chat, 1, identifier, time.time()))
        return (chat, "You subscribed to Market Arena promotional tests. Reply /stop at any time to unsubscribe.")
    db.execute(
        "INSERT INTO subscribers(chat,active,consent,last_command_id,generation) VALUES(?,0,?,?,1) "
        "ON CONFLICT(chat) DO UPDATE SET active=0,last_command_id=excluded.last_command_id,generation=generation+1",
        (chat, time.time(), message_id),
    )
    db.execute("DELETE FROM memberships WHERE chat=?", (chat,))
    db.execute("INSERT INTO consent_log VALUES(?,?,?,?)", (chat, 0, None, time.time()))
    db.execute(
        "INSERT OR IGNORE INTO events SELECT id,'unsubscribes',? FROM deliveries WHERE chat=? AND status='sent'",
        (time.time(), chat),
    )
    return (chat, "You are unsubscribed from all Market Arena promotional tests.")


def service_call(method, **payload):
    # Acknowledgements are best effort, but share the bot-wide cooldown too.
    with database() as db:
        if setting(db, "cooldown_until") > time.time():
            return
    try:
        BotClient().call(method, **payload)
    except TelegramError as error:
        if error.code == 429:
            with database() as db:
                set_max(db, "cooldown_until", time.time() + max(error.retry_after, 1))


def receive(update):
    acknowledgement = None
    msg = update.get("message") or {}
    callback = update.get("callback_query") or {}
    if not isinstance(msg, dict) or not isinstance(callback, dict):
        raise HTTPException(422, "Invalid update structure")
    for obj, key in ((msg, "chat"), (msg, "reply_to_message"), (callback, "from")):
        if key in obj and not isinstance(obj[key], dict):
            raise HTTPException(422, "Invalid update structure")
    if type(update.get("update_id")) is not int:
        raise HTTPException(422, "Integer update_id required")
    with database() as db:
        if db.execute("SELECT 1 FROM updates WHERE id=?", (update["update_id"],)).fetchone():
            return {"ok": True}
        chat = msg.get("chat") or {}
        text = msg.get("text", "")
        if chat.get("type") == "private" and type(chat.get("id")) is int and isinstance(text, str):
            parts = text.split(maxsplit=1)
            command = parts[0].split("@")[0] if parts else ""
            if command in ("/start", "/stop"):
                acknowledgement = consent_command(db, msg, command, parts)
            elif msg.get("reply_to_message"):
                row = db.execute(
                    "SELECT id FROM deliveries WHERE chat=? AND message_id=? AND status='sent'",
                    (chat["id"], msg["reply_to_message"].get("message_id")),
                ).fetchone()
                if row:
                    db.execute("INSERT OR IGNORE INTO events VALUES(?,?,?)", (row[0], "replies", time.time()))
        parts = str(callback.get("data", "")).split(":")
        if len(parts) == 2 and parts[1] in ("interested", "too_expensive", "clicks"):
            row = db.execute(
                "SELECT id FROM deliveries WHERE id=? AND chat=? AND status='sent'",
                (parts[0], callback.get("from", {}).get("id")),
            ).fetchone()
            if row:
                db.execute("INSERT OR IGNORE INTO events VALUES(?,?,?)", (parts[0], parts[1], time.time()))
        db.execute("INSERT INTO updates VALUES(?)", (update["update_id"],))
    if acknowledgement:
        service_call("sendMessage", chat_id=acknowledgement[0], text=acknowledgement[1])
    if callback.get("id"):
        service_call("answerCallbackQuery", callback_query_id=callback["id"])
    return {"ok": True}


def results(identifier, project_id=None, run_id=None):
    with database() as db:
        row = get(db, identifier, project_id, run_id)
        audience = [
            r[0]
            for r in db.execute(
                "SELECT m.chat FROM memberships m JOIN subscribers s ON s.chat=m.chat "
                "WHERE m.campaign=? AND s.active=1",
                (identifier,),
            )
        ]
        variants = []
        for i, label in enumerate("AB"):
            totals = {
                "variant": label,
                "sent": db.execute(
                    "SELECT count(*) FROM deliveries WHERE campaign=? AND variant=? AND status='sent'", (identifier, i)
                ).fetchone()[0],
            }
            for kind in ("clicks", "interested", "too_expensive", "replies", "unsubscribes"):
                totals[kind] = db.execute(
                    "SELECT count(*) FROM events e JOIN deliveries d ON d.id=e.delivery "
                    "WHERE d.campaign=? AND d.variant=? AND e.kind=?",
                    (identifier, i, kind),
                ).fetchone()[0]
            variants.append(totals)
        statuses = dict(
            db.execute("SELECT status,count(*) FROM deliveries WHERE campaign=? GROUP BY status", (identifier,))
        )
        reasons = dict(
            db.execute(
                "SELECT reason,count(*) FROM deliveries WHERE campaign=? AND status='deferred' GROUP BY reason",
                (identifier,),
            )
        )
        retry_at = db.execute(
            "SELECT min(retry_at) FROM deliveries WHERE campaign=? AND status='deferred'", (identifier,)
        ).fetchone()[0]
        cooldown = setting(db, "cooldown_until")
    return {
        "id": identifier,
        "project_id": row["project_id"],
        "run_id": row["run_id"],
        "kit_source": json.loads(row["kit_source"]),
        "message_variants": json.loads(row["variants"]),
        "approved": bool(row["approved"]),
        "variants": variants,
        "contacts": len(audience),
        "variant_sizes": [sum(assignment(identifier, chat) == i for chat in audience) for i in range(2)],
        "delivery_statuses": statuses,
        "deferred_reasons": reasons,
        "next_retry_at": max(retry_at, cooldown) if retry_at is not None else None,
        "bot_cooldown_until": cooldown,
        "subscribe_link": link(identifier),
    }
