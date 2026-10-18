"""A fresh browser asset build retains the reviewed compiled-runtime licenses."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]


def preparer():
    spec = importlib.util.spec_from_file_location("prepare_web_assets", ROOT / "scripts/prepare_web_assets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_versioned_notice_inputs_are_complete_and_hash_pinned(tmp_path):
    module = preparer()
    source = ROOT / "resources/browser-notices"
    manifest = json.loads((source / "manifest.json").read_text())
    assert manifest["upstream_commit"] == module.PIN
    assert len(manifest["files"]) > 100
    for relative, digest in manifest["files"].items():
        assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == digest
    inventory = json.loads((source / "assets/controller-licenses/inventory.json").read_text())
    assert len(inventory["components"]) == 50
    mujoco = json.loads((source / "vendor/mujoco/dependency-license-inventory.json").read_text())
    assert {item["name"] for item in mujoco["components"]} >= {"libccd", "qhull", "lodepng", "tinyxml2", "Emscripten"}
    # Copied inputs must be rejected before publishing even if just one text changes.
    copied = tmp_path / "notices"
    shutil.copytree(source, copied)
    first = next(iter(manifest["files"]))
    (copied / first).write_text("altered")
    with pytest.raises(ValueError, match="Notice input hash mismatch"):
        module.copy_dependency_notices(tmp_path / "web", tmp_path / "upstream", copied)


def test_notice_copy_binds_to_supplied_controller_and_source_lock(tmp_path):
    module = preparer()
    upstream = Path(os.environ.get("JUMPER_UPSTREAM", str(ROOT.parent / "clawmetry-jumper-upstream")))
    # The upstream directory is fetched at the exact public pin by the CI job.
    controller = upstream / "out/bundle_example/jumper/runtime/web/controller.wasm"
    web = tmp_path / "web"
    target = web / "assets/bundle/runtime/web/controller.wasm"
    target.parent.mkdir(parents=True)
    shutil.copyfile(controller, target)
    result = module.copy_dependency_notices(web, upstream)
    assert result["file_count"] > 100
    assert (web / "THIRD_PARTY_NOTICES.txt").is_file()
    assert (web / "vendor/mujoco/licenses/qhull-COPYING.txt").is_file()
    target.write_bytes(b"different controller")
    with pytest.raises(ValueError, match="Controller does not match"):
        module.copy_dependency_notices(web, upstream)


def test_delivery_manifest_records_actual_bytes_without_claiming_clean_source(tmp_path):
    module = preparer()
    (tmp_path / "example.js").write_text("export const value = 1;\n")
    result = module.write_delivery_manifest(tmp_path)
    assert len(result["source"]["checkout_head"]) == 40
    assert isinstance(result["source"]["uncommitted_reviewed_source"], bool)
    assert result["files"]["example.js"]["sha256"] == hashlib.sha256((tmp_path / "example.js").read_bytes()).hexdigest()
    assert "deployment-manifest.json" not in result["files"]
