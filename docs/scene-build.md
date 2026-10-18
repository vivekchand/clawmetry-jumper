# Official Mizu desk scene build

## Current useful-desk revision, October 18

The canonical authored input remains [mizu-desk.scene.json](../scenes/mizu-desk.scene.json), now SHA256 `f7b1ed014005f2998ec01670a14f7d796569613b413f35878af9c359f1e92167`. The original build record below is historical; its old vessel, laptop positions, zero heading, hashes and geometry counts do not describe the current input.

The user requested a robot facing the seated person, a reachable laptop, and useful empty-cup and cleanup tasks. This revision arranges the room and task destinations. The official map still supplies no controller, dynamic task object, grasp, handoff, manipulation score, liquid or hardware behavior. The host owns any dynamic empty cup and cleanup object and must qualify their actual contacts, motion and stable outcomes separately.

### Layout contract

Coordinates are world meters, Z up. The native Jumper front is +X at zero heading.

- Support spawn is `[0.02,-0.02,0]`, yaw `-90` degrees. The native host should preserve its own valid base height and set root XY to `[0.02,-0.02]`, with Hamilton quaternion wxyz `[0.7071067811865476,0,0,-0.7071067811865475]`. This faces the person side of the desk. A package support point must not be copied into robot root Z.
- The tabletop remains exactly `x=±0.86`, `y=±0.58`, top `z=0`, with unchanged physical support/friction. The room floor remains `z=-0.75`; it cannot establish tabletop containment after a fall.
- Laptop keyboard center is `[-0.40,-0.435,0.009]`, half-size `[0.19,0.105,0.009]`; its front edge is `y=-0.54`, about 0.12 m from the static hand centers. The screen center is `[-0.40,-0.335,0.141]`; its display faces negative Y toward the seated proxy and leans away by 12 degrees. This is reachable static context, not an animated typing action or verified ergonomic model.
- `stationary_sip_vessel_proxy` was removed. No fixed cup can be mistaken for a delivered object. The existing `coaster` is a collision-disabled, visual-only target marker at `[0.06,-0.31,0.001]`, radius 0.048 m; it adds no hidden contact step.
- `tidy_tray_floor` is centered `[0.22,-0.1725,-0.004]`, half-size `[0.09,0.0625,0.004]`. Its top is exactly flush at `z=0`, removing a step-climbing dependency. The two side walls and back are real static collision geometry, with an open front toward negative Y. Side wall centers are `x=0.126` and `0.314`, with center Y -0.1725 and half-depth 0.0625 m; back center is `y=-0.106`. The user-authorized 5 mm front-only extension moves the floor front edge to `y=-0.235`, while the back stays at `y=-0.110`. The actual interior bounds are `x=[0.130,0.310]`, `y=[-0.235,-0.110]`, with geometric center `[0.22,-0.1725]` and half-size `[0.09,0.0625]`. Keep the semantic placement target `[0.22,-0.17]` separate from those asymmetric physical containment bounds. The map contains no initial cleanup body. The host's exact dynamic geometry determines whether its initial footprint partly overlaps the flush floor; overlap alone never establishes placement, displacement or task success. Wall bottoms are flush with the desk, with height 0.036 m. The host must account for this actual floor/wall geometry when qualifying placement.
- Early design trials considered cup XY around `[0.05,-0.25]` and a small cleanup item around `[0.18,-0.25]`. These coordinates, object shapes and reset heights are not authored into this map; the exact current dynamic model and qualification report own them. The cup target `[0.06,-0.31]` is nearer the static right-hand context point `[-0.13,-0.66]`; cleanup targets tray center `[0.22,-0.17]`. Contact-slide trials motivated these revised locations. The map itself supplies no task or manipulation qualification; see the separate [native qualification](native-contact-qualification.md) and browser acceptance records for host behavior on the exact final model. The demonstrated task is a contact-guided slide, not an airborne grasp or human handoff. The physics owner may revise them within the clear positive-X/negative-Y workspace after actual jaw/reach/contact trials. The laptop occupies negative X and must remain outside the task workspace.
- The static human, notebook and pen remain contextual. The palette uses sage `#a4beb1`, moss `#234e43`, cream `#f6f5eb`, sand `#b6aa8c` and ink `#223d34`. The package keeps the unchanged original robot skin; a sage host visual override is separate from this environment build.

### Official build and actual checks

The unchanged official Design checkout is commit `918d192857fcea1678c2a40b339501004a94d838`. Its existing Python 3.14 environment runs MuJoCo 3.16.0; no package was installed for this revision. Its documented compiler produced 39 static bodies/geoms, 2 lights, 10 materials and zero qpos. A one-second environment smoke passed. The official `.map/2` export, trusted-profile verification and new-directory import all passed; composition contains 80 bodies, 23 joints and 121 geoms with zero actuators. Five spawn rays find the actual desk at z=0 with zero severe spawn contacts. These are bounded package-loading checks, not full-footprint or controller acceptance.

The same official composition independently compiled/forwarded in the demo's existing MuJoCo 3.11.0 environment, with the expected -90-degree root quaternion. Four actual native PNGs were rendered from the official scene and composed package; the story and overhead views were opened and inspected. They show the laptop beside the hands, screen toward the person, clear target zones and the robot facing that desk side. Native composition retains the upstream asset-dictionary warning; actual resource resolution passed on both tested engines.

Candidate artifact, outside tracked source:

```text
artifacts/useful-desk-scene-trayextend/mizu-desk.useful.candidate.map
schema: kk-scene-package/2
SHA256: dfa59a34941f1dbaf26205c7c19b6a85353e54372417fa9f364c361d59bceb0b
bytes: 9145246
files: 55
trusted profile SHA256: 051e5c98ae4d948604bf095667f7eeb329a21b43885cc912c5f4dcbbeb83aef9
```

Use the environment at `artifacts/useful-desk-scene-trayextend/imported/scene.xml` for host attachment, preserving relative resources. The host must retain its robot model, inertia, joints, timestep and controller and remove duplicated support geometry. Existing exported original-robot display pose is not a task reset/control pose. Dynamic cup/object bodies are intentionally absent from this static environment.

Run from the official Design checkout, setting the demo path to the intended isolated worktree. Use fresh output paths if previous artifacts exist:

```sh
JUMPER_DEMO=/Users/vivek/projects/clawmetry-jumper/.worktrees/useful-desk-skills
.venv/bin/python -m mjscene validate "$JUMPER_DEMO/scenes/mizu-desk.scene.json"
.venv/bin/python -m mjscene build "$JUMPER_DEMO/scenes/mizu-desk.scene.json" \
  --out "$JUMPER_DEMO/artifacts/useful-desk-scene-trayextend/build" --smoke 1
.venv/bin/python scripts/shellflow.py export-map "$JUMPER_DEMO/scenes/mizu-desk.scene.json" \
  --id mizu-desk --title 'Mizu Useful Desk Companion' \
  --default-skin library/skins/jumper-original.skin --profile robots/jumper/profile.json \
  --output "$JUMPER_DEMO/artifacts/useful-desk-scene-trayextend/mizu-desk.useful.candidate.map"
.venv/bin/python scripts/shellflow.py verify-package \
  "$JUMPER_DEMO/artifacts/useful-desk-scene-trayextend/mizu-desk.useful.candidate.map" \
  --profile robots/jumper/profile.json --capability rigid --capability jumper --mujoco
.venv/bin/python scripts/shellflow.py import-package \
  "$JUMPER_DEMO/artifacts/useful-desk-scene-trayextend/mizu-desk.useful.candidate.map" \
  --profile robots/jumper/profile.json --capability rigid --capability jumper --mujoco \
  --destination "$JUMPER_DEMO/artifacts/useful-desk-scene-trayextend/imported"
```

Reports, four native images and their SHA inventory are under `artifacts/useful-desk-scene-trayextend/`, including `provenance.json`, `verify.json`, `verify-adapter-engine.json` and `composition.json`. This is a local simulator candidate. No formal Design library release, Web visual audit, browser dynamics qualification, manipulation success, hardware test or publication is implied.

### Verified official audio boundary

At pinned Training commit `78966f45de6f2b6de3f7cea017f32a39f8b993e6`, [official hardware documentation](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/docs/HARDWARE.md) lists two speakers and four digital MEMS microphones. That establishes documented components, not an exercised speaker/speech interface. The inspected deployment/runtime code and documentation supply no verified native TTS, speech or speaker-control API. The [documented audio example](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/docs/USAGE.md#exporting-a-performance-as-well-as-a-policy) muxes prerecorded music into an offline dance video. Any companion chime or speech implemented by the browser must therefore remain explicitly browser-provided and opt-in; this scene adds no audio implementation.

---

# Original Mizu desk scene build, retained for provenance

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

Use a separate checkout and environment. These commands were run from the Design repository after installing its documented `.[sim,dev]` extras. The recorded environment used Python 3.14 and MuJoCo 3.16.0. That is package-loading evidence; the demo's pinned runtime must perform its own dynamics checks.

```sh
git clone https://github.com/KingKongRobotics/jumper-design.git
cd jumper-design
git checkout 918d192857fcea1678c2a40b339501004a94d838
git lfs pull
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[sim,dev]'
```

Set the demo directory to its actual local path, and use fresh output paths because the exporter refuses to replace an existing package:

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
| Official default robot + map composition | Native compile and forward passed on both Design MuJoCo 3.16.0 and demo MuJoCo 3.11.0: 81 bodies, 23 joints including floating root, 122 geoms, 0 actuators. |
| Spawn support | Five rays within 0.05 m of the origin found actual desk collision and visual support at `z=0`; zero severe spawn contacts. Limited sampling only. |
| Official import | Passed into a new directory; original package retained. |
| Native visual inspection | Opened both `environment-native.png` and `default-composition-native.png`. Finite desk, seated proxy, props and complete original robot are visible without clipping. |
| Policy playback, full footprint and boundary behavior after attachment | Required in the demo; not established by this package check. |
| Web importer, live browser physics, formal preview and hardware | Not run or claimed by this scene build. |

The official native composition emitted its warning about attaching a child without an asset dictionary to a parent with one. Compilation, forward and the two actual renders passed. A subsequent host attachment must still verify resource resolution instead of assuming that the warning is harmless for all compositions.

Evidence remains under `artifacts/official-scene/`: `verify.json`, `verify-adapter-engine.json`, `import.json`, `default-composition.json` and the two native PNGs. Keep these reports separate from later controller results and browser acceptance.

## Live browser feasibility, inspected separately

The public Design repository does not contain the BE UNLIMITED simulator UI. Its `docs/scene-upstream.md` explicitly excludes the original Web viewer, despite a generic CLI message suggesting a `web/` directory. Its visual-audit scripts expect a separate BE website checkout. Do not copy deployed website bundles or claim that an open-source BE UI was supplied.

A separate vanilla JavaScript host can use public maintained components for genuine live physics:

- [MuJoCo's official JavaScript bindings](https://github.com/google-deepmind/mujoco/blob/main/wasm/README.md), Apache-2.0. The package `@mujoco/mujoco@3.11.0` matches the demo engine and supplies ESM `mujoco.js` and `mujoco.wasm`. Its type declarations include `MjVFS.addBuffer`, `MjModel.from_xml_path(path, vfs)`, `mj_step` and `qfrc_applied`. Native loading is not browser proof.
- The pinned Training bundle's `runtime/web/controller.js` and `controller.wasm` implement `WebFsm`, with its exact contracts and exported ONNX policies. Follow `deploy/fsm/BUNDLE_README.md`, including its reference replay and separate ONNX inference comparison. Do not replace its controller with visual joint animation.
- [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/deploy.html), MIT, supplies browser inference. Serve matching JS, loader and WASM files together; start with `numThreads=1`. A browser host must measure actual inference latency and avoid overlapping control ticks.
- A renderer such as Three.js, MIT, displays geometry using the actual MuJoCo state. Its camera orbit can be interactive while playback is paused, but the UI must distinguish pause, live physics and recorded evidence.

The official MuJoCo single-thread build does not require cross-origin isolation. Multi-thread builds require COOP/COEP and compatible resources, so they are a separate deployment choice. Static ESM and WASM can be served by the existing landing server without adding React or an npm build step; downloading a pinned distributable is different from adding a frontend build system.

Prefer fixed, server-prevalidated assets for the first hosted demonstration. Let visitors choose bounded task scenarios, not arbitrary executable `.app` uploads. A general Appearance/Scene/APP loader needs the documented resource, hash, path, capability and platform rejection checks before accepting external packages. No implementation or deployment of this browser host is claimed by this document.
