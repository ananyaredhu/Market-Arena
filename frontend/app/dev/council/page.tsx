"use client";
// Standalone page so Person B can build the Council panel without anyone else's code.
import { useEffect, useState } from "react";

import CouncilPanel from "@/components/council/CouncilPanel";
import { post } from "@/lib/api";
import type { CouncilOutput, KitOutput } from "@/lib/types";

export default function DevCouncil() {
  const [council, setCouncil] = useState<CouncilOutput | null>(null);
  const [kit, setKit] = useState<KitOutput | null>(null);
  useEffect(() => {
    post<CouncilOutput>("/runs/run_42/council").then(setCouncil);
    post<KitOutput>("/runs/run_42/kit").then(setKit);
  }, []);
  if (!council || !kit) return <main className="p-8 text-muted">Loading…</main>;
  return (
    <main className="mx-auto max-w-6xl p-10">
      <CouncilPanel council={council} kit={kit} />
    </main>
  );
}
