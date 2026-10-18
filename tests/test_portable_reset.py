"""Serialized model order must not corrupt a free prop or robot reset pose."""
import importlib.util
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np
import pytest


def preparer():
    path = Path(__file__).resolve().parents[1] / "scripts/prepare_web_assets.py"
    spec = importlib.util.spec_from_file_location("prepare_portable_reset", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def model(order):
    bodies = {
        "robot": '<body name="robot"><freejoint name="base"/><geom type="sphere" size=".1"/></body>',
        "cup": '<body name="cup"><freejoint name="cup_free"/><geom type="cylinder" size=".02 .05"/></body>',
    }
    return mujoco.MjModel.from_xml_string('<mujoco><worldbody>' + ''.join(bodies[n] for n in order) + '</worldbody></mujoco>')


def test_reordered_free_bodies_keep_named_pose_and_nonidentity_quaternion():
    source = model(["robot", "cup"])
    data = mujoco.MjData(source)
    data.qpos[:] = [.02, -.02, .17, np.sqrt(.5), 0, 0, -np.sqrt(.5), .05, -.255, .05, 1, 0, 0, 0]
    portable = model(["cup", "robot"])
    actual = preparer().portable_initial_qpos(source, data, portable)
    assert actual[:7] == pytest.approx(data.qpos[7:])
    assert actual[7:] == pytest.approx(data.qpos[:7])
    with pytest.raises(ValueError, match="identities differ"):
        preparer().portable_initial_qpos(source, data, model(["robot"]))


def test_task_enablement_refuses_a_different_model_or_changed_source(tmp_path):
    module = preparer()
    module.ROOT = tmp_path
    assert module.desk_qualification('model') is None
    plans = {name: {"qualified": True} for name in ['cup','cleanup']}
    assert module.enable_desk_plans(plans, 'model') is None
    assert not any(plan['qualified'] for plan in plans.values())
    sources = ["src/clawmetry_jumper/simulator.py", "src/clawmetry_jumper/manipulation.py",
               "src/clawmetry_jumper/contact_plans.py", "scenes/mizu-desk.scene.json",
               "web/simulation.js", "web/manipulation.js", "web/app.js", "scripts/prepare_web_assets.py"]
    for name in sources:
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(name)
    record = {"schema": "mizu_fixed_scene_qualification/1", "upstream_commit": module.PIN,
              "browser_model_sha256": 'model', "actions": ['cup', 'cleanup'],
              "source_sha256": {name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() for name in sources},
              "measured_results": {name: {runtime: {"passed": True} for runtime in ['native','browser']} for name in ['cup','cleanup']}}
    path = tmp_path / 'resources/desk-skill-qualification.json'
    path.parent.mkdir()
    path.write_text(json.dumps(record))
    assert module.desk_qualification('model')['actions'] == ['cup','cleanup']
    assert module.enable_desk_plans(plans, 'model')
    assert all(plan['qualified'] for plan in plans.values())
    with pytest.raises(ValueError, match='portable model'):
        module.desk_qualification('other')
    (tmp_path / 'web/manipulation.js').write_text('changed')
    with pytest.raises(ValueError, match='source changed'):
        module.desk_qualification('model')
