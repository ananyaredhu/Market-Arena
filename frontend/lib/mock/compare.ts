// MOCK COPY for the Scenario compare screen (design placeholder text).
// Real data: the two RunResults from POST /scenarios/compare. Aggregate "flip" numbers come from Person A's
// flip summary once built (Master Plan 5.2).

export const SCENARIO_A = { tag: "Scenario A · baseline", price: "S$7 / month", note: "14-day trial · no student plan" };
export const SCENARIO_B = { tag: "Scenario B · student plan", price: "S$3 / month", note: "Same trial · verified-student price" };

export const FLIP_SUMMARY = [
  { pct: "18%", tone: "coral" as const, text: "of Budget students flip to you with a S$2 price cut." },
  { pct: "6%", tone: "amber" as const, text: "of Busy professionals flip if you add calendar sync." },
  { pct: "1%", tone: "violet" as const, text: "of Skeptics flip on any price. Don’t chase them." },
];

export const TRADEOFF_NOTE =
  "A price cut lifts share, but revenue per customer falls. Whether total revenue rises depends on how many customers you gain. Test that before you commit.";
