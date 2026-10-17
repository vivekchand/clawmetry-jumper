import json
from pathlib import Path

import pytest

from clawmetry_jumper.cli import record

UPSTREAM = Path(__file__).resolve().parents[2] / "clawmetry-jumper-upstream"


@pytest.mark.skipif(not UPSTREAM.exists(), reason="Requires pinned public Jumper checkout")
def test_record_reaches_observation_loss_and_preserves_earlier_evidence(tmp_path):
    out = tmp_path / "recording"
    record(UPSTREAM, out, enable_controls=True, seconds=32, video=False)
    result = json.loads((out / "run-report.json").read_text())
    assert result["reference"]["passed"]
    assert any(e.get("type") == "observation_lost" for e in result["events"])
    assert any(e.get("status") == "unknown" for e in result["events"])
    assert result["min_table_margin_m"] > .12
    assert not result["physical_stop_confirmed"]
    assert result["provenance"]["tracked_inputs_clean"]
    assert len(result["provenance"]["files_sha256"]) > 20
    with pytest.raises(ValueError, match="earlier evidence"):
        record(UPSTREAM, out, seconds=1, video=False)
