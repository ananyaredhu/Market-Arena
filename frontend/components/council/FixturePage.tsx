"use client";

/**
 * Standalone fixture page for Person B (also usable from app/dev/council).
 * Works with no API: imports local JSON fixtures.
 */
import { useState } from "react";

import type { CouncilOutput, KitOutput } from "@/lib/types";

import CouncilPanel from "./CouncilPanel";
import councilSaas from "./fixtures/council_saas.json";
import kitSaas from "./fixtures/kit_saas.json";
import councilCafe from "./fixtures/council_cafe.json";
import kitCafe from "./fixtures/kit_cafe.json";

const PACKS = {
  saas: { council: councilSaas as CouncilOutput, kit: kitSaas as KitOutput },
  cafe: { council: councilCafe as CouncilOutput, kit: kitCafe as KitOutput },
} as const;

export default function CouncilFixturePage() {
  const [pack, setPack] = useState<keyof typeof PACKS>("saas");
  const data = PACKS[pack];

  return (
    <main className="mx-auto max-w-6xl p-10">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <strong>Council fixture page</strong>
        <button type="button" className="rounded-full border px-3 py-1 text-sm" onClick={() => setPack("saas")}>
          SaaS
        </button>
        <button type="button" className="rounded-full border px-3 py-1 text-sm" onClick={() => setPack("cafe")}>
          Café
        </button>
        <span className="text-sm text-muted">Pack: {pack}</span>
      </div>
      <CouncilPanel council={data.council} kit={data.kit} />
    </main>
  );
}
