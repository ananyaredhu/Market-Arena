"use client";
// OWNER: Person B. Screen 3 mockup: "Arena Council verdict".
import { use, useEffect, useState } from "react";

import CouncilPanel from "@/components/council/CouncilPanel";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { post } from "@/lib/api";
import type { CouncilOutput, KitOutput } from "@/lib/types";

export default function CouncilView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [council, setCouncil] = useState<CouncilOutput | null>(null);
  const [kit, setKit] = useState<KitOutput | null>(null);

  useEffect(() => {
    post<CouncilOutput>("/runs/run_42/council").then(setCouncil);
    post<KitOutput>("/runs/run_42/kit").then(setKit);
  }, []);

  return (
    <PageShell glow="council">
      <AppHeader
        active="council"
        projectId={id}
        subtitle={`Council · StudyFlow · ${council?.run_id ?? "…"}`}
        disclaimer="Sample numbers · simulated outcome under stated assumptions"
      />
      {council && kit ? <CouncilPanel council={council} kit={kit} /> : <p className="text-muted">Loading…</p>}
    </PageShell>
  );
}
