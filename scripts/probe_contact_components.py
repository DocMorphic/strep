"""Frozen component ablation: raw fingers, authored fingers, and arm edits.

This is a diagnostic sweep, never a candidate selector or a quality approval.
"""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from load_contact_trial import load
from hull_surface_correspondences import correspondences
from verify_palm_region import measure


def run(study, audit, output):
    study, audit, output = [Path(p).resolve() for p in (study, audit, output)]
    recipe = read(study / 'request.json')
    done = read(study / 'completion.json')
    exported = read(audit / 'completion.json')
    if not done['accepted_step'] or done['parameters_sha256'] != sha256(study / 'parameters.json'):
        raise ValueError('Hash-bound accepted development step required')
    if exported['geometry_summary_sha256'] != sha256(audit / 'geometry-summary.json'):
        raise ValueError('Completed full geometry audit required')
    summary = read(audit / 'geometry-summary.json')
    for row in summary['rows']:
        if row['samples_sha256'] != sha256(audit / 'geometry' / row['variant'] / 'samples.json'):
            raise ValueError('Audited samples changed')
    names = sorted(set(recipe['implementation']) | {'probe_contact_components.py'})
    inputs = [study / n for n in ['request.json', 'completion.json', 'parameters.json',
        'initial-parameters.json', 'A-source-local.npz', 'B-source-local.npz', 'palm-region.json']]
    inputs += [audit / n for n in ['completion.json', 'geometry-summary.json',
        'geometry/raw/samples.json', 'geometry/candidate/samples.json']]
    states = [dict(id='raw', fingers='raw_local', arm_scale=0.),
              dict(id='fingers_only', fingers='authored_finger_local', arm_scale=0.),
              dict(id='arms_only', fingers='raw_local', arm_scale=1.)]
    states += [dict(id=f'combined_{int(a*100):03d}', fingers='authored_finger_local', arm_scale=a)
               for a in [.25, .5, .75, 1.]]
    output.mkdir(parents=True, exist_ok=False)
    (output / 'implementation').mkdir()
    for name in names:
        source = ROOT / 'scripts' / name
        if name in recipe['implementation'] and sha256(source) != recipe['implementation'][name]:
            raise ValueError('Trial implementation changed: ' + name)
        shutil.copyfile(source, output / 'implementation' / name)
    proc = psutil.Process()
    request = dict(at=now(), pid=proc.pid, created=proc.create_time(), study=str(study), audit=str(audit),
        inputs={str(p): sha256(p) for p in inputs}, states=states, frames=recipe['frames'],
        endpoint_depth_tolerance_m=2e-6, implementation={n:sha256(output/'implementation'/n) for n in names},
        quality_approved=False, scope='Fixed7-state component ablation on30 existing development times. '
        'Raw finger baseline versus authored fingers and scaled accepted arm controls. No optimization, '
        'new animation generation, export or selection. Endpoints checked against independent decoded audit. '
        'No full-clock, self-collision, physical, anatomical or human-quality claim for intermediate states.')
    save(output / 'request.json', request)

    def phase(status, **details):
        save(output / 'pipeline.json', dict(at=now(), status=status, quality_approved=False, **details))
        print(status, details, flush=True)

    try:
        with threadpool_limits(limits=1):
            _, fitter, faces, initial = load(study)
            candidate = np.asarray(read(study / 'parameters.json')['controls'], float)
            raw = {s['frame']:s for s in read(audit/'geometry/raw/samples.json')['rows']}
            final = {s['frame']:s for s in read(audit/'geometry/candidate/samples.json')['rows']}
            records = []
            local_inputs = []
            preservation = []
            for label, actor in zip(['A','B'], fitter.actors):
                with np.load(study / (label+'-source-local.npz'), allow_pickle=False) as data:
                    values = {key:data[key].copy() for key in ['raw_local','authored_finger_local']}
                delta = np.max(np.abs(values['raw_local'] - values['authored_finger_local']), axis=(0,2,3))
                changed = np.flatnonzero(delta > 1e-10).tolist()
                if not set(changed).issubset(recipe['sources'][label]['finger_nodes']):
                    raise ValueError('Authored posture also changes non-finger local transforms')
                local_inputs.append(values)
                preservation.append(dict(actor=label, changed_local_nodes=changed, finger_only=True))
            lower = np.maximum(-fitter.bounds, initial-np.radians(5))
            upper = np.minimum(fitter.bounds, initial+np.radians(5))
            save(output/'preflight.json', dict(preservation=preservation,
                raw_zero_inside_prior_local_box=bool(np.all(lower<=0) and np.all(upper>=0)),
                raw_zero_outside_coordinates=int(np.sum((lower>0)|(upper<0))),
                max_initial_component_degrees=float(np.degrees(np.abs(initial).max())),
                quality_approved=False))
            for state in states:
                start = time.perf_counter()
                for actor, values in zip(fitter.actors, local_inputs):
                    actor.base.local = values[state['fingers']]
                    actor.cache = None
                controls = candidate * state['arm_scale']
                slack = float(fitter.step_pair(controls)[0].min())
                if slack < -1e-8 or np.any(np.abs(controls)>fitter.bounds+1e-10):
                    raise ValueError('Scaled arm controls violate declared hard bounds')
                rows = []
                for frame in request['frames']:
                    phase('geometry', state=state['id'], completed_samples=len(rows), total_samples=len(request['frames']))
                    _, collision = correspondences(fitter.actors, frame, controls, faces, margin=.003)
                    row = dict(frame=frame, collision=collision)
                    if frame == fitter.event:
                        parts = np.split(controls, [fitter.sizes[0]])
                        points = [a.rig.vertices(a.pose(frame,x))@a.rotation.T+a.translation for a,x in zip(fitter.actors,parts)]
                        row['region'] = measure(points,[a.patch for a in fitter.actors],faces,.003)
                    rows.append(row)
                    save(output/(state['id']+'.json'), dict(rows=rows, quality_approved=False))
                depths = [max(d['max_depth_m'] for d in r['collision']) for r in rows]
                reference = raw if state['id']=='raw' else final if state['id']=='combined_100' else None
                error = max(abs(depth-max(d['max_depth_m'] for d in reference[r['frame']]['collision'])) for depth,r in zip(depths,rows)) if reference else None
                if error is not None and error > request['endpoint_depth_tolerance_m']:
                    raise ValueError('Component endpoint differs from independent decoded geometry')
                event = next(r['region'] for r in rows if r['frame']==fitter.event)
                records.append(dict(**state, max_depth_m=max(depths), samples_over_5mm=sum(d>.005 for d in depths),
                    raw_cap_regressions=[r['frame'] for r,d in zip(rows,depths) if d>max(.005,max(c['max_depth_m'] for c in raw[r['frame']]['collision']))+2e-6],
                    event_region_counts=[d['within_tolerance_count'] for d in event['directions']],
                    event_opposing_normal_degrees=event['opposing_normal_degrees'], event_region=event,
                    endpoint_max_error_m=error, minimum_hard_arm_slack=slack, seconds=time.perf_counter()-start,
                    samples_sha256=sha256(output/(state['id']+'.json'))))
                save(output/'summary.json', dict(rows=records, quality_approved=False))
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest: raise ValueError('Input changed: '+path)
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:
                raise ValueError('Implementation changed: '+name)
        save(output/'completion.json',dict(at=now(),states=len(records),samples_per_state=len(request['frames']),
            summary_sha256=sha256(output/'summary.json'),preflight_sha256=sha256(output/'preflight.json'),quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc())
        raise


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ['study','audit','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.study,a.audit,a.output)
