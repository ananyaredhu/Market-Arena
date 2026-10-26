"use client";
// OWNER: Person C. Live Arena for a persisted run, with an explicit shared demo mode.
import { use, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import Arena from "@/components/arena/Arena";
import ScenarioPicker from "@/components/arena/ScenarioPicker";
import SegmentLegend from "@/components/arena/SegmentLegend";
import ShareList from "@/components/arena/ShareList";
import GlassBoxDrawer from "@/components/glassbox/GlassBoxDrawer";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { getAdjustedRun } from "@/lib/api";
import { DEMO_PROJECT_ID, projectHref, selectedRunId } from "@/lib/run-context";
import type { RunResult } from "@/lib/types";

const DEMO_SCENARIOS = [
  { id: "run_42", label: "S$7" },
  { id: "run_42_price3", label: "S$3" },
];

export default function ProjectView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const requestedRunId = useSearchParams().get("run");
  const runId = selectedRunId(id, requestedRunId);
  if (!runId) return (
    <PageShell glow="arena" padded={false}>
      <AppHeader active="arena" projectId={id} />
      <p className="p-8 text-muted">This project has no run selected. Start a simulation from the intake screen.</p>
    </PageShell>
  );
  // Changing either route ID remounts the run view before old data can render.
  return <ArenaRun key={`${id}:${runId}`} projectId={id} selectedRunId={runId} />;
}

function ArenaRun({ projectId: id, selectedRunId }: { projectId: string; selectedRunId: string }) {
  const router = useRouter();
  const isDemo = id === DEMO_PROJECT_ID;
  const scenarios = isDemo ? DEMO_SCENARIOS : [{ id: selectedRunId, label: "Live run" }];
  const [run, setRun] = useState<RunResult | null>(null);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!selectedRunId) return;
    setError(null);
    getAdjustedRun(selectedRunId, id)
      .then(result => {
        if (result.run_id !== selectedRunId) throw new Error("The backend returned a different run.");
        setRun(result);
      })
      .catch((cause: unknown) => {
        setRun(null);
        setError(cause instanceof Error ? cause.message : "The saved simulation could not be loaded.");
      });
  }, [id, selectedRunId]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  if (error) {
    return (
      <PageShell glow="arena" padded={false}>
        <p className="p-8 text-coral" role="alert">
          Could not load run {selectedRunId}: {error}
        </p>
      </PageShell>
    );
  }
  if (!run) return <PageShell glow="arena" padded={false}><p className="p-8 text-muted">Loading simulation…</p></PageShell>;

  const selectedStillPresent = agentId != null && run.choices.some((choice) => choice.agent_id === agentId);
  const moved = run.choices.filter((choice) => choice.prev_choice != null && choice.prev_choice !== choice.choice).length;
  const segments = [...new Set(run.choices.map((choice) => choice.segment))];
  const summary =
    moved === 0
      ? "Baseline run. Pick another price and watch the dots migrate."
      : `${moved} of ${run.choices.length} customers switched vs. the baseline.`;

  return (
    <PageShell glow="arena" padded={false}>
      <div className="border-b border-line px-6 py-3.5">
        <AppHeader active="arena" projectId={id} runContext={{ projectId: id, runId: selectedRunId }} meta={`StudyFlow · SaaS pack · ${run.run_id} · seed ${run.seed}`} />
      </div>
      <div className="flex flex-1 flex-wrap items-stretch">
        <aside className="flex flex-[0_0_280px] flex-col gap-6 border-r border-line p-6">
          <ScenarioPicker
            title="Scenario · price per month"
            choices={scenarios}
            value={selectedRunId}
            onChange={next => {
              if (isDemo) router.replace(projectHref(id, "arena", { projectId: id, runId: next }));
            }}
            summary={summary}
          />
          <ShareList runResult={run} />
          <SegmentLegend segments={segments} />
        </aside>
        <main className="flex min-w-0 flex-[1_1_560px]">
          <Arena runResult={run} onAgentClick={setAgentId} selectedAgentId={agentId} />
        </main>
        <div className="flex flex-[0_0_380px]">
          {agentId && selectedStillPresent ? (
            <GlassBoxDrawer agentId={agentId} runId={run.run_id} onOverride={load} optionIds={run.option_ids} />
          ) : (
            <aside className="flex w-full items-center justify-center border-l border-line bg-[#0f1420] p-6 text-center text-sm text-muted">
              Click any dot to open the Glass-Box: why this customer chose what they chose.
            </aside>
          )}
        </div>
      </div>
    </PageShell>
  );
}
