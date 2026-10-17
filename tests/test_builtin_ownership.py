"""This repository is an example consumer, never a second product adapter."""
from pathlib import Path
import tomllib

from clawmetry.physical_ai import DeskMonitor, JumperObserver, Request, Task, TaskGate


def test_governance_and_observation_are_owned_by_the_main_package():
    for value in (DeskMonitor, JumperObserver, Request, Task, TaskGate):
        assert value.__module__.startswith("clawmetry.physical_ai")
    root = Path(__file__).parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    assert "clawmetry" in project["dependencies"]
    assert "clawmetry.extensions" not in project.get("entry-points", {})
    assert not (root / "src/clawmetry_jumper/plugin.py").exists()
    assert not (root / "src/clawmetry_jumper/guard.py").exists()
    assert not (root / "src/clawmetry_jumper/monitor.py").exists()
