<!--lint disable strong-marker-->

# Review Log: WO-JUMPER-USEFUL-DESK

**Work Order:** WO-JUMPER-USEFUL-DESK — Facing companion with physical cup and cleanup skills
**Initialized At (UTC):** 2026-10-18T19:32:27Z

This file records review and verification rounds. Append new rounds; do not overwrite prior rounds.

---

## Round 1

### Requirements Alignment

**Blocking:**

**Advisory:**

### Blueprint Alignment

**Blocking:**

**Advisory:**

### Architecture And Conventions

**Blocking:**

**Advisory:**

### Tests And Build

**Commands run:**

**Blocking:**

**Advisory:**

### User-Facing Verification

**Skipped:** _yes/no_ - _reason if yes_

**Evidence:**

**Blocking:**

**Advisory:**

### Security, Privacy, And Data Safety

**Skipped:** _yes/no_ - _reason if yes_

**Blocking:**

**Advisory:**

### Round 1 Verdict

- Total blocking:
- Total advisory:
- Files reviewed:
- **Verdict:** _APPROVED or CHANGES_REQUESTED_

---

<!-- Subsequent rounds: copy the structure above and increment the round number. -->

## Round 2: Independent audio-only source review

Reviewer: `/root/runtime_gate_diagnosis`. Scope: opt-in browser companion audio and its app lifecycle integration; the rest of this work order remains pending.

### Requirements and blueprint alignment

**Blocking:** None in this scope. Audio is muted by default, browser-provided, optional, and independent of complete on-screen messages. No native Jumper speaker API, microphone capture, remote TTS, or hardware speech is claimed.

### Architecture, security, privacy and lifecycle

**Blocking:** None. AudioContext is created only after explicit enable. Speech selects only an English voice explicitly marked localService; remote-only voice lists never trigger default-service fallback. The reviewed audio module makes no network or storage calls. Text is bounded. Pause, hidden state, reset and disposal cancel output. Pending activation, retired resume rejection, retired utterance errors and checkbox completions are generation-fenced. No-audio and voice-only status messages now match actual capability.

Three independently reproduced activation/cancellation races were repaired before approval: an old rejected resume disabling a newer activation; stop during pending resume leaving later speech enabled; and a permission event speaking/canceling activation before enable finished. Permanent deferred tests cover these windows without increased sleeps.

### Tests and build

`node tests/companion_audio_check.cjs` passed; `python3 -m pytest -q tests/test_companion_audio.py` passed (1 test); `git diff --check` passed. Node probes include default mute, local-service selection, remote-only rejection, hidden/disposed suppression, pending-stop, old rejection after newer success, event during pending enable, and disposal before resume completion.

### User-facing verification and limits

Source/component lifecycle and disclosure reviewed. Actual device voice listening and rebuilt browser/hosted acceptance are not performed in this round. This approval does not qualify final audio quality, native speaker behavior, physics tasks, or publication.

### Reviewed SHA256

- `web/audio.js`: `acde211f15640c5e248c242a1102f4759c7c1dd4c325be11dd300c1cdc528616`
- `web/app.js` (audio-related integration only): `94e413ad45a1406d515c5e153edbe1759cbb1367d0ec0342166307ac256ab6b4`
- `tests/companion_audio_check.cjs`: `ab58e324e33992a29fa1752512fc7f80c4485305ecb0e410a059c245ef961524`
- `tests/test_companion_audio.py`: `2e6abf85352817f6356e066063b0b73fa3962470a0cfc9f4472fb665c1ab704b`

### Round 2 verdict

**APPROVED, audio-only source scope.** Zero blocking findings; overall work-order acceptance remains pending actual manipulation and browser qualification.

---

## Round 3: Independent scene-only review

Reviewer: `/root/runtime_gate_diagnosis`. Scope: `scenes/mizu-desk.scene.json`, the current useful-desk section of `docs/scene-build.md`, and the exact native package/render evidence in `artifacts/useful-desk-scene-contact/`. No manipulation/controller or hosted dynamics approval is implied.

### Requirements and blueprint alignment

**Blocking:** None within static layout scope. Spawn XY `[0.02,-0.02]` and yaw `-90` face the seated-person side; documentation correctly distinguishes support-point Z from floating robot base height. The laptop keyboard is beside the hands, with display toward the person. Negative-X laptop context remains separate from the positive-X task workspace. The coaster is a visible marker, and the open-front cleanup tray has actual finite side/back collision walls and a flush support floor. Human geometry is explicitly a static simplified proxy. Historical build notes are separated and expressly superseded by the current scene contract.

### Architecture, geometry and safety

**Blocking:** None. The scene supplies environment geometry, not controller/model replacements. Table bounds/top/friction remain unchanged; the lower room floor cannot count as desk support. No invisible wall, translucent obstruction, dynamic constraint, object weld or fixed delivered-cup substitute is present. The removed fixed vessel is absent. Only decorative screen/hair and the disclosed coaster marker disable collision. All scene materials and compiled geoms are opaque. Host-owned dynamic objects and measured manipulation outcomes remain separate.

### Tests and native evidence

Independently recalculated the scene SHA and all 12 file hashes recorded by `provenance.json`; every entry matched. Inspected official verify/import/composition reports: valid map/2, 55 files, actual 3.16.0 compile/forward and 3.11.0 composition checks, 23 robot joints retained, zero actuators in the package display composition, five limited spawn-support rays, and no severe spawn contacts. These reports explicitly disclaim full footprint/dynamics acceptance.

Independently loaded `imported/scene.xml` using the existing MuJoCo 3.11.0 environment and ran `mj_forward`: 39 bodies/geoms, zero qpos, zero actuators, zero equality constraints, all geom alpha 1. Native positions/sizes/contact masks matched the tabletop, flush tray floor and three real tray walls. Coaster contype/conaffinity are both zero as documented. No static vessel geom exists.

### User-facing verification and limits

Opened actual `composed-desk_story.png` and `composed-desk_overhead.png`. The seated person, reachable laptop context, finite desk, person-facing original robot, coaster and open tray are legible without clipping or opacity tricks. The original robot is red in this official package composition; any later sage host override is explicitly separate. Browser/host rendering, dynamic object reach/grasp/slide/carry/release, seed sweeps, tabletop containment, human clearance and hardware remain pending and are not established by static renders. Existing upstream asset-dictionary warning is retained transparently in the record.

### Reviewed SHA256

- `scenes/mizu-desk.scene.json`: `1427018a6b0d2c5b2f432bf1c9a3a842a07bf76c230d74c235bff3aa7c84c0d0`
- `docs/scene-build.md`: `148f41b18d8cb33c51da3afbe6f6bd3afd97a0aa7d2a8cbed42acad140e07440`
- `artifacts/useful-desk-scene-contact/provenance.json`: `280f4d71602a903db82fc61759e13dfca4eb599215f13a996ed1d2b3a8fc3104`
- Candidate map: `08bd1cfcfb490126b529d8ef72d075cfc2dd489d18f40cba862f18efa98f3389`
- Story native PNG: `234ec2c5ee83348e4479aa80068f50576867b11e22159320e33c055ee476a25a`
- Overhead native PNG: `01bbe25562e2baa9287f7028b7f919b9525baddcfe2697f8046567920854ed68`

### Round 3 verdict

**APPROVED, scene-only static layout/provenance scope.** Zero blocking findings. Overall work order remains pending independently qualified contact-only skills, failure handling and actual rebuilt browser acceptance. No merge, install or publication performed.

---

## Round 4: Independent browser-task and prepared-asset review, interim

Reviewer: `/root/cloud_guard_review`. Scope is the unowned root-authored `web/manipulation.js`, `web/simulation.js` and `scripts/prepare_web_assets.py`. This reviewer authored the scene and therefore does not independently approve any scene revision. No implementation edits, package installation or publication were performed for this review.

### Findings and corrections

- **R4.1 P2, premature completion, resolved on source:** the first implementation emitted completion and cleared the active task while still in native claw support, then queued the controller return. Any subsequent collision/drift was outside task monitoring. The author added an explicit monitored return phase, no scripted arm override after return, actual locomotion acknowledgement, two seconds of returned stance and a further 0.75 seconds of valid placement before completion. Whole-task robot/object/other-object checks remain active through this phase. Permanent tests refuse pre-return success and invalidate a return disturbance.
- **R4.2 P2, walking-key cancellation race, resolved:** when a stage's key hold expired, the queued key-up was removed by an abort before native consumption, while heldKeys had already been cleared. The original independent executable probe `/private/tmp/review_desk_key_cancel.cjs` reproduced KeyW still held after abort. The author now retains all task-owned keys in a persistent set and emits every owned release when finishing. Rerunning the original probe confirms KeyW is released. A permanent between-ticks cancellation case passes.
- **R4.3 P2, object boundary continuity, pending:** browser targets checks robot full-body tabletop clearance and object height/tilt, but initially did not irreversibly check the task object's full footprint against the tabletop throughout its path. Final target containment must not erase an earlier object escape. Native qualification already treats its object-boundary violation as permanent. Author notified; final correction review pending.
- The earlier center-only placement and jaw-only release concerns were corrected before this round: final placement uses the actual conservative object geom AABB within the circular coaster/physical tray, and release uses contacts against all robot collision geoms. Prior jaw interaction remains separate evidence. Browser entry now waits for locomotion settling, actual native claw entry and its configured settling interval. Native-key hold duration is bounded and key names are fixed.

### Prepared-model verification

Independently compared actual generated portable assets with the native simulator before the later tray refinement. All 25 named joint initial positions and named body world positions match exactly. Wire qpos/dof addresses, prop body/free-joint addresses, geom sets/local AABBs, remapped jaw identities, scene/model hashes and timestep were checked. Robot mass/inertia remained exact; negligible serialization rounding affected only static mannequin inferred mass and cup mass (+2e-8 kg). The public generated plan remained qualified:false. Proof: `artifacts/review-prepared-model.json`. This proof must be refreshed for the final scene/model; it does not qualify task dynamics or arbitrary model uploads.

### Verification and remaining gates

The shipped Node desk suite and original cancellation probe pass. Five focused Python checks pass with the actual `JUMPER_UPSTREAM` checkout explicitly supplied; the first no-variable attempt correctly failed because the isolated worktree's default sibling upstream path did not exist, then passed after supplying the real pin. No test was skipped or weakened. Actual native/browser task trajectories, seed/abort/loss checks, exact final generated asset comparison and current frozen-source review remain pending. Native and browser return-settle timers should use matching measured-mode acceptance or be disclosed as separate prerequisites. No claim is made from a temporary development-only qualified override; published plans remain disabled until qualification.

**Interim verdict: CHANGES_REQUESTED for R4.3 and final exact-model/browser evidence.** Prior scene-only and audio-only approvals remain separate; the new tray-extension scene itself needs its independent delta review.

---

## Round 4: Independent static scene delta review

Reviewer: `/root/runtime_gate_diagnosis`. **APPROVED, scene-only 5 mm tray-front extension.** This supersedes Round 3's scene input/artifact hashes while retaining its other bounded conclusions; native/browser manipulation qualification remains pending.

Independently loaded old and new imported environments in MuJoCo 3.11.0 and compared named compiled geoms. Exactly `tidy_tray_floor_geom`, `tidy_tray_left_geom` and `tidy_tray_right_geom` changed position/size. New center Y is -0.1725, half-depth .0625: the front moves from -.230 to -.235 while the back stays -.110. Floor top stays z=0; tabletop and all other geoms are unchanged. Friction, contact masks/dimensions, geom types and RGBA are byte-equal across models; all geoms remain opaque, with no constraints or dynamic bodies. Actual tray interior is x=[.130,.310], y=[-.235,-.110]. Documentation correctly separates its geometric center from semantic placement target [.22,-.17].

All 12 new provenance file hashes plus the source scene hash match. Opened the actual new native story and overhead PNGs: layout/readability remains consistent, with a real open-front tray and no hidden support/trick geometry. Existing package-loading reports retain their compile/forward-only scope. New model still has 39 bodies/geoms, nq=nu=neq=0. Fresh skill qualification must use this new exact environment; prior skill results on the old tray are insufficient.

Reviewed SHA256:
- Scene: `f7b1ed014005f2998ec01670a14f7d796569613b413f35878af9c359f1e92167`
- Scene build documentation: `a2edd573457055da32fae593ed0aaa30f06e7f9542b21019708dd0a043e98b77`
- New provenance: `dcb90a8baae046626a64b32b6c2575116f8f8ec5f8405e19798050d2d29350fc`
- Map: `dfa59a34941f1dbaf26205c7c19b6a85353e54372417fa9f364c361d59bceb0b`
- Imported environment: `dafae7067208241a5557da1071653783b0efc11218fb163d2e711ace42ff95e1`

Zero blocking findings in this static delta. No implementation edits, install or publication performed.

---

## Round 5: Independent native contact-physics bucket review

Reviewer: `/root/runtime_gate_diagnosis`. Scope: native simulator additions, manipulation geometry/planning helpers, fixed contact arrays, qualification runner and native tests. **APPROVED for the exact fixed-scene native simulation candidate below.** Overall browser/deployment and general robustness acceptance remain separate.

### Requirements, architecture and actuation safety

No blocking finding. Both props are genuine free bodies: a 45 g hollow empty cup assembled from a bottom plus 16 walls, and a 12 g small spherical cleanup item. The left palm/finger use the pinned upstream five-foot task's convex jaw pieces. Native tests verify original robot masses/inertias exactly unchanged and no added equality constraint. Planning IK modifies separate scratch MjData only. Runtime override accepts finite original-range LF joint targets only, cannot address another leg or object, and passes through the retained 200 Hz controller / 1 kHz physics PD, motor torque-speed and thermal limits. Object positions are initialized only at model/reset; no object parenting, weld, runtime teleport, applied object force, liquid, airborne carry or human handoff is implemented or claimed. Geometry/contact-model changes are explicitly simulation-specific.

### Measured outcome and irreversible failures

Qualification requires actual contact history, meaningful displacement, conservative whole collision-shape containment, release from all robot geometry, low object velocity/spin, supported height, a stable .75 s result, and an actual native KeyV return with at least 2 s in locomotion before that dwell. Cup additionally needs upright posture and measured approach toward the human-context point. Original robot/table margin, tilt, other-object displacement and fallen/invalid state failures are irreversible across the run. Box-corner, sphere-radius and conservative projected-cylinder containment are geometrically valid and never center-only.

Earlier full-shape failures are preserved honestly: cup overshoot and cleanup disturbing the other cup were rejected. The accepted revision adjusts real motion (cup KeyW hold .72 s; cleanup additional KeyS step-back .8 s), without changing targets/start positions or loosening the prior failure thresholds. Candidate qualified flags remain false during this review; enabling requires independent actual browser qualification.

### Independent native execution and tests

Ran the real `qualify()` implementation from `scripts/qualify_desk_skills.py` on the exact new imported environment for both tasks, with an additional read-only instrumentation wrapper around every actual `mujoco.mj_step`. At every substep it asserted zero object generalized/external forces, zero equality constraints, and unchanged object qpos since the preceding integrator output. This catches pose writes outside native integration. Source hashes were compared before/after each audit and were unchanged.

- Cup: completed at 19.25 s; 254 jaw-contact samples; final position `[.0516504,-.3159382,.0499121]`; displacement 60.96 mm; minimum robot tabletop margin 253.27 mm; max robot tilt 9.02 degrees; other object moved 2.04 mm. All final checks true, no permanent failure.
- Cleanup: completed at 27.25 s; 1,442 jaw-contact samples; final position `[.2162565,-.2067551,.0247928]`; displacement 56.43 mm; minimum margin 269.45 mm; max tilt 2.69 degrees; other object moved 12.79 mm. Whole sphere is inside the actual tray bounds; all final checks true, no permanent failure.
- Instrumented accepted runs: 46,500 physics substeps, 93,000 object-force checks, 46,498 object-pose continuity comparisons, all passed.
- Independently aborted both tasks at 10 s: both returned `passed=false`, `outcome=aborted`; neither could earn completion. Additional 20,010 physics substeps / 40,020 object-force checks passed. This checks interrupted evidence, not general physical recovery after cancellation.
- `JUMPER_UPSTREAM=/Users/vivek/projects/clawmetry-jumper-upstream PYTHONPATH=src /Users/vivek/projects/clawmetry-jumper/.venv/bin/python -m pytest -q tests/test_contact_physics.py tests/test_simulator.py`: 6 passed, no skips.
- `node tests/desk_skills_check.cjs`: passed current task evidence/cancellation probes. `git diff --check`: passed.

Independent artifacts: `/private/tmp/mizu-independent-native-final/{proof,cup,cleanup}.json` and `/private/tmp/mizu-independent-native-abort/{proof,cup,cleanup}.json`. The transient audit scripts are outside tracked source. Exact compiled model SHA256 is `a2ce17a45cd1664461ea09104f49b97f2cd75dceb470613f1af76bf665a3c0b8`, imported environment `dafae7067208241a5557da1071653783b0efc11218fb163d2e711ace42ff95e1`, upstream `78966f45de6f2b6de3f7cea017f32a39f8b993e6`.

### Source hashes

- `src/clawmetry_jumper/simulator.py`: `91fa7fb424d139b85876957dac982e5539340da8343383d2930a3e758c04ef16`
- `src/clawmetry_jumper/manipulation.py`: `0a99d83595450b29bda02b45d61362d868b532f53d823736f92d86ec378dadbf`
- `src/clawmetry_jumper/contact_plans.py`: `162f4e712999a44e87be8575da8ccd55c288b8f8532bbaff2bb4dc0117834631`
- `scripts/qualify_desk_skills.py`: `de414b9af0f87e825c1ac9626eb803932e682bee137ff8c53e1cabbce6ee052e`
- `tests/test_contact_physics.py`: `1f13da60f22dabea63c833cf89c9a09fd43afe62a37aae6748e6ed8494983c4a`

### Limits and verdict

**APPROVED, bounded native contact-only simulation bucket; zero blocking findings.** This establishes two exact nominal scene tasks and honest interrupted outcomes, not arbitrary starting poses, unrestricted task planning, seed/entry-time robustness, airborne grasp/cup carrying, liquid delivery, human detection, containment guarantees or hardware operation. Author's ongoing entry-time/offset matrix and actual WASM/browser task runs remain required before broader claims or UI enablement. No merge, install or publication performed.

---

## Round 6: Final guarded browser-task source review

Reviewer: `/root/cloud_guard_review`. Scope is the root-authored browser task monitor, simulation integration and prepared-asset mapping, with the reviewed source hashes below. Scene authorship remains excluded from this independent approval. No implementation edits, installed package changes or publication by this reviewer.

### Final findings and corrections

All three findings from the browser-source Round 4 are resolved. Success remains under monitoring through actual native return, two seconds of locomotion and another 0.75 seconds of released placement. Task-owned walking keys retain persistent ownership until cancellation releases them, including the independently reproduced between-ticks key-up race. The object's full measured footprint is checked against the desk irreversibly during the whole task. Original cancellation probe now releases KeyW; private probes confirm object-edge/robot-edge failure and observation-loss unknown outcomes cannot later recover into success.

Target containment is based on actual primitive geometry. Circle checking uses sphere radius, a conservative cylinder disk/projected half-height bound and each actual wall's oriented containing-box corners; it does not invent material in the empty aggregate-AABB corners of the hollow cup. Sphere bounds are orientation invariant. The physical tray containment center can differ from the semantic target, preserving the asymmetric front extension. Release requires no contact against any robot collision geom, while prior jaw interaction remains separately required. Disturbance and other-object movement abort the active task. Scripted arm commands remain bounded original-joint targets with native support/walking input; no prop teleport, constraint, applied prop force or hardware control is added by the reviewed browser files.

### Independent verification

- Shipped Node desk suite passes, including contact/release, geometry overhang, no-contact failure, cancellation, native return disturbance, bounded walking hold, persistent walking release, sphere orientation and asymmetric tray center cases.
- Five focused Python desk/audio/notice checks pass with the real pinned upstream explicitly supplied. `git diff --check` passes.
- Independent geometry comparison sampled actual MuJoCo cylinder/box/sphere surfaces in 80 object cases; no false containment results occurred. Positive cases included 20 cup poses and 33 cleanup poses, alongside rotated/outside cases. Proof: `artifacts/review-object-geometry.json` and `/private/tmp/review_desk_geometry.cjs`.
- Refreshed final-tray portable/native comparison verifies every one of 25 named joint initial values, all named body positions, original robot mass/inertia, wire/dof mappings, prop body/free-joint mappings, geom/local-AABB sets, jaw identities, scene/model hashes and 1 ms timestep. Initial joint/body pose errors are zero. Only negligible serialization rounding affects static inferred masses and cup mass (+2e-8 kg). Proof: `artifacts/review-prepared-model-trayextend.json`; prepared model SHA9430e34190c1ff8061b3e80f6164ec78c20d35d8f65ba956993f7e1be12d1184.
- Re-read the current native qualifier: measured locomotion return_at, two seconds of waiting and a fresh 0.75-second stable interval now match the browser acceptance intent. Native trajectory/seed acceptance is separately reviewed; these source checks do not establish identical browser dynamics.

### Scope and delivery boundary

**APPROVED for the reviewed guarded browser-source and asset-address mapping bucket.** Zero remaining blocking or advisory source findings in this scope. The generated public configuration inspected here still has both task flags qualified:false; no temporary development override is a delivery claim. Enabling an exact final plan/config and publishing it still require its actual native and browser success/failure/abort/loss qualification, exact artifact/provenance matching, full UI/lifecycle verification and parent delivery review. This source verdict does not approve a stale generated task plan, simulator hardware behavior, full manipulation work order, scene authored by this reviewer, merge or deployment.

Reviewed SHA256:

- `web/manipulation.js`: `fcb3437413b665cc180db3f322a55ea86978fc5c4952363e5677883b7de29d16`
- `web/simulation.js`: `f12d0343d2753480aef28788da6d2571b898a01b9277c3408d90d341886791b3`
- `scripts/prepare_web_assets.py`: `7c7e41778e71195d2d88f73fb6cf84051729723f009e52a04961c32e74ae8f2c`
- `tests/desk_skills_check.cjs`: `ed2b176bd958f2fd5a35e42296134b387d00f73f8013dbeefd5c9263a0c88127`
- `tests/test_desk_skills.py`: `2e9b2d9594fd93b320ed5427719b3c8965f6e894fc567b90297ea04403e68cab`

---

## Round 7: Browser-source narrow follow-up

Reviewer: `/root/cloud_guard_review`. During the Round 6 record handoff, two root-owned files received a narrow additive correction: source task mode transitions now retain the active skill request ID; pickup gating now honors separately declared tight XY/reset-height tolerance, and sphere-like cleanup plans can explicitly omit an upright-axis requirement. Read the complete current files and these changes. They preserve prior containment, whole-path failure, key ownership and after-return gates. Re-ran the shipped desk suite, original key-release race probe, irreversible object/robot edge and observation-loss probes, and 80-case primitive containment comparison: all pass. No implementation edits by reviewer.

**APPROVED for this source delta under the same Round 6 boundary.** Actual task enablement/publication still requires exact frozen configuration and native/browser qualification; this does not certify a development override or a stale plan. Final reviewed source copies and hash inventory are retained at `artifacts/review-web-source-final/`.

Current reviewed SHA256:

- `web/manipulation.js`: `6c03a4355d783b20ea57fefcea13aac98a1b44f9fd6ab0600c1773fe0ed5e6a4`
- `web/simulation.js`: `9116dc28aa39d1d5193bc43c45a3ae9cee9f8c69b0899dc2e5043341faafe26c`
- `scripts/prepare_web_assets.py`: `7c7e41778e71195d2d88f73fb6cf84051729723f009e52a04961c32e74ae8f2c`
- `tests/desk_skills_check.cjs`: `ed2b176bd958f2fd5a35e42296134b387d00f73f8013dbeefd5c9263a0c88127`
- `tests/test_desk_skills.py`: `2e9b2d9594fd93b320ed5427719b3c8965f6e894fc567b90297ea04403e68cab`

---

## Round 8: Fresh-scene task helper review, interim

Reviewer: `/root/cloud_guard_review`. Scope is the new root-owned app startObjectTask helper and its direct request entry conditions. Prior root-source approvals apply only to their recorded hashes; this new helper is reviewed separately.

**Blocking R8.1 P2:** the helper checks engine.skills.active but not engine.activeRequest. A legitimate active wave/bow can therefore be reset and replaced by an object task, contrary to the requested overlap/no-reset-during-task policy. Independently reproduced by executing the actual helper text: an engine with activeRequest=wave produced sceneResets=1, requests=1 and allowed=true. Probe: `/private/tmp/review_fresh_scene_helper.cjs`. Guard both action types before pausing and again after the drain before any reset; decline without altering the scene.

The captured engine/generation/pageClosed checks correctly prevent a retired page from resetting a replacement instance after draining a busy step. taskStarting serializes normal UI starts; direct request rejects aged scenes. The explicit fresh-scene copy and retained episode evidence correctly disclose/reset the fixed initial condition. An advisory asks for a durable per-episode reuse marker instead of searching bounded event history. Final deferred-overlap/pagehide/active-gesture/fresh-reset tests and current nominal browser proof remain pending.

**Interim verdict: CHANGES_REQUESTED for R8.1.** No implementation edits by reviewer.

---

## Round 9: Native metadata, documentation and evidence-binding follow-up

Reviewer: `/root/runtime_gate_diagnosis`. **APPROVED, bounded extension of Round 5's native simulation bucket.** No implementation edits by reviewer.

The current contact plans differ from the independently instrumented accepted motions only by pickup admission metadata: cup XY tolerance 1.5 mm, cleanup XY .5 mm, and separate Z settling tolerance 12 mm. Every joint array, stage duration and native key/timing is exactly equal to the previously reviewed arrays. The physical model, targets and starts are unchanged. Narrower admission is not a success guarantee; runtime measurement remains required.

Reviewed `docs/native-contact-qualification.md`: numeric nominal measurements match actual records, the 45 g hollow cup / 12 g spherical cleanup item and exact tray bounds are described correctly, scratch IK is distinguished from live state edits, and contact-guided sliding is not presented as airborne carry/hardware/handoff. Cleanup's failed +1 mm X perturbation is retained explicitly. The document separates native results from the root-owned announced fresh-scene browser lifecycle and hosted acceptance. It makes no general autonomous cleanup claim.

Found an evidence-binding uncertainty during review: older incremental-edit timing artifacts cited an on-disk qualifier hash that could not substantiate immutable executed-module identity. The author resolved this by rerunning all four timing cases, both +1 mm offsets, and held-W abort on the frozen current qualifier, and marking every older case research-only with `reported_disk_source_sha256` and an explicit insufficient executed-source-binding status. No old uncertain case is used as acceptance.

Independently verified all nine `current_frozen_evidence` artifact SHA values and all five execution-source bindings against actual current files. Nominal cup/cleanup, both ±1-control-tick cases, and cup +1 mm pass with complete final checks; cleanup +1 mm still fails `other_unchanged` and full target containment. Held-W abort is nonpassed/aborted and its final measurement follows the key release at 12.01 s. Current nominal results are identical to the independent Round 5 instrumented nominal run. Final index SHA256: `6cad8fce2a96a2049b927a311314913c9421b48fd6fc95c8eef34fcb60cd1387` at `/private/tmp/mizu-desk-contact/qualification-index.json`. Nine split-jaw mesh hashes are included in current input provenance.

Additional actual native geometry tests: `JUMPER_UPSTREAM=/Users/vivek/projects/clawmetry-jumper-upstream PYTHONPATH=src /Users/vivek/projects/clawmetry-jumper/.venv/bin/python -m pytest -q tests/test_contact_geometry.py` — 2 passed, no skips. Earlier independently passed six simulator/model tests and substep force/pose audit remain applicable because model, override implementation and motion arrays are unchanged.

Reviewed SHA256:
- `src/clawmetry_jumper/contact_plans.py`: `3b94390a2f14354299031b94e5ba0c0dbe42e83080e5dc3efdd20312104d7dea`
- `scripts/qualify_desk_skills.py`: `8b62ae563d441d5818f10ee67bcbe228a115dc4adb8072e2cba9cada8fff0f43`
- `scripts/plan_desk_skills.py`: `cd851121a9419e892742ce2f2ef8588de53ea4448823e8cccf286f5b45a90ba0`
- `docs/native-contact-qualification.md`: `00a51808d003b8cb07f17b34f3f4dec445a8ad3f941dc389faae9dbd0f4a754b`
- `tests/test_contact_geometry.py`: `a17e7f64b33a8534cbe4f6ed9908355a8a483a5f228ae9f5060cc2e2e30601ab`

Zero unresolved blocking findings in this native metadata/docs bucket. Root-owned browser fresh-scene/overlap/cancellation behavior, release, hosting, hardware, arbitrary starting poses and general manipulation remain separate gates. No merge, installation or publication performed.

---

## Round 10: Fresh-scene lifecycle and exact delivery enablement

Reviewer: `/root/cloud_guard_review`. **APPROVED for the root-owned browser task/lifecycle, portable model mapping and certificate enablement bucket.** No implementation edits by reviewer. Static scene is separately reviewed by `/root/runtime_gate_diagnosis`; this verdict does not self-approve my scene authorship.

Round 8's active-greeting reset blocker is resolved: both existing object tasks and wave/bow requests are checked before pausing and after inference drains, with no reset on overlap. The captured engine/generation and page-close checks prevent a retired helper from resetting a replacement page; hidden pages stay paused. The durable per-episode acceptance boolean replaces the bounded-event reuse check. Independently executed the actual helper with deferred busy steps: active greeting, late overlap, concurrent start, retired generation, closed page and hidden page all pass. Permanent fresh-scene tests cover these paths. Direct engine entry refuses aged/reused scenes. The UI explicitly announces that each object task starts a fresh scene; previous episode evidence remains available.

A final enablement P2 was found and corrected before approval: native templates could previously retain qualified:true when a qualification record was absent. `enable_desk_plans` now clears all flags before checking the exact record and enables only its verified cup/cleanup actions; the regression deliberately begins with true flags and no record. Missing records also remove a stale generated certificate. Source/model drift fails before public configuration is emitted. All eight recorded source hashes match the actual files. Both native report hashes and both initial browser evidence hashes match their actual retained files. The latter are development qualification evidence, not confused with the subsequent public-flow acceptance.

Read the current full browser harness and inspected its completed actual Chromium report at `artifacts/useful-desk-browser/full-acceptance/browser-report.json` (SHA256 `dbea9fedea7a4819525513aa453a23abd7215d716579102d8e79e91dc7ecff38`): 14 cases, passed:true and zero JavaScript errors. The harness uses generated qualified configuration and the actual public fresh-scene helper, with no flag overrides. It starts from an aged scene, checks overlap without reset, both measured placements/contact history, actual native locomotion return, another five seconds of stable containment, retained old episodes, repeat rejection, cancellation and observation loss during a held native walking input, ordinary gestures/unknown outcomes, opt-in assets, desktop/mobile and disposal/paused rendering. Inspected cup, cleanup and 390 px mobile screenshots. Cup completed at about 19.275 s with 6.16 cm displacement; cleanup at about 27.275 s with 5.78 cm displacement. Both remained contained after the extra five seconds. These are measured scripted contact-guided slides in the fixed scene.

Independent targeted reruns: shipped desk and fresh-scene Node suites, original deferred helper probe, original between-ticks held-key cancellation probe, and four Python fresh-scene/desk/portable-reset tests all pass. `git diff --check` is clean. Prior 80-pose primitive geometry/model address checks and whole-run fail/unknown probes apply to the unchanged reviewed geometry/skill implementation.

Delivery artifact note: during this review the existing generated `web/assets/desk-skill-qualification.json` still held the pre-final preparer hash. The current source resource and model bindings are correct; parent was notified to regenerate the normal asset package and manifest before delivery. This does not change physics or the browser runtime source, but the generated certificate must match before packaging. This source verdict is not merge/deployment approval.

Known limits remain explicit: cleanup failed a 1 mm reset perturbation and an arbitrary delayed start. Only the announced canonical fresh-scene flow is qualified. No generalized autonomous manipulation, airborne carry, liquid handling, human recognition, hardware safety or actual phone delivery is established. Native task motion and scene have their own separate approvals.

Frozen reviewed SHA256:

- `web/app.js`: `43810ef84d3f4ad08263321c45d24618edd3378b543d49a95111074edb29369f`
- `web/simulation.js`: `0f26bee727ebb9c7abc091949d15472d88a724294a59dc30f6e588bcee544ba5`
- `web/manipulation.js`: `6c03a4355d783b20ea57fefcea13aac98a1b44f9fd6ab0600c1773fe0ed5e6a4`
- `scripts/prepare_web_assets.py`: `c8323986163a8bfa2f0d45c935ef2fd16e44df909630549117fbef7808577cf4`
- `resources/desk-skill-qualification.json`: `7d4f7489bfef78a37a4a2065e984750183128bd64b47574b5f78e23ffd02db7e`
- `tests/fresh_scene_check.cjs`: `1cfe08bf9935461c70e3d199900983dabc1e17e776ee970afb1cbf1833b79578`
- `tests/test_portable_reset.py`: `dc38ba142ad73c630132f0f49d7178f4dda6305f88ac4769afd32de031e977dd`
- `web/tests/browser_acceptance.py`: `af328ae9f02fc06c464ce7ff59e795d1aa0279466fbc5acc7b607a836746afbc`

## Round 11: Parent integration audit

Canonical fresh-scene contact scope reviewed after independent native, scene, audio, lifecycle and guarded browser buckets. Full actual Chromium report at `artifacts/useful-desk-browser/full-acceptance/browser-report.json`: passed, zero page errors, both placements and five-second post-return stability, cancellation/unknown loss, gesture/fault/privacy/mobile/lifecycle checks. Python suite: 52 passed, one pre-existing worktree-path CLI skip; author separately exercised that exact actual 32-second recording contract successfully. No general manipulation/hardware claim. All reviewed source buckets are APPROVED. Source packaging APPROVED; regenerate the copied qualification record/manifest, then obtain current-head source CI and normal landing/native deployment gates. Whole delivery is not yet complete.
