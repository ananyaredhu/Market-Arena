"""Write contracts/<Name>.schema.json from the Pydantic models.

`python -m scripts.export_schemas`          regenerate
`python -m scripts.export_schemas --check`  fail if the committed schemas are out of date (CI)
"""
import json
import sys
from pathlib import Path

from backend.common.contracts import CONTRACTS

OUT = Path(__file__).resolve().parent.parent / "contracts"


def render(model) -> str:
    return json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"


def main(check: bool) -> int:
    stale = []
    for name, model in CONTRACTS.items():
        path = OUT / f"{name}.schema.json"
        text = render(model)
        if check:
            if not path.exists() or path.read_text() != text:
                stale.append(path.name)
        else:
            path.write_text(text)
    if stale:
        print("Out of date, run `make schemas`:", ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
