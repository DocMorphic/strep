"""Frozen cross-action, single-rule study; geometry is not semantic approval."""
import copy
import itertools
import shutil
import zipfile
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from strep import model_directory
from action_requests import validate_batch, request_digest, conditioning_texts
from motion_profile import default_profile, brief
from inspect_motion import skeleton_metadata, validate_motion

STUDY = ROOT/'reports/profile-response-v1'
JOB = ROOT/'reports/action-jobs/profile-response-v1'
REQUEST = ROOT/'benchmarks/profile-response-v1.json'
ACTIONS = {
    'wave': 'A person raises their right arm, waves hello, then lowers the arm.',
    'squat': 'A person squats down, then stands upright again.',
    'kick': 'A person performs a forward kick with the right leg, then returns to standing.',
}
CONDITIONS = {'plain': None, 'low': 0, 'middle': 50, 'high': 100}


def angle(a, b):
    a, b = np.asarray(a), np.asarray(b)
    norms = np.linalg.norm(a, axis=-1)*np.linalg.norm(b, axis=-1)
    if not np.isfinite(norms).all() or np.any(norms < 1e-10):
        raise ValueError('Degenerate or nonfinite measurement segment')
    return np.degrees(np.arccos(np.clip(np.sum(a*b, axis=-1)/norms, -1, 1)))


def span(values):
    return float(np.percentile(values, 95)-np.percentile(values, 5))


def descriptors(positions, names):
    p = np.asarray(positions)
    if p.ndim != 3 or p.shape[1:] != (len(names), 3) or len(p) < 2 or not np.isfinite(p).all():
        raise ValueError('Expected finite [frames,joints,3] positions')
    j = {name: p[:, i] for i, name in enumerate(names)}
    torso_down = j['Hips']-j['Neck1']
    shoulder = angle(j['RightForeArm']-j['RightArm'], torso_down)
    # SOMA names the hip joint Leg and the knee joint Shin (not UpLeg/Leg).
    hip = angle(j['RightShin']-j['RightLeg'], torso_down)
    knees = [180-angle(j[s+'Leg']-j[s+'Shin'], j[s+'Foot']-j[s+'Shin']) for s in ['Left','Right']]
    return dict(wave=span(shoulder), squat=float(np.mean([span(v) for v in knees])), kick=span(hip),
                knee_flexion_p95_degrees=float(np.mean([np.percentile(v,95) for v in knees])),
                right_hip_angle_p95_degrees=float(np.percentile(hip,95)),
                right_shoulder_elevation_p95_degrees=float(np.percentile(shoulder,95)))


def freeze():
    if REQUEST.exists() or STUDY.exists() or JOB.exists():
        raise ValueError('Study already exists; do not replace a frozen protocol')
    requests=[]
    for action,prompt in ACTIONS.items():
        for condition,value in CONDITIONS.items():
            r=dict(id=action+'-'+condition,label=f'{action.title()} / mobility {condition}',
                   segments=[dict(prompt=prompt,duration_s=4)],seeds=[301,302,303],scene_requirements=[])
            if value is not None:
                profile=default_profile();profile.update(name='Single mobility rule',style='',training='',state='')
                stat=copy.deepcopy(next(s for s in profile['stats'] if s['id']=='mobility'))
                stat['value']=value;profile['stats']=[stat];r['motion_profile']=profile
            requests.append(r)
    batch=validate_batch(dict(schema_version=1,requests=requests));save(REQUEST,batch)
    save(STUDY/'protocol.json',dict(created_at=now(),request_sha256=request_digest(batch),request_file_sha256=sha256(REQUEST),
        actions=ACTIONS,conditions=CONDITIONS,seeds=[301,302,303],frames=120,fps=30,expected_takes=36,
        status='development_study_not_release_holdout',inference='Unchanged checkpoint, 100 steps, raw finite clips, no correction or constraints.',
        primary_metric='Per-action angular excursion: p95 minus p5 over all 120 frames, in degrees.',
        definitions={'wave':'Right upper-arm elevation relative to torso-down.',
                     'squat':'Mean left/right knee flexion excursion from thigh, knee and ankle positions.',
                     'kick':'Right thigh angle excursion relative to torso-down; unsigned, not anatomical signed hip flexion.'},
        numerical_direction_screen='For each action: median low < middle < high, and high-low > 5 degrees in at least 2 of 3 matched seeds. Strict inequalities. Plain is reported separately, never a profile midpoint.',
        margin_degrees=5,minimum_matching_seeds=2,
        human_review={'status':'not_collected','required':['Action recognizability','Low/high range ranking','Naturalness and editability'],
                      'instruction':'Review all variants including failures. Do not infer these ratings from numerical excursions.'},
        limits=['Three seeds do not estimate general reliability','Unconditioned 4-second output can omit requested action',
                'Angular excursion can grow because of incorrect action or jitter','Mobility describes art direction, not measured physical ability',
                'Unsigned segment angles miss some movement planes; no force, joint-limit or balance certification'],
        release_floor_screen_m=read(ROOT/'benchmarks/project-release-v1.json')['gates']['absolute_surface_penetration_max_m'],
        diagnostic_floor_screen_m=.005,style_response_validated=False))
    shutil.copyfile(Path(__file__),STUDY/'frozen-analysis.py')
    print(f'Frozen {len(requests)} requests / 36 takes; {request_digest(batch)}')


def direction_screen(rows, margin=5., minimum=2):
    by={(r['condition'],r['seed']):r['primary_excursion_degrees'] for r in rows}
    seeds=sorted({r['seed'] for r in rows})
    if len(by)!=len(rows) or set(by)!=set(itertools.product(CONDITIONS,seeds)) or not seeds:
        raise ValueError('Incomplete or duplicate matched conditions')
    if not all(np.isfinite(v) for v in by.values()): raise ValueError('Nonfinite descriptor')
    medians={c:float(np.median([by[c,s] for s in seeds])) for c in CONDITIONS}
    pairs=[dict(seed=s,high_minus_low_degrees=by['high',s]-by['low',s],
                margin_pass=bool(by['high',s]-by['low',s]>margin)) for s in seeds]
    ordered=medians['low']<medians['middle']<medians['high']
    return dict(medians_degrees=medians,matched_pairs=pairs,median_order_pass=bool(ordered),
                numerical_direction_screen_pass=bool(ordered and sum(p['margin_pass'] for p in pairs)>=minimum),
                semantic_review_complete=False,style_response_validated=False)


def analyze():
    protocol=read(STUDY/'protocol.json');batch=validate_batch(read(JOB/'request.json'))
    assert read(JOB/'pipeline.json')['status']=='complete'
    assert request_digest(batch)==protocol['request_sha256']
    assert sha256(REQUEST)==protocol['request_file_sha256']
    cache=read(JOB/'conditioning/manifest.json')
    assert cache['request_sha256']==protocol['request_sha256']
    assert sorted(cache['entries'])==conditioning_texts(batch)
    for entry in cache['entries'].values():assert sha256(JOB/'conditioning'/entry['file'])==entry['sha256']
    checkpoint=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
    assert sha256(model_directory(checkpoint)/'model.safetensors')==checkpoint['files_sha256']['model.safetensors']
    summary=read(JOB/'summary.json');floor={t['id']:t for t in read(JOB/'ground-audit.json')['trials']}
    assert len(summary['trials'])==protocol['expected_takes']
    expected={(r['id'],s) for r in batch['requests'] for s in r['seeds']};seen=set();rows=[];manifest=[]
    for trial in summary['trials']:
        dest=JOB/'takes'/trial['id'];record=read(dest/'generation-record.json');request=trial['request']
        key=(request['id'],trial['seed']);assert key in expected and key not in seen;seen.add(key)
        assert request==next(r for r in batch['requests'] if r['id']==request['id'])==record['request']
        assert record['request_sha256']==protocol['request_sha256'] and record['seed']==trial['seed']
        assert record['checkpoint_sha256']==checkpoint['files_sha256']['model.safetensors']
        assert record['checkpoint_revision']==checkpoint['revision'] and record['diffusion_steps']==100
        assert record['postprocessing'] is False and not record['constraints']
        resolved=brief(request);assert record.get('motion_brief')==resolved==trial.get('motion_brief')
        if resolved:
            assert read(dest/'motion-brief.json')==resolved
            assert sha256(JOB/'profile-implementation/motion_profile.py')==resolved['compiler_sha256']
        for name,digest in trial['hashes'].items():assert sha256(dest/name)==digest
        with zipfile.ZipFile(dest/'animation-pack.zip') as z:
            assert z.testzip() is None
            for name in z.namelist():
                local=ROOT/'vendor/kimodo/LICENSE' if name=='LICENSE.txt' else dest/name
                assert z.read(name)==local.read_bytes()
        motion=dict(np.load(dest/'motion.npz',allow_pickle=False));names,_,_=validate_motion(motion,30)
        assert len(motion['posed_joints'])==120 and sha256(dest/'motion.npz')==record['npz_sha256']==floor[trial['id']]['source_sha256']
        action,condition=request['id'].split('-');desc=descriptors(motion['posed_joints'],names)
        rows.append(dict(id=trial['id'],action=action,condition=condition,seed=trial['seed'],
            primary_excursion_degrees=desc[action],descriptors=desc,source_sha256=record['npz_sha256'],
            mesh_floor_depth_m=floor[trial['id']]['mesh_max_depth_m'],
            exceeds_proposed_release_floor=bool(floor[trial['id']]['mesh_max_depth_m']>protocol['release_floor_screen_m']),
            metrics=trial['metrics'],semantic_review=None,style_review=None))
        manifest.append(dict(id=trial['id'],path=(dest/'soma.glb').relative_to(JOB).as_posix(),sha256=sha256(dest/'soma.glb'),frames=120,fps=30))
    assert seen==expected
    results={a:direction_screen([r for r in rows if r['action']==a],protocol['margin_degrees'],protocol['minimum_matching_seeds']) for a in ACTIONS}
    save(STUDY/'analysis.json',dict(created_at=now(),verification_passed=True,analysis_sha256=sha256(Path(__file__)),
        frozen_analysis_sha256=sha256(STUDY/'frozen-analysis.py'),cases=rows,actions=results,
        quality_approved=False,style_response_validated=False,half_frame_surface_audit=False))
    save(JOB/'manifest.json',dict(cases=manifest));print(results)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','analyze']);a=p.parse_args()
    freeze() if a.command=='freeze' else analyze()
