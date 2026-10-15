"""Frontend Council and Kit views: state copy and share parsing, without a browser."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
COUNCIL_VIEW = ROOT / "frontend" / "app" / "project" / "[id]" / "council" / "CouncilView.tsx"
KIT_VIEW = ROOT / "frontend" / "app" / "project" / "[id]" / "kit" / "KitView.tsx"
PANEL = ROOT / "frontend" / "components" / "council" / "CouncilPanel.tsx"
METRICS = ROOT / "frontend" / "lib" / "councilMetrics.ts"
API = ROOT / "frontend" / "lib" / "api.ts"

MEDIAN_SHARE = re.compile(r"median share of (\d+(?:\.\d+)?)")
SHARE_MOVE = re.compile(r"share (\d+(?:\.\d+)?) -> (\d+(?:\.\d+)?)")
SEGMENT_LINE = re.compile(r"^([^:]+): (\d+) of (\d+) simulated agents chose .+ \((\d+(?:\.\d+)?)\)")


def test_api_base_matches_the_backend_port():
    text = API.read_text()
    assert "http://localhost:8000" in text
    assert "localhost:8001" not in text


def test_views_render_loading_empty_and_error():
    council = COUNCIL_VIEW.read_text()
    kit = KIT_VIEW.read_text()
    for text in (council, kit):
        assert "Loading" in text
        assert 'status === "empty"' in text
        assert 'status === "error"' in text
        assert 'status === "ready"' in text
        assert "project_id: id" in text
    assert "run_42" in council  # default demo id, overridable with ?run=
    assert "useSearchParams" in council
    assert "Fixture fallback" not in council or "fixture_fallback" in council
    panel = PANEL.read_text()
    assert "1 - council.fragility" not in panel
    assert "SEGMENT_VOICES" not in panel


def test_metric_patterns_match_the_typescript_helpers():
    source = METRICS.read_text()
    assert "median share of" in source
    assert "share (" in source or "share " in source
    assert "simulated agents chose" in source

    verdict = "Simulated outcome: median share of 0.18 (p10 0.16, p90 0.19)."
    assert MEDIAN_SHARE.search(verdict).group(1) == "0.18"
    move = SHARE_MOVE.search("share 0.190 -> 0.140 (-0.050, -26.3%)")
    assert move.group(1) == "0.190" and move.group(2) == "0.140"
    segment = SEGMENT_LINE.search("Power planners: 33 of 90 simulated agents chose StudyFlow (0.37)")
    assert segment.group(1) == "Power planners"
    assert segment.group(4) == "0.37"
    assert MEDIAN_SHARE.search("No share was calculated.") is None
