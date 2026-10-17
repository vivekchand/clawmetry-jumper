"""Native Jumper bundle playback, with real MuJoCo dynamics and no training stack.

This is a local simulation host, not a hardware controller. The upstream bundle
owns observations, policy inference scheduling, command decoding and mode changes.
The host supplies physics, named joint mappings and the upstream servo model.
"""
from __future__ import annotations

import ast
import copy
import importlib.machinery
import importlib.util
import json
import hashlib
import math
from pathlib import Path
import re
import sysconfig
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import onnxruntime as ort

from .provenance import verify_upstream


def _literal_constants(path: Path, names: set[str]) -> dict:
    """Read literal hardware facts without importing Torch-dependent modules."""
    values = {}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign):
            targets = [n.id for n in node.targets if isinstance(n, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        else:
            continue
        for name in targets:
            if name in names:
                values[name] = ast.literal_eval(node.value)
    if names - values.keys():
        raise ValueError(f"Upstream constants missing: {sorted(names - values.keys())}")
    return values


def _servo_spec(path: Path) -> dict[str, float]:
    """Read this pinned YAML block; reject absent, null or nonnumeric values.

    This bounded reader deliberately supports only the shipped scalar contract,
    not general YAML. It never imports upstream training code or executes YAML.
    """
    text = path.read_text()
    section = text.split("\n  joint_servo:\n", 1)[1].split("\n  joint_servo_100:", 1)[0]
    section = section.split("\n    torque_speed:\n", 1)[1].split("\n    friction:", 1)[0]
    if not re.search(r"^      model: exp_decay_with_cutoff\s*$", section, re.M):
        raise ValueError("Unsupported upstream servo curve")
    result = {}
    for name in ("plateau_torque_nm", "corner_speed_rpm", "decay_speed_rpm",
                 "cutoff_speed_rpm", "peak_duration_s", "thermal_continuous_torque_nm"):
        match = re.search(rf"^      {name}:\s*([^#\n]+)", section, re.M)
        if not match:
            raise ValueError(f"Missing servo specification: {name}")
        value = float(match.group(1).strip())
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Invalid servo specification: {name}")
        result[name] = value
    if result["thermal_continuous_torque_nm"] >= result["plateau_torque_nm"]:
        raise ValueError("Continuous torque must be below peak torque")
    return result


class JumperSimulator:
    """A reproducible 200 Hz native-controller / 1 kHz physics simulation.

    Only reset writes the starting pose. Every subsequent rendered pose comes
    from MuJoCo integration of the bundle's PD commands. Props are decorative
    and outside the initial robot work area; cup manipulation is not modeled.
    """

    dt = 0.005
    physics_dt = 0.001

    def __init__(self, upstream: Path, *, scene_xml: Path | None = None):
        self.upstream = Path(upstream).resolve()
        self.scene_xml = Path(scene_xml).resolve() if scene_xml else None
        self.provenance = verify_upstream(self.upstream)
        if self.scene_xml:
            self.provenance["scene_xml_sha256"] = hashlib.sha256(self.scene_xml.read_bytes()).hexdigest()
        self.bundle = self.upstream / "out/bundle_example/jumper"
        self.manifest = json.loads((self.bundle / "bundle.json").read_text())
        if self.manifest.get("schema") != "kk-policy-bundle/1":
            raise ValueError("Unsupported Jumper bundle schema")
        self.contract_texts = {
            mode: (self.bundle / entry["contract"]).read_text()
            for mode, entry in self.manifest["modes"].items()
        }
        self.contracts = {k: json.loads(v) for k, v in self.contract_texts.items()}
        self.trajectories = {
            mode: (self.bundle / entry["trajectory"]).read_text()
            for mode, entry in self.manifest["modes"].items() if entry.get("trajectory")
        }
        self.home_contract = self.contracts["locomotion"]
        self.wire = list(self.home_contract["wire_joint_order"])
        if any(c["wire_joint_order"] != self.wire for c in self.contracts.values()):
            raise ValueError("Bundle modes disagree about wire joint order")
        self.control_hz = max(float(c["control"]["control_hz"]) for c in self.contracts.values())
        if self.control_hz != 200:
            raise ValueError("This host expects the pinned bundle's 200 Hz control rate")
        self._extension = self._load_extension()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.sessions = {
            mode: ort.InferenceSession(str(self.bundle / entry["models"]["onnx"]),
                                       sess_options=options, providers=["CPUExecutionProvider"])
            for mode, entry in self.manifest["modes"].items()
        }
        self.servo = _servo_spec(self.upstream / "assets/jumper/motor/motor_config.yaml")
        self._thermal_time = self.servo["peak_duration_s"] / math.log(
            1 / (1 - (self.servo["thermal_continuous_torque_nm"] /
                       self.servo["plateau_torque_nm"]) ** 2))
        self._renderer = None
        self._render_size = None
        self.reset()

    def _load_extension(self):
        runtime = self.manifest["runtimes"]["mjlab"]
        platform = sysconfig.get_platform()
        key = "macosx-universal2" if platform.startswith("macosx-") else platform
        path = self.bundle / runtime["extensions"][key]["file"]
        loader = importlib.machinery.ExtensionFileLoader("mjrl_fsm", str(path))
        spec = importlib.util.spec_from_file_location("mjrl_fsm", path, loader=loader)
        if spec is None:
            raise RuntimeError(f"Cannot load native controller: {path}")
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module

    def _new_fsm(self):
        limits = self.home_contract["joint_limits"]
        return self._extension.Fsm(
            (self.bundle / "controller.toml").read_text(), self.contract_texts,
            {"joint_names": self.wire,
             "joint_pos_lo": [limits[n][0] for n in self.wire],
             "joint_pos_hi": [limits[n][1] for n in self.wire],
             "output_rate_hz": self.control_hz},
            trajectories=self.trajectories, operators=True,
        )

    def verify_reference(self) -> dict:
        """Verify a fresh controller without disturbing the running simulation."""
        report = self._new_fsm().check_reference((self.bundle / "reference.json").read_text())
        result = {name: getattr(report, name) for name in
                  ("frames", "inferences", "observation", "target", "mode_mismatches", "divergent")}
        result["passed"] = bool(not result["mode_mismatches"] and not result["divergent"]
                                and result["observation"] <= 1e-6 and result["target"] <= 1e-6)
        return result

    def _scene_xml(self) -> str:
        asset = self.upstream / "assets/jumper/jumper.xml"
        root = ET.parse(asset).getroot()
        root.find("compiler").set("meshdir", str(asset.parent))
        for mesh in root.findall("./asset/mesh"):
            mesh.set("file", str((asset.parent / mesh.attrib["file"]).resolve()))
        root.find("option").set("timestep", str(self.physics_dt))
        constants = _literal_constants(
            self.upstream / "tasks/jumper/common/constants.py",
            {"FEET", "LIMB_LINKS", "TIP_LINKS", "CHASSIS_LINKS",
             "_CONTACT_SOLREF", "_CONTACT_SOLIMP", "_FOOT_FRICTION"})
        feet = {n + "_meshcol" for n in constants["FEET"]}
        collision = feet | {n + "_meshcol" for key in
                            ("LIMB_LINKS", "TIP_LINKS", "CHASSIS_LINKS") for n in constants[key]}
        legs = ("LF", "RF", "LM", "RM", "LR", "RR")
        all_bits = sum(1 << (i + 1) for i in range(6))
        for geom in root.findall(".//geom"):
            name = geom.get("name", "")
            if name in collision:
                leg = next((i for i, prefix in enumerate(legs) if name.startswith(prefix + "_")), None)
                geom.set("contype", str(1 | (1 << (leg + 1)) if leg is not None else 1))
                geom.set("conaffinity", str(all_bits & ~(1 << (leg + 1)) if leg is not None else 0))
                geom.set("condim", "3" if name in feet else "1")
                geom.set("priority", "1" if name in feet else "0")
                geom.set("solref", " ".join(map(str, constants["_CONTACT_SOLREF"])))
                geom.set("solimp", " ".join(map(str, constants["_CONTACT_SOLIMP"])))
                if name in feet:
                    geom.set("friction", " ".join(map(str, constants["_FOOT_FRICTION"])))
            else:
                geom.set("contype", "0")
                geom.set("conaffinity", "0")
            if name.endswith("_visual"):
                # Appearance only. Preserve masses, collision meshes and joints.
                red = [float(v) for v in geom.get("rgba", "1 1 1 1").split()]
                if red[0] > 0.65 and red[1] < 0.2:
                    geom.set("rgba", "0.38 0.65 0.55 1")
                elif max(red[:3]) < 0.15:
                    geom.set("rgba", "0.12 0.20 0.20 1")
        world = root.find("worldbody")
        if self.scene_xml:
            # Import the environment produced by the official Design map
            # importer. Its robot is intentionally not substituted for the
            # training model; its compiler defaults must not leak into it.
            scene = ET.parse(self.scene_xml).getroot()
            compiler = scene.find("compiler")
            degrees = compiler is None or compiler.get("angle", "degree") == "degree"
            defaults = scene.find("./default/geom")
            for node in scene.findall("./asset/*"):
                root.find("asset").append(copy.deepcopy(node))
            for child in scene.findall("./worldbody/*"):
                item = copy.deepcopy(child)
                for node in item.iter():
                    if degrees and node.get("euler"):
                        node.set("euler", " ".join(str(math.radians(float(v))) for v in node.get("euler").split()))
                    if node.tag == "geom" and defaults is not None:
                        for key, value in defaults.attrib.items():
                            if key not in node.attrib:
                                node.set(key, value)
                world.append(item)
            return ET.tostring(root, encoding="unicode")
        ET.SubElement(world, "geom", name="desk_surface", type="box", size="0.86 0.58 0.025",
                      pos="0 0 -0.025", rgba="0.76 0.69 0.57 1", friction="1 0.01 0.01",
                      contype="1", conaffinity="1", solref="0.02 1", solimp="0.8 0.90 0.002 0.5 2")
        ET.SubElement(world, "geom", name="room_floor", type="plane", size="6 6 .1",
                      pos="0 0 -0.68", rgba="0.81 0.84 0.79 1", contype="1", conaffinity="1")
        # Decorative props deliberately outside a 0.3 m radius around Jumper.
        for name, size, pos, rgba in (
            ("monitor_stand", ".11 .07 .012", "-.40 .37 .012", ".24 .32 .31 1"),
            ("monitor_neck", ".025 .025 .13", "-.40 .40 .15", ".24 .32 .31 1"),
            ("monitor_body", ".24 .016 .15", "-.40 .42 .37", ".19 .27 .27 1"),
            ("monitor_screen", ".215 .002 .125", "-.40 .400 .37", ".50 .70 .63 1"),
            ("notebook", ".11 .08 .008", ".48 -.28 .009", ".42 .60 .55 1"),
        ):
            ET.SubElement(world, "geom", name=name, type="box", size=size, pos=pos,
                          rgba=rgba, contype="0", conaffinity="0")
        ET.SubElement(world, "geom", name="water_glass", type="cylinder", size=".032 .055",
                      pos=".46 .32 .056", rgba=".42 .70 .74 .5", contype="0", conaffinity="0")
        ET.SubElement(world, "light", name="desk_key", pos="1 -1 2", dir="-1 1 -2",
                      diffuse=".7 .7 .65", ambient=".4 .4 .4", castshadow="true")
        return ET.tostring(root, encoding="unicode")

    def reset(self) -> dict:
        """Start a new episode; no subsequent step resets or teleports the robot."""
        self.close()
        self.model = mujoco.MjModel.from_xml_string(self._scene_xml())
        self.data = mujoco.MjData(self.model)
        self._joint_ids = np.array([self.model.joint(n).id for n in self.wire])
        self._qadr = self.model.jnt_qposadr[self._joint_ids]
        self._dadr = self.model.jnt_dofadr[self._joint_ids]
        base_joint = self.model.joint("floating_base")
        base_qadr = base_joint.qposadr[0]
        self.data.qpos[base_qadr:base_qadr + 3] = self.home_contract["base_init_pos"]
        self.data.qpos[base_qadr + 3:base_qadr + 7] = [1, 0, 0, 0]
        self.data.qpos[self._qadr] = [self.home_contract["default_joint_pos"][n] for n in self.wire]
        self._body = self.model.body("base_link").id
        self._robot_collision_ids = np.array([
            i for i in range(self.model.ngeom)
            if self.model.body_rootid[self.model.geom_bodyid[i]] == self._body
            and (self.model.geom_contype[i] or self.model.geom_conaffinity[i])
        ], dtype=int)
        self._torque = np.zeros(len(self.wire))
        self._heat = np.zeros(len(self.wire))
        self._tick = 0
        self.fsm = self._new_fsm()
        self._logs = []
        self._key_results = []
        mujoco.mj_forward(self.model, self.data)
        return self.snapshot()

    def step(self, keys: list[tuple[str, bool]] | None = None) -> dict:
        """Advance 5 ms with key edges delivered to the native controller."""
        if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
            raise FloatingPointError("Nonfinite physics state cannot reach the controller")
        now = self._tick * 5000
        self.fsm.set_state(self.data.qpos[self._qadr].tolist(),
                           self.data.qvel[self._dadr].tolist(), self._torque.tolist(),
                           self.data.xquat[self._body].tolist(),
                           self.data.sensor("imu_ang_vel").data.tolist(), now)
        self.fsm.set_pad_frame([], {}, connected=False, now_us=now)
        self._key_results = [{"key": key, "down": bool(down),
                              "bound": bool(self.fsm.set_key(key, bool(down), now))}
                             for key, down in (keys or [])]
        mode = self.fsm.tick(now)
        if mode is not None:
            session = self.sessions[mode]
            action = session.run(None, {session.get_inputs()[0].name:
                np.asarray([self.fsm.observation()], dtype=np.float32)})[0][0]
            if not np.isfinite(action).all():
                raise FloatingPointError("Nonfinite ONNX output")
            self.fsm.resume(action.tolist())
        targets = np.asarray(self.fsm.positions())
        kp, kd = np.asarray(self.fsm.kp()), np.asarray(self.fsm.kd())
        for _ in range(5):
            q, velocity = self.data.qpos[self._qadr], self.data.qvel[self._dadr]
            raw = kp * (targets - q) - kd * velocity
            speed = np.abs(velocity)
            rpm = 2 * math.pi / 60
            curve = self.servo["plateau_torque_nm"] * np.exp(
                -np.maximum(speed - self.servo["corner_speed_rpm"] * rpm, 0) /
                (self.servo["decay_speed_rpm"] * rpm))
            curve[speed >= self.servo["cutoff_speed_rpm"] * rpm] = 0
            ceiling = np.where(self._heat >= 1, self.servo["thermal_continuous_torque_nm"],
                               self.servo["plateau_torque_nm"])
            limit = np.minimum(curve, ceiling)
            self._torque = np.clip(raw, -limit, limit)
            self._heat = np.maximum(0, self._heat +
                ((self._torque / self.servo["thermal_continuous_torque_nm"]) ** 2 - self._heat)
                * (self.physics_dt / self._thermal_time))
            self.data.qfrc_applied[:] = 0
            self.data.qfrc_applied[self._dadr] = self._torque
            mujoco.mj_step(self.model, self.data)
        # mj_step leaves position-derived sensors at the preceding integration
        # state. Refresh them so snapshot and the next controller agree in time.
        mujoco.mj_forward(self.model, self.data)
        self._tick += 1
        self._logs = [{"time_s": at / 1e6, "from": source, "to": target,
                       "rule": rule, "condition": why}
                      for at, source, target, rule, why in self.fsm.take_log()]
        return self.snapshot()

    def snapshot(self) -> dict:
        quat = self.data.xquat[self._body]
        rotation = self.data.xmat[self._body].reshape(3, 3)
        tilt = math.degrees(math.acos(float(np.clip(rotation[2, 2], -1, 1))))
        ids = self._robot_collision_ids
        geom_rotation = self.data.geom_xmat[ids].reshape(-1, 3, 3)
        local_aabb = self.model.geom_aabb[ids]
        centers = self.data.geom_xpos[ids] + np.einsum("nij,nj->ni", geom_rotation, local_aabb[:, :3])
        half_sizes = np.einsum("nij,nj->ni", np.abs(geom_rotation), local_aabb[:, 3:])
        lower, upper = (centers - half_sizes).min(axis=0), (centers + half_sizes).max(axis=0)
        margin = min(lower[0] + .86, .86 - upper[0], lower[1] + .58, .58 - upper[1])
        body_velocity = self.data.sensor("imu_lin_vel").data
        return {
            "time_s": float(self.data.time), "mode": self.fsm.mode,
            "running_policy": bool(self.fsm.running_policy),
            "position_m": self.data.xpos[self._body].tolist(), "quat_wxyz": quat.tolist(),
            "base_velocity_m_s": (rotation @ body_velocity).tolist(),
            "base_velocity_body_m_s": body_velocity.tolist(),
            "collision_aabb_m": {"min": lower.tolist(), "max": upper.tolist()},
            "table_margin_m": float(margin),
            "table_bounds_m": {"min": [-.86, -.58, 0], "max": [.86, .58, 0]},
            "tilt_deg": tilt, "joint_positions_rad": dict(zip(self.wire, self.data.qpos[self._qadr].tolist())),
            "joint_velocities_rad_s": dict(zip(self.wire, self.data.qvel[self._dadr].tolist())),
            "joint_torques_nm": dict(zip(self.wire, self._torque.tolist())),
            "controller_logs": list(self._logs), "key_results": list(self._key_results),
            "finite": bool(np.isfinite(self.data.qpos).all() and np.isfinite(self.data.qvel).all()),
            "max_motor_heat_ratio": float(self._heat.max()),
            "evidence_kind": "simulation", "torque_source": "simulator_applied_pd_torque",
        }

    def render(self, width: int = 1280, height: int = 720) -> np.ndarray:
        """Return an RGB frame with a fixed camera, without advancing physics."""
        if self._renderer is None or self._render_size != (width, height):
            self.close()
            self.model.vis.global_.offwidth = max(width, 1280)
            self.model.vis.global_.offheight = max(height, 960)
            self._renderer = mujoco.Renderer(self.model, width=width, height=height)
            self._render_size = (width, height)
        camera = mujoco.MjvCamera()
        camera.lookat[:] = [-0.04, 0.06, 0.10]
        camera.distance = 1.34
        camera.azimuth = 115
        camera.elevation = -27
        option = mujoco.MjvOption()
        option.geomgroup[1] = 0  # Hide collision hulls; preserve original visual meshes.
        self._renderer.update_scene(self.data, camera=camera, scene_option=option)
        return self._renderer.render().copy()

    def close(self) -> None:
        renderer = getattr(self, "_renderer", None)
        if renderer is not None:
            renderer.close()
        self._renderer = None
        self._render_size = None
