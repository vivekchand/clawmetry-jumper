from pathlib import Path
from types import SimpleNamespace
import importlib.util
import subprocess

import pytest

from clawmetry_jumper.provenance import validate_official_outputs, verify_upstream


def test_any_existing_official_artifact_is_preserved(tmp_path):
    video, db = tmp_path / "film.mp4", tmp_path / "events.duckdb"
    outputs = validate_official_outputs(video, db)
    for artifact in outputs:
        artifact.write_text("keep me")
        with pytest.raises(ValueError, match="earlier recordings"):
            validate_official_outputs(video, db)
        assert artifact.read_text() == "keep me"
        artifact.unlink()
    with pytest.raises(ValueError):
        validate_official_outputs(video, video)
    with pytest.raises(ValueError):
        validate_official_outputs(Path(str(db) + ".wal"), db)


def test_wrong_source_commit_refused_before_execution(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "sentinel.py").write_text("raise AssertionError('must not execute')")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-qm", "test"], check=True)
    with pytest.raises(ValueError, match="pinned unmodified"):
        verify_upstream(tmp_path, official=True)
    script = Path(__file__).resolve().parents[1] / "scripts/official_replay.py"
    spec = importlib.util.spec_from_file_location("official_test_preflight", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The minimal test environment has no upstream training package. A wrong
    # source must be rejected before importing it, not die in its code later.
    with pytest.raises(ValueError, match="pinned unmodified"):
        module.run(SimpleNamespace(upstream=tmp_path, video=tmp_path / "out.mp4",
                                   evidence=tmp_path / "out.duckdb"))
