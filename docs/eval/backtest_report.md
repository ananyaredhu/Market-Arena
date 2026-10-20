# Backtest report

*Generated 2026-10-15 05:07 UTC · priors `cafe:d6977f09ccbf, saas:af5ec85d8bab` · 15 repeats × seeds per case · LLM baseline: off*

**What this tests.** Whether the simulator's predicted *direction* (a price or feature change) or *success* (a launch reaching a stated target) matches what really happened in documented real events. It is not a forecast of sales and says nothing about magnitude.

## Headline

**No sourced real cases have been scored yet.** 1 case(s) are waiting for sourcing: cafe_case_01. Until real cases exist there is no accuracy to report; the synthetic self-tests below only prove the plumbing works.

## Every case

| Case | Question | Observed | Simulator | Seeds agree | Naive | LLM | |
|---|---|---|---|---|---|---|---|
| selftest_launch_fail | Plumbing self-test (not a real event). An expensive, weak product shou | fail | fail | 100% | fail ✓ | - | synthetic |
| selftest_launch_success | Plumbing self-test (not a real event). A cheap, strong product should  | success | success | 100% | success ✓ | - | synthetic |
| selftest_no_change | Plumbing self-test (not a real event). An unchanged market should show | flat | flat (+0.0% ± 0.0%) | 100% | flat ✓ | - | synthetic |
| selftest_price_cut | Plumbing self-test (not a real event). A large price cut should raise  | up | up (+7.1% ± 0.5%) | 100% | up ✓ | - | synthetic |
| selftest_price_rise | Plumbing self-test (not a real event). A large price rise should lower | down | down (-5.3% ± 0.3%) | 100% | down ✓ | - | synthetic |

## Failures

No real cases scored.

## Plumbing self-test (synthetic, not counted above)

5 of 5 synthetic cases behave as constructed.

## Cases not scored

- `cafe_case_01` (needs_sourcing) from `/Users/ananyaredhu/PycharmProjects/Market-Arena/backend/council/backtest/cafe_case_01.yaml`

## Protocol (what keeps this honest)

1. One frozen set of priors (the pack's template) for every case; nothing is tuned per case.
2. No LLM is used by the simulator side, so a result cannot depend on a model's mood.
3. The prediction rule (share change of at least ±1 point is up/down, otherwise flat; success if the share reaches the threshold) is fixed in code before any outcome is looked at.
4. Case inputs must come from information public *before* the event, and thresholds must be fixed beforehand with a written rationale.
5. Five independent populations are simulated per case; the prediction is the majority, and how many agree is shown.
6. Every outcome needs a source URL and access date; unsourced cases are never scored.

## Limits

- Few cases means wide intervals. This is evidence about direction on the cases tried, not proof.
- Real outcomes have confounders (season, marketing, competitors) that the simulator does not model.
- The pack priors are illustrative assumptions, not data. A good result says the structure is sensible; a bad one may mean the priors do not fit that market.
- A language model may remember a real event from its training data, which can flatter the LLM baseline.
