"use client";
// OWNER: Person A. Human overrides for one customer (Master Plan 5.3): lock a choice, edit a parameter, tune the
// whole segment, or exclude the customer. The backend trial-runs every override and refuses ones the engine cannot
// run, so the message shown here is the engine's own reason. Everything is written to the audit trail.
import { useCallback, useEffect, useState } from "react";

import { Button, SectionLabel } from "@/components/ui";
import { api, del, post } from "@/lib/api";
import { optionStyle } from "@/lib/theme";
import type { AuditTrail, OverrideResponse } from "@/lib/types";

type Mode = "lock" | "edit" | "tune" | "exclude";

const PARAMS: [string, string][] = [
  ["budget", "Budget"],
  ["alpha", "Price sensitivity"],
  ["switch", "Switching cost"],
  ["risk", "Risk aversion"],
  ["outside_utility", "Appeal of doing nothing"],
];

const MODES: [Mode, string][] = [
  ["lock", "Lock choice"],
  ["edit", "Edit parameters"],
  ["tune", "Tune segment"],
  ["exclude", "Exclude"],
];

const field = "min-h-10 rounded-lg border border-line-3 bg-bg px-3 text-sm text-ink";

interface Props {
  agentId: string;
  segmentId: string;
  optionIds: string[];
  onChanged: () => void;
}

export default function OverrideControls({ agentId, segmentId, optionIds, onChanged }: Props) {
  const [mode, setMode] = useState<Mode | null>(null);
  const [option, setOption] = useState(optionIds[0]);
  const [param, setParam] = useState(PARAMS[0][0]);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [trail, setTrail] = useState<AuditTrail | null>(null);

  const refresh = useCallback(() => api<AuditTrail>("/overrides").then(setTrail).catch(() => setTrail(null)), []);
  useEffect(() => {
    refresh();
  }, [refresh, agentId]);

  async function submit(body: Record<string, unknown>) {
    setBusy(true);
    setMessage(null);
    try {
      const r = await post<OverrideResponse>("/overrides", body);
      setMessage({ ok: true, text: `${r.override.effect} ${r.moved} customer(s) moved.` });
      setMode(null);
      setValue("");
      await refresh();
      onChanged();
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "The override was refused." });
    } finally {
      setBusy(false);
    }
  }

  async function undo(id: string) {
    setBusy(true);
    try {
      await del(`/overrides/${id}`);
      setMessage({ ok: true, text: "Override removed." });
      await refresh();
      onChanged();
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "Could not remove it." });
    } finally {
      setBusy(false);
    }
  }

  const num = Number(value);
  const mine = trail?.human_adjustments.filter((o) => o.agent_id === agentId || o.segment_id === segmentId) ?? [];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {MODES.map(([m, label]) => (
          <Button
            key={m}
            aria-pressed={mode === m}
            disabled={busy}
            onClick={() => setMode(mode === m ? null : m)}
            className={mode === m ? "px-4 !border-accent" : "px-4"}
          >
            {label}
          </Button>
        ))}
      </div>

      {mode === "lock" && (
        <div className="flex flex-wrap items-center gap-2">
          <select aria-label="Option to pin to" className={field} value={option} onChange={(e) => setOption(e.target.value)}>
            {optionIds.map((id) => (
              <option key={id} value={id}>{optionStyle(id).label}</option>
            ))}
          </select>
          <Button variant="primary" disabled={busy} onClick={() => submit({ type: "lock", agent_id: agentId, option_id: option })}>
            Pin this customer
          </Button>
        </div>
      )}

      {(mode === "edit" || mode === "tune") && (
        <div className="flex flex-wrap items-center gap-2">
          <select aria-label="Parameter" className={field} value={param} onChange={(e) => setParam(e.target.value)}>
            {PARAMS.map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <input
            aria-label={mode === "edit" ? "New value" : "Multiply by"}
            className={`${field} w-28`}
            inputMode="decimal"
            placeholder={mode === "edit" ? "new value" : "× e.g. 1.2"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <Button
            variant="primary"
            disabled={busy || value.trim() === "" || Number.isNaN(num)}
            onClick={() =>
              submit(
                mode === "edit"
                  ? { type: "edit", agent_id: agentId, param, value: num }
                  : { type: "segment_tune", segment_id: segmentId, param, factor: num },
              )
            }
          >
            {mode === "edit" ? "Apply to this customer" : "Apply to the segment"}
          </Button>
        </div>
      )}

      {mode === "exclude" && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-ink-soft">
          Remove this customer from the run?
          <Button variant="primary" disabled={busy} onClick={() => submit({ type: "exclude", agent_id: agentId })}>
            Exclude
          </Button>
        </div>
      )}

      {message && (
        <p role="status" className={`m-0 text-xs leading-normal ${message.ok ? "text-teal" : "text-coral"}`}>
          {message.text}
        </p>
      )}

      {mine.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <SectionLabel>Human adjustments on this customer</SectionLabel>
          {mine.map((o) => (
            <div key={o.id} className="flex items-start justify-between gap-2 text-xs leading-normal text-ink-soft">
              <span>{o.effect}</span>
              <button type="button" disabled={busy} onClick={() => undo(o.id)} className="shrink-0 text-accent underline">
                Undo
              </button>
            </div>
          ))}
        </div>
      )}

      <p className="m-0 text-xs leading-normal text-muted">
        {trail?.summary ?? "Every override is written to the audit trail: machine-generated vs. human-adjusted."}
      </p>
    </div>
  );
}
