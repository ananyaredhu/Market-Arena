"use client";

/**
 * Standalone fixture page for Person B.
 * Mount under any Next.js route, e.g. app/dev/council/page.tsx → export { default } from ...
 * Works with no API: imports local JSON fixtures.
 */
import { useState } from "react";
import { CouncilPanel } from "./CouncilPanel";
import type { CouncilOutput, KitOutput } from "./types";

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
    <main style={{ padding: "1.5rem", background: "#f5f5f4", minHeight: "100vh" }}>
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <strong>Council fixture page</strong>
        <button type="button" className="ma-btn" onClick={() => setPack("saas")}>
          SaaS
        </button>
        <button type="button" className="ma-btn" onClick={() => setPack("cafe")}>
          Café
        </button>
        <span className="ma-muted">Pack: {pack}</span>
      </div>
      <CouncilPanel council={data.council} kit={data.kit} />
    </main>
  );
}
