# Mizu: a little help, with clear boundaries

Draft for the BE UNLIMITED Create workflow. This is a project brief, not a claim
that the platform has generated or published it.

## Scene prompt

Create a calm, inviting home-office scene for the Jumper crab robot. A person is
seated at a desk with a laptop, an untouched drinking glass, a pen, a few sheets
of paper and a small tray. The finite rectangular tabletop is 1.72 m wide and
1.16 m deep. Put its top at z=0, and the floor at z=-0.75 m. Seat the person just
outside its front edge, with both hands visible and away from the robot's first
action. Keep a clear central resting area. Arrange the glass, pen, paper and
tray within the tabletop, with generous room for the whole robot and grippers
before the edge. No railings or invisible walls: the task boundary must be
observed and enforced by the application, not hidden physical barriers.

Keep the original Jumper mechanics and silhouette. Use a subdued sage shell,
warm cream details and dark moss joints. Soft daylight, clean proportions and
gentle interactions should make it feel like a desk companion. Keep the full
table edge, the person's hands and the robot's feet easy to see. It may travel
across the table when a task needs it, then return to its resting area. Avoid
constant roaming, surprise jumps or dramatic alarm effects.

## Interaction story

A person gets absorbed in work. Mizu gently offers a stretch, then a sip of
water. At the end of the session, it offers to put agreed objects away. The
owner may accept or skip each suggestion. Its agency stays within the current
task, the approved objects and the tabletop workspace.

ClawMetry observes actions continuously and records what was requested, what
was allowed, what the controller accepted and what actually happened. When the
owner returns after being away, the timeline makes those events understandable.
If the robot approaches the edge, is unexpectedly lifted, receives an
out-of-scope instruction or loses observation, ClawMetry raises a clear alert.
Phone delivery is a separately configured and verified capability.

## Scenario list and current evidence

| Scenario | Current delivery status |
|---|---|
| Person works beside calm Jumper | Authored official scene; person is a static proxy |
| Stretch/sip greeting | Real native wave and bow recorded; timers scripted |
| Decline unrelated jump during reminder | Recorded task gate denial before controller |
| Pick up and deliver glass across desk | Skill development and physics qualification needed |
| Clear agreed pen/paper into tray | Skill development and physics qualification needed |
| Unexpected lifting/removal | Actual external-force simulation test being prepared |
| Edge approach/crossing | Whole-body monitor implemented; actual disturbance qualification pending |
| Untrusted command asks to move a private object | Task-object scope refusal implemented; no universal attack detection claim |
| Review while-away history | Local DuckDB history and read-only viewer implemented |
| Phone alert | Opt-in HTTPS webhook adapter; real phone delivery unconfigured |

## Film direction

Open with the human need, show one useful interaction, then reveal why permission
and observation matter. Keep the companion warm and the oversight calm. Intercut
real simulator evidence with clearly labeled concept imagery only where needed.
The shot of cup delivery must stay a concept until actual contact-only transport
has passed. No welded cups, invisible force assists or pose animation presented
as learned robot behavior.

## Source and hosting

Code: https://github.com/vivekchand/clawmetry-jumper
Vision: https://clawmetry.com/physical-ai
Planned public playground: https://clawmetry.com/jumper (not yet deployed).

Use the official `.map`, `.skin` and `.app` package routes where supported. The
new adapter is independently Apache-2.0, with upstream model/policy/controller
attribution retained. Project creation is separate from contest submission and
acceptance of its reuse terms.
