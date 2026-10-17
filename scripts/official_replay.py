#!/usr/bin/env python3
"""Instrument official Jumper play --app and its own MP4 recorder externally.

Run with the upstream editable environment. No upstream file is modified, no
custom physics or renderer is substituted, and no trained/hardware claim is made.
"""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import asdict
import importlib.util
import json
import math
import os
from pathlib import Path
import sys


def scalar_joint_measurements(model, data, root_body):
    """Read each named robot scalar joint through its declared MuJoCo addresses.

    Scene props and the floating base are excluded. Slide units remain metres;
    they must never be presented as angular measurements. Applied/controller
    torques are not inferred from state or actuator array order.
    """
    import mujoco
    measured = {"joint_positions_rad": {}, "joint_velocities_rad_s": {},
                "joint_positions_m": {}, "joint_velocities_m_s": {}}
    for index in range(model.njnt):
        if model.body_rootid[model.jnt_bodyid[index]] != root_body:
            continue
        kind = model.jnt_type[index]
        if kind == mujoco.mjtJoint.mjJNT_HINGE:
            position_key, velocity_key = "joint_positions_rad", "joint_velocities_rad_s"
        elif kind == mujoco.mjtJoint.mjJNT_SLIDE:
            position_key, velocity_key = "joint_positions_m", "joint_velocities_m_s"
        else:
            continue
        name = model.joint(index).name
        if not name:
            continue
        measured[position_key][name] = float(data.qpos[model.jnt_qposadr[index]])
        measured[velocity_key][name] = float(data.qvel[model.jnt_dofadr[index]])
    return measured


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream", type=Path, required=True)
    p.add_argument("--scene", type=Path, required=True, help="Official .map scene package")
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--journal-dir", type=Path, default=None,
                   help="Override ClawMetry's shared journal directory for isolated verification")
    p.add_argument("--run-id", default="mizu-official-replay")
    p.add_argument("--steps", type=int, default=7000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--enable-simulator-controls", action="store_true")
    p.add_argument("--calm-skin", action=argparse.BooleanOptionalAction, default=True,
                   help="Change robot visual RGBA only; preserve official geometry and physics")
    p.add_argument("--table-bounds", type=float, nargs=4, default=(-.86, .86, -.58, .58),
                   metavar=("X_MIN", "X_MAX", "Y_MIN", "Y_MAX"))
    p.add_argument("--table-height", type=float, default=0.)
    p.add_argument("--wave-at", type=float, default=3.)
    p.add_argument("--bow-at", type=float, default=14.)
    p.add_argument("--jump-at", type=float, default=25.)
    p.add_argument("--video-width", type=int, default=1280)
    p.add_argument("--video-height", type=int, default=720)
    p.add_argument("--video-fps", type=float, default=30.)
    p.add_argument("--camera-distance", type=float, default=1.8)
    p.add_argument("--camera-azimuth", type=float, default=115.)
    p.add_argument("--camera-elevation", type=float, default=-23.)
    p.add_argument("--lookat-height", type=float, default=.18)
    p.add_argument("--plan-only", action="store_true")
    return p


def official_arguments(args) -> list[str]:
    return ["play.py", "--app", str(args.upstream / "out/bundle_example/jumper"),
            "--task", "jumper.posture", "--backend", "native", "--device", "cpu",
            "--num_envs", "1", "--headless", "--steps", str(args.steps),
            "--video", str(args.video), "--scene", str(args.scene), "--speed", "0",
            "--video-width", str(args.video_width), "--video-height", str(args.video_height),
            "--video-fps", str(args.video_fps), "--video-distance", str(args.camera_distance),
            "--video-azimuth", str(args.camera_azimuth), "--video-elevation", str(args.camera_elevation),
            "--no-video-follow", "--video-lookat-height", str(args.lookat_height),
            "--stop-on-done", "--replay-info-out", str(args.video.with_suffix(".replay-info.json"))]


def run(args) -> dict:
    from clawmetry_jumper.provenance import verify_upstream, validate_official_outputs
    # Validate before loading upstream executable Python or opening a writer.
    validate_official_outputs(args.video, args.evidence)
    provenance = verify_upstream(args.upstream, official=True)
    provenance["scene_sha256"] = hashlib.sha256(args.scene.read_bytes()).hexdigest()
    import numpy as np
    import mujoco
    from clawmetry_jumper.evidence import EvidenceStore
    from clawmetry.physical_ai import DeskMonitor, JumperObserver, Request, Task, TaskGate
    import mjrl.app_play as app_play
    import tasks

    # Refuse silently importing some other editable checkout.
    if not Path(app_play.__file__).resolve().is_relative_to(args.upstream):
        raise RuntimeError("Use the pinned upstream's editable Python environment")
    spec = importlib.util.spec_from_file_location("clawmetry_official_play", args.upstream / "scripts/play.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load official scripts/play.py")
    previous_path, previous_argv, previous_cwd = list(sys.path), list(sys.argv), Path.cwd()
    sys.path.insert(0, str(args.upstream / "scripts"))  # play.py's sibling _cli module
    play = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(play)
    official_player = app_play.AppPlayer
    load_config = tasks.load_env_cfg
    official_loop = play._loop
    store = EvidenceStore(args.evidence)
    task = Task("mizu-desk-reminders", frozenset({"wave", "bow"}),
                bounds_xy=tuple(args.table_bounds))
    gate = TaskGate(task, controls_enabled=args.enable_simulator_controls,
                    supported_actions={"wave", "bow"})
    monitor = DeskMonitor()
    observer = JumperObserver("mizu-official", environment="simulation", directory=args.journal_dir,
                              monitor=DeskMonitor(), sample_interval_s=.1)
    observer.__enter__()
    state = {"steps": 0, "finite": True, "min_table_margin_m": None,
             "max_tilt_deg": 0., "modes": set(), "decisions": [], "resets": 0,
             "completed": False, "seed": args.seed, "renderer": "official ReplayVideo",
             "provenance": {k: v for k, v in provenance.items() if k != "files_sha256"}}
    args.video.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2))

    def seeded_config(*pos, **kw):
        cfg = load_config(*pos, **kw)
        cfg.seed = args.seed
        return cfg

    class ObservedPlayer(official_player):
        def __init__(self, *pos, **kw):
            super().__init__(*pos, **kw)
            self._clawmetry_count = 0
            self._clawmetry_sent = set()
            self._clawmetry_releases = []
            self._clawmetry_logs = []
            self._clawmetry_schedule = [(args.wave_at, "wave", "key_1"),
                                        (args.bow_at, "bow", "key_2"),
                                        (args.jump_at, "jump", "key_space")]
            model, _ = self._env.unwrapped.sim.env_mjdata(0)
            base = next(i for i in range(model.nbody) if model.body(i).name.endswith("/base_link"))
            self._clawmetry_base = base
            root = model.body_rootid[base]
            self._clawmetry_root = root
            self._clawmetry_collision = np.array([
                i for i in range(model.ngeom)
                if model.body_rootid[model.geom_bodyid[i]] == root and
                (model.geom_contype[i] or model.geom_conaffinity[i])], dtype=int)
            if args.calm_skin:
                # Train does not load Design .skin packages. Apply this small,
                # disclosed appearance-only override before ReplayVideo copies
                # its model. Contacts, meshes, masses and joints stay original.
                models = (model, self._env.unwrapped.sim.mj_model,
                          self._env.unwrapped.sim.render_model)
                for appearance in models:
                    for i in range(appearance.ngeom):
                        geom = appearance.geom(i)
                        if not geom.name.startswith("robot/") or not geom.name.endswith("_visual"):
                            continue
                        rgba = appearance.geom_rgba[i]
                        if rgba[0] > .65 and rgba[1] < .2:
                            appearance.geom_rgba[i] = [.38, .65, .55, 1]
                        elif max(rgba[:3]) < .15:
                            appearance.geom_rgba[i] = [.12, .20, .20, 1]
            self.latest = self.observation()
            observer.observe(self.latest, now_s=0.)
            store.append(args.run_id, 0, "outcome", {
                "status": "started", "evidence_kind": "simulation", "engine": "official Jumper play --app",
                "controls_enabled": args.enable_simulator_controls, "task": asdict(task) | {"actions": sorted(task.actions), "objects": []},
                "seed": args.seed, "scene": str(args.scene), "scene_contains_human_detection": False,
                "appearance_override": "visual_rgba_mint_sage" if args.calm_skin else None,
                "physical_stop_confirmed": False,
            })

        def observation(self):
            env = self._env.unwrapped
            model, data = env.sim.env_mjdata(0)
            base, ids = self._clawmetry_base, self._clawmetry_collision
            rotations = data.geom_xmat[ids].reshape(-1, 3, 3)
            boxes = model.geom_aabb[ids]
            centers = data.geom_xpos[ids] + np.einsum("nij,nj->ni", rotations, boxes[:, :3])
            extent = np.einsum("nij,nj->ni", np.abs(rotations), boxes[:, 3:])
            low, high = (centers - extent).min(axis=0), (centers + extent).max(axis=0)
            x0, x1, y0, y1 = args.table_bounds
            margin = min(low[0] - x0, x1 - high[0], low[1] - y0, y1 - high[1])
            velocity = np.zeros(6)
            mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_BODY, base, velocity, 0)
            tilt = math.degrees(math.acos(float(np.clip(data.xmat[base].reshape(3, 3)[2, 2], -1, 1))))
            return {"time_s": self._clawmetry_count * env.step_dt,
                    **scalar_joint_measurements(model, data, self._clawmetry_root),
                    "position_m": data.xpos[base].tolist(), "quat_wxyz": data.xquat[base].tolist(),
                    "base_velocity_m_s": velocity[3:].tolist(), "tilt_deg": tilt,
                    "collision_aabb_m": {"min": low.tolist(), "max": high.tolist()},
                    "table_margin_m": float(margin),
                    "table_bounds_m": {"min": [x0, y0, args.table_height], "max": [x1, y1, args.table_height]},
                    "finite": bool(np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()),
                    "mode": self.fsm.mode, "running_policy": bool(self.fsm.running_policy),
                    "evidence_kind": "simulation", "engine": "official Jumper play --app"}

        def __call__(self, obs):
            now = self._clawmetry_count * self._env.unwrapped.step_dt
            for key in self._clawmetry_releases:
                self.fsm.set_key(key, False, round(now * 1e6))
            self._clawmetry_releases = []
            for at, action, key in self._clawmetry_schedule:
                if now + 1e-9 < at or action in self._clawmetry_sent:
                    continue
                self._clawmetry_sent.add(action)
                request = Request(f"official-{action}", task.task_id, action)
                decision = observer.decide(gate, request, self.latest, now_s=now)
                store.append(args.run_id, now, "reminder", {
                    "message": {"wave": "Take a sip of water", "bow": "A gentle stretch break",
                                "jump": "Jump requested outside the desk-reminder task"}[action],
                    "evidence_kind": "simulation"})
                store.append(args.run_id, now, "request", asdict(request))
                store.append(args.run_id, now, "decision", decision.to_dict())
                state["decisions"].append(decision.to_dict())
                if decision.send_to_controller:
                    bound = self.fsm.set_key(key, True, round(now * 1e6))
                    self._clawmetry_releases.append(key)
                    store.append(args.run_id, now, "controller", {
                        "request_id": request.request_id, "key": key, "bound": bool(bound),
                        "status": "input_delivered", "physical_stop_confirmed": False})
                    observer.emit("controller.receipt", {"request_id": request.request_id,
                        "key": key, "bound": bool(bound), "status": "input_delivered", "time_s": now})
            return super().__call__(obs)

        def _report(self):
            # Drain once, preserving the original tuples and reasons in evidence.
            for at, source, target, rule, why in self.fsm.take_log():
                receipt = {"time_s": at / 1e6, "from": source, "to": target,
                           "rule": rule, "condition": why, "evidence_kind": "simulation"}
                store.append(args.run_id, at / 1e6, "controller", receipt)
                observer.emit("controller.receipt", {"receipt_type": "mode_transition", **receipt})
                self._clawmetry_logs.append(receipt)
                print(f"\n[clawmetry] native {source} -> {target}: {why}")
            super()._report()

        def after_step(self, dones):
            self._clawmetry_count += 1
            state["steps"] = self._clawmetry_count
            now = self._clawmetry_count * self._env.unwrapped.step_dt
            if bool(dones.any()):
                state["resets"] += 1
                observer.check(now)
                store.append(args.run_id, now, "outcome", {
                    "status": "episode_ended", "outcome": "unknown", "evidence_kind": "simulation",
                    "message": "Official environment ended and reset; recording stops before displaying that reset."})
                return
            self.latest = self.observation()
            observer.observe(self.latest, now_s=now)
            state["finite"] = state["finite"] and self.latest["finite"]
            state["modes"].add(self.latest["mode"])
            old_margin = state["min_table_margin_m"]
            state["min_table_margin_m"] = min(old_margin, self.latest["table_margin_m"]) if old_margin is not None else self.latest["table_margin_m"]
            state["max_tilt_deg"] = max(state["max_tilt_deg"], self.latest["tilt_deg"])
            if self._clawmetry_count % 10 == 0:
                store.append(args.run_id, now, "observation", self.latest)
            for alert in monitor.update(self.latest, now):
                store.append(args.run_id, now, "alert", alert)
                store.append(args.run_id, now, "notification", {"alert_type": alert["type"],
                    "status": "not_configured", "phone_delivery_confirmed": False,
                    "scope": "demo_capture_only"})

    def observed_loop(env, policy, *pos, **kw):
        original_step = env.step

        def observed_step(action):
            result = original_step(action)
            policy.after_step(result[2])
            return result

        env.step = observed_step
        try:
            return official_loop(env, policy, *pos, **kw)
        finally:
            env.step = original_step

    try:
        tasks.load_env_cfg = seeded_config
        app_play.AppPlayer = ObservedPlayer
        play._loop = observed_loop
        sys.argv = official_arguments(args)
        os.chdir(args.upstream)
        play.main()
        state["completed"] = True
    finally:
        tasks.load_env_cfg = load_config
        app_play.AppPlayer = official_player
        play._loop = official_loop
        sys.path[:] = previous_path
        sys.argv = previous_argv
        os.chdir(previous_cwd)
        state["modes"] = sorted(state["modes"])
        state["official_argv"] = official_arguments(args)
        state["upstream_files_modified"] = False
        state["physical_stop_confirmed"] = False
        observer.__exit__(*sys.exc_info())
        state["shared_observer"] = observer.status()
        args.video.with_suffix(".clawmetry.json").write_text(json.dumps(state, indent=2, allow_nan=False) + "\n")
        store.append(args.run_id, state["steps"] * .005, "outcome", state)
        store.close()
    return state


def main():
    p = parser()
    args = p.parse_args()
    for key in ("upstream", "scene", "video", "evidence"):
        setattr(args, key, getattr(args, key).expanduser().resolve())
    if not 0 < args.steps <= 120000:
        p.error("--steps must be between 1 and 120000")
    if not all(math.isfinite(x) for x in (*args.table_bounds, args.table_height, args.wave_at,
                                         args.bow_at, args.jump_at)):
        p.error("Scene bounds and schedule times must be finite")
    if min(args.wave_at, args.bow_at, args.jump_at) < 0:
        p.error("Schedule times cannot be negative")
    if args.plan_only:
        print(json.dumps({"official_argv": official_arguments(args), "seed": args.seed,
                          "controls_enabled": args.enable_simulator_controls}, indent=2))
        return
    if not args.scene.exists():
        p.error("--scene must name an existing official scene package")
    args.video.parent.mkdir(parents=True, exist_ok=True)
    result = run(args)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
