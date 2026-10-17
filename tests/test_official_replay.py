"""Host telemetry uses model addresses, preserving physical joint units."""
import importlib.util
from pathlib import Path

import pytest


def test_scalar_joint_measurements_use_named_addresses_and_exclude_scene_props():
    mujoco = pytest.importorskip("mujoco")
    source = Path(__file__).resolve().parents[1] / "scripts" / "official_replay.py"
    spec = importlib.util.spec_from_file_location("official_replay_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = mujoco.MjModel.from_xml_string("""
      <mujoco><worldbody>
        <body name="prop"><joint name="prop_slider" type="slide"/>
          <geom type="sphere" size=".01"/></body>
        <body name="robot"><freejoint/><geom type="sphere" size=".01"/>
          <body name="arm"><joint name="elbow" type="hinge"/>
            <geom type="sphere" size=".01"/>
            <body name="grip"><joint name="grip_slide" type="slide"/>
              <geom type="sphere" size=".01"/></body>
          </body>
        </body>
      </worldbody></mujoco>""")
    data = mujoco.MjData(model)
    for name, position, velocity in [("prop_slider", 9., 8.), ("elbow", .4, -.7),
                                      ("grip_slide", .012, .003)]:
        joint = model.joint(name).id
        data.qpos[model.jnt_qposadr[joint]] = position
        data.qvel[model.jnt_dofadr[joint]] = velocity
    measured = module.scalar_joint_measurements(model, data, model.body("robot").id)
    assert measured == {"joint_positions_rad": {"elbow": .4},
                        "joint_velocities_rad_s": {"elbow": -.7},
                        "joint_positions_m": {"grip_slide": .012},
                        "joint_velocities_m_s": {"grip_slide": .003}}
    assert "joint_torques_nm" not in measured
