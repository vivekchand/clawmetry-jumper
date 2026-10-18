"""Task completion must depend on observed contact, placement and release."""
import shutil
import subprocess
from pathlib import Path
import pytest


def test_browser_desk_skill_evidence_and_cancellation_contract():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is unavailable for browser-module contract test')
    subprocess.run([node, 'tests/desk_skills_check.cjs'], cwd=Path(__file__).resolve().parents[1], check=True)
