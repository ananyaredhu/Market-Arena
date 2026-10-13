// MOCK COPY for the Experiment Kit + Telegram screen (design placeholder text).
// Real data: KitOutput from POST /runs/{id}/kit, Telegram results from GET /telegram/campaigns/{id}/results.

export const KIT_STEPS = ["Simulate", "Draft assets", "Approve", "Send to opt-in list", "Compare with simulation"];
export const KIT_DONE = [0, 1];
export const KIT_CURRENT = 2;

/** Pass thresholds shown on each hypothesis chip (KitOutput.hypotheses are plain strings today). */
export const PASS_TAGS = ["pass ≥ 70% of S$7 conversion", "pass ≥ 50% of waitlist from this segment", "pass: B beats A by 2+ pts"];

export const LANDING_HEADLINE = "Your exam plan, rebuilt every time life happens.";
export const LANDING_CTA = ["Start free trial · S$7/mo", "Join waitlist"];

export const TELEGRAM = {
  contacts: 47,
  variantSizes: [24, 23],
  results: [
    { variant: "A", rate: 7.9 },
    { variant: "B", rate: 11.5 },
  ],
};
