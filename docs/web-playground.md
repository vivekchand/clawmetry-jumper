# Live Jumper browser playground

The source under `web/` is a standalone vanilla HTML, CSS and JavaScript application for the Mizu demo. After an explicit Start button, it runs **MuJoCo 3.11.0 WebAssembly physics, the official Jumper WebFsm controller and ONNX policy inference on the visitor's device**. Three.js renders the actual simulated geometry transforms. No recorded pose sequence drives the robot. The built-in observer and shared task governance live in [ClawMetry OSS](https://github.com/vivekchand/clawmetry); this standalone browser demo does not replace the built-in integration in the normal ClawMetry installation.

This implements a local desk companion experiment. A visitor can request a wave or stretch invitation, inspect an unrelated jump or cup request being declined, and deliberately apply a simulated disturbance or interrupt the observation feed. The public page has no hardware, camera, microphone, account, billing or backend action connection.

## Prepare and serve

Use the Mizu demo's existing simulation environment and pinned public upstream checkout. First build/import the official scene using [scene-build.md](scene-build.md). Then:

```sh
.venv/bin/python scripts/prepare_web_assets.py \
  --upstream ../clawmetry-jumper-upstream \
  --scene artifacts/official-scene/imported/scene.xml
python3 -m http.server 8957 --bind 127.0.0.1 --directory web
```

Open `http://127.0.0.1:8957/`. The preparation script requires the Mizu demo's pinned native MuJoCo 3.11.0 and existing simulator dependencies, plus `curl` for TLS downloads. It does not install npm or run a frontend build.

The script reuses `JumperSimulator(scene_xml=...)` to prepare the exact native model, contact configuration, calm visual colors and official desk environment. It compiles the model, rewrites asset references to portable VFS names, compiles that portable XML again, and exports fixed render geometry. No geometry is reconstructed from screenshots. Only declared public Jumper inputs and pinned vendor distributions are copied.

It downloads these fixed packages and verifies their pinned SHA512 archive integrity before extracting selected files:

| Component | Version | License |
|---|---|---|
| `@mujoco/mujoco` | 3.11.0 | Apache-2.0 |
| `onnxruntime-web` | 1.30.0 | MIT, with retained third-party notices |
| `three` | 0.178.0 | MIT |
| Jumper model, policies and controller | `78966f45de6f2b6de3f7cea017f32a39f8b993e6` | Upstream Apache-2.0 scope and NOTICE |

MuJoCo and ONNX package notices absent from their npm archives are fetched from the corresponding official version tags. Vendor licenses, ONNX third-party notices and Jumper LICENSE/NOTICE remain in the generated delivery. Pinned full compiled-dependency notices are reproduced from versioned `resources/browser-notices/` inputs. This includes MuJoCo core/WASM dependencies, the official controller's 50-crate web-feature source/lock inventory and embedded Rust standard-library notices. The preparer checks every notice text hash, controller WASM digest and upstream Cargo.lock before copying; a changed controller requires a new reviewed inventory. These are source/lock records, not a bit-reproducible build attestation. `web/THIRD_PARTY_NOTICES.txt` indexes the served texts.

Model and package archive SHA256 values are recorded in `web/asset-build.json`; `web/deployment-manifest.json` records each prepared file hash and honest source-tree revision/dirty status. Large `web/vendor/`, `web/assets/`, test results and build receipts are ignored by Git; preparing them is an explicit delivery step, not an assumed fresh-clone capability.

## Runtime and evidence

- No model/runtime assets are fetched or physics started before the visitor presses Start. Dependencies and assets are served from the same host. There are no analytics or external font requests.
- The fixed model XML and all 76 VFS resources are checked against their prepared SHA256 and byte counts before compilation. There is no arbitrary `.app`, `.map` or `.skin` upload path.
- The official browser controller first checks all 24 bundled reference frames. Startup rejects controller disagreement above `1e-6`, a mode mismatch or divergent term. Browser ONNX inference is checked separately against all 18 inference reference frames, with declared tolerance `2e-5`.
- The loop serializes asynchronous inference, never overlapping control ticks. It uses 200 Hz control steps with five native 1 ms physics substeps, the upstream servo torque-speed curve and thermal limit. A slow device runs more slowly instead of skipping physics time or fabricating a pose.
- Browser joint mappings, quaternion order, body-frame gyroscope and applied PD torque are explicit. Policy observations and mode changes come from the upstream controller.
- Requests have unique IDs and separate permission, controller binding, entered-mode and measured-return events. A pending request cannot be stacked into another gesture. Unimplemented cup handling and out-of-task jumping are not forwarded.
- The monitor measures the conservative collision-geometry AABB against the finite tabletop at 200 Hz. It reports edge proximity, boundary breach, large tilt and raised body position. These are simulator measurements, not human detection or certified safeguards.
- The explicit force tests apply a 45 N vertical or sideways wrench for 0.35 simulated seconds, then clear the external force. The native low-level controller and physics continue afterward. A breach or fall remains visible; no fence, hidden position clamp or recovery teleport is added.
- The observation-loss test interrupts ClawMetry's measurement feed for three simulated seconds while native controller and renderer continue. New gesture requests are denied. Missing samples carry `outcome: unknown`; a gesture spanning that loss cannot receive a complete verified outcome.
- Pause means the browser simulation is paused. It is not a claim that a physical robot was stopped. Changing browser tabs pauses this local simulation and releases operator input. A paused page redraws only after camera or viewport changes. Page navigation disposes the controller, model, inference sessions and Three.js resources; returning through the browser page cache requires a fresh Start opt-in.
- Timeline events remain local in memory. The download contains event IDs, episode IDs, qualification results, bounded samples, missing-data status and observed margins. It contains no user identity or network credentials. Resets create a new episode; they do not rewrite previous evidence. Bounds are 1,000 events and 6,000 samples at 10 Hz, with truncation explicitly recorded.

The phone-shaped status area is an **on-screen alert preview**. It sends no real phone notification. The seated human is a static primitive proxy; the cup and other desk objects stay fixed. This page does not demonstrate glass delivery, liquid handling, person recognition, autonomous tidying or hardware safety.

## Browser acceptance

`web/tests/browser_acceptance.py` launches an isolated automated Chromium profile through Playwright. It does not attach to the user's Chrome. With the local server running:

```sh
python web/tests/browser_acceptance.py
```

Use a Python environment with Playwright and its Chromium installed. The test checks startup opt-in, controller and ONNX agreement, genuine wave/bow mode entry and return, denials, observation loss during motion, continued physics, force removal, measured disturbance alerts, same-host requests and a 390-pixel mobile layout. Reports and actual screenshots are written to `web/test-results/`. This is not testing Safari, every GPU, or real hardware.

The initial Chromium qualification measured zero controller observation/target difference and `4.76837158203125e-7` maximum absolute ONNX inference error. Wave and bow returned to locomotion, with measured minimum tabletop margins of approximately 0.358 m and 0.354 m respectively in those runs. The lifting disturbance tipped the simulated robot; the sideways disturbance crossed the tabletop boundary and fell onto the room floor. These failures are deliberately preserved and alerted, not presented as prevention successes. Consult the current browser report for the exact source and final acceptance result.

## Hosting boundary

Serve the complete prepared `web/` tree under a trailing-slash path such as `/jumper/playground/`, and redirect its slashless form before serving the HTML. All imports and asset paths are relative, so a wrapper may embed that directory without a build step. Serve `.wasm` as `application/wasm`, JavaScript modules as JavaScript, and use HTTPS so Web Crypto is available. The configured single-thread MuJoCo and ONNX paths do not require COOP/COEP. Test the actual hosted path and asset hashes before announcing it.

The public Design repository supplies the official scene compiler and package checks but excludes the BE UNLIMITED simulator website. This page is an independently implemented host using public runtimes. It does not copy the BE UI or assume rights to its deployed application bundles. A future general package loader needs its own protocol, resource, capability and platform validation; no upload control should be added by merely permitting those filename extensions.

No landing route, cloud deployment, publishing or production acceptance is performed by these files alone.
