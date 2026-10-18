# Useful Mizu desk companion
User scope: face the seated person; laptop within reach; calm opt-in sound/speech; real empty-cup delivery and one-object desk cleanup. Extend existing public simulator, preserve main OSS ClawMetry adapter ownership. No hardware control, new backend, paid speech or user-data upload.

## Design
Retain sage#a4beb1, moss#234e43, cream#f6f5eb, table sand#b6aa8c and ink#223d34 and existing sans-serif. Robot faces seated owner, laptop near hands. Show task/progress/result first, measurements and fault tests secondary. Object target zones must be readable. Browser sound is explicitly opt-in and browser-provided, never asserted as native hardware support.

## Implementation
1. Research upstream claw/operator/locomotion capabilities and actual audio support. Separate physics and scene exploration under Software Factory.
2. Correct scene JSON and rebuild official map; change starting base heading toward seated person. Keep robot inertias/joints/servo physics and one tabletop.
3. Add free-joint empty cup and small cleanup object. Prototype contact-only manipulation via upstream interfaces or explicitly identified simulation-only scripted joint PD skill. Preserve floating-base dynamics. No object parenting/weld/teleport, hidden applied object force, liquid simulation or unproven human handoff. Completion requires actual displacement, target containment, release and stable measured result without boundary breach. Preserve failures and iterate until qualified.
4. UI cup/cleanup actions enable only qualified skills. Record request/permission/controller/progress/outcome separately; reject overlap/stale/edge/out-of-task. Disturbances invalidate outcomes. Reset cancels skills/audio, retains episode evidence.
5. Quiet opt-in chimes/browser speech, no remote TTS or microphone. Stop on pause/hide/reset/dispose; captions complete without audio.
6. Actual native physics and browser task qualification, failure/abort/loss, seed sweeps, existing regressions, mobile/no-network/lifecycle checks. Independent full review buckets, fix and repeat.
7. Reviewed source PR/CI/merge; landing pinned-assets PR/deploy; exact hosted verification/screenshots. No contest/YouTube publish; no installed Pro/cloud billing changes.

## Evidence
Record object poses/contact history, targets/tolerances, source/model hashes, controller kind and measured failures. Preserve native reference checks/licenses. Never substitute static initial object positions for grasp or success evidence.

## Measured scope refinement
Actual contact tests selected sliding an empty cup and one rigid paper-ball proxy, not airborne pickup. Both tasks explicitly start a visible fresh episode before a request. Cleanup failed a 1 mm source offset and delayed arbitrary-state start; those failures remain retained. No reset occurs mid-task. Native and browser require full-shape placement/release and monitored controller return. The source-bound qualification record fails closed on model/source drift.
