"""Optional local voice must never choose a remote/default speech service."""
import shutil
import subprocess
from pathlib import Path
import pytest


def test_companion_audio_lifecycle_and_local_voice_contract():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is unavailable for browser-module contract test')
    subprocess.run([node, 'tests/companion_audio_check.cjs'], cwd=Path(__file__).resolve().parents[1], check=True)
