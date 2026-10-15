"use client";
// OWNER: Person C. Screen 1 mockup: "Live Arena + Glass-Box". Composes the three owners' components.
// Left: scenario picker, shares, legend (C). Centre: Arena (C). Right: Glass-Box drawer (A).
// The two runs are the mock fixtures; replace with scenarios from POST /scenarios/{id}/run.
import { use, useCallback, useEffect, useState } from "react";

import Arena from "@/components/arena/Arena";
import ScenarioPicker from "@/components/arena/ScenarioPicker";
import SegmentLegend from "@/components/arena/SegmentLegend";
import ShareList from "@/components/arena/ShareList";
import GlassBoxDrawer from "@/components/glassbox/GlassBoxDrawer";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { api } from "@/lib/api";
import type { RunResult } from "@/lib/types";

const SCENARIOS = [
  { id: "run_42", label: "S$7" },
  { id: "run_42_price3", label: "S$3" },
];

export default function ProjectView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [runs, setRuns] = useState<Record<string, RunResult>>({});
  const [scenario, setScenario] = useState(SCENARIOS[0].id);
  const [agentId, setAgentId] = useState<string | null>(null);

  // Person A's /adjusted route returns the run with the project's saved human overrides applied.
  const load = useCallback(() => {
    SCENARIOS.forEach((s) =>
      api<RunResult>(`/runs/${s.id}/adjusted`).then((r) => setRuns((prev) => ({ ...prev, [s.id]: r }))),
    );
  }, []);
  useEffect(() => {
    load();
  }, [load, id]);

  const run = runs[scenario];
  if (!run) return <PageShell glow="arena" padded={false}><p className="p-8 text-muted">Loading…</p></PageShell>;
  const selectedStillPresent = agentId != null && run.choices.some((c) => c.agent_id === agentId); // false after Exclude

  const moved = run.choices.filter((c) => c.prev_choice != null && c.prev_choice !== c.choice).length;
  const segments = [...new Set(run.choices.map((c) => c.segment))];
  const summary =
    moved === 0
      ? "Baseline run. Pick another price and watch the dots migrate."
      : `${moved} of ${run.choices.length} customers switched vs. the baseline.`;

  return (
    <PageShell glow="arena" padded={false}>
      <div className="border-b border-line px-6 py-3.5">
        <AppHeader active="arena" projectId={id} meta={`StudyFlow · SaaS pack · ${run.run_id} · seed ${run.seed}`} />
      </div>
      <div className="flex flex-1 flex-wrap items-stretch">
        <aside className="flex flex-[0_0_280px] flex-col gap-6 border-r border-line p-6">
          <ScenarioPicker
            title="Scenario · price per month"
            choices={SCENARIOS}
            value={scenario}
            onChange={setScenario}
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
