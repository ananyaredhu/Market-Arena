"use client";
// OWNER: Person B (Kit columns) and Person C (Telegram console). Screen 5 mockup: "Experiment Kit + Telegram".
import { use, useEffect, useState } from "react";

import StepPills from "@/components/intake/StepPills";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import HypothesisList from "@/components/kit/HypothesisList";
import LandingPreview from "@/components/kit/LandingPreview";
import TelegramConsole from "@/components/telegram/TelegramConsole";
import { Button } from "@/components/ui";
import { post } from "@/lib/api";
import { KIT_CURRENT, KIT_DONE, KIT_STEPS, LANDING_CTA, LANDING_HEADLINE, PASS_TAGS, TELEGRAM } from "@/lib/mock/kit";
import type { KitOutput } from "@/lib/types";

export default function KitView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [kit, setKit] = useState<KitOutput | null>(null);

  useEffect(() => {
    post<KitOutput>("/runs/run_42/kit").then(setKit);
  }, []);

  return (
    <PageShell glow="kit">
      <AppHeader
        active="experiments"
        projectId={id}
        subtitle="Experiment Kit · from simulation to real evidence"
        disclaimer={false}
        right={<Button>Export as Markdown</Button>}
      />
      <StepPills steps={KIT_STEPS} current={KIT_CURRENT} done={KIT_DONE} />

      {kit ? (
        <div className="flex flex-wrap items-stretch gap-5">
          <HypothesisList items={kit.hypotheses.map((text, i) => ({ text, pass: PASS_TAGS[i] }))} />
          <LandingPreview
            headline={LANDING_HEADLINE}
            body={kit.assets.landing_copy}
            ctas={[LANDING_CTA[0], LANDING_CTA[1]]}
            assets={kit.assets}
          />
          <TelegramConsole
            contacts={TELEGRAM.contacts}
            variants={kit.assets.telegram_variants}
            variantSizes={TELEGRAM.variantSizes}
            results={TELEGRAM.results}
          />
        </div>
      ) : (
        <p className="text-muted">Loading…</p>
      )}
    </PageShell>
  );
}
