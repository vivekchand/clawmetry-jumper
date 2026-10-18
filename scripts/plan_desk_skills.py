"""Offline fixed-scene planning with scratch IK and real contact physics.

This simulation tool never edits the live pose of a prop, root, or robot joint
after initialization. Output is a candidate requiring separate qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path

from clawmetry_jumper.manipulation import LF_JOINTS, solve_push
from clawmetry_jumper.simulator import JumperSimulator

WAYPOINTS = {
    'cup': [('approach', [.05, -.207, .13], 3), ('lower', [.05, -.207, .027], 3),
            ('slide', [.06, -.277, .027], 5)],
    'cleanup': [('approach', [.14, -.27, .13], 3), ('lower', [.14, -.27, .027], 3),
                ('slide', [.205, -.19, .027], 5), ('release', [.25, -.15, .14], 3),
                ('retreat', [.24, -.12, .14], 3), ('step_back', None, 2)],
}


def plan(upstream, scene, action):
    sim = JumperSimulator(upstream, scene_xml=scene, desk_skills=True)
    try:
        initial = sim.data.qpos.tolist()
        for tick in range(1100):
            sim.step([('key_v', True)] if tick == 500 else [('key_v', False)] if tick == 501 else [])
        previous = {name: float(sim.data.qpos[sim._qadr[sim.wire.index(name)]]) for name in LF_JOINTS}
        stages, measurements = [], []
        for name, point, seconds in WAYPOINTS[action]:
            candidate = solve_push(sim, point) if point is not None else {
                'joints': {j: previous[j] for j in LF_JOINTS[:4]}, 'error_m': None}
            target = {**candidate['joints'], 'LF_J4_joint': -.95}
            stage = {'name': name, 'duration_s': seconds, 'joint_targets': [target[j] for j in LF_JOINTS]}
            walking = 'key_w' if action == 'cup' and name == 'slide' else 'key_s' if name == 'step_back' else None
            hold = .72 if walking == 'key_w' else .8
            if walking: stage.update(native_keys=['Key' + walking[-1].upper()], native_key_hold_s=hold)
            stages.append(stage)
            for tick in range(round(seconds / sim.dt)):
                t = min(1., (tick+1) / (seconds/sim.dt*.7)); mix = t*t*(3-2*t)
                keys = [(walking, True)] if walking and tick == 0 else [(walking, False)] if walking and tick == round(hold/sim.dt) else []
                observation = sim.step(keys, joint_targets={j: previous[j]*(1-mix)+target[j]*mix for j in LF_JOINTS})
            measurements.append({'stage': name, 'scratch_ik_error_m': candidate['error_m'], 'observation': observation})
            previous = target
        return {'action': action, 'qualified': False, 'stages': stages, 'measurements': measurements,
                'initial_qpos': initial, 'model_xml_sha256': hashlib.sha256(sim.compiled_xml.encode()).hexdigest(),
                'scene_xml_sha256': hashlib.sha256(Path(scene).read_bytes()).hexdigest(), 'provenance': sim.provenance}
    finally:
        sim.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--action', choices=WAYPOINTS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Choose a new output path; prior evidence will not be overwritten')
    report = plan(args.upstream, args.scene, args.action)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as file: file.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'action': args.action, 'qualified': False, 'model_xml_sha256': report['model_xml_sha256']}))


if __name__ == '__main__': main()
