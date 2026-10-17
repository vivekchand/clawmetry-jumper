# Companion skills

A skill is a purposeful action within a user-approved task. Its policy or motion
implementation is separate from the permissions surrounding it.

Current simulator requests supported by `TaskGate`:

| Skill | Native binding | Status |
|---|---|---|
| Wave | key_1 / gesture_hello | Measured on the tabletop |
| Bow | key_2 / gesture_bow | Measured on the tabletop |
| Offer paw | key_3 / gesture_paw | Available upstream; not yet desk-qualified here |
| Salute | key_4 / gesture_salute | Available upstream; not yet desk-qualified here |
| Walk to an object | Requires path and boundary controller | Planned, refused by adapter |
| Bring the glass | Requires contact-only pick, carry, place | Planned, refused by adapter |
| Tidy pen or paper | Requires authorized object selection and grasp | Planned, refused by adapter |

Sip and stretch reminders are app interactions. Demonstrating a wave after a
scripted timer does not establish detection of dehydration, posture or human
intent. Tidy permission never allows moving every object on a desk.

To add an executable skill:

1. Define its task, allowed objects, approach path, destination and abort/recovery
   conditions. Keep arbitrary scripts, raw controller keys and user-supplied
   models out of request payloads.
2. Implement it outside the gate using the official controller contract. Preserve
   name-based joint mappings, measured feedback, 1 kHz physics and low-level PD.
3. Qualify the entire motion and return against the real tabletop geometry,
   contact state, body reach and edge margin. Run repeated varied starts and
   failed controls. A good-looking render is insufficient.
4. Add its explicit action to the gate only after qualification. Keep observation
   mode the default, command acceptance separate from outcome, and stale data
   unknown. Add rejection and malformed-state tests.
5. Record an uncut actual run, inputs, source/asset hashes and a measured report.
   Document supported conditions and failures. Keep hardware qualification separate.

Task example: `Task('sip', frozenset({'wave'}), frozenset({'glass'}))`. It
permits a qualified greeting for the sip routine; it does not implement a grasp.
