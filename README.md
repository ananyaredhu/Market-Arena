# Market Arena

AI startup-market simulation for the NTU AI Alliance Entrepreneurship Competition.

Planning docs:

- [`MARKET_ARENA_Master_Plan.md`](MARKET_ARENA_Master_Plan.md)
- [`MARKET_ARENA_Team_Work_Split.md`](MARKET_ARENA_Team_Work_Split.md)

## Person B (Council & Kit)

See [`PERSON_B_README.md`](PERSON_B_README.md) for setup, tests, and ownership.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-person-b.txt
cd backend && ../.venv/bin/pytest
open ../frontend/components/council/council_standalone.html
```
