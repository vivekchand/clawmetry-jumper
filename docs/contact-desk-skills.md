# Contact-guided desk tasks

The optional browser desk model adds an empty rigid cup and a small rigid sphere
that represents a paper ball. These bodies have free joints. Contact and gravity
move them. There is no liquid, flexible paper, human handoff or physical robot
qualification.

The official Jumper five-foot controller supports the robot. A bounded scripted
joint controller moves only the original five left-claw joints, with the original
joint limits, torque-speed curve and thermal limits. One stage can send a timed
native walking key. The scripted arrays are specific to this scene and starting
state. They are not an autonomous grasp policy or general cleanup capability.

Each object-task button explicitly starts a fresh episode before the request. It
waits for native support to settle, then executes the qualified fixed-scene
script. No reset occurs during an active task, and previous evidence stays in
the session. Delayed arbitrary-state requests are not supported: cleanup failed
a five-second delayed start and a 1 mm reset perturbation in qualification.

The two intended tasks are to slide the empty cup toward the seated person onto
its coaster, and guide the one named paper-ball proxy into the open tray. Neither
uses an airborne pickup. The source plans stay disabled until native and actual
browser physics pass the same placement conditions and independent review.

## What completion means

A request, permission, controller input and physical outcome are separate events.
Time finishing a trajectory is not a successful task. The monitor requires:

- Measured object movement of at least 5 cm, with observed claw contacts.
- For the cup, at least 3 cm less distance to the seated person's hand reference.
- The entire object footprint within the coaster or tray, including the actual
  rotated wall boxes and sphere radius, rather than the object's center alone.
- Release from all robot geometry, upright cup, low object speed and spin, and
  a resting height consistent with the tabletop.
- Native return to locomotion, at least two seconds of monitored return, then
  another 0.75 seconds of stable placement.
- No earlier table-boundary violation, invalid state, excess robot or cup tilt,
  or unintended movement of the other task object.

Interruption, cancellation, invalid geometry or lost observations produces a
failed, interrupted or unknown result. It cannot become success merely because
the object later appears near its target. Physics continues after an aborted
script. Browser pause is not a physical robot stop.

## Reproduction and evidence

Prepare the official scene as described in [scene-build.md](scene-build.md), then
run `scripts/qualify_desk_skills.py` with the pinned upstream checkout, imported
scene XML, action and a new output file. The runner preserves source/model hashes,
initial conditions, exact joint arrays, contacts, whole-run failures and measured
return. It refuses to overwrite a previous result. Development reset offsets are
explicit initial conditions, not runtime object movement.

`web/tests/browser_acceptance.py` exercises the exported portable model in actual
MuJoCo WebAssembly. Native acceptance is a prerequisite; it cannot substitute for
browser rollout because contacts can diverge across runtimes. Keep failed runs
with the successful evidence and document the supported starting conditions.
