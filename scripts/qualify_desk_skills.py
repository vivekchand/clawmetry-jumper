"""Measure real contact-only desk skills against their frozen candidate arrays.

No object state writes, equality constraints or object forces occur in this
runner. A target outcome requires measured release and stability; time alone
cannot complete a skill. Reset offsets are explicit model initial conditions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
from clawmetry_jumper.simulator import JumperSimulator
from clawmetry_jumper.manipulation import target_contains_object


def qualify(upstream, scene, action, *, offset=(0., 0.), abort_at=None, entry_tick_offset=0):
    if type(entry_tick_offset) is not int or entry_tick_offset not in (-1, 0, 1):
        raise ValueError('Native entry timing qualification is limited to one control tick')
    target_name = 'empty_cup' if action == 'cup' else 'cleanup_block'
    sim = JumperSimulator(upstream, scene_xml=scene, desk_skills=True,
                          object_offsets={target_name: [*offset, 0.]})
    config = sim.manipulation_config()
    plan = config['plans'][action]
    starts = {name: np.array(obj['start_position_m']) for name, obj in config['objects'].items()}
    contacts, stable_s, max_tilt, min_margin, max_other = 0, 0., 0., float('inf'), 0.
    initial_qpos = sim.data.qpos.tolist()
    history, stage_results, failures = [], [], set()
    def measure(stage):
        nonlocal contacts, stable_s, max_tilt, min_margin, max_other
        o = sim.snapshot(); obj = o['objects'][target_name]
        pairs, robot_pairs = 0, 0
        geoms = set(config['objects'][target_name]['geom_ids']); jaws = set(config['jaw_geom_ids'])
        robot = set(config['robot_geom_ids'])
        for c in sim.data.contact:
            a, b = map(int, c.geom)
            if (a in geoms and b in jaws) or (b in geoms and a in jaws): pairs += 1
            if (a in geoms and b in robot) or (b in geoms and a in robot): robot_pairs += 1
        contacts += bool(pairs)
        position = np.array(obj['position_m'])
        goal = config['objects'][target_name]
        box = obj['bounds_m']
        footprint = target_contains_object(sim.model, sim.data, goal['geom_ids'], goal)
        error = float(np.linalg.norm(position[:2] - config['objects'][target_name]['target_xy']))
        displacement = float(np.linalg.norm(position[:2] - starts[target_name][:2]))
        hand = np.array(plan.get('hand_xy', [0., 0.]))
        approach = float(np.linalg.norm(starts[target_name][:2] - hand) - np.linalg.norm(position[:2] - hand))
        other = max(float(np.linalg.norm(np.array(v['position_m']) - starts[k])) for k, v in o['objects'].items() if k != target_name)
        max_other = max(max_other, other); max_tilt = max(max_tilt, o['tilt_deg']); min_margin = min(min_margin, o['table_margin_m'])
        checks = dict(target=error <= plan['target_tolerance_m'], footprint=footprint,
                      moved=displacement >= plan.get('minimum_displacement_m', .05),
                      hand=not plan.get('hand_xy') or approach >= plan.get('minimum_hand_approach_m', .03),
                      upright=not plan.get('upright_required', True) or obj['tilt_deg'] < 12., low_speed=np.linalg.norm(obj['linear_velocity_m_s']) < .025,
                      low_spin=np.linalg.norm(obj['angular_velocity_rad_s']) < .4,
                      resting=abs(position[2] - starts[target_name][2]) < .012,
                      released=robot_pairs == 0, contacted=contacts >= 2, other_unchanged=other <= .015,
                      robot_stable=o['tilt_deg'] < 15., inside_table=o['table_margin_m'] > .08,
                      object_inside=abs(position[0]) < .8 and abs(position[1]) < .52,
                      native_locomotion=stage != 'native_return' or o['mode'] == 'locomotion')
        checks = {key: bool(value) for key, value in checks.items()}
        for key in ('other_unchanged', 'robot_stable', 'inside_table', 'object_inside'):
            if not checks[key]: failures.add(key)
        if not o['finite'] or position[2] < -.02: failures.add('invalid_or_fallen')
        if plan.get('upright_required', True) and obj['tilt_deg'] > 30: failures.add('object_tipped')
        stable_s = stable_s + sim.dt if all(checks.values()) else 0.
        return dict(time_s=o['time_s'], stage=stage, mode=o['mode'], position_m=obj['position_m'], bounds_m=box, tilt_deg=obj['tilt_deg'],
                    robot_tilt_deg=o['tilt_deg'], table_margin_m=o['table_margin_m'], jaw_contacts=pairs,
                    robot_contacts=robot_pairs,
                    target_error_m=error, displacement_m=displacement, hand_approach_m=approach,
                    velocity_m_s=obj['linear_velocity_m_s'], checks=checks, stable_s=stable_s)
    try:
        for n in range(1100 + entry_tick_offset):
            sim.step([('key_v', True)] if n == 500 + entry_tick_offset else [('key_v', False)] if n == 501 + entry_tick_offset else [])
            result = measure('native_settle')
            if n % 20 == 0: history.append(result)
            if failures: break
        last = {name: float(sim.data.qpos[sim._qadr[sim.wire.index(name)]]) for name in config['joint_names']}
        aborted = False
        for stage in plan['stages']:
            if failures: break
            target = dict(zip(config['joint_names'], stage['joint_targets']))
            initial = last.copy()
            held = False
            native_keys = [('key_' + key[-1].lower()) for key in stage.get('native_keys', [])]
            hold_ticks = round(stage.get('native_key_hold_s', stage['duration_s']) / sim.dt)
            for tick in range(round(stage['duration_s'] / sim.dt)):
                t = min(1., (tick + 1) / (stage['duration_s'] / sim.dt * .7)); a = t*t*(3-2*t)
                keys = [(key, True) for key in native_keys] if tick == 0 else [(key, False) for key in native_keys] if tick == hold_ticks else []
                held = bool(native_keys) and tick < hold_ticks
                sim.step(keys, joint_targets={k: initial[k]*(1-a)+target[k]*a for k in last})
                result = measure(stage['name'])
                if tick % 20 == 0: history.append(result)
                if abort_at is not None and result['time_s'] >= abort_at:
                    aborted = True; break
                if failures: break
            if held:
                sim.step([(key, False) for key in native_keys])
                result = measure('cancel_release')
            stage_results.append(result);last = target
            if aborted or failures: break
        if not aborted and not failures:
            stable_s = 0.
            return_at = None
            for tick in range(1600):
                # Native return is part of the measured skill, not a success
                # animation after the last scripted joint command.
                keys = [('key_v', True)] if tick == 0 else [('key_v', False)] if tick == 1 else []
                sim.step(keys)
                if sim.snapshot()['mode'] == 'locomotion': return_at = return_at if return_at is not None else sim.data.time
                else: return_at = None
                result=measure('native_return')
                if return_at is None or sim.data.time-return_at < 2: stable_s = 0.; result['stable_s'] = 0.
                if tick % 20 == 0: history.append(result)
                if failures: break
                if stable_s >= .75: break
            else: failures.add('native_return_timeout')
        passed = not aborted and not failures and stable_s >= .75
        source_root = Path(__file__).resolve().parents[1]
        sources = ['src/clawmetry_jumper/simulator.py', 'src/clawmetry_jumper/manipulation.py',
                   'src/clawmetry_jumper/contact_plans.py', 'scripts/qualify_desk_skills.py', 'scripts/plan_desk_skills.py']
        return dict(action=action, offset_m=list(offset), entry_tick_offset=entry_tick_offset, passed=passed,
                    outcome='aborted' if aborted else 'completed' if passed else 'failed',
                    permanent_failures=sorted(failures),
                    controller_kind=config['controller_kind'], object_forces_applied=False, object_pose_writes_after_reset=0,
                    fixed_plan=plan, final=result, contact_samples=contacts, max_robot_tilt_deg=max_tilt,
                    minimum_table_margin_m=min_margin, maximum_other_displacement_m=max_other,
                    stages=stage_results, history=history,
                    initial_qpos=initial_qpos,
                    scene_xml_sha256=hashlib.sha256(Path(scene).read_bytes()).hexdigest(),
                    model_xml_sha256=hashlib.sha256(sim.compiled_xml.encode()).hexdigest(),
                    input_provenance=sim.provenance,
                    source_sha256={name: hashlib.sha256((source_root/name).read_bytes()).hexdigest() for name in sources},
                    upstream_commit=sim.provenance['upstream_commit'] if 'upstream_commit' in sim.provenance else sim.provenance)
    finally: sim.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path,required=True);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--action',choices=('cup','cleanup'),default='cup');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--offset',type=float,nargs=2,default=[0.,0.]);p.add_argument('--abort-at',type=float)
    p.add_argument('--entry-tick-offset',type=int,choices=(-1,0,1),default=0)
    a=p.parse_args()
    if a.output.exists(): p.error('Output already exists; choose a new qualification artifact path')
    t=time.time();r=qualify(a.upstream,a.scene,a.action,offset=a.offset,abort_at=a.abort_at,entry_tick_offset=a.entry_tick_offset);r['wall_elapsed_s']=time.time()-t
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as file: file.write(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('passed','outcome','action','final','contact_samples','max_robot_tilt_deg','minimum_table_margin_m','maximum_other_displacement_m','wall_elapsed_s')},indent=2))
    return 0 if r['passed'] or a.abort_at is not None and r['outcome']=='aborted' else 1
if __name__=='__main__':raise SystemExit(main())
