"use client";
// OWNER: Person B. Screen 3: Arena Council verdict for one run.
import { use, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import CouncilPanel from "@/components/council/CouncilPanel";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { Button } from "@/components/ui";
import { post } from "@/lib/api";
import type { CouncilOutput, KitOutput } from "@/lib/types";

type Status = "loading" | "ready" | "empty" | "error";

export default function CouncilView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const runId = useSearchParams().get("run") || "run_42";
  const requestKey = `${id}:${runId}`;
  const [activeKey, setActiveKey] = useState(requestKey);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [council, setCouncil] = useState<CouncilOutput | null>(null);
  const [kit, setKit] = useState<KitOutput | null>(null);
  if (activeKey !== requestKey) {
    setActiveKey(requestKey);
    setStatus("loading");
    setError(null);
    setCouncil(null);
    setKit(null);
  }

  useEffect(() => {
    let cancelled = false;
    post<CouncilOutput>(`/runs/${encodeURIComponent(runId)}/council`, { project_id: id })
      .then(async (nextCouncil) => {
        if (cancelled) return null;
        if (nextCouncil.project_id && nextCouncil.project_id !== id) {
          throw new Error("Council result belongs to a different project");
        }
        if (nextCouncil.run_id !== runId) {
          throw new Error(`Council result is for ${nextCouncil.run_id}, not ${runId}`);
        }
        setCouncil(nextCouncil);
        return post<KitOutput>(`/runs/${encodeURIComponent(runId)}/kit`, {
          project_id: id,
          council: nextCouncil,
        });
      })
      .then((nextKit) => {
        if (cancelled || !nextKit) return;
        setKit(nextKit);
        setStatus("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Council request failed";
        setError(message);
        setStatus(message.includes("404") ? "empty" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [id, runId]);

  const origin = council?.scenario_origin;
  const disclaimer =
    origin === "demo"
      ? "Shared demo run · simulated, not stored for this project"
      : origin === "fixture_fallback"
        ? "Fixture fallback · not a live result"
        : "Simulated under stated assumptions · not real demand";

  return (
    <PageShell glow="council">
      <AppHeader
        active="council"
        projectId={id}
        subtitle={`Council · ${runId}`}
        disclaimer={disclaimer}
      />
      {status === "loading" && <p className="text-muted">Loading council for {runId}…</p>}
      {status === "empty" && (
        <div className="flex max-w-xl flex-col gap-3">
          <p className="text-ink">No stored simulation for {runId} on this project.</p>
          <p className="text-sm text-muted">
            Shared demo runs are <span className="font-mono">run_42</span> and{" "}
            <span className="font-mono">run_42_price3</span>. Any other id needs a result stored for this project.
          </p>
          <p className="text-sm text-coral">{error}</p>
        </div>
      )}
      {status === "error" && (
        <div className="flex max-w-xl flex-col gap-3">
          <p className="text-ink">Council could not be calculated for {runId}.</p>
          <p className="text-sm text-coral">{error}</p>
          <Button type="button" onClick={() => window.location.reload()}>Try again</Button>
        </div>
      )}
      {status === "ready" && council && kit && (
        <div className="flex flex-col gap-4">
          {council.scenario_note && <p className="text-sm text-muted">{council.scenario_note}</p>}
          {origin === "demo" && !council.scenario_note && (
            <p className="text-sm text-muted">
              Showing shared demo run {council.run_id}. It is computed by the decision engine and is not a result
              saved for project {id}.
            </p>
          )}
          {council.measured?.segment_uncertainty === "canonical_draw_only" && (
            <p className="text-sm text-muted">
              Segment shares are the canonical draw. This run has no per-segment p10–p90.
            </p>
          )}
          <CouncilPanel council={council} kit={kit} />
        </div>
      )}
    </PageShell>
  );
}
