# Telegram integration — Phase 3B hardening report

Branch: `c/telegram-real-integration`. The branch and existing uncommitted Phase 3 implementation were verified before editing. This report supersedes the earlier implementation report and records the fixes to the read-only audit. No live Telegram calls, webhook registration, secret changes, commits, pushes or merges were performed.

## Audit disposition

| Original check | Status | Implementation evidence |
| --- | --- | --- |
| 1. Operator authentication | PASS | `routes.py`: bearer authentication on create, approve, send and results; missing server credential fails closed. Tests cover absent, wrong and wrong-scheme credentials for all four actions. |
| 2. Webhook authentication | PASS | `routes.py`: constant-time checks of both path secret and Telegram secret-token header, including missing-configuration tests. |
| 3. Consent and revocation | PASS with in-flight limitation | `service.py`: both active consent and exact campaign membership checked at claim and final dispatch; consent generation invalidates claims across stop/re-subscribe. Per-chat Telegram message IDs order consent commands. No network call holds a database transaction. |
| 4. Approval gate | PASS | Persisted immutable campaign text requires explicit approval before promotional delivery. Consent/service acknowledgements are separate and may send before campaign approval. |
| 5. Duplicate protection | PASS | Durable unique campaign/chat claims; persisted update IDs; unique delivery/event-kind metrics; callback recipient attribution; concurrent-send tests. Unknown and sending outcomes are not automatically retried. |
| 6. Real project/run/Kit provenance | PASS | `provenance.py`: real project and persisted-run loaders; matching project and pack; server-generated Kit snapshot and selected hypothesis; run and Kit digests; scope required for results, approval and sending. Legacy campaigns fail closed. SaaS and café tests use actual persisted runs and public Kit endpoints. |
| 7. Secret protection | PASS within application scope | `security.py`: standard Python log records redact configured secrets, Telegram token patterns, bearer values and webhook paths before handlers see them. Covers HTTPX and Uvicorn access logs and exception text. Campaign creation rejects credentials in drafts/source context. Frontend has no server-secret environment references. This is not a forensic audit of all Git history or external proxy logs. |
| 8. Caps and retries | PASS for small tester batches | Persisted bot-wide 429 cooldown and global paced slots; retry eligibility; persistent cap/cooldown deferrals and reasons; successful/failed/unknown/in-flight records preserved; rolling cross-campaign cap. No new worker. |
| 9. No startup/test sends | PASS | No startup network calls. Telegram tests use fake BotClient methods or MockTransport and block real HTTPTransport requests. |
| 10. Real frontend integration | PASS; browser E2E unverified | Scoped backend URLs; displayed-response identity checks; disabled pending controls plus request-generation guard; source hypothesis, delivery status, all engagement and opt-out metrics shown. Real engagement is explicitly separate from simulated demand. |
| 11. Ownership/mock compatibility | PASS | No engine, Council/Kit internals or shared contracts changed. Existing mock endpoint payloads and default sample console preserved. KitView changes only mount the scoped Telegram console. |
| 12. Failure-path coverage | PASS | 59 Telegram test cases, including original 13, plus 3 frontend request-state tests. Full suite and verification results below. |

## Architecture and operational semantics

### Consent

Only `/start <existing verified campaign ID>` in a private chat subscribes a tester. The bot acknowledges promotional-test consent and `/stop`. Publish the same disclosure in the bot description and invitation before the tester presses Start. Plain `/start` without a campaign does not subscribe.

Each accepted consent command requires a positive Telegram `message_id`. The latest accepted message ID is persisted per private chat; a command at or below that watermark cannot change consent, even when delivered under a different update ID. A stop for an unseen subscriber creates a tombstone. This deliberately uses chat message ordering rather than update-ID ordering, which is a separate replay mechanism. Preserve the consent database across restarts; do not erase its ordering watermarks during recovery.

`/stop` commits global revocation and removes all campaign memberships in one short transaction. It increments a consent generation, so a claim created before the stop cannot be dispatched after re-subscription, even to the same campaign. Re-subscribing restores only the specified campaign. Delayed 403 failures do not revoke a newer explicit start.

Consent commits before any acknowledgement HTTP call. A slow acknowledgement can delay the webhook response but cannot delay the committed revocation. SQLite transactions cover only short local work; none spans pacing sleeps or Telegram network requests.

There is an unavoidable gap between the last committed consent check and the irreversible outbound request. A stop in that gap, or while the request is already in flight, cannot recall that message. Subsequent claims/checks honor revocation. The blocked-transport test demonstrates that stop commits while delivery is in flight and prevents the remaining revoked recipients in the batch from being sent. This is not an atomic transaction between SQLite and Telegram and is not a promise of zero post-stop arrivals.

### Provenance and approval

Campaign creation requires a persisted `project_id`, a real persisted `run_id` belonging to that project/pack, a selected `hypothesis_index`, and the source Kit's hypotheses and Telegram variants. Path-like, missing, demo-only, nonexistent or mismatched IDs are rejected.

The Telegram adapter calls existing public Council/Kit services using the loaded run bundle and template wording; it does not modify those internals or invoke an LLM provider. It verifies the submitted source Kit context against the regenerated context, then stores the full canonical Kit, its digest, the full run-bundle digest, pack, selected hypothesis/index and source version. Operator-edited promotional variants are stored separately and require human approval.

Results, approval and sending require both `project_id` and `run_id` query parameters and validate them against the campaign and persisted backend data. A campaign cannot be operated on from an unrelated project/run page. Changed source-run data causes a conflict rather than silently changing the experiment. Historical Kit snapshots remain identifiable even if templates later change.

Scope protects integration consistency; the shared operator bearer credential still authorizes all projects. It is not a multi-tenant account/role system.

### Delivery and recovery

The send endpoint remains a synchronous batch processor for a small tester audience. It persists a unique claim before networking. SQLite serializes claims across workers. A final short transaction checks active consent, membership, consent generation and bot cooldown immediately before dispatch.

Successful messages are never resent. Clear 4xx failures other than 429 remain failed. Network/5xx ambiguity is `unknown`; process interruption after a claim can leave `sending`. Neither is retried automatically. Reconcile these outcomes manually; do not reset their status blindly. The API cannot guarantee exactly-once delivery because Telegram does not accept an application idempotency key.

429 `retry_after` is persisted as a bot-wide cooldown. The current recipient is deferred, other eligible recipients receive persisted cooldown deferrals, and later campaigns share the same cooldown. Service acknowledgements also honor and can establish cooldown. Requests already past their final check cannot be retroactively stopped by a concurrent 429 response. Retrying after the cooldown does not resend prior successes.

The promotional frequency cap is two sent/reserved/unknown outcomes per subscriber in a rolling seven-day window across campaigns. Cap deferrals, their reason and eligibility time are persisted. Results expose cumulative `delivery_statuses`, `deferred_reasons`, `next_retry_at` and `bot_cooldown_until`; a send response reports only work newly processed by that request. Global paced slots target at most 20 promotional dispatches/second within this database. No automatic background retry or external worker was added. Use one bot per database and do not switch tokens mid-batch.

`clicks` remains the contract name for unique Learn-more button taps, not external website visits. Replies and other engagement events are unique per delivered recipient/event kind. Opt-outs are attributed to all successfully delivered campaigns for that chat, including a message completing after revocation; they do not establish causality. The UI displays interested, too-expensive, learn-more taps, replies and opt-outs, with interested/sent rates. There is no external redirect tracking, QR-image generator or automatic simulation calibration write-back.

### Logging and secrets

The Telegram import installs a chained Python LogRecord factory. It redacts configured bot/operator/webhook credentials, token-shaped strings, bearer values, webhook path segments, exception text and stack text before standard handlers receive records. A regression test exercises actual HTTPX request logging through MockTransport; another exercises Uvicorn's access-log format. Application transport errors contain only sanitized numeric codes. Campaign creation rejects credentials in raw draft/context strings before persistence; it does not merely redact them and approve altered content.

Do not replace the LogRecord factory without retaining redaction. External reverse proxies, tunnels, APM collectors and startup tooling are outside this process; disable/redact their webhook-path logging too. Run Uvicorn with `--no-access-log` for a pilot as an additional precaution. Credentials are entered only at runtime in the operator UI and stay in component memory; they are never supplied via a `NEXT_PUBLIC_*` secret. A compromised browser or operator workstation remains able to read runtime credentials. Use HTTPS outside loopback and restrict access to database files/backups.

### Existing databases

Schema changes are additive and transactional. Existing campaign, consent and delivery records are not replaced. Legacy campaigns lacking verified project/Kit provenance cannot be loaded, approved, sent or newly subscribed to; create a new verified campaign. Existing successful, failed, unknown and in-flight delivery claims are retained. Do not manufacture provenance for old campaigns or reuse their IDs.

## Configuration

No environment file or real credential was changed.

| Variable | Purpose |
| --- | --- |
| `MOCK=1` / `MOCK=0` | Fixture mode / real Telegram implementation. Defaults to 1. |
| `TELEGRAM_BOT_TOKEN` | Server-only BotFather API token. |
| `TELEGRAM_BOT_USERNAME` | Bot username without `@`, used in subscription links. |
| `TELEGRAM_OPERATOR_TOKEN` | Independent shared operator bearer credential. |
| `TELEGRAM_WEBHOOK_PATH_SECRET` | Secret webhook path segment. |
| `TELEGRAM_WEBHOOK_SECRET` | Telegram secret-token header value. |
| `TELEGRAM_DB_PATH` | SQLite location, default relative `data/telegram.sqlite3`. |
| `NEXT_PUBLIC_TELEGRAM_MODE=real` | Frontend build/dev-time opt-in to the real console; otherwise sample mode. |
| `NEXT_PUBLIC_API_URL` | Backend origin, defaults to `http://localhost:8000`. |

Existing `MARKET_ARENA_DATA_DIR` controls persisted project/run storage independently of the Telegram database. `LLM_MODE=mock` keeps other application wording offline during local development. Export backend environment variables in the process environment: the app does not call the available `.env` loader. `make api` forces MOCK=1, so use the explicit Uvicorn command for real mode.

## API

In MOCK=1 all existing fixture payloads and paths remain available without extra scope. In real mode all operator routes require `Authorization: Bearer <TELEGRAM_OPERATOR_TOKEN>`.

Create a campaign with `POST /telegram/campaigns`:

```json
{
  "project_id": "proj_<actual persisted ID>",
  "run_id": "run_<actual persisted ID>",
  "hypothesis_index": 0,
  "kit_context": {
    "hypotheses": ["exact hypotheses from the source Kit"],
    "telegram_variants": ["exact source A", "exact source B"]
  },
  "variants": ["reviewable promotional A", "reviewable promotional B"]
}
```

The hypotheses array above is illustrative; use the complete returned Kit array. Draft variants must be nonblank and at most 3900 characters each. The bot adds an opt-out footer.

All existing-campaign operations include `?project_id=<project>&run_id=<run>`:

- `GET /telegram/campaigns/{id}/results`
- `POST /telegram/campaigns/{id}/approve`
- `POST /telegram/campaigns/{id}/send`

The webhook remains `POST /telegram/webhook/{path_secret}`, authenticated additionally by `X-Telegram-Bot-Api-Secret-Token`. Updates and consent persist before best-effort service acknowledgements. Nothing registers or changes a webhook automatically.

## Safe development and one/two-tester pilot

The commands in this section are instructions for later use. No live steps were executed. Live actions still require approval.

### Offline local development

```sh
cd /Users/a91936/Projects/Market-Arena-integration
env -u TELEGRAM_BOT_TOKEN MOCK=1 LLM_MODE=mock \
  .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal:

```sh
cd /Users/a91936/Projects/Market-Arena-integration
NEXT_PUBLIC_TELEGRAM_MODE=mock NEXT_PUBLIC_API_URL=http://localhost:8000 \
  npm --prefix frontend run dev -- --hostname localhost
```

Do not configure a tunnel/webhook or inject updates into a server containing a real bot token during offline development: `/start` and `/stop` acknowledgements are real outbound messages in real mode.

### Pilot prerequisites and setup

1. Review the implementation and obtain approval for live setup/messages. Address the existing Next.js security advisory before exposing the operator application beyond loopback. This hardening task intentionally makes no unrelated dependency upgrade.
2. Create a dedicated bot in verified `@BotFather` with `/newbot`, a display name, and an available username ending in `bot`. Use `/setdescription` to disclose promotional tests and `/stop`, and `/setcommands` to advertise `start` and `stop`. Bot creation has no Bot API command.
3. Provision the four independent server secrets listed above through your local secret mechanism, and set the username. Do not paste credentials into source, command-line arguments, browser public environment variables or Git. Use a new private persistent `TELEGRAM_DB_PATH` for this dedicated bot. Keep the same database for the duration of the pilot.
4. Start the backend from the repository root after those variables are exported:

```sh
MOCK=0 LLM_MODE=mock .venv/bin/python -m uvicorn backend.main:app \
  --host 127.0.0.1 --port 8000 --no-access-log
```

5. Start the local operator UI with real mode:

```sh
NEXT_PUBLIC_TELEGRAM_MODE=real NEXT_PUBLIC_API_URL=http://localhost:8000 \
  npm --prefix frontend run dev -- --hostname localhost
```

6. Publish only the webhook route through a TLS ingress. Do not tunnel the whole backend: other pre-existing app routes are not the Telegram operator boundary. For example, route a tunnel to a local Nginx listener configured as follows, not directly to port 8000:

```nginx
server {
    listen 127.0.0.1:8081;
    server_name _;
    access_log off;
    error_log /dev/null;
    location ^~ /telegram/webhook/ {
        proxy_pass http://127.0.0.1:8000;
    }
    location / { return 404; }
}
```

Use your TLS tunnel/ingress's assigned public HTTPS origin as `PUBLIC_HTTPS_ORIGIN`. Ensure it does not log webhook path credentials. This is a setup helper variable, not an application variable.

Register the webhook only after live approval. Use the existing venv so httpx is available; errors and the resulting secret-bearing URL are not printed:

```sh
.venv/bin/python - <<'PY'
import os
import sys
import httpx
from backend.telegram.security import install_log_redaction

install_log_redaction()
try:
    origin = os.environ["PUBLIC_HTTPS_ORIGIN"].rstrip("/")
    if not origin.startswith("https://"):
        sys.exit("An HTTPS webhook origin is required")
    response = httpx.post(
        "https://api.telegram.org/bot" + os.environ["TELEGRAM_BOT_TOKEN"] + "/setWebhook",
        json={
            "url": origin + "/telegram/webhook/" + os.environ["TELEGRAM_WEBHOOK_PATH_SECRET"],
            "secret_token": os.environ["TELEGRAM_WEBHOOK_SECRET"],
            "allowed_updates": ["message", "callback_query"],
            "max_connections": 1,
        },
        timeout=15,
    )
    response.raise_for_status()
    ok = response.json().get("ok") is True
except Exception:
    sys.exit("Webhook registration failed; details suppressed")
if not ok:
    sys.exit("Telegram rejected webhook registration")
print("Webhook registered")
PY
```

This does not discard pending updates. Use only a new dedicated pilot bot, not a bot with unrelated subscribers or pending production updates. `max_connections=1` reduces concurrent incoming requests but is not a replacement for the application ordering checks.

### Pilot execution

1. In the local app create/select a completed real persisted run. Open that exact project's Kit page with its `run` query parameter. Enter the operator token at runtime.
2. Choose the Kit hypothesis, review/edit two clearly labelled test variants, and create the campaign. Record its ID. Legacy/demo campaigns are not eligible.
3. Invite one consenting tester, optionally a second. Explain the promotion and `/stop` before sharing the deep link. Have each press Start. Expect an acknowledgement, which is a real message even before promotional approval.
4. Refresh and verify the audience is exactly one/two and that the displayed project, run, campaign, hypothesis and drafts are correct. Two testers may hash to the same variant; the pilot tests plumbing, not statistical significance.
5. An unapproved promotional send must return 409. Then click Approve reviewed variants, followed by Send approved campaign once. Verify observed sent counts and delivery states.
6. Tap Interested twice and verify only one interested event. Tap Too expensive/Learn more and reply directly to the bot's delivered message; refresh to inspect observed metrics. Learn more records a tap and does not navigate to a website.
7. Have testers send `/stop`. Confirm contacts drop to zero and opt-outs appear. Sending again must not send another promotion. To test cross-campaign revocation, create a second approved campaign and confirm a stopped tester is not eligible without an explicit Start for that new campaign.
8. Stop processing campaigns and disable the pilot webhook when done. Do not clear consent/delivery records to force retries. Any `unknown`/`sending` state needs manual reconciliation. Disable with a separately approved `deleteWebhook` Bot API request; do not discard unrelated pending updates.

## Verification and remaining limits

- `make test`: 647 tests passed, including 59 Telegram cases. Telegram tests use temporary persisted projects/runs/databases and fake transport; real HTTPTransport is explicitly blocked.
- `make lint`: passed across backend, contracts and scripts.
- `make schemas`: passed; generated shared contracts unchanged.
- `node --test tests/telegram-state.test.mjs` from frontend: 3 passed. These exercise the exact request guard, identity checks and scoped URL helper used by the console; they are not a browser E2E test.
- Frontend TypeScript and ESLint: passed.
- Frontend production build with `NEXT_PUBLIC_TELEGRAM_MODE=real`: passed. The first build compiled/generated pages but stopped with the pre-existing Next.js 16.4.0 vulnerability diagnostic; the real-mode build completed with the same upgrade warning. No dependencies were upgraded.
- Static secret-pattern scan: no token-shaped values in 20 built frontend JS bundles and no server-secret environment references in frontend source. The only two token-shaped source literals are synthetic redaction-test values; no real credentials were introduced.
- `git diff --check`: passed. Tracked and untracked implementation files reviewed; Person A/B internals, environment files and shared contracts unchanged.
- Existing Starlette TestClient/httpx deprecation warning remains.

Remaining operational limits: the last-check/in-flight consent window, synchronous small batches, manual unknown-outcome reconciliation, one bot per database, a shared operator credential rather than tenant roles, cancelled claims requiring a new campaign rather than automatic requeue, and no live/browser end-to-end proof. Standard application logging is redacted; ingress/third-party observability must be configured independently. This is a reviewed tester integration, not an assertion of production readiness.
