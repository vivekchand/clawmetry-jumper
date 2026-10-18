"""Simulation-only desk manipulation geometry and bounded joint commands.

Objects remain free bodies throughout an episode. Only reset sets their pose;
contacts and gravity determine every later displacement. Jaw decomposition is
the pinned upstream five_foot task's own geometry, not a new grasp constraint.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


OBJECTS = {
    "empty_cup": {"position": [.05, -.255, .051], "radius": .025, "height": .100,
                  "target": [.06, -.31], "mass_kg": .045,
                  "target_shape": "circle", "target_radius_m": .048},
    "cleanup_block": {"position": [.18, -.25, .026], "radius": .025, "height": .05,
                      "shape": "sphere", "target": [.22, -.17], "mass_kg": .012,
                      "target_shape": "box", "target_center_xy": [.22, -.1725],
                      "target_bounds_m": [.130, -.235, .310, -.110],
                      "target_half_size_m": [.09, .0625]},
}
LF_JOINTS = tuple(f"LF_J{i}_joint" for i in range(5))


def object_bounds(model, data, geom_ids):
    """World bounds from the actual compiled collision geometry, read-only."""
    ids = np.asarray(geom_ids, dtype=int)
    local = model.geom_aabb[ids]
    rotation = data.geom_xmat[ids].reshape(-1, 3, 3)
    center = data.geom_xpos[ids] + np.einsum('ijk,ik->ij', rotation, local[:, :3])
    half = np.einsum('ijk,ik->ij', np.abs(rotation), local[:, 3:])
    # A sphere has no privileged orientation. Rotating its enclosing cube
    # artificially enlarges the footprint as it rolls.
    spheres = model.geom_type[ids] == mujoco.mjtGeom.mjGEOM_SPHERE
    half[spheres] = model.geom_size[ids[spheres], 0, None]
    return {"min": np.min(center - half, axis=0).tolist(),
            "max": np.max(center + half, axis=0).tolist()}


def target_contains_object(model, data, geom_ids, goal):
    """Conservative whole-collision-shape containment, never center-only."""
    target = np.array(goal['target_xy'], dtype=float)
    if goal['target_shape'] == 'box':
        bounds = object_bounds(model, data, geom_ids)
        target_bounds = goal['target_bounds_m']
        return all(bounds['min'][i] >= target_bounds[i] and
                   bounds['max'][i] <= target_bounds[i+2] for i in (0, 1))
    radius = goal['target_radius_m']
    for gid in geom_ids:
        kind = model.geom_type[gid]
        pos, rot, size = data.geom_xpos[gid], data.geom_xmat[gid].reshape(3, 3), model.geom_size[gid]
        if kind == mujoco.mjtGeom.mjGEOM_BOX:
            for x in (-size[0], size[0]):
                for y in (-size[1], size[1]):
                    for z in (-size[2], size[2]):
                        point = pos + rot @ [x, y, z]
                        if np.linalg.norm(point[:2]-target) > radius: return False
        elif kind == mujoco.mjtGeom.mjGEOM_CYLINDER:
            # Radius bounds the projected disk in every orientation; the
            # projected half-axis adds a conservative tilt allowance.
            support = np.linalg.norm(pos[:2]-target) + size[0] + size[1]*np.linalg.norm(rot[:2, 2])
            if support > radius: return False
        elif kind == mujoco.mjtGeom.mjGEOM_SPHERE:
            if np.linalg.norm(pos[:2]-target)+size[0] > radius: return False
        else:
            return False  # This fixed-scene contract has no other object shape.
    return True


def desk_model(xml: str, upstream: Path, *, object_offsets: dict | None = None) -> str:
    """Add free props and upstream frictional jaws, without any equality.

    The original model's inertias, free root and servo curve are retained.
    The left jaw's single hull is replaced by the official task's six/three
    convex pieces, since the single convex hull fills the mouth completely.
    """
    root = ET.fromstring(xml)
    object_offsets = object_offsets or {}
    if set(object_offsets) - set(OBJECTS):
        raise ValueError("Unknown desk object in reset configuration")
    assets, world = root.find("asset"), root.find("worldbody")
    for parent in root.iter():
        for child in list(parent):
            if child.get("name") in ("stationary_sip_vessel_proxy", "water_glass"):
                parent.remove(child)
    for link, count in (("LF_palm_link", 6), ("LF_finger_link", 3)):
        body = root.find(f".//body[@name='{link}']")
        original = body.find(f"geom[@name='{link}_meshcol']")
        if original is None:
            raise ValueError("Pinned Jumper jaw geometry is missing")
        for i in range(count):
            name = f"desk_{link}_col{i}"
            path = upstream / "tasks/jumper/five_foot/meshes" / f"{link}_col{i}.STL"
            if not path.is_file():
                raise ValueError("Pinned Jumper convex jaw piece is missing")
            ET.SubElement(assets, "mesh", name=name, file=str(path.resolve()))
            geom = original if i == 0 else copy.deepcopy(original)
            geom.set("name", f"{link}_meshcol" + (str(i) if i else ""))
            geom.set("mesh", name)
            geom.set("condim", "3")
            geom.set("priority", "1")
            geom.set("friction", "1 .005 .0001")
            if i:
                body.append(geom)
    root.find("option").set("cone", "elliptic")
    root.find("option").set("impratio", "50")
    for name, spec in OBJECTS.items():
        offset = object_offsets.get(name, [0., 0., 0.])
        if not isinstance(offset, (list, tuple)) or len(offset) != 3 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > .02 for v in offset):
            raise ValueError("Desk reset offset must contain three finite values within 2 cm")
        position = [v + offset[i] for i, v in enumerate(spec["position"])]
        body = ET.SubElement(world, "body", name=name,
                             pos=" ".join(map(str, position)))
        ET.SubElement(body, "freejoint", name=name + "_free")
        common = dict(contype="1", conaffinity="127", condim="6", priority="1",
                      friction=".35 .0002 .00012", solref=".02 1",
                      solimp=".9 .95 .001 .5 2", rgba=".90 .85 .72 1")
        if name == "empty_cup":
            # A real open vessel: a base plus sixteen thin rigid wall segments.
            mass = spec["mass_kg"] / 17
            ET.SubElement(body, "geom", name=name + "_bottom", type="cylinder",
                          size=".025 .002", pos="0 0 -.048", mass=str(mass), **common)
            for i in range(16):
                angle = i * math.tau / 16
                radius = .024
                ET.SubElement(body, "geom", name=f"{name}_wall_{i}", type="box",
                              size=".0015 .0049 .049", mass=str(mass),
                              pos=f"{radius*math.cos(angle)} {radius*math.sin(angle)} 0",
                              quat=f"{math.cos(angle/2)} 0 0 {math.sin(angle/2)}", **common)
        else:
            ET.SubElement(body, "geom", name=name + "_geom", type="sphere",
                          size=str(spec["radius"]),
                          mass=str(spec["mass_kg"]), **common)
    return ET.tostring(root, encoding="unicode")


def grip_frame(model):
    """Measure the official jaws' anvil and opening, in the palm frame.

    This is kinematic planning on separate MjData, not a simulation state edit.
    As upstream documents, mesh vertices must use their compiled geom transform;
    the body frame alone is wrong for MuJoCo's re-oriented mesh coordinates.
    """
    data = mujoco.MjData(model)
    finger = model.joint("LF_J4_joint").qposadr[0]
    palm = model.body("LF_palm_link").id

    def cloud(names):
        points = []
        for name in names:
            gid = model.geom(name + "_visual").id
            mid = model.geom_dataid[gid]
            adr, count = model.mesh_vertadr[mid], model.mesh_vertnum[mid]
            vertices = model.mesh_vert[adr:adr + count]
            points.append(vertices @ data.geom_xmat[gid].reshape(3, 3).T + data.geom_xpos[gid])
        points = np.vstack(points)
        points = points[np.linalg.norm(points - data.body("LF_finger_link").xpos, axis=1) > .04]
        _, indexes = np.unique(np.round(points / .0015), axis=0, return_index=True)
        return points[indexes]

    data.qpos[finger] = .1
    mujoco.mj_forward(model, data)
    fixed = cloud(("LF_palm_link", "LF_palm_pad_f_link", "LF_palm_pad_b_link"))
    moving = cloud(("LF_finger_link", "LF_finger_tip_link"))
    closest, distance = None, float("inf")
    for start in range(0, len(moving), 64):
        d = np.sum((moving[start:start + 64, None] - fixed[None]) ** 2, axis=2)
        index = np.unravel_index(d.argmin(), d.shape)
        if d[index] < distance:
            distance, closest = d[index], fixed[index[1]]
    rotation = data.xmat[palm].reshape(3, 3)
    local_anvil = rotation.T @ (closest - data.xpos[palm])
    data.qpos[finger] = -.65
    mujoco.mj_forward(model, data)
    rotation = data.xmat[palm].reshape(3, 3)
    anvil = data.xpos[palm] + rotation @ local_anvil
    moving = cloud(("LF_finger_link", "LF_finger_tip_link"))
    closing = moving[np.argmin(np.linalg.norm(moving - anvil, axis=1))] - anvil
    closing /= np.linalg.norm(closing)
    inward = data.body("LF_finger_link").xpos - anvil
    inward[2] = 0
    inward /= np.linalg.norm(inward)
    return {"anvil": local_anvil, "closing": rotation.T @ closing,
            "inward": rotation.T @ inward}


def solve_grip(sim, point, *, radius=.025, seed=None):
    """Bounded four-joint IK; a plan never writes the live physics state."""
    model = sim.model
    data = mujoco.MjData(model)
    data.qpos[:] = sim.data.qpos
    frame = getattr(sim, "_desk_grip_frame", None)
    if frame is None:
        frame = sim._desk_grip_frame = grip_frame(model)
    palm = model.body("LF_palm_link").id
    ids = [model.joint(name).id for name in LF_JOINTS[:4]]
    adr = model.jnt_qposadr[ids]
    lo, hi = model.jnt_range[ids].T
    local = frame["anvil"] + frame["closing"] * (radius + .005) + frame["inward"] * .020
    target = np.asarray(point, dtype=float)

    def value(q):
        data.qpos[adr] = q
        mujoco.mj_forward(model, data)
        rotation = data.xmat[palm].reshape(3, 3)
        pos = data.xpos[palm] + rotation @ local
        return np.r_[pos, (rotation @ frame["closing"])[2] * .07]

    seeds = [seed] if seed is not None else [sim.data.qpos[adr].copy(), [-.16, -1.57, -.52, .23], [-1.1, -1.5, -.5, .3]]
    best = None
    for initial in seeds:
        q = np.clip(np.asarray(initial, dtype=float), lo + .01, hi - .01)
        for _ in range(100):
            v = value(q)
            error = np.r_[target, 0.] - v
            if np.linalg.norm(error) < .0004:
                break
            jac = np.column_stack([(value(q + np.eye(4)[i] * 1e-4) - v) / 1e-4 for i in range(4)])
            delta = jac.T @ np.linalg.solve(jac @ jac.T + np.eye(4) * .00001, error)
            q = np.clip(q + np.clip(delta, -.12, .12), lo + .01, hi - .01)
        error = float(np.linalg.norm(np.r_[target, 0.] - value(q)))
        if best is None or error < best[0]:
            best = error, q.copy()
    return {"error_m": best[0], "joints": dict(zip(LF_JOINTS[:4], best[1].tolist())),
            "local_grip_point": local.tolist(), "target_m": target.tolist()}


def solve_push(sim, point, *, seed=None):
    """Place the carried palm's real outer pad for a low contact-guided slide.

    This pad already supports the robot in its ordinary six-foot stance. Using
    it as a pusher avoids pretending that a scripted squeeze is a qualified
    airborne grasp. Only scratch-data forward kinematics is used for planning.
    """
    model = sim.model
    data = mujoco.MjData(model)
    data.qpos[:] = sim.data.qpos
    gid = model.geom("LF_palm_pad_b_link_meshcol").id
    ids = [model.joint(n).id for n in LF_JOINTS[:4]]
    adr = model.jnt_qposadr[ids]
    lo, hi = model.jnt_range[ids].T
    q = np.array(seed if seed is not None else sim.data.qpos[adr], dtype=float)
    target = np.asarray(point, dtype=float)
    def value(angles):
        data.qpos[adr] = angles
        mujoco.mj_forward(model, data)
        return data.geom_xpos[gid].copy()
    for _ in range(150):
        current = value(q)
        error = target - current
        if np.linalg.norm(error) < .0002:
            break
        jac = np.column_stack([(value(q + np.eye(4)[i] * 1e-4) - current) / 1e-4 for i in range(4)])
        step = jac.T @ np.linalg.solve(jac @ jac.T + np.eye(3) * .00001, error)
        q = np.clip(q + np.clip(step, -.08, .08), lo + .02, hi - .02)
    return {"error_m": float(np.linalg.norm(target - value(q))),
            "joints": dict(zip(LF_JOINTS[:4], q.tolist())), "target_m": target.tolist()}
