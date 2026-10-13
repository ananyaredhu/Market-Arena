# Person B contract proposals

These JSON Schemas are generated from `council.schemas` and live under Person B's
folder until the team promotes them to the shared `/contracts` directory.

Regenerate:

```bash
cd backend && ../.venv/bin/python -m council.fixtures.make_fixtures
```

Proposed optional fields (need team approval before promoting):

- `CouncilOutput.limitations`
- `CouncilOutput.engine_source`
- `KitAssets.tracking_plan`
- `KitOffline.price_board_test`
