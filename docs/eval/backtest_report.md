# Backtest report

*Generated 2026-10-29 07:41 UTC · priors `cafe:d6977f09ccbf, saas:af5ec85d8bab` · 15 repeats × seeds per case · LLM baseline: off*

**What this tests.** Whether the simulator's predicted *direction* (a price or feature change) or *success* (a launch reaching a stated target) matches what really happened in documented real events. It is not a forecast of sales and says nothing about magnitude.

## Headline (real, sourced cases only)

| Method | Correct | Accuracy | 95% interval |
|---|---|---|---|
| **Market Arena simulator** | 2 / 4 | 50% | 15% to 85% |
| Chance (fair coin over the outcomes) | n/a | 33% | |
| Naive rule of thumb (cheaper → up, dearer → down) | 2 / 4 | 50% | 15% to 85% |
| Majority-class guess ('down', an oracle that sees the answers) | 3 / 4 | 75% | 30% to 95% |
| Simulator, relative rule (all direction cases; see note) | 3 / 4 | 75% | 30% to 95% |
| Simulator, relative rule, only cases written after it was declared | 1 / 1 | 100% | 21% to 100% |

Chance of doing at least this well by luck alone: p = 0.407 (exact binomial). Head to head with the naive rule: the simulator alone was right on 1 case(s), the naive rule alone on 1.

**Read the interval, not just the percentage:** with 4 case(s) the data cannot separate a good model from a lucky one.

## Every case

| Case | Question | Observed | Simulator | Seeds agree | Relative rule | Naive | LLM | |
|---|---|---|---|---|---|---|---|---|
| cafe_starbucks_china_own_price_cut | After Starbucks China cut the price of dozens of its drinks by about 5 | up | up (+5.1% ± 0.6%) | 100% | up ✓ (retro) | up ✓ | - | right |
| cafe_starbucks_china_price_war | After Luckin and Cotti pushed 9.9-yuan coffee in 2023, did Starbucks C | down | down (-0.9% ± 0.2%) | 60% | down ✓ (retro) | flat ✗ | - | right |
| saas_chegg_free_ai_arrives | After a free AI assistant became widely available to students (ChatGPT | down | flat (-0.1% ± 0.2%) | 100% | flat ✗ (retro) | flat ✗ | - | **wrong** |
| saas_netflix_us_price_rise_2022 | After Netflix raised its US and Canada prices in January 2022 (Standar | down | flat (-0.6% ± 0.4%) | 60% | down ✓ | down ✓ | - | **wrong** |
| selftest_launch_fail | Plumbing self-test (not a real event). An expensive, weak product shou | fail | fail | 100% | - | fail ✓ | - | synthetic |
| selftest_launch_success | Plumbing self-test (not a real event). A cheap, strong product should  | success | success | 100% | - | success ✓ | - | synthetic |
| selftest_no_change | Plumbing self-test (not a real event). An unchanged market should show | flat | flat (+0.0% ± 0.0%) | 100% | flat ✓ (retro) | flat ✓ | - | synthetic |
| selftest_price_cut | Plumbing self-test (not a real event). A large price cut should raise  | up | up (+7.1% ± 0.5%) | 100% | up ✓ (retro) | up ✓ | - | synthetic |
| selftest_price_rise | Plumbing self-test (not a real event). A large price rise should lower | down | down (-5.3% ± 0.3%) | 100% | down ✓ (retro) | down ✓ | - | synthetic |

## Failures

- **saas_chegg_free_ai_arrives**: observed `down`, simulator said `flat` (share before 1.6%, after 1.5%). Explain why before using it.
- **saas_netflix_us_price_rise_2022**: observed `down`, simulator said `flat` (share before 1.9%, after 1.3%). Explain why before using it.

## Plumbing self-test (synthetic, not counted above)

5 of 5 synthetic cases behave as constructed.

## Cases not scored

- `cafe_case_01` (needs_sourcing) from `/Users/ananyaredhu/PycharmProjects/Market-Arena/backend/council/backtest/cafe_case_01.yaml`
- `cafe_luckin_china_price_cut_candidate` (rejected) from `/Users/ananyaredhu/PycharmProjects/Market-Arena/backtest/cases/cafe_luckin_china_price_cut_candidate.yaml`

## Protocol (what keeps this honest)

1. One frozen set of priors (the pack's template) for every case; nothing is tuned per case.
2. No LLM is used by the simulator side, so a result cannot depend on a model's mood.
3. The prediction rule (share change of at least ±1 point is up/down, otherwise flat; success if the share reaches the threshold) is fixed in code before any outcome is looked at.
3b. A second rule is reported alongside, never instead: a change of at least 5% of the product's own starting share is up/down (declared 2026-10-29, after the first SaaS case moved from 1.6% to 1.5% and scored flat under the one-point floor). Cases written before that date show "(retro)": they were seen before the rule existed, so only cases marked prospective count as a clean test of it. The headline table above stays on the original rule.
4. Case inputs must come from information public *before* the event, and thresholds must be fixed beforehand with a written rationale.
5. Five independent populations are simulated per case; the prediction is the majority, and how many agree is shown.
6. Every outcome needs a source URL and access date; unsourced cases are never scored.

## Limits

- Few cases means wide intervals. This is evidence about direction on the cases tried, not proof.
- Real outcomes have confounders (season, marketing, competitors) that the simulator does not model.
- The pack priors are illustrative assumptions, not data. A good result says the structure is sensible; a bad one may mean the priors do not fit that market.
- A language model may remember a real event from its training data, which can flatter the LLM baseline.
