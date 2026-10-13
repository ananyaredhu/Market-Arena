// MOCK COPY for the Council screen. These are the parts of the design that CouncilOutput does not carry yet.
// To make them real, propose OPTIONAL contract fields (all three people agree), e.g.
//   CouncilOutput.segment_voices: [{segment, share_choose_you, quote}]
//   CouncilOutput.risks[].share_before / share_after (numbers, so the bars need no parsing)
// Then delete the matching constant here.

export const SEGMENT_VOICES = [
  { segment: "power", pct: 55, quote: "The adaptive schedule is the reason I’d pay. I’d like calendar sync." },
  { segment: "budget", pct: 20, quote: "S$9 is a lot when a free tool exists. A student plan would change my mind." },
  { segment: "loyal", pct: 7, quote: "I’ve never kept up with a planner. Why would this be different?" },
];

export interface Perturbation {
  label: string;
  from: number; // baseline share (percent)
  to: number; // share after the shock (percent)
  severity: "high" | "medium";
}

export const PERTURBATIONS: Perturbation[] = [
  { label: "Willingness to pay −25%", from: 19, to: 6, severity: "high" },
  { label: "FreeTool adds AI planning", from: 19, to: 11, severity: "high" },
  { label: "Price sensitivity +20%", from: 19, to: 14, severity: "medium" },
];

export const HEADLINE_STATS = {
  medianShare: "19%",
  medianRange: "median share · 14–24%",
  worstShare: "6%",
  worstCaption: "if WTP −25%",
};

export const STRATEGIST = {
  competitor: "ChainApp",
  headline: "ChainApp cuts its price by 20%",
  explanation: "Best of four bounded moves it tried against you: −10% price, −20% price, add a feature, run a promo.",
  shareImpact: "−5 pts",
  moves: "4 / 4",
};
