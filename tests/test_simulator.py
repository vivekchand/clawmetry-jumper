"""Integration checks against the actual pinned bundle, never synthetic motion."""
import os
from pathlib import Path

import numpy as np
import pytest

from clawmetry_jumper.simulator import JumperSimulator


UPSTREAM = Path(os.environ.get("JUMPER_UPSTREAM", str(Path(__file__).parents[2] / "clawmetry-jumper-upstream")))
pytestmark = pytest.mark.skipif(not (UPSTREAM / "out/bundle_example/jumper/bundle.json").exists(),
                                reason="Pinned upstream Jumper bundle is required")


@pytest.fixture(scope="module")
def simulator():
    instance = JumperSimulator(UPSTREAM)
    yield instance
    instance.close()


def test_reference_replay_does_not_change_episode(simulator):
    simulator.reset()
    before = simulator.snapshot()
    report = simulator.verify_reference()
    assert report["passed"] and report["frames"] == 24 and report["inferences"] == 18
    assert simulator.snapshot() == before


def test_idle_physics_stays_finite_and_reports_full_collision_bounds(simulator):
    simulator.reset()
    for _ in range(600):
        state = simulator.step()
        assert state["finite"]
        assert max(abs(t) for t in state["joint_torques_nm"].values()) <= simulator.servo["plateau_torque_nm"]
    assert state["time_s"] == pytest.approx(3)
    assert state["mode"] == "locomotion" and state["running_policy"]
    assert state["tilt_deg"] < 10
    assert state["table_margin_m"] > 0
    assert len(state["joint_positions_rad"]) == 22
    box = state["collision_aabb_m"]
    assert np.all(np.array(box["min"]) < np.array(box["max"]))
    assert box["max"][0] - box["min"][0] > .25


def test_native_wave_changes_joints_then_returns_without_episode_reset(simulator):
    simulator.reset()
    for _ in range(600):
        simulator.step()
    start = simulator.snapshot()
    home = np.array(list(start["joint_positions_rad"].values()))
    observed = set()
    max_change = 0
    for i in range(2200):
        keys = [("key_1", True)] if i == 0 else [("key_1", False)] if i == 1 else []
        state = simulator.step(keys)
        observed.add(state["mode"])
        max_change = max(max_change, float(np.max(np.abs(np.array(list(state["joint_positions_rad"].values())) - home))))
        assert state["finite"] and state["table_margin_m"] > 0
    assert "gesture_hello" in observed
    assert state["mode"] == "locomotion"
    assert state["time_s"] == pytest.approx(14)
    assert max_change > .2  # A controller mode label alone is insufficient.

