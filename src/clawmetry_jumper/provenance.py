"""Verify local simulator inputs before loading executable upstream modules."""
import hashlib
import json
from pathlib import Path
import subprocess

PIN = "78966f45de6f2b6de3f7cea017f32a39f8b993e6"


def verify_upstream(upstream: Path, *, official=False) -> dict:
    upstream = Path(upstream).resolve()
    actual = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    clean = subprocess.run(["git", "-C", str(upstream), "diff", "--quiet", "HEAD", "--"]).returncode == 0
    if actual != PIN or not clean:
        raise ValueError("Use the pinned unmodified Jumper checkout for reproducible playback")
    paths = ["assets/jumper", "tasks/jumper/common", "out/bundle_example/jumper"]
    if official:
        paths += ["scripts", "rl", "controller", "tasks", "pyproject.toml"]
    tracked = subprocess.check_output(["git", "-C", str(upstream), "ls-files", "-z", "--", *paths]).decode().split("\0")
    digests = {}
    for name in filter(None, tracked):
        file = (upstream / name).resolve()
        if not file.is_relative_to(upstream):
            raise ValueError("An upstream input escapes the pinned checkout")
        digests[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return {"upstream_commit": actual, "tracked_inputs_clean": clean, "files_sha256": digests,
            "inputs_digest_sha256": hashlib.sha256(json.dumps(digests, sort_keys=True).encode()).hexdigest()}


def validate_official_outputs(video: Path, evidence: Path) -> list[Path]:
    video, evidence = Path(video).resolve(), Path(evidence).resolve()
    outputs = [video, evidence, Path(str(evidence) + ".wal"),
               video.with_suffix(".replay-info.json"), video.with_suffix(".clawmetry.json"),
               video.with_suffix(".provenance.json")]
    if len(set(outputs)) != len(outputs):
        raise ValueError("Recording and evidence files must have separate names")
    if any(p.exists() for p in outputs):
        raise ValueError("Choose new output names so earlier recordings and evidence stay intact")
    return outputs
