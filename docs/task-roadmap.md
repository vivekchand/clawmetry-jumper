# Desk companion task roadmap

The product idea is a companion that supports sip, move and tidy without taking over the desk. Its default is to be quiet. Reminders can be skipped. A task grants only the specific movement, object and workspace permission it needs. A long work session is not blanket permission to move objects.

This document separates source capabilities, this demo's required proof and future skills. It makes no claim that the acceptance runs below have already passed.

## What the pinned upstream actually supplies

Inspection used clean upstream commit `78966f45de6f2b6de3f7cea017f32a39f8b993e6` in the independent Jumper checkout. The main [manifest](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/deploy/manifests.json) includes posture locomotion, jump, claw modes and four greeting-style gestures. Exported policies and native controller contracts are useful starting points. Availability is distinct from passing a replay in this demo and scene.

| Capability | Source evidence | What it establishes |
|---|---|---|
| Arm and claw control | [five-foot controls](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/tasks/jumper/five_foot/controls.yaml), [native deploy hook](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/tasks/jumper/five_foot/deploy/lib.rs) | A five-leg locomotion policy supports a carried arm. Presets and operator input drive the arm and finger. The policy is not an autonomous object-picking skill. |
| Contact-based object experiments | [grasp harness](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/tasks/jumper/five_foot/tools/grasp_objects.py), [object scene](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/tasks/jumper/five_foot/objects.py) | Real simulation scaffolding exists for frictional grip, lift, shoulder swing, release, a negative control and reset. The props include a can, notebook and soap. This is more than a decorative opening claw. |
| Limits of that evidence | [five-foot measurements](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/tasks/jumper/five_foot/README.md), [grasp setup](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/tasks/jumper/five_foot/mdp/grasp.py) | The harness initially seats a prop at the mouth. Current stowed-arm geometry is documented as failing the three prop grasps; earlier grasp-ready successes concern an older pose. A prepositioned contact test is not approach, grasp and delivery from a desk. |
| Standalone playback caveat | [plain MuJoCo pick/place tool](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/tasks/jumper/five_foot/tools/pick_place.py) | Its own documentation reports a closed-loop walking discrepancy despite component comparisons. Reusing it does not establish reliable transport. Reproduce and resolve the relevant behavior before depending on it. |

These are source inspection findings, not fresh results from running the upstream grasp harness. No new grasp, carrying or payload performance is asserted here.

## Stage 1: a pleasant companion with a small job

Record genuine native MuJoCo playback on one finite desk. Use the upstream model and controller and a calm visual palette. Start with one locally qualified greeting gesture and quiet reminders. Do not require locomotion to communicate a reminder.

| User task | Initial behavior | Required evidence |
|---|---|---|
| “Remind me to stretch.” | Preview one gesture, allow or skip, then return to settled stance. | The requested skill matches the task, controller entry is recorded, playback remains within the designated zone and the run completes without a fall. |
| “Remind me to drink.” | A quiet sip prompt near a stationary cup. | Reminder event and acknowledgement or skip. No inference that a person drank and no claim the robot brought the cup. |
| “Help me finish work.” | Offer a one-object tidy task for later consent. Initially a reminder only. | Show exactly what would move and where. Task is not marked physically complete from a displayed prompt. |
| Unrelated jump request | Deny it before forwarding to the native controller during the reminder task. | Immutable request, reason, denial and subsequent recorded controller mode. Continuous physics remains running. |
| Observation unavailable | Decline new action requests and report evidence unavailable. | Freshness and missing samples visible. The physical outcome remains unknown until observations recover. |

For the first filming pass, fixed tabletop containment is an acceptance criterion, not an assumed property of a pretrained gait. For full qualification, measure the complete collision footprint and the minimum margin to each approved boundary at every physics substep. The present official replay samples the completed 200 Hz control steps; its report does not claim 1 kHz boundary measurements. Also record tilt, support/contact state, unexpected translation and falls. Report the minimum margin and violations over the full run. A zero velocity command, a green overlay or an action denial alone cannot prove containment. Avoid any action whose measured motion cannot fit comfortably in the chosen zone.

## Stage 2: prove one object movement

Begin with a lightweight, rigid, empty vessel or a notebook, in a fixed known pose, with a reachable tray. Keep both source and destination inside the same desk zone. This is an engineering proposal derived from the source limits, not an existing upstream deliver-water capability.

1. Validate actual collision meshes and grasp aperture for that exact object. Reproduce contact-only grip with no weld, hidden attachment or pose reset during the measured attempt. Log any initialization that prepositions the object.
2. Test reach, finger closing, lift and placement separately before composing them. Check stable five-foot support, joint/torque limits and clearance for the whole swept arm, not just the target pose.
3. Add an approach or demonstrated trajectory that starts with the object resting freely on the desk. A trained task policy or an explicitly scripted controller sequence may be used, but label which is doing the work. Language task selection is not a replacement for either.
4. Measure object pose and velocity, grip contacts, lift, slip, orientation, release, final destination and post-release settling. Do not count a prop still trapped in the claw as placed. Retain all attempts, including failures.
5. Perturb object position, orientation, mass and friction within declared bounds. Test a missing object, a blocked destination, grasp slip and stale observation. Report the tested range and actual counts rather than assigning an unsupported reliability percentage.
6. Compare the same initialized attempts with permitted and denied requests. Verify that denial prevents forwarding while leaving the native low-level controller and physics intact. Include task expiry and duplicate requests.

Success means the approved object starts freely on the desk, is acquired by contact, reaches the approved target, is released and settles within an explicitly defined tolerance, while the robot remains in its designated zone. Set tolerances from object geometry and simulator resolution before the evaluation batch. Record them with the results. A simulation cup contains no validated liquid model; an upright rigid vessel is not spill-free water delivery.

## Stage 3: sip, move and tidy as distinct skills

| Direction | Next useful skill | Additional work before claiming it |
|---|---|---|
| Sip | Place one empty vessel on an agreed coaster inside the workspace. | Reliable grasp and release, object pose, stable support and collision checks. Later water handling adds changing load, spill and breakage concerns. A rigid can model does not establish them. |
| Move | A locally qualified invitation gesture, followed by quiet waiting. | Measure acceptance, skip and interruption rates. Do not treat posture or elapsed time as proof of human fatigue or health benefit. |
| Tidy | Move one named notebook to one named tray after work. | Object-specific acquisition, destination verification and exclusion of other objects. Start with a rigid notebook rather than loose paper. |
| Later tidy | Put a pen in its holder, then consider loose paper. | A small cylindrical pen needs suitable grasp geometry; thin flexible sheets require a different model and manipulation strategy. A generic “clear my desk” task is too broad. |

The original [Mizu demonstration](https://www.linkedin.com/feed/update/urn:li:activity:7513599170314928130/) supplies the use-case inspiration. Its SO-101 skills do not transfer automatically to Jumper. One visible comment suggests previewing the next action and measuring interruptions; use that as a future interaction experiment, not as established safety evidence.

## Task permission contract

This is a proposed contract for future task composition. Each permission should contain:

- A stable task ID, explicit allowed skill IDs and one named object when relevant.
- Source and destination zones, a bounded tabletop workspace, expiry and any movement or force limits established by testing.
- A next-action preview and an explicit consent state. `Skip`, `Snooze` and `End task` must not silently become consent.
- A unique action request ID, parent task ID and current observation timestamp. Reject malformed, expired, duplicate or out-of-scope requests before forwarding.
- Separate receipt fields for permission decision, native controller acknowledgement and measured outcome. An accepted request does not mean successful execution.
- A completion criterion, timeout and recovery behavior validated for that skill. On missing telemetry, report unknown. On an object slipping, do not improvise a new grasp or expand the workspace without permission.

“Stay on this tabletop” applies to the robot's complete footprint and motion. A future boundary intervention must account for speed, control delay, support geometry and stopping distance. Filtering new requests is useful, but it does not guarantee that a moving robot cannot drift or fall. No generic software stop should replace the low-level stabilization needed by a moving or airborne machine.

## Validation and claims ledger

For each run retain the pinned source and asset hashes, policy/controller versions, scene and object parameters, seed, task/decision/acknowledgement events, continuous state samples and uncut footage. Publish a compact report with attempted count, completed count, failures, unavailable outcomes, boundary violations, object drops and timing. Never discard failed attempts to improve the reported rate.

The first release can truthfully describe an open-source Mizu demo using built-in ClawMetry observation and task governance only after its own checks pass. Later captions may claim the exact object movement actually demonstrated. Hardware capability requires a separate controlled evaluation; simulator contact, a rendered calm skin and cross-runtime reference agreement do not establish real-world object handling or human safety.
