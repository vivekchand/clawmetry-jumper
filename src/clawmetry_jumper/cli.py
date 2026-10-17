"""Mizu demo runner; observation and task governance ship in ClawMetry itself."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

from clawmetry.physical_ai import DeskMonitor, JumperObserver, Request, Task, TaskGate

from .evidence import EvidenceStore


def record(upstream: Path, output: Path, *, enable_controls=False, seconds=36, video=True,
           journal_dir: Path | None = None):
    from .simulator import JumperSimulator
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose a new empty output folder so earlier evidence stays intact")
    output.mkdir(parents=True, exist_ok=True)
    sim = JumperSimulator(upstream)
    reference = sim.verify_reference()
    if not reference["passed"]:
        raise RuntimeError("The native controller reference did not match")
    store = EvidenceStore(output / "evidence.duckdb")
    run_id = "desk-companion"
    # One stable episode; individual interactions get separate task identities.
    tasks = {
        "stretch": Task("stretch", frozenset({"wave"})),
        "sip": Task("sip", frozenset({"bow"}), frozenset({"glass"})),
        "tidy": Task("tidy", frozenset({"carry"}), frozenset({"pen", "paper"})),
    }
    gates = {k: TaskGate(v, controls_enabled=enable_controls,
                         supported_actions={"wave", "bow"}) for k, v in tasks.items()}
    monitor = DeskMonitor(baseline_height_m=.10647)
    observer = JumperObserver("mizu-native", environment="simulation", directory=journal_dir,
                              monitor=DeskMonitor(baseline_height_m=.10647), sample_interval_s=.1)
    observer.__enter__()
    writer = None
    if video:
        writer = subprocess.Popen([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
            "-pix_fmt", "rgb24", "-s", "1280x720", "-r", "30", "-i", "-",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output / "native-simulation.mp4")], stdin=subprocess.PIPE)
    events = []
    schedule = {600: ("stretch", "wave", "key_1", None),
                2800: ("sip", "bow", "key_2", None),
                5000: ("sip", "jump", None, None),
                5400: ("tidy", "carry", None, "phone"),
                5600: ("tidy", "carry", None, "pen"),
                6200: ("sip", "bow", "key_2", None)}
    releases = []
    margins, max_height, frame_index = [], 0., 0
    snapshot = sim.snapshot()
    try:
        for tick in range(round(seconds / sim.dt)):
            now = snapshot["time_s"]
            blind = 30 <= now < 32
            keys = [(k, False) for due, k in releases if due == tick]
            if tick in schedule:
                task_id, action, key, obj = schedule[tick]
                request = Request(f"request-{tick}", task_id, action, obj)
                obs = {} if blind else snapshot
                decision = observer.decide(gates[task_id], request, obs, now_s=now)
                store.append(run_id, now, "request", asdict(request))
                store.append(run_id, now, "decision", decision.to_dict())
                events.append(dict(time_s=now, **decision.to_dict()))
                if decision.send_to_controller and key:
                    keys.append((key, True))
                    releases.append((tick + 1, key))
                    observer.emit("controller.receipt", {"request_id": request.request_id,
                                  "key": key, "status": "input_scheduled", "time_s": now})
                elif decision.status == "denied":
                    alert = {"type": "task_boundary", "message": decision.reason,
                             "action": action, "evidence_kind": "simulation", "physical_stop_confirmed": False}
                    store.append(run_id, now, "alert", alert)
                    store.append(run_id, now, "notification", {"alert_type": alert["type"],
                        "status": "not_configured", "phone_delivery_confirmed": False,
                        "scope": "demo_capture_only"})
            snapshot = sim.step(keys)
            if blind:
                observer.check(snapshot["time_s"])
            else:
                observer.observe(snapshot, now_s=snapshot["time_s"])
            if tick % 20 == 0:
                if not blind:
                    store.append(run_id, snapshot["time_s"], "observation", snapshot)
                for alert in monitor.update(None if blind else snapshot, snapshot["time_s"]):
                    store.append(run_id, snapshot["time_s"], "alert", alert)
                    store.append(run_id, snapshot["time_s"], "notification", {
                        "alert_type": alert["type"], "status": "not_configured",
                        "phone_delivery_confirmed": False, "scope": "demo_capture_only"})
                    events.append({**alert, "time_s": snapshot["time_s"]})
            for log in snapshot["controller_logs"]:
                store.append(run_id, snapshot["time_s"], "controller", log)
                observer.emit("controller.receipt", {"receipt_type": "mode_transition", **log})
                events.append(dict(kind="controller", **log))
            margins.append(snapshot["table_margin_m"])
            max_height = max(max_height, snapshot["position_m"][2])
            if not snapshot["finite"]:
                raise FloatingPointError("Simulation became nonfinite")
            # Select frames by simulation time. No accelerated inference or
            # repeated still frame masquerades as a successful physical action.
            if writer and snapshot["time_s"] + 1e-8 >= frame_index / 30:
                writer.stdin.write(sim.render().tobytes())
                frame_index += 1
        observer.close()
        result = dict(reference=reference, duration_s=snapshot["time_s"], frames=frame_index,
                      min_table_margin_m=min(margins), max_base_height_m=max_height,
                      finite=True, controls_enabled=enable_controls, final_mode=snapshot["mode"],
                      physical_stop_confirmed=False, phone_delivery_confirmed=False,
                      events=events, engine="MuJoCo 3.11.0, native Jumper controller, ONNX CPU",
                      provenance=sim.provenance)
        result["shared_observer"] = observer.status()
        store.append(run_id, snapshot["time_s"], "outcome", result)
        (output / "run-report.json").write_text(json.dumps(result, indent=2))
    finally:
        observer.__exit__(*sys.exc_info())
        sim.close()
        store.close()
        if writer:
            writer.stdin.close()
            if writer.wait() != 0:
                raise RuntimeError("Video encoding failed")
    print(json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("record", help="Record native simulation and local evidence")
    r.add_argument("--upstream", type=Path, required=True)
    r.add_argument("--output", type=Path, default=Path("artifacts/native"))
    r.add_argument("--enable-simulator-controls", action="store_true")
    r.add_argument("--seconds", type=int, default=36, choices=range(1, 121))
    r.add_argument("--no-video", action="store_true")
    r.add_argument("--journal-dir", type=Path, default=None,
                   help="Override the built-in observer's shared journal directory for isolated tests")
    args = parser.parse_args()
    if args.command == "record":
        record(args.upstream, args.output, enable_controls=args.enable_simulator_controls,
               seconds=args.seconds, video=not args.no_video, journal_dir=args.journal_dir)


if __name__ == "__main__":
    main()
