# Official Mizu desk scene build

## Source and result

The authored input is [mizu-desk.scene.json](../scenes/mizu-desk.scene.json). It uses the official Design Workflow scene schema, primitives, materials, cameras and spawn fields. No hand-written MJCF was substituted for the official scene compiler.

Input SHA256: `62124bc30e776c6414464567a938ca284f9c28a28eba42c4d62451379fbbeb01`.

Design source: [KingKongRobotics/jumper-design](https://github.com/KingKongRobotics/jumper-design), clean commit `918d192857fcea1678c2a40b339501004a94d838`, checked out separately at `/Users/vivek/projects/clawmetry-jumper-design-upstream`. The build follows that commit's `AGENTS.md`, `docs/workflow.md` and `docs/content-packages.md`. Source files remain unchanged; the CLI wrote an untracked workspace index in its own checkout.

The official `shellflow export-map` produced this local candidate:

```text
artifacts/official-scene/mizu-desk.candidate.map
protocol: kk-scene-package/2
SHA256: ec160f807073606c5710834d0d70aa45266cc489769ec9d00847e0652b647540
bytes: 9145114
files: 55
default skin: jumper-original, kk-skin-package/3
trusted profile SHA256: 051e5c98ae4d948604bf095667f7eeb329a21b43885cc912c5f4dcbbeb83aef9
```

This is a local simulator candidate, not a formal Design library release. Its native renders are not a Web visual audit. No `be-web/1` visual extension or reviewed Web thumbnail is claimed, and no website upload or package publication occurred.

## Scene coordinates and purpose

All dimensions are meters in a right-handed, Z-up world. Zero yaw faces +X; the scene's yaw is in degrees.

- `desk_top`: static box, half-size `[0.86, 0.58, 0.025]`, center `[0, 0, -0.025]`. Its actual support top is `z=0`, with finite edges at `x=±0.86`, `y=±0.58`, matching the native runner.
- The room floor is at `z=-0.75`. It can catch a falling robot, but it is not desk support and must not make a tabletop escape count as success.
- Spawn `[0,0,0]` describes the support point, not robot root height. The selected robot/controller supplies the correct base height. Spawn clearance is `0.50`; bounds are declarative workspace metadata, not invisible walls or automatic enforcement.
- A seated static human proxy is constructed from capsules and ellipsoids beside the front edge. Its hands are centered at `y=-0.66`, outside the desk. This is a visibly simplified contextual mannequin, not a detected person, animated human, biomechanical model or validated human clearance system.
- Laptop, vessel proxy, notebook, pen and tray are fixed contextual props. The vessel is a solid cylinder, not a hollow cup or liquid simulation. None is grasped, delivered, scored or tidied by the map.
- No fences, invisible confinement, actuation, robot joint changes or controller are authored in the scene. The pale sage and sand palette belongs to the environment. No new robot shell was generated or selected.

The open desk center provides space for the initial reminder gestures. Successful containment still needs the native runner's full collision-footprint measurements throughout each motion. The official package's five spawn rays do not establish route clearance or a successful policy rollout.

## Reproduce with official tools

Use a separate checkout and environment. These commands were run from the Design repository after installing its documented `.[sim,dev]` extras. The recorded environment used Python 3.14 and MuJoCo 3.16.0. That is package-loading evidence; the adapter's pinned runtime must perform its own dynamics checks.

```sh
git clone https://github.com/KingKongRobotics/jumper-design.git
cd jumper-design
git checkout 918d192857fcea1678c2a40b339501004a94d838
git lfs pull
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[sim,dev]'
```

Set the adapter directory to its actual local path, and use fresh output paths because the exporter refuses to replace an existing package:

```sh
JUMPER_ADAPTER=/Users/vivek/projects/clawmetry-jumper
.venv/bin/python -m mjscene validate "$JUMPER_ADAPTER/scenes/mizu-desk.scene.json"
.venv/bin/python -m mjscene build "$JUMPER_ADAPTER/scenes/mizu-desk.scene.json" \
  --out "$JUMPER_ADAPTER/artifacts/official-scene/build" --smoke 1
.venv/bin/python scripts/shellflow.py export-map \
  "$JUMPER_ADAPTER/scenes/mizu-desk.scene.json" \
  --id mizu-desk --title 'Mizu Desk Companion' \
  --default-skin library/skins/jumper-original.skin \
  --profile robots/jumper/profile.json \
  --output "$JUMPER_ADAPTER/artifacts/official-scene/mizu-desk.candidate.map"
.venv/bin/python scripts/shellflow.py verify-package \
  "$JUMPER_ADAPTER/artifacts/official-scene/mizu-desk.candidate.map" \
  --profile robots/jumper/profile.json --capability rigid --capability jumper --mujoco
.venv/bin/python scripts/shellflow.py import-package \
  "$JUMPER_ADAPTER/artifacts/official-scene/mizu-desk.candidate.map" \
  --profile robots/jumper/profile.json --capability rigid --capability jumper --mujoco \
  --destination "$JUMPER_ADAPTER/artifacts/official-scene/imported"
```

## Input and output contract for the native runner

The canonical source input is `scenes/mizu-desk.scene.json`. The official compiled environment before packaging is `artifacts/official-scene/build/mizu-desk/scene.xml`. The validated, imported package environment is `artifacts/official-scene/imported/scene.xml`; prefer the latter for integration. Its resources and metadata remain at their original relative paths.

The `.map/2` includes a verified complete original robot under `robot/` because that protocol requires a default robot. The native runner already has its own pinned training model, controller and home pose. It should attach **only the environment** to that host model and record this deliberate choice. Do not replace the controller's model with the package's static display pose.

The pinned Training repository's official importer is `scenes/package.py`. Its documented replay accepts `--scene <path.map>` and preserves the task robot. For a custom native host, use equivalent validated package loading followed by `MjSpec.attach`, preserving assets and prefixing environment names. Do not concatenate the environment's compiler, default or option settings into the host. The package exporter removes scene-global options which must not override host dynamics.

After attachment, remove the runner's previous duplicated tabletop, room floor and decorative desk props. Keep one physical `desk_top`, not two overlapping supports. Verify that host timestep, solver options, robot body masses/inertias, joints and contact parameters did not change. The imported scene has stable geometry names such as `desk_top_geom`, `seated_proxy_left_hand_geom` and `stationary_sip_vessel_proxy_geom`, with the host's attach prefix prepended.

## Checks actually completed

| Check | Recorded result |
|---|---|
| Official scene schema | Passed after correcting one duplicate camera/object name; no source errors remain. |
| Official native environment compilation | 40 bodies, 40 geoms, 2 lights, 10 materials, 0 qpos. |
| Environment-only smoke | 1 second of native physics; all objects static. This is not a robot rollout. |
| Official map export, hash and trusted profile validation | Passed, `/2`, 55 files. |
| Official default robot + map composition | Native compile and forward passed on both Design MuJoCo 3.16.0 and adapter MuJoCo 3.11.0: 81 bodies, 23 joints including floating root, 122 geoms, 0 actuators. |
| Spawn support | Five rays within 0.05 m of the origin found actual desk collision and visual support at `z=0`; zero severe spawn contacts. Limited sampling only. |
| Official import | Passed into a new directory; original package retained. |
| Native visual inspection | Opened both `environment-native.png` and `default-composition-native.png`. Finite desk, seated proxy, props and complete original robot are visible without clipping. |
| Policy playback, full footprint and boundary behavior after attachment | Required in the adapter; not established by this package check. |
| Web importer, live browser physics, formal preview and hardware | Not run or claimed by this scene build. |

The official native composition emitted its warning about attaching a child without an asset dictionary to a parent with one. Compilation, forward and the two actual renders passed. A subsequent host attachment must still verify resource resolution instead of assuming that the warning is harmless for all compositions.

Evidence remains under `artifacts/official-scene/`: `verify.json`, `verify-adapter-engine.json`, `import.json`, `default-composition.json` and the two native PNGs. Keep these reports separate from later controller results and browser acceptance.

## Live browser feasibility, inspected separately

The public Design repository does not contain the BE UNLIMITED simulator UI. Its `docs/scene-upstream.md` explicitly excludes the original Web viewer, despite a generic CLI message suggesting a `web/` directory. Its visual-audit scripts expect a separate BE website checkout. Do not copy deployed website bundles or claim that an open-source BE UI was supplied.

A separate vanilla JavaScript host can use public maintained components for genuine live physics:

- [MuJoCo's official JavaScript bindings](https://github.com/google-deepmind/mujoco/blob/main/wasm/README.md), Apache-2.0. The package `@mujoco/mujoco@3.11.0` matches the adapter engine and supplies ESM `mujoco.js` and `mujoco.wasm`. Its type declarations include `MjVFS.addBuffer`, `MjModel.from_xml_path(path, vfs)`, `mj_step` and `qfrc_applied`. Native loading is not browser proof.
- The pinned Training bundle's `runtime/web/controller.js` and `controller.wasm` implement `WebFsm`, with its exact contracts and exported ONNX policies. Follow `deploy/fsm/BUNDLE_README.md`, including its reference replay and separate ONNX inference comparison. Do not replace its controller with visual joint animation.
- [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/deploy.html), MIT, supplies browser inference. Serve matching JS, loader and WASM files together; start with `numThreads=1`. A browser host must measure actual inference latency and avoid overlapping control ticks.
- A renderer such as Three.js, MIT, displays geometry using the actual MuJoCo state. Its camera orbit can be interactive while playback is paused, but the UI must distinguish pause, live physics and recorded evidence.

The official MuJoCo single-thread build does not require cross-origin isolation. Multi-thread builds require COOP/COEP and compatible resources, so they are a separate deployment choice. Static ESM and WASM can be served by the existing landing server without adding React or an npm build step; downloading a pinned distributable is different from adding a frontend build system.

Prefer fixed, server-prevalidated assets for the first hosted demonstration. Let visitors choose bounded task scenarios, not arbitrary executable `.app` uploads. A general Appearance/Scene/APP loader needs the documented resource, hash, path, capability and platform rejection checks before accepting external packages. No implementation or deployment of this browser host is claimed by this document.
