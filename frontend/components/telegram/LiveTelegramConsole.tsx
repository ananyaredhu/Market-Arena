"use client";
import { useEffect, useRef, useState } from "react";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { KitOutput } from "@/lib/types";
import TelegramConsole from "./TelegramConsole";
import { telegramAvailability, type BackendState, type DeliveryState } from "./presentation";
import { assertCampaignIdentity, campaignPath, CampaignRequestGate } from "./campaign-state";

type Results = {
  id: string; project_id: string; run_id: string; message_variants: string[];
  approved: boolean; contacts: number; variant_sizes: number[];
  subscribe_link: string | null;
  kit_source: { hypothesis: string; kit_digest: string };
  variants: { variant: string; sent: number; interested: number; clicks: number; replies: number;
    too_expensive: number; unsubscribes: number }[];
  delivery_statuses: Record<string, number>;
  deferred_reasons: Record<string, number>;
  next_retry_at: number | null;
};

export default function LiveTelegramConsole({ kit, projectId, runId }: {
  kit: KitOutput; projectId: string; runId: string;
}) {
  const [token, setToken] = useState("");
  const [id, setId] = useState("");
  const [draft, setDraft] = useState(kit.assets.telegram_variants.slice(0, 2));
  const [hypothesisIndex, setHypothesisIndex] = useState(0);
  const [data, setData] = useState<Results | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [backend, setBackend] = useState<BackendState>("checking");
  const [delivery, setDelivery] = useState<DeliveryState>("unverified");
  const gate = useRef(new CampaignRequestGate());
  const scope = { projectId, runId };
  useEffect(() => {
    const active = gate.current;
    return () => active.invalidate();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    api<{ mock: boolean }>("/health", { signal: controller.signal })
      .then(health => { if (!controller.signal.aborted) setBackend(health.mock === false ? "real" : "mock"); })
      .catch(() => { if (!controller.signal.aborted) setBackend("offline"); });
    return () => controller.abort();
  }, []);
  async function checkBackend() {
    setBackend("checking");
    try {
      const health = await api<{ mock: boolean }>("/health");
      setBackend(health.mock === false ? "real" : "mock");
    } catch { setBackend("offline"); }
  }

  async function request<T>(path: string, body?: unknown, method = "POST") {
    return api<T>(path, { method, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: method === "GET" ? undefined : JSON.stringify(body ?? {}) });
  }
  async function refresh(ticket: number, campaignId: string) {
    const next = await request<Results>(campaignPath(scope, campaignId, "results"), undefined, "GET");
    if (!Array.isArray(next.message_variants) || !Array.isArray(next.variant_sizes)) {
      throw new Error("Real Telegram console requires backend MOCK=0.");
    }
    assertCampaignIdentity(scope, campaignId, next);
    if (gate.current.current(ticket)) {
      setData(next); setDraft(next.message_variants);
    }
  }
  async function action(work: (ticket: number) => Promise<void>) {
    const ticket = gate.current.begin();
    if (ticket === null) return;
    setBusy(true); setMessage("");
    try { await work(ticket); }
    catch (e) {
      if (gate.current.current(ticket)) {
        const reason = e instanceof Error ? e.message : "Telegram request failed";
        setMessage(reason);
        if (/configuration incomplete|not configured/i.test(reason)) setDelivery("unconfigured");
        if (e instanceof TypeError) setBackend("offline");
      }
    } finally {
      if (gate.current.finish(ticket)) setBusy(false);
    }
  }
  function clearDisplayed() {
    gate.current.invalidate(); setData(null); setMessage(""); setDelivery("unverified");
  }
  const displayed = data && data.id === id && data.project_id === projectId && data.run_id === runId ? data : null;
  return <div className="flex flex-col gap-3">
    <Card className="flex flex-col gap-3">
      <p role="status">{telegramAvailability(backend, delivery)}</p>
      <Button disabled={busy || backend === "checking"} onClick={checkBackend}>Check backend connection</Button>
      <p>Observed Telegram engagement from consenting testers. These counts are separate from simulated demand.</p>
      <label>Operator token (kept only in this page&apos;s memory)
        <input disabled={busy} aria-label="Telegram operator token" type="password" autoComplete="off"
          value={token} onChange={e => { clearDisplayed(); setToken(e.target.value); }} className="block w-full rounded border p-2" />
      </label>
      <p>Share the campaign link with testers. Pressing Start subscribes them to promotional tests; /stop revokes consent.</p>
      {!displayed && <label>Kit hypothesis to test
        <select disabled={busy || !!displayed} value={hypothesisIndex} onChange={e => setHypothesisIndex(Number(e.target.value))}
          className="block w-full rounded border p-2">
          {kit.hypotheses.map((text, i) => <option key={i} value={i}>{text}</option>)}
        </select>
      </label>}
      {draft.map((text, i) => <label key={i}>Variant {"AB"[i]}
        <textarea disabled={busy || !!displayed} aria-label={`Variant ${"AB"[i]}`} maxLength={3900} value={text}
          onChange={e => setDraft(draft.map((t, j) => j === i ? e.target.value : t))} className="block w-full rounded border p-2" />
      </label>)}
      <Button disabled={busy || backend !== "real" || !token || !!displayed} onClick={() => action(async ticket => {
        const created = await request<Results>("/telegram/campaigns", {
          variants: draft, project_id: projectId, run_id: runId, hypothesis_index: hypothesisIndex,
          kit_context: { hypotheses: kit.hypotheses, telegram_variants: kit.assets.telegram_variants },
        });
        assertCampaignIdentity(scope, created.id, created);
        if (gate.current.current(ticket)) setId(created.id);
        await refresh(ticket, created.id);
      })}>Create campaign</Button>
      <label>Campaign ID<input disabled={busy} aria-label="Campaign ID" value={id}
        onChange={e => { clearDisplayed(); setId(e.target.value); }} className="block w-full rounded border p-2" /></label>
      <Button disabled={busy || backend !== "real" || !token || !id} onClick={() => action(ticket => refresh(ticket, id))}>Load / refresh results</Button>
      {displayed?.subscribe_link && <a href={displayed.subscribe_link} target="_blank" rel="noreferrer">Subscribe: {displayed.subscribe_link}</a>}
      {displayed && <>
        <p>Campaign {displayed.id} · Source hypothesis: {displayed.kit_source.hypothesis}</p>
        <Button disabled={busy || backend !== "real" || !token || displayed.approved} onClick={() => action(async ticket => {
          await request(campaignPath(scope, displayed.id, "approve")); await refresh(ticket, displayed.id);
        })}>Approve reviewed variants</Button>
        <Button disabled={busy || backend !== "real" || !token || !displayed.approved} onClick={() => action(async ticket => {
          const sent = await request<{ recipients: number }>(campaignPath(scope, displayed.id, "send"));
          await refresh(ticket, displayed.id);
          if (gate.current.current(ticket)) {
            if (sent.recipients > 0) setDelivery("confirmed");
            setMessage(`Sent to ${sent.recipients} testers. Review delivery statuses below.`);
          }
        })}>Send approved campaign</Button>
        <p>Delivery statuses: {JSON.stringify(displayed.delivery_statuses)}</p>
        <p>Deferred reasons: {JSON.stringify(displayed.deferred_reasons)}</p>
        {displayed.next_retry_at && <p>Next retry eligible: {new Date(displayed.next_retry_at * 1000).toLocaleString()}</p>}
        <p>{displayed.variants.map(v => `${v.variant}: ${v.sent} sent, ${v.interested} interested, ${v.too_expensive} too expensive, ${v.clicks} learn-more taps, ${v.replies} replies, ${v.unsubscribes} opt-outs`).join(" · ")}</p>
      </>}
      <p role="status">{busy ? "Working…" : message}</p>
    </Card>
    {displayed && <TelegramConsole contacts={displayed.contacts} variants={displayed.message_variants} variantSizes={displayed.variant_sizes}
      results={displayed.variants.map(v => ({ variant: v.variant, rate: v.sent ? Math.round(100 * v.interested / v.sent) : 0 }))} live />}
  </div>;
}
