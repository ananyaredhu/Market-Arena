import json
import os

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.telegram import service
from backend.telegram.client import BotClient, TelegramError
from backend.telegram.store import database


@pytest.fixture
def env(monkeypatch, tmp_path):
    for key, value in {
        "MOCK": "0",
        "TELEGRAM_DB_PATH": str(tmp_path / "tg.db"),
        "MARKET_ARENA_DATA_DIR": str(tmp_path / "projects"),
        "LLM_MODE": "mock",
        "COUNCIL_ENGINE": "engine",
        "TELEGRAM_OPERATOR_TOKEN": "operator",
        "TELEGRAM_WEBHOOK_PATH_SECRET": "path",
        "TELEGRAM_WEBHOOK_SECRET": "header",
        "TELEGRAM_BOT_TOKEN": "fake",
        "TELEGRAM_BOT_USERNAME": "arena_test_bot",
    }.items():
        monkeypatch.setenv(key, value)
    calls = []

    def send(self, chat, text, keyboard=None):
        calls.append((chat, text, keyboard))
        return {"message_id": len(calls)}

    monkeypatch.setattr(BotClient, "send", send)
    monkeypatch.setattr(BotClient, "call", lambda *args, **kwargs: True)
    monkeypatch.setattr(service.time, "sleep", lambda _: None)
    client = TestClient(app)
    project = client.post(
        "/projects", json={"idea": "StudyFlow study planner for students, S$9 per month.", "pack": "saas"}
    ).json()
    scenario = client.post(
        "/scenarios", json={"project_id": project["id"], "n_agents": 40, "repeats": 3, "seed": 7}
    ).json()
    run = client.post(f"/scenarios/{scenario['id']}/run").json()
    kit_response = client.post(f"/runs/{run['run_id']}/kit", json={"project_id": project["id"]})
    assert kit_response.status_code == 200, kit_response.text
    kit = kit_response.json()
    client.campaign_body = {
        "variants": ["A", "B"],
        "project_id": project["id"],
        "run_id": run["run_id"],
        "hypothesis_index": 0,
        "kit_context": {"hypotheses": kit["hypotheses"], "telegram_variants": kit["assets"]["telegram_variants"]},
    }
    return client, calls


AUTH = {"Authorization": "Bearer operator"}
HOOK = {"X-Telegram-Bot-Api-Secret-Token": "header"}


def scope(client):
    return {k: client.campaign_body[k] for k in ("project_id", "run_id")}


def url(client, identifier, action):
    from urllib.parse import urlencode

    return f"/telegram/campaigns/{identifier}/{action}?" + urlencode(scope(client))


def create(client):
    response = client.post("/telegram/campaigns", json=client.campaign_body, headers=AUTH)
    assert response.status_code == 200
    return response.json()["id"]


def update(client, n, chat, text, message_id=None):
    return client.post(
        "/telegram/webhook/path",
        headers=HOOK,
        json={
            "update_id": n,
            "message": {
                "chat": {"id": chat, "type": "private"},
                "text": text,
                "message_id": n if message_id is None else message_id,
            },
        },
    )


def test_full_flow_and_replay(env):
    c, calls = env
    identifier = create(c)
    assert c.post(url(c, identifier, "send"), headers=AUTH).status_code == 409
    for n in range(1, 5):
        assert update(c, n, n, "/start " + identifier).status_code == 200
    update(c, 5, 4, "/stop")
    c.post(url(c, identifier, "approve"), headers=AUTH)
    assert c.post(url(c, identifier, "send"), headers=AUTH).json()["recipients"] == 3
    assert len(calls) == 3
    assert c.post(url(c, identifier, "send"), headers=AUTH).json()["recipients"] == 0
    delivery, kind = calls[0][2][0][0]["callback_data"].split(":")
    payload = {"update_id": 20, "callback_query": {"from": {"id": calls[0][0]}, "data": f"{delivery}:{kind}"}}
    for _ in range(2):
        assert c.post("/telegram/webhook/path", json=payload, headers=HOOK).status_code == 200
    payload["update_id"] = 21
    payload["callback_query"]["from"]["id"] = 999
    c.post("/telegram/webhook/path", json=payload, headers=HOOK)
    result = c.get(url(c, identifier, "results"), headers=AUTH).json()
    assert sum(v["sent"] for v in result["variants"]) == 3
    assert sum(v["interested"] for v in result["variants"]) == 1
    assert result["contacts"] == 3
    with database() as db:
        assert db.execute("SELECT count(*) FROM consent_log").fetchone()[0] == 5


def test_security_validation(env):
    c, calls = env
    assert c.post("/telegram/campaigns", json={"variants": ["a", "b"]}).status_code == 401
    assert c.post("/telegram/campaigns", json={"variants": [""]}, headers=AUTH).status_code == 422
    assert c.post("/telegram/webhook/path", json={"update_id": 1}).status_code == 401
    assert c.post("/telegram/webhook/wrong", json={"update_id": 1}, headers=HOOK).status_code == 401
    assert c.get("/telegram/campaigns/absent/results", headers=AUTH).status_code == 404
    assert not calls


@pytest.mark.parametrize("code,status", [(0, "unknown"), (429, "deferred"), (403, "failed")])
def test_delivery_failures(env, monkeypatch, code, status):
    c, calls = env
    identifier = create(c)
    update(c, 1, 1, "/start " + identifier)
    c.post(url(c, identifier, "approve"), headers=AUTH)

    def fail(*args, **kwargs):
        raise TelegramError(code, 60)

    monkeypatch.setattr(BotClient, "send", fail)
    c.post(url(c, identifier, "send"), headers=AUTH)
    result = c.get(url(c, identifier, "results"), headers=AUTH).json()
    assert result["delivery_statuses"] == {status: 1}
    assert c.post(url(c, identifier, "send"), headers=AUTH).json()["recipients"] == 0


def test_frequency_cap_and_opt_back_in(env):
    c, calls = env
    for n in range(3):
        identifier = create(c)
        update(c, n + 1, 42, "/start " + identifier)
        c.post(url(c, identifier, "approve"), headers=AUTH)
        c.post(url(c, identifier, "send"), headers=AUTH)
    assert len(calls) == 2
    update(c, 10, 42, "/stop")
    update(c, 11, 42, "/start " + identifier)
    assert c.get(url(c, identifier, "results"), headers=AUTH).json()["contacts"] == 1


def test_mock_preserved(env, monkeypatch):
    c, calls = env
    monkeypatch.setenv("MOCK", "1")
    assert c.post("/telegram/campaigns").json()["id"] == "cmp_1"
    assert c.post("/telegram/campaigns/cmp_1/send").json()["status"] == "sent"
    assert c.post("/telegram/webhook/anything").json() == {"ok": True}
    assert not calls


def test_reply_and_private_consent_only(env):
    c, calls = env
    identifier = create(c)
    c.post(
        "/telegram/webhook/path",
        headers=HOOK,
        json={"update_id": 1, "message": {"chat": {"id": 8, "type": "group"}, "text": "/start " + identifier}},
    )
    assert service.results(identifier, **scope(c))["contacts"] == 0
    update(c, 2, 8, "/start " + identifier)
    service.approve(identifier, **scope(c))
    service.send(identifier, **scope(c))
    payload = {
        "update_id": 3,
        "message": {"chat": {"id": 8, "type": "private"}, "text": "Yes", "reply_to_message": {"message_id": 1}},
    }
    c.post("/telegram/webhook/path", headers=HOOK, json=payload)
    assert sum(v["replies"] for v in service.results(identifier, **scope(c))["variants"]) == 1


def test_transport_redacts_token(monkeypatch):
    import httpx

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "never-show-token")

    def fail(*args, **kwargs):
        raise httpx.ConnectError("never-show-token")

    monkeypatch.setattr(httpx, "post", fail)
    with pytest.raises(TelegramError) as error:
        BotClient().call("sendMessage", chat_id=1, text="a")
    assert "never-show-token" not in str(error.value)


def test_transport_payload_and_retry(monkeypatch):
    import httpx

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    requests = []

    def respond(url, **kwargs):
        requests.append(kwargs["json"])
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 4}})

    monkeypatch.setattr(httpx, "post", respond)
    assert BotClient().send(1, "text", [[{"text": "Yes", "callback_data": "yes"}]]) == {"message_id": 4}
    assert requests[0]["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "yes"
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: httpx.Response(429, json={"ok": False, "error_code": 429, "parameters": {"retry_after": 30}}),
    )
    with pytest.raises(TelegramError) as error:
        BotClient().send(1, "text")
    assert error.value.retry_after == 30


def test_concurrent_send_claims(env):
    from concurrent.futures import ThreadPoolExecutor

    c, calls = env
    identifier = create(c)
    update(c, 1, 22, "/start " + identifier)
    service.approve(identifier, **scope(c))
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda key: service.send(key, **scope(c)), [identifier, identifier]))
    assert sum(r["recipients"] for r in outcomes) == 1
    assert len(calls) == 1


def test_malformed_webhook(env):
    c, _ = env
    response = c.post("/telegram/webhook/path", headers=HOOK, json={"update_id": 1, "message": {"chat": "invalid"}})
    assert response.status_code == 422


def test_resubscribe_does_not_restore_old_campaign_consent(env):
    c, _ = env
    first, second = create(c), create(c)
    update(c, 1, 42, "/start " + first)
    update(c, 2, 42, "/stop")
    update(c, 3, 42, "/start " + second)
    assert service.results(first, **scope(c))["contacts"] == 0
    assert service.results(second, **scope(c))["contacts"] == 1


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch):
    import httpx

    def forbidden(*args, **kwargs):
        raise AssertionError("Telegram tests must not use a real HTTP transport")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


@pytest.mark.parametrize(
    "operation,method", [("create", "post"), ("approve", "post"), ("send", "post"), ("results", "get")]
)
@pytest.mark.parametrize("authorization", [None, "Bearer wrong", "Basic operator"])
def test_all_operator_actions_require_auth(env, operation, method, authorization):
    c, calls = env
    path = "/telegram/campaigns" if operation == "create" else url(c, "cmp_missing", operation)
    headers = {} if authorization is None else {"Authorization": authorization}
    assert getattr(c, method)(path, headers=headers).status_code == 401
    assert not calls


@pytest.mark.parametrize(
    "key,path,headers",
    [
        ("TELEGRAM_OPERATOR_TOKEN", "/telegram/campaigns", AUTH),
        ("TELEGRAM_WEBHOOK_PATH_SECRET", "/telegram/webhook/path", HOOK),
        ("TELEGRAM_WEBHOOK_SECRET", "/telegram/webhook/path", HOOK),
    ],
)
def test_missing_server_secrets_fail_closed(env, monkeypatch, key, path, headers):
    c, calls = env
    monkeypatch.delenv(key)
    assert c.post(path, headers=headers, json={"update_id": 1}).status_code == 503
    assert not calls


def test_missing_bot_token_and_wrong_header(env, monkeypatch):
    c, calls = env
    identifier = create(c)
    service.approve(identifier, **scope(c))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    assert c.post(url(c, identifier, "send"), headers=AUTH).status_code == 503
    assert (
        c.post(
            "/telegram/webhook/path", json={"update_id": 1}, headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}
        ).status_code
        == 401
    )
    assert not calls


@pytest.mark.parametrize(
    "overrides,status",
    [
        ({"run_id": None}, 422),
        ({"project_id": None}, 422),
        ({"run_id": "../../outside"}, 422),
        ({"project_id": "../outside"}, 422),
        ({"run_id": "run_42"}, 404),
        ({"project_id": "proj_missing"}, 404),
        ({"hypothesis_index": 100}, 422),
        ({"hypothesis_index": True}, 422),
        ({"kit_context": {}}, 409),
    ],
)
def test_invalid_campaign_provenance(env, overrides, status):
    c, calls = env
    response = c.post("/telegram/campaigns", json={**c.campaign_body, **overrides}, headers=AUTH)
    assert response.status_code == status, response.text
    with database() as db:
        assert db.execute("SELECT count(*) FROM campaigns").fetchone()[0] == 0
    assert not calls


def test_mismatched_project_and_scoped_operations(env):
    c, calls = env
    other = c.post("/projects", json={"idea": "A different study planner for S$8 per month.", "pack": "saas"}).json()
    assert (
        c.post("/telegram/campaigns", json={**c.campaign_body, "project_id": other["id"]}, headers=AUTH).status_code
        == 409
    )
    identifier = create(c)
    for action, method in [("results", "get"), ("approve", "post"), ("send", "post")]:
        path = url(c, identifier, action).replace(scope(c)["project_id"], other["id"])
        assert getattr(c, method)(path, headers=AUTH).status_code == 404
        path = url(c, identifier, action).replace(scope(c)["run_id"], "run_unrelated")
        assert getattr(c, method)(path, headers=AUTH).status_code == 404
        assert getattr(c, method)(f"/telegram/campaigns/{identifier}/{action}", headers=AUTH).status_code == 422
    assert not calls


def test_provenance_snapshot_and_mutated_run(env):
    from pathlib import Path

    c, _ = env
    identifier = create(c)
    observed = service.results(identifier, **scope(c))
    source = observed["kit_source"]
    assert observed["project_id"] == scope(c)["project_id"]
    assert observed["run_id"] == scope(c)["run_id"]
    assert source["kit"]["assets"]["telegram_variants"] == c.campaign_body["kit_context"]["telegram_variants"]
    assert source["hypothesis"] == c.campaign_body["kit_context"]["hypotheses"][0]
    assert len(source["run_digest"]) == len(source["kit_digest"]) == 64
    path = Path(os.environ["MARKET_ARENA_DATA_DIR"]) / "runs" / (scope(c)["run_id"] + ".json")
    bundle = json.loads(path.read_text())
    bundle["assumptions"]["test_mutation"] = True
    path.write_text(json.dumps(bundle))
    assert c.post(url(c, identifier, "approve"), headers=AUTH).status_code == 409


def test_stop_does_not_wait_for_network_or_allow_remaining_batch(env, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    c, calls = env
    identifier = create(c)
    update(c, 1, 1, "/start " + identifier)
    update(c, 2, 2, "/start " + identifier)
    service.approve(identifier, **scope(c))
    entered, release = Event(), Event()

    def blocked(self, chat, text, keyboard=None):
        calls.append((chat, text, keyboard))
        entered.set()
        assert release.wait(3), "test did not release fake transport"
        return {"message_id": 1}

    monkeypatch.setattr(BotClient, "send", blocked)
    with ThreadPoolExecutor(max_workers=2) as pool:
        sending = pool.submit(service.send, identifier, **scope(c))
        try:
            assert entered.wait(2)
            # Both revocations must finish while transport is still blocked.
            for n, chat in [(3, 1), (4, 2)]:
                stopped = pool.submit(update, c, n, chat, "/stop")
                assert stopped.result(timeout=1).status_code == 200
            with database() as db:
                assert db.execute("SELECT count(*) FROM subscribers WHERE active=1").fetchone()[0] == 0
        finally:
            release.set()
        assert sending.result(timeout=3)["recipients"] == 1
    assert [call[0] for call in calls] == [1]
    assert sum(v["unsubscribes"] for v in service.results(identifier, **scope(c))["variants"]) == 1


@pytest.mark.parametrize("same_campaign", [False, True])
def test_stop_and_resubscribe_invalidates_claim(env, monkeypatch, same_campaign):
    c, calls = env
    first, second = create(c), create(c)
    update(c, 1, 42, "/start " + first)
    service.approve(first, **scope(c))
    original = service.ready

    def revoke_before_dispatch(identifier, delivery):
        assert update(c, 2, 42, "/stop").status_code == 200
        assert update(c, 3, 42, "/start " + (first if same_campaign else second)).status_code == 200
        return original(identifier, delivery)

    monkeypatch.setattr(service, "ready", revoke_before_dispatch)
    assert service.send(first, **scope(c))["cancelled"] == 1
    assert not calls
    with database() as db:
        row = db.execute("SELECT * FROM deliveries").fetchone()
        assert row["status"] == "cancelled"


def test_stale_or_reordered_consent_cannot_restore_subscription(env):
    c, _ = env
    identifier = create(c)
    assert update(c, 1, 42, "/start " + identifier, message_id=10).status_code == 200
    assert update(c, 2, 42, "/stop", message_id=20).status_code == 200
    # A later update_id carrying an older message must be ignored.
    update(c, 3, 42, "/start " + identifier, message_id=15)
    assert service.results(identifier, **scope(c))["contacts"] == 0
    # A stop for a previously unseen chat creates an ordering tombstone.
    update(c, 4, 43, "/stop", message_id=20)
    update(c, 5, 43, "/start " + identifier, message_id=10)
    assert service.results(identifier, **scope(c))["contacts"] == 0
    # A genuinely newer start is allowed, even if its update_id is lower.
    update(c, 0, 42, "/start " + identifier, message_id=21)
    update(c, 6, 42, "/stop", message_id=19)
    assert service.results(identifier, **scope(c))["contacts"] == 1


def test_bot_cooldown_and_retry_preserves_successes(env, monkeypatch):
    c, calls = env
    clock = [1000000.0]
    monkeypatch.setattr(service.time, "time", lambda: clock[0])
    first, second = create(c), create(c)
    for n, chat in enumerate([1, 2, 3], 1):
        update(c, n, chat, "/start " + first)
    update(c, 4, 4, "/start " + second)
    for identifier in [first, second]:
        service.approve(identifier, **scope(c))
    fail = [True]

    def transport(self, chat, text, keyboard=None):
        calls.append((chat, text, keyboard))
        if chat == 2 and fail[0]:
            raise TelegramError(429, 60)
        return {"message_id": chat}

    monkeypatch.setattr(BotClient, "send", transport)
    result = service.send(first, **scope(c))
    assert result["sent"] == 1 and result["deferred"] == 2
    assert [x[0] for x in calls] == [1, 2]
    assert service.send(second, **scope(c))["deferred"] == 1
    assert [x[0] for x in calls] == [1, 2]
    observed = service.results(first, **scope(c))
    assert observed["delivery_statuses"] == {"sent": 1, "deferred": 2}
    assert observed["deferred_reasons"] == {"telegram_429": 1, "bot_cooldown": 1}
    clock[0] += 59
    service.send(first, **scope(c))
    assert len(calls) == 2
    clock[0] += 1
    fail[0] = False
    assert service.send(first, **scope(c))["sent"] == 2
    assert service.send(second, **scope(c))["sent"] == 1
    assert [x[0] for x in calls] == [1, 2, 2, 3, 4]
    assert service.results(first, **scope(c))["delivery_statuses"] == {"sent": 3}


def test_frequency_cap_expiry_is_persisted(env, monkeypatch):
    c, calls = env
    clock = [1000000.0]
    monkeypatch.setattr(service.time, "time", lambda: clock[0])
    for n in range(1, 4):
        identifier = create(c)
        update(c, n, 42, "/start " + identifier)
        service.approve(identifier, **scope(c))
        service.send(identifier, **scope(c))
    assert len(calls) == 2
    observed = service.results(identifier, **scope(c))
    assert observed["deferred_reasons"] == {"frequency_cap": 1}
    assert observed["next_retry_at"] == clock[0] + 604800
    clock[0] += 604800
    assert service.send(identifier, **scope(c))["sent"] == 1
    assert len(calls) == 3


def test_partial_failures_and_inflight_are_not_blindly_retried(env, monkeypatch):
    c, calls = env
    identifier = create(c)
    for n in range(1, 5):
        update(c, n, n, "/start " + identifier)
    service.approve(identifier, **scope(c))
    # Simulate a process dying immediately after its durable claim.
    claimed = service.claim(identifier, 4)

    def transport(self, chat, text, keyboard=None):
        calls.append((chat, text, keyboard))
        if chat in (2, 3):
            raise TelegramError(403 if chat == 2 else 0)
        return {"message_id": chat}

    monkeypatch.setattr(BotClient, "send", transport)
    result = service.send(identifier, **scope(c))
    assert (result["sent"], result["failed"], result["unknown"]) == (1, 1, 1)
    assert service.send(identifier, **scope(c))["recipients"] == 0
    assert len(calls) == 3
    statuses = service.results(identifier, **scope(c))["delivery_statuses"]
    assert statuses == {"sent": 1, "failed": 1, "unknown": 1, "sending": 1}
    with database() as db:
        assert db.execute("SELECT id FROM deliveries WHERE chat=4").fetchone()[0] == claimed["id"]
        assert db.execute("SELECT active FROM subscribers WHERE chat=2").fetchone()[0] == 0


def test_repeated_callbacks_with_different_update_ids_do_not_inflate_metrics(env):
    c, calls = env
    identifier = create(c)
    update(c, 1, 42, "/start " + identifier)
    service.approve(identifier, **scope(c))
    service.send(identifier, **scope(c))
    for n in range(2, 6):
        c.post(
            "/telegram/webhook/path",
            headers=HOOK,
            json={"update_id": n, "callback_query": {"from": {"id": 42}, "data": calls[0][2][0][0]["callback_data"]}},
        )
    assert sum(v["interested"] for v in service.results(identifier, **scope(c))["variants"]) == 1


@pytest.mark.parametrize(
    "secret_name",
    ["TELEGRAM_BOT_TOKEN", "TELEGRAM_OPERATOR_TOKEN", "TELEGRAM_WEBHOOK_SECRET", "TELEGRAM_WEBHOOK_PATH_SECRET"],
)
def test_campaigns_reject_accidental_credential_persistence(env, secret_name):
    c, _ = env
    body = {**c.campaign_body, "variants": ["Accidental " + os.environ[secret_name], "B"]}
    assert c.post("/telegram/campaigns", json=body, headers=AUTH).status_code == 422
    with database() as db:
        assert db.execute("SELECT count(*) FROM campaigns").fetchone()[0] == 0


def test_httpx_uvicorn_and_exception_logs_are_redacted(env, monkeypatch, caplog):
    import logging

    import httpx

    c, _ = env
    token = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdef123456789"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    monkeypatch.setenv("TELEGRAM_OPERATOR_TOKEN", "private-operator-credential")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_PATH_SECRET", "private-webhook-path")
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("httpx").info(
            "HTTP Request: POST %s", httpx.URL("https://api.telegram.org/bot" + token + "/sendMessage")
        )
        logging.getLogger("uvicorn.access").info(
            '%s - "%s %s HTTP/%s" %d', "127.0.0.1", "POST", "/telegram/webhook/private-webhook-path", "1.1", 200
        )
        try:
            raise RuntimeError("Bearer private-operator-credential " + token)
        except RuntimeError:
            logging.getLogger("telegram-test").exception("transport failed")
    for secret in [token, "private-operator-credential", "private-webhook-path"]:
        assert secret not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_legacy_schema_migration_preserves_claims_and_blocks_unverified_campaign(env, monkeypatch, tmp_path):
    import sqlite3

    c, _ = env
    path = tmp_path / "legacy.sqlite3"
    db = sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE campaigns (id TEXT PRIMARY KEY, variants TEXT NOT NULL, approved INTEGER DEFAULT 0,
      created REAL NOT NULL, run_id TEXT);
    CREATE TABLE subscribers (chat INTEGER PRIMARY KEY,active INTEGER NOT NULL,consent REAL NOT NULL);
    CREATE TABLE deliveries (id TEXT PRIMARY KEY,campaign TEXT,chat INTEGER,variant INTEGER,status TEXT,at REAL,
      message_id INTEGER,retry_at REAL DEFAULT 0,UNIQUE(campaign,chat));
    INSERT INTO campaigns VALUES('legacy','["a","b"]',1,1,'run_old');
    INSERT INTO deliveries(id,campaign,chat,variant,status,at) VALUES('existing','legacy',42,0,'sending',1);
    """)
    db.close()
    monkeypatch.setenv("TELEGRAM_DB_PATH", str(path))
    assert c.get(url(c, "legacy", "results"), headers=AUTH).status_code == 409
    with database() as migrated:
        assert migrated.execute("SELECT id,status FROM deliveries").fetchone()[:] == ("existing", "sending")
        assert "project_id" in {row[1] for row in migrated.execute("PRAGMA table_info(campaigns)")}


def test_service_acknowledgement_429_also_cools_promotional_sends(env, monkeypatch):
    c, calls = env
    identifier = create(c)

    def rate_limit(*args, **kwargs):
        raise TelegramError(429, 60)

    monkeypatch.setattr(BotClient, "call", rate_limit)
    assert update(c, 1, 42, "/start " + identifier).status_code == 200
    service.approve(identifier, **scope(c))
    assert service.send(identifier, **scope(c))["deferred"] == 1
    assert not calls
    assert service.results(identifier, **scope(c))["contacts"] == 1


def test_actual_httpx_request_logging_uses_redaction(env, monkeypatch, caplog):
    import logging

    import httpx

    token = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdef123456789"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True, "result": True}))
    # Restore the real BotClient.call, shadowed by the integration fixture.
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("backend.telegram._client_test", Path("backend/telegram/client.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with httpx.Client(transport=transport) as client:
        monkeypatch.setattr(httpx, "post", client.post)
        with caplog.at_level(logging.INFO, logger="httpx"):
            assert module.BotClient().call("getMe") is True
    assert "HTTP Request" in caplog.text
    assert token not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_delayed_403_does_not_revoke_newer_explicit_start(env):
    c, _ = env
    identifier = create(c)
    update(c, 1, 42, "/start " + identifier)
    delivery = service.claim(identifier, 42)
    update(c, 2, 42, "/start " + identifier)
    service.complete(identifier, delivery, error=TelegramError(403))
    assert service.results(identifier, **scope(c))["contacts"] == 1


def test_cafe_campaign_provenance_uses_persisted_kit(env):
    c, _ = env
    project = c.post("/projects", json={"idea": "Corner Brew cafe serves coffee for S$5 a cup.", "pack": "cafe"}).json()
    scenario = c.post("/scenarios", json={"project_id": project["id"], "n_agents": 40, "repeats": 3, "seed": 7}).json()
    run = c.post(f"/scenarios/{scenario['id']}/run").json()
    kit = c.post(f"/runs/{run['run_id']}/kit", json={"project_id": project["id"]}).json()
    response = c.post(
        "/telegram/campaigns",
        headers=AUTH,
        json={
            "project_id": project["id"],
            "run_id": run["run_id"],
            "variants": kit["assets"]["telegram_variants"],
            "hypothesis_index": 1,
            "kit_context": {"hypotheses": kit["hypotheses"], "telegram_variants": kit["assets"]["telegram_variants"]},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["kit_source"]["pack"] == "cafe"
    assert response.json()["kit_source"]["hypothesis"] == kit["hypotheses"][1]


def test_uvicorn_access_formatter_preserves_shape_and_redacts_path(env):
    import logging

    from uvicorn.logging import AccessFormatter

    record = logging.getLogger("uvicorn.access").makeRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:8000", "POST", "/telegram/webhook/path", "1.1", 200),
        None,
    )
    rendered = AccessFormatter(fmt='%(client_addr)s - "%(request_line)s" %(status_code)s', use_colors=False).format(
        record
    )
    assert "/telegram/webhook/[REDACTED]" in rendered
    assert "200 OK" in rendered
    assert record.args[-1] == 200
