"use client";
// OWNER: Person B. MOCKUP of the Council screen body (layout and styling from the design board).
// Frozen props: <CouncilPanel council={CouncilOutput} kit={KitOutput} />
// Real data: verdict, confidence, fragility, experiments, competitor_reaction (CouncilOutput).
// Mock data (lib/mock/council.ts): customer quotes and the what-if bars, until the contract carries them.
import { HEADLINE_STATS, PERTURBATIONS, SEGMENT_VOICES, STRATEGIST } from "@/lib/mock/council";
import type { CouncilOutput, KitOutput } from "@/lib/types";

import CustomerCouncil from "./CustomerCouncil";
import DevilsAdvocate from "./DevilsAdvocate";
import ExperimentsRow from "./ExperimentsRow";
import StrategistCard from "./StrategistCard";
import VerdictHero from "./VerdictHero";

interface Props {
  council: CouncilOutput;
  kit: KitOutput; // used by the Kit screen; kept here so the prop contract stays frozen
}

export default function CouncilPanel({ council }: Props) {
  return (
    <div className="flex flex-col gap-6">
      <VerdictHero
        verdict={council.verdict}
        runId={council.run_id}
        confidence={council.confidence}
        fragility={council.fragility}
        stats={[
          { value: HEADLINE_STATS.medianShare, caption: HEADLINE_STATS.medianRange },
          { value: HEADLINE_STATS.worstShare, caption: HEADLINE_STATS.worstCaption, captionTone: "coral" },
        ]}
      />
      <div className="flex flex-wrap items-stretch gap-5">
        <CustomerCouncil voices={SEGMENT_VOICES} />
        <DevilsAdvocate items={PERTURBATIONS} baseline={19} />
        <StrategistCard {...STRATEGIST} />
      </div>
      <ExperimentsRow experiments={council.experiments} />
    </div>
  );
}
