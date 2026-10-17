# Mizu's next desk companion: Jumper

Production storyboard, 82 seconds. This is a filming plan, not a record that the adapter has passed its physics checks. Replace every provisional measurement with the recorder's real result before export.

## Creative direction

A small companion helps a person keep a pleasant workday: focus, stretch, drink, finish and tidy. It asks, accepts a skip, and uses the approved tabletop for purposeful tasks and returns to a resting area. Its personality comes from timing and a gentle greeting, rather than constant movement or surprise tricks.

The [original Mizu post](https://www.linkedin.com/feed/update/urn:li:activity:7513599170314928130/) describes sip, move and tidy using two SO-101 arms, demonstrations and a talking fox. The supplied 87.6-second clip shows a work session, a stretch, a cup handoff and cleanup. That is the narrative continuity. The SO-101 demonstration and this Jumper simulation are different systems; the former does not validate the latter's manipulation skills.

Use muted sage for the shell, warm cream accents, dark moss joints and a sand-colored tabletop. Preserve the actual robot geometry, contacts, mass and joint limits. A color treatment is a visual appearance study, not a validated physical shell. Keep the legs readable against the desk. Warm daylight, a steady three-quarter camera and a small top-down inset make the space easy to understand. Avoid flashing colors, alarm sounds and ominous music.

## Main edit

| Time | Genuine footage and composition | Narration | On-screen text and evidence |
|---|---|---|---|
| 0–7 s | Brief crop of the supplied Mizu work/stretch clip, then match-cut to the actual Jumper simulation on its tabletop. Label the two systems separately. | “Mizu began with a simple idea: a desk companion that helps us take care of ourselves.” | `Mizu: SO-101 prototype` then `Jumper: MuJoCo simulation`. Title: `A little company for a healthier workday` |
| 7–17 s | Wide simulator view. Jumper is settled in the approved desk zone, with a laptop and an untouched cup as stationary context. A task card requests a stretch reminder. No cup motion. | “This is the next experiment: a calm companion beside your work, with a small space and a clear job.” | `Task: offer a stretch reminder` · `Allowed: one greeting gesture` · `Travel skill: pending qualification`. Show the real measured tabletop margin, never a decorative success badge. |
| 17–30 s | One-second next-action preview, then a genuine successful upstream greeting policy replay through the native controller. Keep the full meaningful motion and return in shot. A visible `Skip` choice can be an editorial preview only unless the application implements it. | “The interaction we want is simple: see the next move, accept a friendly wave, or skip the reminder.” | `Next: greeting gesture` → `Request allowed` → actual controller mode and measured outcome. Mark `Interface concept` if consent/skip is not implemented. Prefer the least exuberant gesture that has passed the local measurement run. |
| 30–41 s | Return to quiet stance. Sip reminder appears beside the stationary cup. Use an actual measured bow only if it fits the zone; otherwise the settled robot is sufficient. | “Then, a quiet nudge to drink. Today it can remind us. Bringing the glass is a separate skill we still need to prove.” | `Sip reminder` · `Cup transport: planned`. Do not show an attached or animated cup following the claw. |
| 41–53 s | Same tabletop and continuous physics. A scripted test asks for a jump during the reminder task. The gate denies the request before it enters the native controller. Show the real request receipt and following controller state. | “A reminder is permission for that task. An unrelated jump request is declined before it reaches the controller.” | `Scripted scope test` · `Requested: jump` · `Denied: outside this task` · `Controller: [recorded mode]`. No cut implying an airborne robot was stopped. |
| 53–63 s | Brief genuine stale-observation case. Keep any physics still running visible; pair the last available sample with its age. Do not freeze the video to suggest a physical stop. | “If observations go missing, the record says unknown. A missing picture cannot tell us that a robot has stopped.” | `Observation stale` · `New request denied` · `Physical outcome unknown`. Use actual sample age and receipt. |
| 63–75 s | Calm end-of-work view. Display `Tidy after work?` beside a pen and tray. Then a small roadmap card, with no synthetic grasp animation. A short, separately labeled Mizu cleanup clip can illustrate the inspiration if it improves the edit. | “At the end of work, the ambition is to put one agreed object away. First an empty cup or notebook in simulation, with every step measured.” | `Next skills: empty-vessel placement · one-object tidy` · `Not demonstrated by this Jumper adapter`. Keep the desk boundary visible. |
| 75–82 s | Actual successful settled Jumper footage, then compact source and reproduction card. | “Useful company. Clear permission. Evidence of what actually happened.” | `Open-source local prototype` · `Native MuJoCo + upstream controller` · `Simulator evidence only`. Clickable sources belong in the accompanying description, not just rendered text. |

If the full greeting needs more time, extend the edit to at most 90 seconds. Do not speed up a stumble, cut away from a failure, or substitute joint animation for controller-driven footage. The original Mizu inserts are optional; the complete Jumper story must still make sense without them.

## Shot acceptance before assembly

- Each simulator shot must identify its exact model, policy, controller, scene, seed and recorded session. Retain its uncut recording and local event evidence.
- The desk is a finite tabletop with real collision geometry and a visible edge. Measure the robot's collision footprint against the allowed zone throughout each accepted clip. Body-origin containment alone is insufficient. Report any negative margin, fall, penetration or unexpected travel as a failed run. Do not teleport or clamp it back into the zone.
- Permission, controller acceptance and measured outcome are separate captions. Denial proves that the adapter withheld that command, not that other command paths are impossible or that physics has become safe.
- The greeting must actually run locally before the narration says it can wave. Upstream availability alone is not local execution proof. If no gesture meets the tabletop criterion, show a settled robot and label gesture playback pending; do not release the planned success edit.
- Keep `MuJoCo simulation` legible throughout simulator footage. State that no hardware control, human detection, fall prevention guarantee, liquid handling or autonomous tidying is demonstrated.
- Render policy playback at recorded speed. A montage may shorten quiet time with an explicit cut, but must preserve the request-to-outcome sequence for the permission test.
- Keep captions inside the frame, readable on a phone, and away from the robot's feet and evidence. Use plain status words and subdued amber for unavailable evidence. No red strobe or manufactured emergency.
- If a UI feature appears only as an editorial card, label it `Interface concept`. Do not composite a fictional interactive dashboard as if captured from the working app.

## Sources and credits

- Mizu inspiration: the linked post and the user-supplied original video. Attribute the Mizu team and event in the video description, using the post's exact names after checking spelling. Do not imply that a teammate endorsed this new adapter.
- Jumper model, policies and native controller: [KingKong Robotics, pinned source](https://github.com/KingKongRobotics/jumper/tree/78966f45de6f2b6de3f7cea017f32a39f8b993e6). Retain its LICENSE and NOTICE alongside redistributed materials.
- Policy names and integration contract: [pinned manifest](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/deploy/manifests.json) and [bundle format](https://github.com/KingKongRobotics/jumper/blob/78966f45de6f2b6de3f7cea017f32a39f8b993e6/deploy/BUNDLE.md).
- Video description should link to the adapter's actual repository and reproduction instructions once available. No invented URL, contest submission, rights acceptance or publication is part of this storyboard.
