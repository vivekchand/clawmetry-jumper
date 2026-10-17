# Native Jumper playback notes

Upstream source: KingKongRobotics/jumper at
`78966f45de6f2b6de3f7cea017f32a39f8b993e6`. The bundled native controller
records build commit `ce71f79b191766f0208dca34516564a37816c729`.

The standalone host is `src/clawmetry_jumper/simulator.py`. It imports native
MuJoCo, NumPy and ONNX Runtime, plus the bundle's platform-specific `mjrl_fsm`
extension. It does not import the upstream training stack. This minimal playback
environment has not passed the upstream training/deployment setup gates.

## Verified controller protocol

- The macOS universal2 ABI3 extension loads on this arm64 Mac. A fresh controller's
  `check_reference(reference.json)` reports 24 frames, 18 inferences, observation
  error 0, target error 0 and no mode mismatches or divergent terms.
- The controller constructor takes TOML text, a map of contract JSON texts,
  a robot facts dictionary and a map of trajectory JSON texts. All 12 modes load.
- Upstream's reference-check command is
  `python scripts/deploy.py --check-reference out/bundle_example/jumper`.
  It depends on that repository's environment. This standalone host exposes
  `JumperSimulator(...).verify_reference()` without importing training packages.
- Reference replay mutates its controller. Verification therefore creates a
  separate fresh controller; reset creates another for the actual episode.
- The host ticks at 200 Hz and integrates physics at 1 kHz. `tick(now_us)` returns
  a mode only when inference is due. Feed that mode's ONNX raw float32 observation
  `[1, observation_dim]` and call `resume(action)` once. Every tick publishes
  `positions()`, `kp()` and `kd()`, including ramps and holds.
- Wire arrays contain all 22 named joints. Policies can drive 20; grippers at
  wire indices 4 and 9 are held. Never use policy index as MuJoCo joint index.
- Inputs are joint radians, rad/s, applied PD torque, body quaternion `(w,x,y,z)`
  and body-frame gyro. MuJoCo's `imu_ang_vel` and `imu_lin_vel` sensors provide
  body-frame rates. Rotate the latter by the base rotation for world velocity.
- `set_pad_frame([], {}, connected=False, now_us=...)` is still required each
  tick without a pad; this refreshes operator presence. Otherwise the 500 ms
  command timeout forgets latched gestures.
- `key_1` down then up requests hello; `key_2` bow, `key_3` paw, `key_4` salute.
  The hello recording lasts 7.32 s and starts after the measured switch-in ramp.
  `key_space` requests jump. Ctrl release leaves a recording early.

## Physics and rendering

Reset initializes the free base at the locomotion contract's `base_init_pos`,
`[0,0,0.10647]` m, identity quaternion, and every joint at its named home pose.
Only reset writes qpos. Subsequent poses result from integrated dynamics.

The original MJCF has no ground or actuators. The host adds a desk with top at
z=0 and applies PD torque through named `qfrc_applied` degrees of freedom every
physics substep. Decorative monitor, notebook and water-glass props sit outside
the initial robot work area. They are noncolliding visual context, not simulated
manipulation targets. The robot's mint/sage skin changes visual RGBA only.

Collision selection, leg bitmasks, silicone foot friction and contact solver
parameters are read as literals from the pinned `tasks/jumper/common/constants.py`.
The host disables unselected meshes. Visual meshes and collision hulls remain
distinct; rendering hides collision group 1.

Servo torque follows `assets/jumper/motor/motor_config.yaml`, matching the
upstream `ServoCurveActuator`: 1.7464 Nm peak, flat to 293.5 rpm, exponential
decay over 240.5 rpm, zero at 611 rpm. The per-joint heat state derives its
time constant from the 0.3 s peak budget and 1.2 Nm continuous limit. This is an
upstream simulation model with documented hardware uncertainties, not a thermal
measurement or hardware validation.

Snapshots include mode, running policy, draining native transition logs, actual
joint/body state, applied PD torque and conservative world collision AABB. AABB
rotation uses `abs(R) @ half_extents`; signed tabletop XY margin covers every
enabled robot collision geom. It is a monitoring measurement, not proof of
containment or a controller capable of stopping an airborne robot.

`render(width,height)` uses a cached `mujoco.Renderer` with a fixed free camera,
returning RGB uint8 without advancing physics. Offscreen rendering works with
normal Python on this Mac; upstream's interactive viewer requires `mjpython`.

First measured smoke: five seconds idle remained finite at approximately
`[0.00262, 0.00385, 0.10297]` m, tilt 0.693 degrees. Actual 640x360 offscreen
rendering succeeded. Full gesture and task-gate evidence should be recorded
separately by the demo harness.

Further measured smoke runs: hello requested at 3.0 s entered `gesture_hello`
and returned to locomotion at 10.945 s. Over the continuous 14 s episode, physics
remained finite, maximum base tilt was 7.195 degrees and minimum conservative
collision-bounds tabletop margin was 0.35821 m. A separate explicit permitted-jump
control episode reached 0.22660 m base height, returned to locomotion and remained
finite. These are simulator outcomes, not evidence of physical containment.
The three standalone simulator integration tests pass in 2.22 s on this Mac.

The shipped safe state uses damping only (`kp=0`, `kd=0.01`) and automatically
returns when tilt and feedback recover. It is not a guaranteed stop. The Mizu
demo demonstrates reminders and native gestures; cup delivery remains ambition.
