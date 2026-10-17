# Official Jumper simulator replay

`scripts/official_replay.py` invokes the pinned upstream `scripts/play.py.main()`
with its original native environment, `AppPlayer`, ONNX policies and `ReplayVideo`
MP4 recorder. It does not use this project's standalone MuJoCo scene or renderer.
No upstream source file is changed.

Train does not load Design `.skin` files. By default the wrapper applies a
disclosed mint/sage RGBA override to the original robot's visual geoms in memory,
before the official recorder copies its model. Geometry, masses, collision and
physics remain unchanged. `--no-calm-skin` preserves the original red appearance.

Use the separate upstream editable environment. The upstream training libraries
are required by this official path. Installing them does not establish that all
upstream training/deployment/toolchain verification gates have passed.

```bash
/path/to/jumper-upstream/.venv/bin/python scripts/official_replay.py \
  --upstream /path/to/jumper-upstream \
  --scene scenes/mizu-desk.map \
  --video output/mizu-official.mp4 \
  --evidence output/mizu-official.duckdb \
  --enable-simulator-controls --steps 7000 --seed 42
```

Install this adapter into that environment with `pip install -e . --no-deps`,
and install its evidence dependency `duckdb` if absent. The caller must provide
the actual `.map` package, not the Design source JSON. The official importer
places the map's spawn at the origin, turns its heading onto +X and keeps the
task's original robot. Bounds passed with `--table-bounds X_MIN X_MAX Y_MIN Y_MAX`
and `--table-height` must describe that imported coordinate frame. Defaults are
the standalone example's 1.72 by 1.16 m tabletop centered on the origin; change
these when the official scene differs.

The forwarded official command uses `--app out/bundle_example/jumper`,
`--task jumper.posture --backend native --device cpu --num_envs 1 --headless`,
the requested finite steps and video, `--scene`, `--speed 0`, and a fixed camera.
`--stop-on-done` prevents the recorder from showing a reset as continuous motion.
The actual upstream CLI has no `--seed`: the wrapper owns that argument and sets
the environment config's `seed` before the official environment is constructed.
`--plan-only` prints the exact forwarded arguments without allocating simulation.

The only in-memory integration hooks are an `AppPlayer` subclass and an external
wrapper around its official loop's environment `step`. They preserve the native
physics and video path. Scripted key edges pass through `TaskGate`: wave at 3 s,
bow at 14 s, denied jump at 25 s. Simulator control is disabled unless explicitly
enabled. The jump remains outside the authorized reminder task and never reaches
the native controller. Optional `--wave-at`, `--bow-at`, `--jump-at` support short
smoke tests. An input-delivery receipt is separate from a later native transition
and measured result.

After each real physics step, observations come from the native backend's public
`env.sim.env_mjdata(0)`. Full enabled robot collision bounds determine signed
table clearance. `DeskMonitor` checks fresh state, edge proximity, base lift and
tilt; alerts and notification status are written locally. No webhook or phone
delivery is configured by this wrapper. Observations persist at 20 Hz; requests,
decisions and native transitions persist individually. A seated figure in the
scene is visual/physical scene content, not proof of human detection or intent
recognition.

Outputs are the official MP4, its `.replay-info.json`, `.clawmetry.json` measured
summary and local DuckDB evidence. A failed or terminated episode is retained
as such. This wrapper does not promise physical containment, reset hidden falls,
transport a cup, or claim a hardware stop. Initial state randomization and all
official task physics remain in force, with a fixed seed for repeatability.

## Measured local replay, 17 October 2026

`artifacts/official-replay/mizu-official.mp4` was produced by the actual official
recorder using `artifacts/official-scene/mizu-desk.candidate.map` and seed 42.
It contains 1051 H.264 frames at 1280x720 and 30 fps: 35 simulated seconds plus
the initial frame. The seated figure, tabletop and mint visual override were
visually checked in an extracted frame.

All 7000 controller steps remained finite, with no episode resets. Minimum
conservative full-robot tabletop clearance was 0.310279 m and maximum base tilt
was 10.2535 degrees. The native controller entered hello at 3.0 s and returned
at 10.96 s, then entered bow at 14.0 s and returned at 23.195 s. The jump request
at 25 s was denied before controller delivery; no jump transition occurred.

The local DuckDB contains 700 decimated observations, three task decisions and
six controller receipts, including the four actual native mode transitions.
This nominal episode generated no physical-hazard alerts or notification
attempts. It demonstrates task request filtering and observed tabletop margin,
not detection of malicious intent, a delivered phone alert or hard containment.
