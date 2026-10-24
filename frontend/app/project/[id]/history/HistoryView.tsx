"use client";
// OWNER: Person B. Council decisions saved for this project's runs.
import Link from "next/link";
import { use, useEffect, useState } from "react";

import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { Button, Card, Pill, SectionLabel } from "@/components/ui";
import { api } from "@/lib/api";
import type { CouncilHistory, HistoryComparison, HistoryEntry } from "@/lib/types";

type Status = "loading" | "ready" | "empty" | "error";

function shareText(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "not stored";
  return `${Math.round(value * 1000) / 10}%`;
}

function changeText(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "not comparable";
  const points = Math.round(value * 1000) / 10;
  const sign = points > 0 ? "+" : "";
  return `${sign}${points} percentage points`;
}

function when(entry: HistoryEntry): string {
  return entry.created_at || entry.council_recorded_at || "time not stored";
}

function moveText(entry: HistoryEntry): string {
  if (!entry.competitor_move) return "not recorded";
  return `${entry.competitor_move.competitor_id} · ${entry.competitor_move.move}`;
}

export default function HistoryView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<CouncilHistory | null>(null);
  const [baseId, setBaseId] = useState("");
  const [otherId, setOtherId] = useState("");
  const [compareStatus, setCompareStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [compareError, setCompareError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<HistoryComparison | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<CouncilHistory>(`/projects/${encodeURIComponent(id)}/council-history`)
      .then((next) => {
        if (cancelled) return;
        setHistory(next);
        setStatus(next.entries.length ? "ready" : "empty");
        if (next.entries[0]) setBaseId(next.entries[0].run_id);
        if (next.entries[1]) setOtherId(next.entries[1].run_id);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "History request failed");
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  function compare() {
    if (!baseId || !otherId || baseId === otherId) {
      setCompareStatus("error");
      setCompareError("Choose two different stored runs.");
      setComparison(null);
      return;
    }
    setCompareStatus("loading");
    setCompareError(null);
    const query = new URLSearchParams({ base: baseId, other: otherId });
    api<HistoryComparison>(`/projects/${encodeURIComponent(id)}/council-history/compare?${query}`)
      .then((next) => {
        setComparison(next);
        setCompareStatus("ready");
      })
      .catch((err: unknown) => {
        setComparison(null);
        setCompareError(err instanceof Error ? err.message : "Comparison failed");
        setCompareStatus("error");
      });
  }

  return (
    <PageShell glow="council">
      <AppHeader
        active="history"
        projectId={id}
        subtitle="Decision history"
        disclaimer="Simulated outcomes · not real demand"
      />
      {status === "loading" && <p className="text-muted">Loading decision history…</p>}
      {status === "empty" && (
        <div className="flex max-w-xl flex-col gap-3">
          <p className="text-ink">No stored runs for this project.</p>
          <p className="text-sm text-muted">
            History lists only runs saved for this project. It does not add demo runs. Open the Council on a saved run
            to record a verdict.
          </p>
          {history?.note && <p className="text-sm text-muted">{history.note}</p>}
          {error && <p className="text-sm text-coral">{error}</p>}
        </div>
      )}
      {status === "error" && (
        <div className="flex max-w-xl flex-col gap-3">
          <p className="text-ink">Decision history could not be loaded.</p>
          <p className="text-sm text-coral">{error}</p>
          <Button type="button" onClick={() => window.location.reload()}>Try again</Button>
        </div>
      )}
      {status === "ready" && history && (
        <div className="flex flex-col gap-5">
          <p className="max-w-3xl text-sm text-muted">{history.note}</p>
          <div className="flex flex-col gap-3">
            {history.entries.map((entry) => (
              <Card key={entry.run_id} className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <SectionLabel>Run {entry.run_id}</SectionLabel>
                  <Pill variant={entry.run_label === "demo" ? "idle" : "done"}>
                    {entry.run_label === "demo" ? "Demo" : "Live stored run"}
                  </Pill>
                  {entry.pack && <Pill variant="outline">{entry.pack}</Pill>}
                </div>
                <p className="text-sm text-muted">
                  {entry.scenario_id ? `Scenario ${entry.scenario_id}` : "Scenario id not stored"} · {when(entry)}
                </p>
                <div className="grid gap-2 text-sm md:grid-cols-2">
                  <p>Simulated share: <span className="font-mono">{shareText(entry.share)}</span></p>
                  <p>Range: <span className="font-mono">{shareText(entry.p10)} – {shareText(entry.p90)}</span></p>
                  <p>Confidence: {entry.confidence ?? "not recorded"}</p>
                  <p>Recommended move: {moveText(entry)}</p>
                  {typeof entry.overrides_applied === "number" && (
                    <p>Project adjustments on the saved verdict: {entry.overrides_applied}</p>
                  )}
                </div>
                <p className="text-sm text-ink">
                  {entry.verdict ?? "Council verdict has not been saved for this run."}
                </p>
                {entry.limitations.length > 0 && (
                  <p className="text-sm text-muted">{entry.limitations.join(" ")}</p>
                )}
                <Link className="text-sm text-accent" href={`/project/${id}/council?run=${encodeURIComponent(entry.run_id)}`}>
                  Open this Council result
                </Link>
              </Card>
            ))}
          </div>
          {history.problems.length > 0 && (
            <Card variant="warn">
              <p className="text-sm text-warn-ink">
                {history.problems.map((problem) => `${problem.run_id}: ${problem.detail}`).join(" ")}
              </p>
            </Card>
          )}
          <Card variant="raised" className="flex flex-col gap-3">
            <SectionLabel>Compare two runs</SectionLabel>
            <div className="flex flex-wrap gap-3">
              <label className="flex flex-col gap-1 text-sm text-muted">
                Base
                <select className="rounded-lg bg-bg px-3 py-2 text-ink" value={baseId} onChange={(event) => setBaseId(event.target.value)}>
                  {history.entries.map((entry) => (
                    <option key={entry.run_id} value={entry.run_id}>{entry.run_id}</option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm text-muted">
                Other
                <select className="rounded-lg bg-bg px-3 py-2 text-ink" value={otherId} onChange={(event) => setOtherId(event.target.value)}>
                  {history.entries.map((entry) => (
                    <option key={entry.run_id} value={entry.run_id}>{entry.run_id}</option>
                  ))}
                </select>
              </label>
              <Button type="button" onClick={compare} disabled={history.entries.length < 2 || compareStatus === "loading"}>
                {compareStatus === "loading" ? "Comparing…" : "Compare"}
              </Button>
            </div>
            {history.entries.length < 2 && (
              <p className="text-sm text-muted">At least two stored runs are needed before a comparison.</p>
            )}
            {compareStatus === "error" && <p className="text-sm text-coral">{compareError}</p>}
            {compareStatus === "ready" && comparison && (
              <div className="flex flex-col gap-2 text-sm">
                <p>
                  Simulated share change:{" "}
                  {comparison.observed.share.comparable
                    ? changeText(comparison.observed.share.value)
                    : "not comparable"}
                  . {comparison.observed.share.detail}
                </p>
                <p>
                  Verdict: {comparison.interpretation.verdict.comparable
                    ? (comparison.interpretation.verdict.changed ? "the wording changed" : "the wording is the same")
                    : "not comparable"}.
                </p>
                <p>
                  Confidence: {comparison.interpretation.confidence.comparable
                    ? `${comparison.interpretation.confidence.base} → ${comparison.interpretation.confidence.other}`
                    : "not comparable"}. {comparison.interpretation.confidence.detail}
                </p>
                <p>
                  Recommended move: {comparison.interpretation.competitor_move.comparable
                    ? (comparison.interpretation.competitor_move.changed ? "changed" : "unchanged")
                    : "not comparable"}. {comparison.interpretation.competitor_move.detail}
                </p>
                {comparison.scenario_differences.length > 0 && (
                  <ul className="list-disc pl-5 text-muted">
                    {comparison.scenario_differences.map((item) => (
                      <li key={item.field}>{item.statement}</li>
                    ))}
                  </ul>
                )}
                {comparison.limitations.map((line) => (
                  <p key={line} className="text-muted">{line}</p>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </PageShell>
  );
}
