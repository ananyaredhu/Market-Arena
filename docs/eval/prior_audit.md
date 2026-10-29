# Prior audit: `saas` pack

*Demo product `StudyFlow` at 7.0 SGD per month; share on the pack's template customers (base 6.2%); 3 seeds x 15 repeats; no language model.*

## Where the priors come from

- **Datasets (real, applied in full):** budget ranges are scaled by the country's income level (World Bank) and by the measured change in consumer prices from the starting year to the latest year (SingStat for Singapore, Eurostat for Europe, the US Bureau of Labor Statistics for the US). Other countries get the income scale only.
- **Assumptions (everything else):** price sensitivity, feature weights, switching cost, risk, outside appeal, randomness, brand pull, incumbency and segment shares are the pack author's stated assumptions. No open dataset measures them. Surveys and articles about them are kept in the Resources library, as reference only, and never move a prior.

## How much each prior class matters

Each class's ranges, in every segment, multiplied by 0.75 and by 1.25. Change in the demo product's share, in percentage points.

| Prior | What it is | x0.75 | x1.25 |
|---|---|---|---|
| `budget` | what a customer can spend per period | -1.1 | +0.8 |
| `alpha` | price sensitivity | +0.9 | -0.6 |
| `w` | weight on each feature | -0.8 | +0.7 |
| `switch` | cost of leaving what they use now | +0.2 | -0.3 |
| `risk` | dislike of trying something new | +0.3 | -0.2 |
| `outside_utility` | appeal of doing nothing / a free tool | +0.0 | +0.0 |
| `tau` | how random choices are | -0.6 | +0.6 |
| `brand` | pull of a known competitor (the new product starts at 0) | +0.1 | -0.2 |

## The biggest assumption: how well known the new product is

The pack gives a brand-new product a brand score of 0 in every segment. If it were already known:

| Brand score for the product | Change in share (points) |
|---|---|
| 0.2 | +1.6 |
| 0.4 | +3.3 |

Read: no single prior class moves the share by more than about a point in either direction here, while giving the product a brand score of 0.4 moves it by several. The new product's lack of brand is the largest lever and an assumption the user should set for their own case.

## Segments and ranges (the assumptions in full)

### Budget-conscious students (`budget`, share 35%)
- budget (3.0, 9.0), price sensitivity (0.15, 0.3), switching (0.1, 0.5), risk (0.1, 0.5), outside appeal (0.1, 0.5), randomness (0.6, 1.0)
- feature weights: ai_planning (0.1, 0.5), simplicity (0.5, 0.9), privacy (0.1, 0.4), integrations (0.0, 0.2)
- brand pull: {'free_tool': (0.2, 0.6), 'chain_app': (0.0, 0.3)}; starts with: {'free_tool': 0.7, 'outside': 0.3}
- basis: illustrative assumption

### Exam-focused students (`exam`, share 25%)
- budget (6.0, 15.0), price sensitivity (0.05, 0.15), switching (0.1, 0.5), risk (0.1, 0.5), outside appeal (0.1, 0.5), randomness (0.6, 1.0)
- feature weights: ai_planning (0.5, 0.9), simplicity (0.3, 0.7), privacy (0.2, 0.5), integrations (0.1, 0.4)
- brand pull: {'free_tool': (0.0, 0.3), 'chain_app': (0.0, 0.3)}; starts with: {'free_tool': 0.5, 'chain_app': 0.3, 'outside': 0.2}
- basis: illustrative assumption

### Productivity enthusiasts (`power`, share 15%)
- budget (8.0, 25.0), price sensitivity (0.05, 0.1), switching (0.1, 0.4), risk (0.1, 0.4), outside appeal (0.1, 0.4), randomness (0.6, 1.0)
- feature weights: ai_planning (0.3, 0.7), simplicity (0.2, 0.5), privacy (0.4, 0.9), integrations (0.5, 0.9)
- brand pull: {'free_tool': (0.0, 0.2), 'chain_app': (0.0, 0.3)}; starts with: {'chain_app': 0.6, 'free_tool': 0.4}
- basis: illustrative assumption

### Free-tool loyalists (hostile) (`loyal`, share 25%, hostile)
- budget (0.0, 4.0), price sensitivity (0.25, 0.3), switching (0.5, 0.9), risk (0.3, 0.7), outside appeal (0.1, 0.5), randomness (0.6, 1.0)
- feature weights: ai_planning (0.0, 0.2), simplicity (0.6, 1.0), privacy (0.1, 0.4), integrations (0.0, 0.1)
- brand pull: {'free_tool': (0.6, 1.0), 'chain_app': (0.0, 0.3)}; starts with: {'free_tool': 0.85, 'outside': 0.15}
- basis: illustrative assumption
