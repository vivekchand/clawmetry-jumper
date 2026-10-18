"""Containment witnesses use actual shapes, not just a prop center."""
import math
import mujoco
import numpy as np
from clawmetry_jumper.manipulation import object_bounds, target_contains_object


def model(geom):
    m = mujoco.MjModel.from_xml_string('<mujoco><worldbody><body name="prop">' + geom + '</body></worldbody></mujoco>')
    d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    return m, d


def test_rotated_sphere_has_orientation_invariant_bounds_and_full_box_containment():
    q = ' '.join(map(str, [math.cos(.9), math.sin(.9)/math.sqrt(3), math.sin(.9)/math.sqrt(3), math.sin(.9)/math.sqrt(3)]))
    m, d = model('<geom type="sphere" size=".025" quat="'+q+'"/>')
    bounds = object_bounds(m, d, [0])
    np.testing.assert_allclose(bounds['min'], [-.025]*3)
    np.testing.assert_allclose(bounds['max'], [.025]*3)
    goal = {'target_shape':'box', 'target_xy':[0,0], 'target_bounds_m':[-.026,-.026,.026,.026]}
    assert target_contains_object(m, d, [0], goal)
    goal['target_bounds_m'][0] = -.024
    assert not target_contains_object(m, d, [0], goal)  # Center alone still fits.


def test_circle_checks_actual_box_corners_and_projected_cylinder_axis():
    m, d = model('<geom type="box" size=".01 .01 .04" pos=".03 0 0"/>')
    goal = {'target_shape':'circle', 'target_xy':[0,0], 'target_radius_m':.045}
    assert target_contains_object(m, d, [0], goal)
    goal['target_radius_m'] = .040
    assert not target_contains_object(m, d, [0], goal)
    m, d = model('<geom type="cylinder" size=".025 .05" quat=".7071067812 .7071067812 0 0"/>')
    goal['target_radius_m'] = .074
    assert not target_contains_object(m, d, [0], goal)
    goal['target_radius_m'] = .076
    assert target_contains_object(m, d, [0], goal)
