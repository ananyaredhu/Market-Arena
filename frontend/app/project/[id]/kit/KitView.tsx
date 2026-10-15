"use client";
// OWNER: Person B (Kit columns) and Person C (Telegram console).
import { use, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import StepPills from "@/components/intake/StepPills";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import HypothesisList from "@/components/kit/HypothesisList";
import LandingPreview from "@/components/kit/LandingPreview";
import TelegramConsole from "@/components/telegram/TelegramConsole";
import { Button } from "@/components/ui";
import { post } from "@/lib/api";
import { KIT_CURRENT, KIT_DONE, KIT_STEPS, TELEGRAM } from "@/lib/mock/kit";
import type { CouncilOutput, KitOutput } from "@/lib/types";

type Status = "loading" | "ready" | "empty" | "error";

function landingParts(copy: string): { headline: string; body: string; ctas: [string, string] } {
  const lines = copy.split("\n");
  const headingIndex = lines.findIndex((line) => line.startsWith("# "));
  const headline = headingIndex >= 0 ? lines[headingIndex].slice(2).trim() : "Landing page";
  const body = lines.filter((_, index) => index !== headingIndex).join("\n").trim();
  const variants = lines
    .filter((line) => line.startsWith("- Variant"))
    .map((line) => line.replace(/^- /, ""));
  return {
    headline,
    body,
    ctas: [variants[0] ?? "Primary variant", variants[1] ?? "Alternate variant"],
  };
}

function markdownExport(kit: KitOutput, runId: string): string {
  return [
    `# Experiment kit for ${runId}`,
    "",
    "These are proposed tests. Simulation results do not establish real customer demand.",
    "",
    "## Hypotheses",
    ...kit.hypotheses.map((item) => `- ${item}`),
    "",
    "## Landing",
    kit.assets.landing_copy,
    "",
  ].join("\n");
}

export default function KitView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const runId = useSearchParams().get("run") || "run_42";
  const requestKey = `${id}:${runId}`;
  const [activeKey, setActiveKey] = useState(requestKey);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [kit, setKit] = useState<KitOutput | null>(null);
  if (activeKey !== requestKey) {
    setActiveKey(requestKey);
    setStatus("loading");
    setError(null);
    setKit(null);
  }

  useEffect(() => {
    let cancelled = false;
    post<CouncilOutput>(`/runs/${encodeURIComponent(runId)}/council`, { project_id: id })
      .then((council) => {
        if (cancelled) return null;
        if (council.run_id !== runId) throw new Error(`Council result is for ${council.run_id}, not ${runId}`);
        return post<KitOutput>(`/runs/${encodeURIComponent(runId)}/kit`, { project_id: id, council });
      })
      .then((nextKit) => {
        if (cancelled || !nextKit) return;
        setKit(nextKit);
        setStatus("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Kit request failed";
        setError(message);
        setStatus(message.includes("404") ? "empty" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [id, runId]);

  function exportMarkdown() {
    if (!kit) return;
    const blob = new Blob([markdownExport(kit, runId)], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `experiment-kit-${runId}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <PageShell glow="kit">
      <AppHeader
        active="experiments"
        projectId={id}
        subtitle={`Experiment Kit · ${runId}`}
        disclaimer="Proposed tests · simulation is not real demand"
        right={<Button type="button" onClick={exportMarkdown} disabled={!kit}>Export as Markdown</Button>}
      />
      <StepPills steps={KIT_STEPS} current={KIT_CURRENT} done={KIT_DONE} />

      {status === "loading" && <p className="text-muted">Loading experiment kit for {runId}…</p>}
      {status === "empty" && (
        <p className="text-muted">No stored run {runId} for this project. {error}</p>
      )}
      {status === "error" && <p className="text-coral">Experiment kit failed. {error}</p>}
      {status === "ready" && kit && (
        <div className="flex flex-col gap-4">
          {kit.scenario_note && <p className="text-sm text-muted">{kit.scenario_note}</p>}
          {kit.unsupported && kit.unsupported.length > 0 && (
            <p className="text-sm text-muted">{kit.unsupported.join(" ")}</p>
          )}
          <div className="flex flex-wrap items-stretch gap-5">
            <HypothesisList items={kit.hypotheses.map((text) => ({ text }))} />
            <LandingPreview
              headline={landingParts(kit.assets.landing_copy).headline}
              body={landingParts(kit.assets.landing_copy).body}
              ctas={landingParts(kit.assets.landing_copy).ctas}
              assets={kit.assets}
            />
            <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-2">
              <p className="text-sm text-muted">
                Sample preview only. These contact counts and rates are not results for {runId}.
              </p>
              <TelegramConsole
                contacts={TELEGRAM.contacts}
                variants={kit.assets.telegram_variants}
                variantSizes={TELEGRAM.variantSizes}
                results={TELEGRAM.results}
              />
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
