# Mizu on Jumper, with ClawMetry

A calm desk companion, with a clear task and a record of what it actually did.

![Native Jumper simulation with our desk scene and seated person](docs/images/desk-scene.png)

Mizu began as a healthy desktop prototype at the La Machine robotics hackathon:
a reminder to stretch, water brought within reach, and a little tidying after
work. This open-source experiment brings that idea to KingKong Robotics' Jumper.
ClawMetry adds task permissions, full-body tabletop measurements, local activity
history and alerts. It is a **local simulation prototype**. It does not establish
hardware safety or autonomous glass delivery.

## What works in the recorded run

- The official Jumper `play --app` simulator and MP4 recorder run our finite desk
  scene, with a seated static human proxy and a calm sage robot color treatment.
- Real native-controller wave and bow complete and return to the standing policy.
- An unrelated jump request is denied before controller delivery.
- The full collision footprint remains within the table in the measured episode.
- Requests, decisions, native transitions and observations persist in local DuckDB.
- A read-only ClawMetry extension shows recorded history at `/jumper`.
- Monitors detect measured edge approach/crossing, unexpected lift, excessive tilt
  and unavailable observations. Optional HTTPS webhooks record delivery receipts.

On the recorded seed-42 run: **7,000 control steps, no resets, 0.310 m minimum
conservative tabletop clearance**. This is one measured episode, not a physical
containment guarantee. [Run details](docs/official-replay.md).

Phone delivery is not configured by default. An accepted webhook is not proof
that a phone displayed an alert. Missing observations produce `unknown`, not a
claim that the robot stopped. A rejected action is a task-scope test, not proof
of protection from every attack or command path.

## Run locally

Python 3.10 to 3.13 is required for the pinned simulator. Use an isolated environment.

```sh
git clone https://github.com/vivekchand/clawmetry-jumper.git
cd clawmetry-jumper
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[sim,dev]'
git clone https://github.com/KingKongRobotics/jumper.git ../jumper
cd ../jumper
git checkout 78966f45de6f2b6de3f7cea017f32a39f8b993e6
cd ../clawmetry-jumper
.venv/bin/clawmetry-jumper record --upstream ../jumper --output artifacts/my-first-run
```

The default observes without sending skill requests. To explicitly enable
simulator controls, add `--enable-simulator-controls`. Every recording needs a
new output folder so previous history is preserved. This lightweight runner is
separate from the official training environment. It uses the shipped native
controller, ONNX policies and actual MuJoCo physics.

To record **through the official simulator**, including the authored desk and
seated person, follow [scene preparation](docs/scene-build.md) then
[official replay](docs/official-replay.md). Neither path uses generated video as
physics evidence. The full upstream training/device-build setup is not claimed
ready merely because playback works.

```sh
.venv/bin/clawmetry-jumper serve --db artifacts/my-first-run/evidence.duckdb
# Open http://127.0.0.1:8946/jumper
.venv/bin/python -m pytest -q
```

Installing this package beside ClawMetry exposes its public extension entry point.
Use `JUMPER_EVIDENCE_STORE` for a shared simulator/server store or configure
`JUMPER_EVIDENCE_DB` for a completed database. An active DuckDB writer must serve
its readers through the same process. Nothing is sent to cloud by this adapter.

## Add companion skills

See [skills](skills/README.md) for task definitions, the execution boundary and
validation requirements. The current executable skills are native greeting
policies. Traversing the table, picking up an empty vessel, transporting water
and putting a pen away require validated motion/manipulation skills. The
[task roadmap](docs/task-roadmap.md) documents the actual upstream grasp
experiments and their present limitations. No cup is welded to a claw to make
an apparent success.

The intended workspace is the entire approved tabletop, with purposeful travel
for a task and return to a resting place. Whole-body clearance and a validated
path matter; a destination check alone does not establish safe travel.

## Story and credits

[Storyboard](docs/storyboard.md) · [Original Mizu post](https://www.linkedin.com/feed/update/urn:li:activity:7513599170314928130/)
· [ClawMetry Physical AI](https://clawmetry.com/physical-ai)

Jumper model, policy and controller: [KingKong Robotics](https://github.com/KingKongRobotics/jumper).
Scene tools: [Jumper Design](https://github.com/KingKongRobotics/jumper-design).
Simulation: [MuJoCo](https://github.com/google-deepmind/mujoco).

Apache-2.0 for this adapter. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
Third-party runtime and asset licenses remain their own.
