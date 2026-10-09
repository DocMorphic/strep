"""Matched serial 60 Hz Jolt CCD probes; preserve all original motion checks."""
import argparse
from pathlib import Path
import time
from scene_collision_profile import PROFILES,matched_settings
from study_scene_prop_ownership import study,verify,METHODS
from strep import ROOT,read,save,sha256,now


def compare(paths):
    runs=[]
    for path in paths:
        path=Path(path)
        request=read(path/'request.json');raw=read(path/'engine-output.json');result=read(path/'result.json')
        if result['request_sha256']!=sha256(path/'request.json') or result['raw_output_sha256']!=sha256(path/'engine-output.json'):
            raise ValueError('Study artifact binding changed')
        for name,digest in request['methods_sha256'].items():
            if digest!=sha256(path/'methods'/name):raise ValueError('Archived implementation changed')
        checked=verify(request,raw)
        if any(result.get(key)!=value for key,value in checked.items()):raise ValueError('Result does not replay actual observations')
        runs.append((path,request,raw,result))
    if len(runs)!=len(PROFILES) or [r[1]['collision_profile'] for r in runs]!=list(PROFILES):
        raise ValueError('Complete baseline and both CCD probes required in order')
    _,base,base_raw,base_result=runs[0];rows=[]
    for path,request,raw,result in runs:
        if request['physics_fps']!=60 or any(request[key]!=base[key] for key in ('physics_fps','cases','methods_sha256','engine_sha256')):
            raise ValueError('Matched 60 Hz engine, source and authored cases required')
        if raw['engine']!=base_raw['engine'] or raw['backend']!=base_raw['backend']:
            raise ValueError('Actual engine identity changed')
        changes=matched_settings(base_result['collision_settings'],result['collision_settings'],request['collision_profile'],60)
        positives=[c for c in result['cases'] if c['id'] in ('shared','reverse-body-order')]
        rows.append(dict(profile=request['collision_profile'],settings_changed=changes,
            result_sha256=sha256(path/'result.json'),request_sha256=sha256(path/'request.json'),raw_sha256=sha256(path/'engine-output.json'),
            actual_engine_cases=len(result['cases']),positive_cases=positives,
            all_four_fault_cases_detected=all(c.get('fault_detected') is True for c in result['cases'] if c['id'] not in ('shared','reverse-body-order')),
            discrete_depth_screen_passed=all(c['discrete_collision_depth_screens_passed'] for c in positives),
            exact_physical_timing_passed=all(c['exact_physical_event_timing_passed'] for c in positives)))
    return dict(schema='strep-scene-collision-profiles-v1',at=now(),rows=rows,
        engine_sha256=base['engine_sha256'],actual_engine=base_raw['engine'],baseline_settings=base_result['collision_settings'],
        matched_authored_scene_and_methods=True,physics_fps=60,surface_depth_limit_m=.01,
        renderer_executed=False,human_reviewed=False,quality_approved=False,release_approved=False)


def run(output):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'reports').resolve()):raise ValueError('Fresh local reports path required')
    output.mkdir(parents=True,exist_ok=False)
    bound={name:sha256(ROOT/'scripts'/name) for name in METHODS+['study_scene_collision_profiles.py']}
    paths=[];wall={}
    for name in PROFILES:
        path=output/name;start=time.monotonic();study(path,60,name);wall[name]=time.monotonic()-start;paths.append(path)
        if any(sha256(ROOT/'scripts'/key)!=value for key,value in bound.items()):raise ValueError('Active study sources changed')
    result=compare(paths);result.update(serial_wall_seconds=wall,methods_sha256=bound)
    save(output/'comparison.json',result)
    print('CCD comparison:',[(r['profile'],r['discrete_depth_screen_passed'],r['exact_physical_timing_passed']) for r in result['rows']])
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
