"""Actual native model boundaries for the opt-in scripted contact demonstration."""
import os
from pathlib import Path

import mujoco
import numpy as np
import pytest

from clawmetry_jumper.simulator import JumperSimulator
from clawmetry_jumper.manipulation import LF_JOINTS, OBJECTS, desk_model

UPSTREAM = Path(os.environ.get('JUMPER_UPSTREAM', str(Path(__file__).parents[2] / 'clawmetry-jumper-upstream')))
pytestmark = pytest.mark.skipif(not (UPSTREAM / 'out/bundle_example/jumper/bundle.json').exists(),
                                reason='Pinned upstream Jumper bundle is required')


@pytest.fixture(scope='module')
def models():
    baseline = JumperSimulator(UPSTREAM)
    desk = JumperSimulator(UPSTREAM, desk_skills=True)
    yield baseline, desk
    desk.close(); baseline.close()


def test_free_props_and_convex_jaws_preserve_original_robot_inertia(models):
    baseline, desk = models
    assert desk.model.nq == baseline.model.nq + 14
    assert desk.model.neq == baseline.model.neq
    for body_id in range(1, baseline.model.nbody):
        name = baseline.model.body(body_id).name
        new_id = desk.model.body(name).id
        np.testing.assert_allclose(desk.model.body_mass[new_id], baseline.model.body_mass[body_id], rtol=0, atol=0)
        np.testing.assert_allclose(desk.model.body_inertia[new_id], baseline.model.body_inertia[body_id], rtol=0, atol=0)
    for name, count in [('LF_palm_link', 6), ('LF_finger_link', 3)]:
        pieces = [g for g in range(desk.model.ngeom) if desk.model.geom(g).name.startswith(name + '_meshcol')]
        assert len(pieces) == count
    for name, spec in OBJECTS.items():
        body = desk.model.body(name).id
        joint = desk.model.joint(name + '_free').id
        assert desk.model.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE
        assert desk.model.body_mass[body] == pytest.approx(spec['mass_kg'])
    config = desk.manipulation_config()
    assert config['objects']['empty_cup']['shape'] == 'hollow_cup'
    assert config['objects']['cleanup_block']['shape'] == 'sphere'
    assert len(config['objects']['empty_cup']['geom_ids']) == 17
    assert desk.compiled_xml == desk._model_xml
    assert 'name="empty_cup_free"' in desk.compiled_xml
    assert baseline.manipulation_config() is None


def test_joint_override_cannot_write_props_or_other_legs(models, monkeypatch):
    _, desk = models
    desk.reset()
    real_step = mujoco.mj_step
    observed = []
    def witnessed_step(model, data):
        other = data.qfrc_applied.copy()
        other[desk._dadr] = 0
        assert np.count_nonzero(other) == 0
        assert not np.any(data.xfrc_applied)
        observed.append(data.qpos.copy())
        real_step(model, data)
    monkeypatch.setattr(mujoco, 'mj_step', witnessed_step)
    before = desk.snapshot()['objects']['empty_cup']['position_m'][2]
    for _ in range(30):
        observation = desk.step(joint_targets={'LF_J4_joint': -.65})
        assert max(abs(x) for x in observation['joint_torques_nm'].values()) <= desk.servo['plateau_torque_nm']
    assert len(observed) == 150
    assert observation['objects']['empty_cup']['position_m'][2] < before
    for invalid in ({'RF_J0_joint': 0}, {'empty_cup_free': 0}, {'LF_J0_joint': float('nan')},
                    {'LF_J0_joint': True}, {'LF_J0_joint': 100}):
        q = desk.data.qpos.copy(); t = desk.data.time
        with pytest.raises(ValueError): desk.step(joint_targets=invalid)
        np.testing.assert_array_equal(desk.data.qpos, q)
        assert desk.data.time == t


def test_offset_and_fixed_joint_plan_bounds_are_explicit(models):
    baseline, desk = models
    for offsets in ({'wrong': [0, 0, 0]}, {'empty_cup': [0, 0]}, {'empty_cup': [True, 0, 0]},
                    {'empty_cup': [float('inf'), 0, 0]}, {'empty_cup': [.03, 0, 0]}):
        with pytest.raises(ValueError): desk_model(baseline.compiled_xml, UPSTREAM, object_offsets=offsets)
    config = desk.manipulation_config()
    assert config['joint_names'] == list(LF_JOINTS)
    assert set(config['jaw_geom_ids']) <= set(config['robot_geom_ids'])
    for plan in config['plans'].values():
        for stage in plan['stages']:
            assert stage['duration_s'] > 0 and len(stage['joint_targets']) == 5
            for name, value in zip(LF_JOINTS, stage['joint_targets']):
                lo, hi = desk.model.jnt_range[desk.model.joint(name).id]
                assert np.isfinite(value) and lo <= value <= hi
