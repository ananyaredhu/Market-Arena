"use client";
// OWNER: Person B. Council screen body (layout from the design board).
// Frozen props: <CouncilPanel council={CouncilOutput} kit={KitOutput} />
// Real data drives verdict, confidence, fragility, experiments, risks, competitor_reaction.
// Mock copy still fills customer quotes until optional contract fields land.
import { SEGMENT_VOICES } from "@/lib/mock/council";
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

function parseSharePct(metric: string, fallback: number): number {
  const match = metric.match(/(\d+(?:\.\d+)?)\s*%/);
  if (match) return Number(match[1]);
  const arrow = metric.match(/->\s*(\d+(?:\.\d+)?)/);
  if (arrow) {
    const value = Number(arrow[1]);
    return value <= 1 ? Math.round(value * 1000) / 10 : value;
  }
  return fallback;
}

function headlineStats(council: CouncilOutput) {
  const worst = council.risks[0];
  const worstPct = worst ? parseSharePct(worst.metric, 6) : 6;
  return [
    {
      value: `${Math.round(council.fragility < 1 ? (1 - council.fragility) * 20 + 5 : 8)}%`,
      caption: "indicative share · see run totals",
    },
    {
      value: `${worstPct}%`,
      caption: worst ? `if ${worst.title}` : "top risk",
      captionTone: "coral" as const,
    },
  ];
}

function perturbationsFromRisks(council: CouncilOutput) {
  if (!council.risks.length) {
    return [{ label: "No ranked risks", from: 10, to: 10, severity: "medium" as const }];
  }
  return council.risks.map((risk, index) => {
    const after = parseSharePct(risk.metric, 10 - index);
    const beforeMatch = risk.metric.match(/share\s+(\d+(?:\.\d+)?)/i);
    const beforeRaw = beforeMatch ? Number(beforeMatch[1]) : after + 5;
    const before = beforeRaw <= 1 ? Math.round(beforeRaw * 1000) / 10 : beforeRaw;
    return {
      label: risk.title,
      from: before,
      to: after <= 1 && !risk.metric.includes("%") ? Math.round(after * 1000) / 10 : after,
      severity: (index === 0 ? "high" : "medium") as "high" | "medium",
    };
  });
}

function strategistFromCouncil(council: CouncilOutput) {
  const reaction = council.competitor_reaction;
  if (!reaction) {
    return {
      competitor: "No rival move",
      headline: "No competitor move reduced simulated share",
      explanation: "Among the four bounded moves, none cut your share under the current priors.",
      shareImpact: "0 pts",
      moves: "4 / 4",
    };
  }
  const pts = Math.round(reaction.effect_on_share * 1000) / 10;
  return {
    competitor: reaction.competitor_id,
    headline: `${reaction.competitor_id} responds with ${reaction.move}`,
    explanation: "Best of four bounded moves: −10% price, −20% price, add a feature, run a promo.",
    shareImpact: `${pts} pts`,
    moves: "4 / 4",
  };
}

export default function CouncilPanel({ council }: Props) {
  const baseline =
    perturbationsFromRisks(council)[0]?.from ||
    Math.max(1, Math.round((1 - council.fragility) * 20));
  const stats = headlineStats(council);
  // Prefer a clearer median caption when fragility is available.
  stats[0] = {
    value: `${Math.round(baseline)}%`,
    caption: `baseline share · fragility ${council.fragility.toFixed(2)}`,
  };

  return (
    <div className="flex flex-col gap-6">
      <VerdictHero
        verdict={council.verdict}
        runId={council.run_id}
        confidence={council.confidence}
        fragility={council.fragility}
        stats={stats}
      />
      <div className="flex flex-wrap items-stretch gap-5">
        <CustomerCouncil
          voices={
            council.who_buys.length || council.who_rejects.length
              ? [
                  ...council.who_buys.slice(0, 2).map((line, i) => ({
                    segment: `buys-${i}`,
                    pct: Math.max(5, baseline - i * 5),
                    quote: line,
                  })),
                  ...council.who_rejects.slice(0, 1).map((line) => ({
                    segment: "rejects",
                    pct: Math.max(3, Math.round(baseline / 3)),
                    quote: line,
                  })),
                ]
              : SEGMENT_VOICES
          }
        />
        <DevilsAdvocate items={perturbationsFromRisks(council)} baseline={baseline || 19} />
        <StrategistCard {...strategistFromCouncil(council)} />
      </div>
      <ExperimentsRow experiments={council.experiments} />
    </div>
  );
}
