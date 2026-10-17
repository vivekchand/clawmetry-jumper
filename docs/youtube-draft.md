# YouTube review draft

Status: rendered for review, not uploaded, published or submitted to a contest.
The original WhatsApp video is not included. Narration uses the previously
approved ElevenLabs Eleven v3 Rachel voice through fal. Listening review of this
new narration remains pending; this tool session cannot hear audio. The old
system-voice cut is rejected and separated from the current render. No external
music or paid generated footage is used.

## Title

Mizu: A Calmer Desk Companion, with ClawMetry | Real Jumper Simulation

## Description

A little hello. A water reminder. A moment to stretch.

Mizu explores a calmer desk companion, inspired by the healthy-companion idea
shared in the LeRobot community. This version uses the open-source Jumper robot
and ClawMetry to keep task permissions, actual controller behavior and measured
simulator outcomes visible.

The main 35-second demonstration runs at its original speed in the official
Jumper simulator and video recorder. A hello and bow reach the native controller.
A jump request is outside the reminder task, so its input is withheld. The local
history records what was requested, what was allowed and what actually happened.
All 351 sampled observations include 22 named joints with measured positions and
velocities. Observation and task governance come from the ordinary built-in
`clawmetry` package; Mizu supplies the scene and optional simulation host.

A separate native MuJoCo test applies a real simulated upward force. Measured
rise and tilt trigger local alerts. No delivered phone notification is shown.
Shared ClawMetry channels depend on the owner's notification preferences; a
preview or local receipt is not proof that a phone displayed a message.

Cup delivery and desk tidying are planned skills, not demonstrated capabilities.
These are simulation results, not hardware validation or a physical-stop guarantee.
The seated figure belongs to the scene; this demonstration does not recognize
people or infer malicious intent.

ClawMetry observation and governance source:
https://github.com/vivekchand/clawmetry

Mizu scene and reproduction:
https://github.com/vivekchand/clawmetry-jumper

Physical AI story:
https://clawmetry.com/physical-ai

The web playground at clawmetry.com/jumper was in preparation when this review
draft was built. Check its status before publishing that link as available.

Chapters:
00:00 Meet Mizu
00:07 Useful today, planned next
00:12 Official Jumper simulation
00:47 Review the local history
00:57 Separate scripted lift test
01:07 Detection and notification delivery
01:14 Build the next chapter

Credits: Jumper model, exported policies and native controller from
KingKongRobotics/jumper, pinned at
78966f45de6f2b6de3f7cea017f32a39f8b993e6. Environment produced through the official
Jumper Design map pipeline. Mint/sage appearance changes visual colors only.
See this repository's NOTICE and source credits for licenses and provenance.

Premium neural narration. Listening review pending. No external music.

#Jumper #CrabRobot #OpenSourceRobot #PhysicalAI #ClawMetry

## Review artifacts

- `artifacts/film/Mizu-ClawMetry-Review-Draft.mp4`: 84-second 1080p review export.
- Matching `.srt`: editable narration captions; the same captions are burned in.
- `Mizu-ClawMetry-Portrait-Review.mp4`: 35-second portrait excerpt of the same
  official recording, at its original speed, with aligned premium narration.
- `transcript.txt` and `narration.json`: words, voice and actual audio timing.
- `contact-sheet.jpg`: nine frames for layout and claim review.
- `film-manifest.json`: source footage and measured run references.
- `premium-voice/`: authored clip inputs, paid-job receipts and actual provider
  speech timestamps. Clips retain their natural speed and are not cut short.
- `brand/`: official horizontal ClawMetry lockup, source attribution and hash.
- `official-shared-journal.jsonl`: the actual shared built-in observation run,
  copied for reproducibility and referenced by SHA-256 in the manifest.
- `scripted-lift-native.mp4`, `.report.json` and `.duckdb`: separate actual force
  experiment and local alert/notification receipts.

Publishing, contest submission and broad reuse terms have not been accepted by
this build script. Review the rendered film and current playground status first.
Listen to names, technical terms, pauses and warmth before any YouTube upload.

The renderer requires premium clips and the official logo. It refuses a system
voice fallback. After preparing approved clips and their provider receipts:

```sh
.venv/bin/python scripts/build_film.py \
  --voice-dir artifacts/film/premium-voice \
  --brand artifacts/film/brand/clawmetry-logo-horizontal-darkbg.png \
  --reuse-lift --portrait
```

The `--reuse-lift` flag uses the existing measured clip and complete shared-core
report. Omit it only when a new physical experiment recording is needed.
Font lookup is lazy: the existing macOS faces preserve this export, other hosts
can use DejaVu Sans, or supply `--font` and `--bold-font` TrueType paths.

Optional public narration tooling uses only the Python standard library and the
[fal Eleven v3 API](https://fal.ai/models/fal-ai/elevenlabs/tts/eleven-v3/api).
It sends authored narration only, never simulator events or private traces.
It requires an explicit generation flag and can incur provider charges. Set
`FAL_KEY` or `FAL_CREDENTIALS_FILE` in the environment; do not commit credentials.
Generate and listen to an audition first, then generate the candidate clips:

```sh
python3 scripts/neural_narration.py --generate --audition
python3 scripts/neural_narration.py --generate
```

The tool caches input/model/voice receipts, resumes queued jobs and refuses an
ambiguous submission rather than submitting it again. Existing matching clips
need neither credentials nor a new paid request. No private repository helper
is imported. A provider name and technical checks do not establish naturalness;
the manifest retains a pending listening status until someone actually reviews it.
