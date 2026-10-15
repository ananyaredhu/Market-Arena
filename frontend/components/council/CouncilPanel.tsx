"use client";
// OWNER: Person B. Council screen body (layout from the design board).
// Frozen props: <CouncilPanel council={CouncilOutput} kit={KitOutput} />
// Headline numbers come from measured fields or from figures already written in the council text.
import type { CouncilOutput, KitOutput } from "@/lib/types";
import { baselineShare, formatShare, medianShare, parseSegmentLine, parseShareMove } from "@/lib/councilMetrics";

import CustomerCouncil from "./CustomerCouncil";
import DevilsAdvocate from "./DevilsAdvocate";
import ExperimentsRow from "./ExperimentsRow";
import StrategistCard from "./StrategistCard";
import VerdictHero from "./VerdictHero";

interface Props {
  council: CouncilOutput;
  kit: KitOutput; // used by the Kit screen; kept here so the prop contract stays frozen
}

const MOVE_TEXT: Record<string, string> = {
  price_cut_10: "a 10% price cut",
  price_cut_20: "a 20% price cut",
  add_feature: "adding a feature",
  promo: "a promotion",
};

function headlineStats(council: CouncilOutput) {
  const median = medianShare(council);
  const worst = council.measured?.risks[0];
  const parsedWorst = council.risks[0] ? parseShareMove(council.risks[0].metric) : null;
  const worstShare = worst?.perturbed_share ?? parsedWorst?.after ?? null;
  return [
    {
      value: median == null ? "—" : formatShare(median),
      caption:
        council.measured?.p10 != null && council.measured?.p90 != null
          ? `median share · ${formatShare(council.measured.p10)}–${formatShare(council.measured.p90)}`
          : "median share from this run",
    },
    {
      value: worstShare == null ? "—" : formatShare(worstShare),
      caption: worst?.title ?? council.risks[0]?.title ?? "no ranked risk",
      captionTone: "coral" as const,
    },
  ];
}

function perturbationsFromCouncil(council: CouncilOutput) {
  if (council.measured?.risks.length) {
    return council.measured.risks.map((risk, index) => ({
      label: risk.title,
      from: Math.round(risk.baseline_share * 1000) / 10,
      to: Math.round(risk.perturbed_share * 1000) / 10,
      severity: (index === 0 ? "high" : "medium") as "high" | "medium",
    }));
  }
  return council.risks.flatMap((risk, index) => {
    const move = parseShareMove(risk.metric);
    if (!move) return [];
    return [{
      label: risk.title,
      from: Math.round(move.before * 1000) / 10,
      to: Math.round(move.after * 1000) / 10,
      severity: (index === 0 ? "high" : "medium") as "high" | "medium",
    }];
  });
}

function strategistFromCouncil(council: CouncilOutput) {
  const measured = council.measured?.competitor;
  const reaction = council.competitor_reaction;
  if (!measured && !reaction) {
    return {
      competitor: "No rival move",
      headline: "No competitor move reduced simulated share",
      explanation: "Among the bounded moves the engine evaluated, none cut your share.",
      shareImpact: "—",
      moves: "evaluated",
    };
  }
  const change = measured?.share_change ?? reaction?.effect_on_share ?? 0;
  const move = measured?.move ?? reaction?.move ?? "";
  const name = measured?.competitor_id ?? reaction?.competitor_id ?? "Rival";
  const pts = Math.round(change * 1000) / 10;
  return {
    competitor: name,
    headline: `${name} responds with ${MOVE_TEXT[move] ?? move}`,
    explanation: measured?.description
      ? `Selected from engine runs. ${measured.description}.`
      : "Selected from the bounded moves the engine was able to evaluate.",
    shareImpact: `${pts} pts`,
    moves: "calculated",
  };
}

function voicesFromCouncil(council: CouncilOutput) {
  if (council.measured?.segments.length) {
    return council.measured.segments.slice(0, 3).map((segment) => ({
      segment: segment.id,
      pct: Math.round(segment.share * 1000) / 10,
      quote: `${segment.name}: ${segment.n_you} of ${segment.n} simulated agents chose you (${formatShare(segment.share)}).`,
    }));
  }
  return [...council.who_buys, ...council.who_rejects].slice(0, 3).flatMap((line) => {
    const parsed = parseSegmentLine(line);
    if (!parsed) return [{ segment: "segment", pct: 0, quote: line }];
    return [{
      segment: parsed.name,
      pct: Math.round(parsed.share * 1000) / 10,
      quote: line,
    }];
  });
}

export default function CouncilPanel({ council }: Props) {
  const baseline = baselineShare(council);
  const baselinePct = baseline == null ? 0 : Math.round(baseline * 1000) / 10;
  const items = perturbationsFromCouncil(council);

  return (
    <div className="flex flex-col gap-6">
      <VerdictHero
        verdict={council.verdict}
        runId={council.run_id}
        confidence={council.confidence}
        fragility={council.fragility}
        stats={headlineStats(council)}
      />
      {council.scenario_origin === "fixture_fallback" && (
        <p className="text-sm text-coral">Fixture fallback. These figures were not computed for this run.</p>
      )}
      <div className="flex flex-wrap items-stretch gap-5">
        <CustomerCouncil voices={voicesFromCouncil(council)} />
        <DevilsAdvocate
          items={items.length ? items : [{ label: "No measured risk", from: baselinePct, to: baselinePct, severity: "medium" }]}
          baseline={baselinePct || 1}
        />
        <StrategistCard {...strategistFromCouncil(council)} />
      </div>
      <ExperimentsRow experiments={council.experiments} />
      {council.trend_context && council.trend_context.length > 0 && (
        <p className="text-sm text-muted">
          Cited context, not applied to the shares:{" "}
          {council.trend_context.map((note) => `${note.trend} (${note.source_url})`).join(" · ")}
        </p>
      )}
    </div>
  );
}
