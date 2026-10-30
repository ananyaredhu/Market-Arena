# Intake changes for Person C (from Person A)

While connecting real runs and the price finder I found seven problems in the intake path. C had no open work, so they
are fixed here, in `backend/intake/projects.py` and its neighbours. Same reproduction as before:

```python
from backend.intake.projects import ProjectCreateRequest as R, build_product_profile as b
p = b(R(idea="A study planner app for NUS students at $9 a month", pack="saas"))
print(p.price, p.missing_assumptions)   # was: 0.0 and "What price will customers pay?"
```

| # | Problem | Now |
|---|---|---|
| 1 | `$9`, `3$`, `9 dollars`, `€4.50`, `500 rupees` were not read as prices, so `POST /scenarios` refused the project | All of them are read. A bare `$` is the pack's currency (US dollars when the market is the US). A number with no currency (`9 students`) is never a price. |
| 2 | Geography was never read from the text | `backend/intake/geography.py` finds the first country or city named (85 country names and 80 cities, covering 74 countries). A country written out (`Germany`) is turned into its code. Nothing named means Singapore is still assumed, and still asked. |
| 3 | A pet-grooming idea was accepted under the SaaS pack with no word | A warning is added to `missing_assumptions` when the idea does not match the pack's words, or reads like the other pack. It never refuses. |
| 4 | The free-tier question existed for SaaS only | The café pack asks about a free sample, loyalty reward or introductory offer. |
| 5 | `StudyFlow` became `Studyflow` | Words that already have a capital letter keep it; the name stops at the first comma. |
| 6 | Café currency was `S$`, SaaS `SGD`; the Kit printed `SGD7` for SaaS; a 500 INR price was compared with S$ budgets | Both packs use the code. `backend/common/money.py` turns a code into its symbol, and the Kit and Council use it. The market is simulated in the founder's currency (below). |
| 7 | A project with no price could not be simulated or priced | New route below. |

New things you may want to use:

- **The founder's currency is kept, never converted.** `profile.currency` is the currency written with the price
  (`500 rupees` gives `INR`), else the currency of the country the market is in (`Berlin` gives `EUR`), else the pack's.
  A bare `$` is the market's own dollar when it has one (`AUD` in Australia), US dollars when the market uses another
  currency, and the pack's currency when no market is named.
- **The market is simulated in that currency.** The packs' money assumptions are written in Singapore dollars, so
  `backend/population/localise.py` re-expresses them (customer budgets, rivals' prices, price sensitivity) by one factor
  from real data: the World Bank purchasing-power-parity factor, as a ratio to Singapore. It is a price-level factor, not
  an exchange rate, and the founder's own price is never touched. Where the data is missing the pack is left as written
  and `population.generation.currency.note` says so. The same note is in the scenario's `assumptions`.
- **Every screen's symbol follows the project.** Stored runs carry the currency in `population.generation.currency.code`;
  Compare, the price finder, Glass-Box, the Kit and the Council read it (`₹500`, not `S$500`).
- **`POST /projects/{project_id}/price-suggestion`** `{cost?, min_price?, max_price?, steps?, seed?, n_agents?, repeats?}`.
  For a project with no price (or any project): builds the market from the pack's template customers with a placeholder
  price (the project's own, else the pack's demo price), sweeps the price, and returns the same shape as
  `POST /pricing/suggest` plus `price_was_missing`, `placeholder_price`, `currency`, `currency_note` and `basis`. It stores nothing. Show
  `suggestion.price` and `band` as "where to start testing" and let the founder confirm or type a price before it becomes
  the project's price. Do not save the suggestion silently.
- The Compare screen has a "Find a price" panel for stored runs (`/compare?project=<id>&run=<id>`).

Tests: `backend/tests/test_intake_rules.py`. Tell me if any extraction rule is wrong for your screens.
