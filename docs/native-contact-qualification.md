# Native contact task qualification

This record covers a fixed-scene simulation experiment. It does not establish
hardware manipulation, liquid handling, a human handoff, arbitrary object
pickup, or autonomous desk cleaning. The cup and round desk item are free
MuJoCo bodies. Their only applied forces are gravity and simulated contacts.
The robot uses its original floating base, inertias, motor torque/speed curve
and thermal limits. Scripted LF joint PD targets augment the official native
five-foot support policy; short forward/backward inputs go through the same
official controller. No object weld, pose attachment, carry teleport or hidden
object force is used.

## Frozen environment and model

Build the official environment using [scene-build.md](scene-build.md). The
qualification scene is the imported front-extended tray revision. Its official
map SHA256 is `dfa59a34941f1dbaf26205c7c19b6a85353e54372417fa9f364c361d59bceb0b`.
The pinned unchanged upstream Jumper commit is
`78966f45de6f2b6de3f7cea017f32a39f8b993e6`. Native tests use MuJoCo 3.11.0.

The host creates an empty 45 g hollow cup from one bottom cylinder and sixteen
rigid wall boxes, approximately 50 mm wide and 100 mm tall. Its initial center
is `[0.05,-0.255,0.051]` m. The 12 g cleanup item is a 25 mm radius rigid sphere
at `[0.18,-0.25,0.026]` m. The retained internal ID `cleanup_block` is not a claim
that the current object is a box. A sphere has no upright orientation.

The actual split collision jaws are the pinned upstream task's six palm and
three finger pieces. The former single convex hull filled the jaw opening.
The original explicit robot masses/inertias remain unchanged. These nine newly
consumed mesh files are included in the run's input hash inventory.

`simulator.compiled_xml` is the exact composed XML, including props, jaws and
environment. The accepted local composed XML SHA256 is
`a2ce17a45cd1664461ea09104f49b97f2cd75dceb470613f1af76bf665a3c0b8`.
This XML contains resolved local resource paths, so another checkout may have
a different byte digest despite equivalent pinned resources. The portable web
export has its own separately recorded XML and resource hashes.

## Acceptance conditions

Permission and elapsed time cannot establish completion. A completed run must
finish all scripted stages, actually return to native `locomotion`, wait two
seconds there, then satisfy all placement checks for another 0.75 seconds.
The object must move at least 50 mm from its initial center, fit completely
inside its physical target, be released from every robot collision geom,
rest near its initial height, and have low linear/angular speed. At least two
earlier jaw-contact samples are required. The cup must finish within 12 degrees
of upright and at least 30 mm nearer the owner's static hand-context point
`[-0.13,-0.66]` m. The model has no human recognition or handoff detector.

The cup's circle target is centered `[0.06,-0.31]`, radius 48 mm. Whole-shape
containment checks the actual wall-box corners and a conservative projected
bottom-cylinder bound. The cleanup target's actual interior bounds are
`x=[0.130,0.310]`, `y=[-0.235,-0.110]`; its semantic center remains
`[0.22,-0.17]`. Sphere bounds use its true orientation-independent radius.

Boundary loss, invalid/fallen state, excessive robot tilt, or more than 15 mm
motion of the nonselected prop permanently fails the native run. A cup tipping
beyond 30 degrees also fails permanently. Native qualification conservatively
requires more than 80 mm tabletop margin and less than 15 degrees robot tilt.
The room floor never counts as tabletop containment. Cancellation returns an
aborted result even if a transient target condition happened earlier.

## Measured native results

The two accepted nominal runs use the same final model and exact serialized
joint arrays. Cup forward input is held for 0.72 seconds during its slide.
Cleanup finishes with 0.8 seconds of backward native input before mode return,
keeping the returning LF limb away from the other cup.

| Nominal task | Final displacement | Target-center error | Maximum robot tilt | Minimum table margin | Other prop motion |
|---|---:|---:|---:|---:|---:|
| Empty cup toward owner | 60.96 mm | 10.25 mm | 9.02 degrees | 253.27 mm | 2.04 mm |
| Round desk item into tray | 56.43 mm | 36.95 mm | 2.69 degrees | 269.45 mm | 12.79 mm |

Both finish released and fully contained after native return and the stable
dwell. The cup is 54.13 mm nearer the hand-context point and finishes nearly
upright. Repeated nominal runs reproduce the result. Both skills also pass
native-entry timing shifted by minus/plus one 5 ms control tick. A cup start
shifted +1 mm in X passes. A cleanup start shifted +1 mm in X fails target and
other-object checks. That negative result is retained: cleanup remains a narrow
known-scene script, not a robust general placement policy. Abort while walking
is held releases the key and reports aborted, without claiming containment or
a completed placement.

The browser integration therefore starts a clearly announced fresh scene for
each object task and retains previous episode evidence. It does not reset a
running task or silently move a prop into reach. Direct late/reused-state task
requests are rejected. Pickup XY admissibility is 1.5 mm for the cup and 0.5 mm
for cleanup, with a separate 12 mm height-settling tolerance; those gates are
not success guarantees. Every run still needs measured completion.

Earlier grasp/retreat and incomplete-placement attempts failed. In particular,
an unreachable scripted retreat could tip an already placed cup; a direct
cleanup mode return could disturb the other cup. Neither is in the accepted
plan. Failed attempts do not become positive evidence by later recovery.

## Reproduce

Install the demo's simulator extras and use a clean pinned upstream checkout.
Use fresh output paths: the scripts refuse to overwrite prior evidence.

```sh
python scripts/plan_desk_skills.py \
  --upstream ../clawmetry-jumper-upstream \
  --scene artifacts/useful-desk-scene-trayextend/imported/scene.xml \
  --action cup --output artifacts/cup-new-candidate.json
python scripts/qualify_desk_skills.py \
  --upstream ../clawmetry-jumper-upstream \
  --scene artifacts/useful-desk-scene-trayextend/imported/scene.xml \
  --action cup --output artifacts/cup-new-qualification.json
```

Use `--action cleanup` for the other task. The planner performs IK on separate
scratch `MjData`; it does not move live objects by assigning their poses. The
qualifier replays the committed arrays independently and records initial qpos,
model/scene/input/source hashes, per-stage measurements, bounded-rate history,
whole-run extrema and permanent failures. Additional checks are
`--entry-tick-offset -1`, `--entry-tick-offset 1`, `--offset .001 0`, and
`--abort-at 12`. Perturbation failure exits nonzero and is expected where the
known-scene conditions are exceeded.

Native results are separate from actual browser/WASM qualification and public
deployment. The runtime still requires observed success on every invocation;
neither this record nor a `qualified` flag grants success to a failed run.
