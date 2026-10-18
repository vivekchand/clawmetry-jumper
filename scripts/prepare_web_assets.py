#!/usr/bin/env python3
"""Prepare pinned, public simulator inputs. No npm, frontend build or secrets.

Large generated assets are local delivery files under web/vendor and web/assets.
The browser loads only these prevalidated fixed inputs, never arbitrary uploads.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from clawmetry_jumper.simulator import JumperSimulator  # noqa: E402

PIN = "78966f45de6f2b6de3f7cea017f32a39f8b993e6"
PACKAGES = {
    "mujoco": ("https://registry.npmjs.org/@mujoco/mujoco/-/mujoco-3.11.0.tgz", {
        "package/mujoco.js": "mujoco.js", "package/mujoco.wasm": "mujoco.wasm",
        "package/LICENSE": "LICENSE", "package/README.md": "README.md"}),
    "ort": ("https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-1.30.0.tgz", {
        "package/dist/ort.wasm.min.mjs": "ort.wasm.min.mjs",
        "package/dist/ort-wasm-simd-threaded.mjs": "ort-wasm-simd-threaded.mjs",
        "package/dist/ort-wasm-simd-threaded.wasm": "ort-wasm-simd-threaded.wasm",
        "package/LICENSE": "LICENSE", "package/ThirdPartyNotices.txt": "ThirdPartyNotices.txt"}),
    "three": ("https://registry.npmjs.org/three/-/three-0.178.0.tgz", {
        "package/build/three.module.js": "three.module.js",
        "package/build/three.core.js": "three.core.js",
        "package/examples/jsm/controls/OrbitControls.js": "OrbitControls.js",
        "package/LICENSE": "LICENSE"}),
}
INTEGRITY = {
    "mujoco": "ZtBhIX8It5EZUcRfxalYTilSG52JYoItEOBYOXdkviwZWaZ8XBuuSuNBwnXqhV1VkXpWbpPc27vGdQsTiSVX3Q==",
    "ort": "q0y+JrrtukXSzsBWEMccVfqX25LRmosXHF+CaRJmg8pZClzcV7svNc4rKY3jL02Vb7QmRMDs1SigqR4CXAfKYQ==",
    "three": "ybFIB0+x8mz0wnZgSGy2MO/WCO6xZhQSZnmfytSPyNpM0sBafGRVhdaj+erYh5U+RhQOAg/eXqw5uVDiM2BjhQ==",
}
NOTICES = {
    "mujoco": {"LICENSE": "https://raw.githubusercontent.com/google-deepmind/mujoco/3.11.0/LICENSE"},
    "ort": {"LICENSE": "https://raw.githubusercontent.com/microsoft/onnxruntime/v1.30.0/LICENSE",
            "ThirdPartyNotices.txt": "https://raw.githubusercontent.com/microsoft/onnxruntime/v1.30.0/ThirdPartyNotices.txt"},
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def portable_initial_qpos(source_model, source_data, portable):
    """Map the actual reset state by joint identity across MjSpec ordering."""
    if {portable.joint(i).name for i in range(portable.njnt)} != {source_model.joint(i).name for i in range(source_model.njnt)}:
        raise ValueError("Portable joint identities differ from native source")
    qpos = np.asarray(portable.qpos0).copy()
    for i in range(portable.njnt):
        target_joint = portable.joint(i)
        source_joint = source_model.joint(target_joint.name)
        if int(target_joint.type[0]) != int(source_joint.type[0]):
            raise ValueError("Portable joint type differs from native source")
        width = 7 if int(target_joint.type[0]) == 0 else 4 if int(target_joint.type[0]) == 1 else 1
        dst, src = int(target_joint.qposadr[0]), int(source_joint.qposadr[0])
        qpos[dst:dst + width] = source_data.qpos[src:src + width]
    return qpos


def desk_qualification(model_sha256: str) -> dict | None:
    """Enable only the exact reviewed fixed-scene source and portable model."""
    path = ROOT / "resources/desk-skill-qualification.json"
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    if record.get("schema") != "mizu_fixed_scene_qualification/1" or record.get("upstream_commit") != PIN or record.get("browser_model_sha256") != model_sha256:
        raise ValueError("Desk qualification does not match this portable model")
    required = {"src/clawmetry_jumper/simulator.py", "src/clawmetry_jumper/manipulation.py",
                "src/clawmetry_jumper/contact_plans.py", "scenes/mizu-desk.scene.json",
                "web/simulation.js", "web/manipulation.js", "web/app.js", "scripts/prepare_web_assets.py"}
    if set(record.get("source_sha256", {})) != required or set(record.get("actions", [])) != {"cup", "cleanup"}:
        raise ValueError("Desk qualification source coverage is incomplete")
    for name, digest in record["source_sha256"].items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError(f"Desk qualification source changed: {name}")
    for action in record["actions"]:
        if not all(record.get("measured_results", {}).get(action, {}).get(runtime, {}).get("passed") is True for runtime in ("native", "browser")):
            raise ValueError("Desk qualification has no measured passing outcome")
    return record


def enable_desk_plans(plans: dict, model_sha256: str) -> dict | None:
    # Native templates cannot grant browser qualification on their own.
    for plan in plans.values():
        plan["qualified"] = False
    record = desk_qualification(model_sha256)
    if record:
        for action in record["actions"]:
            if action not in plans:
                raise ValueError("Qualified desk action is absent from this model")
            plans[action]["qualified"] = True
    return record


def copy_dependency_notices(web: Path, upstream: Path, inputs: Path | None = None) -> dict:
    """Reproduce the reviewed notices without a local Cargo cache or live license lookup.

    Full upstream texts and locked source inventories are versioned as small build
    inputs. Verify their hashes and their binding to the supplied controller before
    copying. A changed controller needs a new reviewed inventory, not guessed rights.
    """
    inputs = inputs or ROOT / "resources" / "browser-notices"
    manifest = json.loads((inputs / "manifest.json").read_text())
    if manifest.get("upstream_commit") != PIN:
        raise ValueError("Notice inventory upstream revision mismatch")
    for relative, digest in manifest["files"].items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Invalid notice path")
        if sha((inputs / path).read_bytes()) != digest:
            raise ValueError(f"Notice input hash mismatch: {relative}")
    controller = json.loads((inputs / "assets/controller-licenses/inventory.json").read_text())
    if controller["upstream_revision"] != PIN:
        raise ValueError("Controller notice revision mismatch")
    if sha((web / "assets/bundle/runtime/web/controller.wasm").read_bytes()) != controller["controller_wasm_sha256"]:
        raise ValueError("Controller does not match reviewed dependency notices")
    if sha((upstream / "deploy/fsm/Cargo.lock").read_bytes()) != controller["cargo_lock_sha256"]:
        raise ValueError("Controller source lock does not match reviewed notices")
    for relative in manifest["files"]:
        target = web / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inputs / relative, target)
    return {"manifest_sha256": sha((inputs / "manifest.json").read_bytes()),
            "file_count": len(manifest["files"]),
            "controller_wasm_sha256": controller["controller_wasm_sha256"]}


def write_delivery_manifest(web: Path) -> dict:
    """Record exact local delivery hashes and honest source-tree provenance."""
    source_paths = ["web", "scripts/prepare_web_assets.py", "src/clawmetry_jumper",
                    "resources/browser-notices", "resources/desk-skill-qualification.json", "scenes/mizu-desk.scene.json"]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", *source_paths],
                                    cwd=ROOT, text=True).strip()
    files = {p.relative_to(web).as_posix(): {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
             for p in sorted(web.rglob("*")) if p.is_file()
             and p.name != "deployment-manifest.json" and "test-results" not in p.relative_to(web).parts}
    manifest = {"schema": "clawmetry.jumper.web-delivery.v1", "source": {
        "repository": "https://github.com/vivekchand/clawmetry-jumper", "checkout_head": head,
        "uncommitted_reviewed_source": bool(dirty),
        "adapter_repository": "https://github.com/vivekchand/clawmetry"}, "files": files}
    (web / "deployment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def npm_assets(web: Path) -> dict:
    result = {}
    for name, (url, selected) in PACKAGES.items():
        output = web / "vendor" / name
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="jumper-web-vendor-") as temp:
            archive = Path(temp) / "package.tgz"
            subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                            "--max-time", "120", url, "--output", str(archive)], check=True)
            content = archive.read_bytes()
            if base64.b64encode(hashlib.sha512(content).digest()).decode() != INTEGRITY[name]:
                raise ValueError(f"Pinned npm archive integrity mismatch: {name}")
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
                for source, dest in selected.items():
                    try:
                        member = tar.getmember(source)
                    except KeyError:
                        if dest in NOTICES.get(name, {}):
                            subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                                "--max-time", "60", NOTICES[name][dest], "--output", str(output / dest)], check=True)
                            continue
                        if dest in {"README.md", "ThirdPartyNotices.txt"}:
                            continue
                        raise ValueError(f"Required vendor file missing: {name}/{source}")
                    if not member.isfile() or member.size > 80_000_000:
                        raise ValueError(f"Invalid vendor member: {source}")
                    data = tar.extractfile(member).read()
                    (output / dest).write_bytes(data)
            result[name] = {"url": url, "archive_sha256": sha(content)}
    return result


def prepare(upstream: Path, scene: Path, web: Path) -> dict:
    if mujoco.__version__ != "3.11.0":
        raise ValueError("Prepare with the adapter's pinned MuJoCo 3.11.0 environment")
    web.mkdir(parents=True, exist_ok=True)
    packages = npm_assets(web)
    assets = web / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    simulator = JumperSimulator(upstream, scene_xml=scene, desk_skills=True)
    try:
        # Reuse the exact native host's model, contacts and official scene.
        root = ET.fromstring(simulator.compiled_xml)
        host = mujoco.MjSpec.from_string(ET.tostring(root, encoding="unicode"))
        model = host.compile()
        xml = ET.fromstring(host.to_xml())
        xml.find("compiler").set("meshdir", "")
        xml.find("compiler").set("texturedir", "")
        vfs = []
        for i, element in enumerate(xml.findall(".//*[@file]")):
            source = Path(element.attrib["file"])
            if not source.is_absolute():
                raise ValueError(f"Expected resolved fixed asset: {source}")
            data = source.read_bytes()
            name = f"input-{i:03d}-{source.name}"
            (assets / name).write_bytes(data)
            vfs.append({"path": name, "sha256": sha(data), "bytes": len(data)})
            element.set("file", name)
        xml_bytes = ET.tostring(xml, encoding="utf-8")
        (assets / "model.xml").write_bytes(xml_bytes)
        # Verify the portable XML, resolving exactly the browser VFS bytes.
        portable = mujoco.MjModel.from_xml_string(xml_bytes.decode(),
                    {r["path"]: (assets / r["path"]).read_bytes() for r in vfs})
        if portable.nq != model.nq or portable.ngeom != model.ngeom:
            raise ValueError("Portable model does not match compiled source")
        # Recompiling serialized MjSpec can reorder world/free bodies. Match
        # joint identities instead of copying addresses or zeroing free quats.
        qpos = portable_initial_qpos(simulator.model, simulator.data, portable)
        base = portable.joint("floating_base").qposadr[0]
        qadr = [int(portable.jnt_qposadr[portable.joint(n).id]) for n in simulator.wire]
        dadr = [int(portable.jnt_dofadr[portable.joint(n).id]) for n in simulator.wire]
        body = portable.body("base_link").id
        collision = [i for i in range(portable.ngeom)
                     if portable.body_rootid[portable.geom_bodyid[i]] == body
                     and (portable.geom_contype[i] or portable.geom_conaffinity[i])]
        render_geoms = []
        mesh_data = {}
        for i in range(portable.ngeom):
            if int(portable.geom_group[i]) == 1:
                continue  # collision meshes; actual display geoms remain
            mid = int(portable.geom_dataid[i])
            material = int(portable.geom_matid[i])
            rgba = (portable.mat_rgba[material] if material >= 0
                    and np.array_equal(portable.geom_rgba[i], [0.5, 0.5, 0.5, 1])
                    else portable.geom_rgba[i])
            render_geoms.append({"id": i, "name": portable.geom(i).name,
                "type": int(portable.geom_type[i]), "size": portable.geom_size[i].tolist(),
                "rgba": rgba.tolist(), "mesh": mid})
            if int(portable.geom_type[i]) == 7 and str(mid) not in mesh_data:
                va, vn = int(portable.mesh_vertadr[mid]), int(portable.mesh_vertnum[mid])
                fa, fn = int(portable.mesh_faceadr[mid]), int(portable.mesh_facenum[mid])
                mesh_data[str(mid)] = {
                    "vertices_f32": base64.b64encode(portable.mesh_vert[va:va+vn].astype('<f4').tobytes()).decode(),
                    "faces_u32": base64.b64encode(portable.mesh_face[fa:fa+fn].astype('<u4').tobytes()).decode()}
        bundle_out = assets / "bundle"
        bundle_out.mkdir(exist_ok=True)
        wanted = {"bundle.json", "controller.toml", "reference.json", "manual.en.json",
                  simulator.manifest["runtimes"]["web"]["glue"],
                  simulator.manifest["runtimes"]["web"]["wasm"]}
        for mode, entry in simulator.manifest["modes"].items():
            wanted.add(entry["contract"])
            wanted.add(entry["models"]["onnx"])
            if entry.get("trajectory"):
                wanted.add(entry["trajectory"])
        for relative in sorted(wanted):
            src, dst = simulator.bundle / relative, bundle_out / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        for name in ("LICENSE", "NOTICE"):
            shutil.copyfile(upstream / name, assets / f"UPSTREAM_{name}")
        notices = copy_dependency_notices(web, upstream)
        config = {"schema": "jumper_web_fixed_assets/1", "upstream_commit": PIN,
            "mujoco_version": mujoco.__version__, "model": "model.xml", "model_sha256": sha(xml_bytes),
            "vfs": vfs, "wire": simulator.wire, "qadr": qadr, "dadr": dadr,
            "base_body": body, "base_qadr": int(base), "initial_qpos": qpos.tolist(),
            "gyro_adr": int(portable.sensor("imu_ang_vel").adr[0]),
            "velocity_adr": int(portable.sensor("imu_lin_vel").adr[0]),
            "robot_collision_geoms": collision,
            "collision_local_aabb": {str(i): portable.geom_aabb[i].tolist() for i in collision},
            "physics_dt": .001, "control_dt": .005, "servo": simulator.servo,
            "render_geoms": render_geoms, "render_meshes": mesh_data,
            "table_bounds": [-.86, -.58, .86, .58], "scene_source": "official Design map environment",
            "scene_xml_sha256": sha(scene.read_bytes()),
            "counts": {"nq": portable.nq, "nv": portable.nv, "nbody": portable.nbody,
                       "ngeom": portable.ngeom, "njnt": portable.njnt},
            "native_controller_reference": simulator.verify_reference(), "vendor": packages}
        config["manipulation"] = simulator.manipulation_config()
        if config["manipulation"]:
            config["manipulation"]["jaw_geom_ids"] = [portable.geom(simulator.model.geom(i).name).id for i in config["manipulation"]["jaw_geom_ids"]]
            for name, item in config["manipulation"]["objects"].items():
                body = portable.body(name).id
                joint = portable.joint(name + "_free")
                item.update(body_id=body, joint_id=joint.id, qpos_adr=int(joint.qposadr[0]), dof_adr=int(joint.dofadr[0]),
                            geom_ids=np.flatnonzero(portable.geom_bodyid == body).tolist())
                item["local_aabb"] = {str(i): portable.geom_aabb[i].tolist() for i in item["geom_ids"]}
                item["geometry"] = {str(i): {"type": int(portable.geom_type[i]), "size": portable.geom_size[i].tolist()} for i in item["geom_ids"]}
            qualification = enable_desk_plans(config["manipulation"]["plans"], sha(xml_bytes))
            if qualification:
                shutil.copyfile(ROOT / "resources/desk-skill-qualification.json", assets / "desk-skill-qualification.json")
            else:
                (assets / "desk-skill-qualification.json").unlink(missing_ok=True)
        (assets / "config.json").write_text(json.dumps(config, separators=(",", ":")) + "\n")
        result = {"ok": True, "model_sha256": config["model_sha256"], "counts": config["counts"],
                  "native_controller_reference": config["native_controller_reference"],
                  "vendor": packages, "vfs_files": len(vfs), "dependency_notices": notices}
        (web / "asset-build.json").write_text(json.dumps(result, indent=2) + "\n")
        write_delivery_manifest(web)
        return result
    finally:
        simulator.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream", type=Path, required=True)
    p.add_argument("--scene", type=Path, required=True, help="Validated official imported scene.xml")
    p.add_argument("--web", type=Path, default=ROOT / "web")
    args = p.parse_args()
    print(json.dumps(prepare(args.upstream.resolve(), args.scene.resolve(), args.web.resolve()), indent=2))
