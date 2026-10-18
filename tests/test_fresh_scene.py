"""A task scene must never reset another in-flight action or retired engine."""
import shutil
import subprocess
from pathlib import Path
import pytest


def test_explicit_fresh_scene_lifecycle():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is unavailable for browser-module contract test')
    subprocess.run([node, 'tests/fresh_scene_check.cjs'], cwd=Path(__file__).resolve().parents[1], check=True)
