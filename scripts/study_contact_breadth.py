"""Predeclared cross-family contact fitting and root feasibility experiments."""
import argparse
import json
from pathlib import Path
import re
import shutil
import time
import traceback

import numpy as np
import psutil
import torch
from threadpoolctl import threadpool_limits

from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from contact_spec import validate
from contact_timing_job import prepare as prepare_check, run as run_check, validate_options
from checked_contact_job import prepare as prepare_fit, verify as verify_fit
from floor_contact import Surface
from support_contact import regions


def validate_protocol(plan):
    if plan.get('schema_version')!=1 or not re.fullmatch(r'[a-z0-9-]{1,45}',plan.get('id','')):
        raise ValueError('Versioned development protocol identifier required')
    if not re.fullmatch(r'[a-z0-9-]{1,70}',plan.get('source_collection','')):
        raise ValueError('Simple source collection identifier required')
    if plan.get('quality_approved') is not False: raise ValueError('Development study cannot approve quality')
    if plan.get('fit')!=dict(outer_stage_count=4,iteration_count=120,authored_point_scaling='tolerance',
                            export_floor_guard=True,export_point_position_guard=True):
        raise ValueError('This protocol uses the retained four-stage fitting method')
    if plan.get('repair')!=dict(attempts=6,trust_m=1e-5,normalized_margin=1e-4):
        raise ValueError('Root repair protocol must match the implemented method')
    binding=plan.get('binding',{})
    if set(binding)!={'offset_m','minimum_target_y_m'} or len(binding['offset_m'])!=3:
        raise ValueError('Declared target binding required')
    if not np.isfinite(binding['offset_m']).all() or not np.isfinite(binding['minimum_target_y_m']) or binding['minimum_target_y_m']<0:
        raise ValueError('Finite target binding and nonnegative height required')
    cases=plan.get('cases')
    if not isinstance(cases,list) or not cases: raise ValueError('Predeclared cases required')
    ids=set()
    for row in cases:
        if not re.fullmatch(r'[a-z0-9-]{1,40}',row.get('id','')) or row['id'] in ids:
            raise ValueError('Distinct simple case identifiers required')
        if not re.fullmatch(r'[a-z0-9-]{1,70}',row.get('take_id','')): raise ValueError('Simple take identifier required')
        ids.add(row['id'])
        if type(row.get('seed'))!=int or type(row.get('frames'))!=int: raise ValueError('Integer source seed and frame count required')
        pin=row.get('pin')
        if not isinstance(pin,list) or len(pin)!=2 or any(type(f)!=int for f in pin): raise ValueError('Declared pin interval required')
        spec=dict(regions={row.get('region',''):dict(mode='explicit',segments=[dict(start_frame=pin[0],end_frame=pin[1],space='world')])})
        validate_options(dict(edit_window=row.get('window')),spec,row['frames'])
    return plan


def bind_case(plan,case,motion,skin):
    if len(motion['root_positions'])!=case['frames']: raise ValueError('Source clock differs from declaration')
    groups=regions(skin)
    if case['region'] not in groups: raise ValueError('Unknown declared region')
    surface=Surface(skin);a,b=case['pin'];ids=groups[case['region']]
    points=surface.vertices(motion['global_rot_mats'][a],motion['posed_joints'][a],ids)
    vertex=int(ids[points[:,1].argmin()]);middle=(a+b)//2
    target=surface.vertices(motion['global_rot_mats'][middle],motion['posed_joints'][middle],np.array([vertex]))[0]
    target=target+np.asarray(plan['binding']['offset_m'])
    target[1]=max(float(target[1]),plan['binding']['minimum_target_y_m'])
    spec=dict(schema_version=1,fps=30,frame_count=case['frames'],regions={case['region']:dict(mode='explicit',segments=[
        dict(start_frame=a,end_frame=b,vertex_id=vertex,space='world',position_m=target.tolist())])})
    validate(spec,case['frames'],groups);validate_options(dict(edit_window=case['window']),spec,case['frames'])
    return spec


def job_path(plan,case,stage):
    return ROOT/'reports/contact-jobs'/(plan['id']+'-'+case['id']+'-'+stage)


def verify_suite(folder):
    frozen=read(folder/'freeze.json')
    for name,digest in frozen['inputs'].items():
        if sha256(Path(name))!=digest: raise ValueError('Frozen study input changed: '+name)
    for name,digest in frozen['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest or sha256(folder/'implementation'/name)!=digest:
            raise ValueError('Frozen study method changed: '+name)
    if sha256(folder/'protocol.json')!=frozen['protocol_sha256']: raise ValueError('Frozen protocol changed')


def prepare(protocol_path,folder):
    protocol_path,folder=Path(protocol_path).resolve(),Path(folder).resolve()
    plan=validate_protocol(read(protocol_path))
    if folder.exists(): raise ValueError('Preserve prior study')
    if any(job_path(plan,c,s).exists() for c in plan['cases'] for s in ['check','fit','repair']):
        raise ValueError('A declared job already exists; preserve it')
    # Holdout reservations are inspected only for overlap, never used to tune.
    reservation=ROOT/'benchmarks/release-prompt-reservations-v1.json'
    reserved_seeds={seed for c in read(reservation)['cases'] for seed in c['seeds']}
    if any(c['seed'] in reserved_seeds for c in plan['cases']): raise ValueError('Development seed overlaps release reservation')
    inputs={str(ASSET):sha256(ASSET),str(protocol_path):sha256(protocol_path),str(reservation):sha256(reservation)}
    for case in plan['cases']:
        source=ROOT/'reports'/plan['source_collection']/'takes'/case['take_id']
        for name in ['motion.npz','soma.glb','motion.bvh','root-motion.json','contacts.json','evidence.json','request.json','timeline.json','generation-record.json']:
            inputs[str(source/name)]=sha256(source/name)
        for part in ['raw','limb']:
            for path in (source/part).rglob('*'):
                if path.is_file(): inputs[str(path)]=sha256(path)
        record=read(source/'evidence.json')
        if record.get('seed')!=case['seed']: raise ValueError('Source seed differs from declaration')
    folder.mkdir(parents=True);shutil.copyfile(protocol_path,folder/'protocol.json');(folder/'implementation').mkdir()
    methods={}
    for path in (ROOT/'scripts').glob('*.py'):
        shutil.copyfile(path,folder/'implementation'/path.name);methods[path.name]=sha256(path)
    save(folder/'freeze.json',dict(created_at=now(),inputs=inputs,implementation=methods,protocol_sha256=sha256(folder/'protocol.json')))
    save(folder/'pipeline.json',dict(status='prepared',quality_approved=False))
    verify_suite(folder)


def prepare_cases(folder):
    """Freeze every binding and run all timing checks before fitting any case."""
    verify_suite(folder);plan=read(folder/'protocol.json');skin=dict(np.load(ASSET));rows=[]
    for case in plan['cases']:
        source=ROOT/'reports'/plan['source_collection']/'takes'/case['take_id']
        motion=dict(np.load(source/'motion.npz'));spec=bind_case(plan,case,motion,skin)
        check=job_path(plan,case,'check');prepare_check(source,spec,dict(edit_window=case['window']),check)
        result=run_check(check);save(check/'pipeline.json',result)
        # Root Y cannot alter XZ. This is a necessary source-initializer test,
        # not a verdict on full pose fitting or on a later fitted initializer.
        from export_point_position_objective import ExportPointPositionObjective
        from inspect_motion import skeleton_metadata
        _,parents,*_=skeleton_metadata(77);tensor=lambda a:torch.tensor(a,dtype=torch.float64)
        obj=ExportPointPositionObjective(tensor(motion['global_rot_mats']),tensor(motion['posed_joints']),parents,skin,spec)
        with torch.no_grad(): track=obj.points(tensor(motion['global_rot_mats']),tensor(motion['posed_joints'])).numpy()
        a,b=case['pin'];target=spec['regions'][case['region']]['segments'][0]['position_m']
        horizontal=np.linalg.norm((track[a*4:b*4+1,0]-target)[:,[0,2]],axis=1)
        row=dict(id=case['id'],family=case['family'],status=result['status'],conflicts=result['conflicts'],
            check_revision=sha256(check/'timing-result.json'),spec=spec,
            original_source_root_only_position_lower_bound_m=float(horizontal.max()),
            root_only_source_position_impossible=bool(horizontal.max()>.005),quality_approved=False)
        rows.append(row);save(folder/'preflight.json',dict(cases=rows,complete=False,quality_approved=False))
        print('preflight',case['id'],result['status'],'conflicts',result['conflicts'],'root-only source lower bound',float(horizontal.max()),flush=True)
    verify_suite(folder);save(folder/'preflight.json',dict(cases=rows,complete=True,quality_approved=False))
    save(folder/'pipeline.json',dict(status='checks_complete',quality_approved=False))


def run_case(folder,case_id):
    verify_suite(folder);plan=read(folder/'protocol.json');preflight=read(folder/'preflight.json')
    if not preflight['complete']: raise ValueError('Freeze and check every case before fitting')
    case=next(c for c in plan['cases'] if c['id']==case_id)
    checked=next(c for c in preflight['cases'] if c['id']==case_id)
    result_path=folder/'cases'/(case_id+'.json')
    if result_path.exists(): raise ValueError('Preserve existing case result')
    if checked['status']!='checked':
        save(result_path,dict(id=case_id,status='timing_rejected',conflicts=checked['conflicts'],fit_started=False,quality_approved=False))
        print('case',case_id,'timing_rejected',flush=True);return
    fit=job_path(plan,case,'fit');repair=job_path(plan,case,'repair');check=job_path(plan,case,'check')
    prepare_fit(dict(checked_plan=check.name,revision=checked['check_revision']),fit)
    save(fit/'breadth-protocol.json',dict(suite_protocol_sha256=sha256(folder/'protocol.json'),case=case,fit=plan['fit']))
    frozen=read(fit/'checked-freeze.json');frozen['inputs']['breadth-protocol.json']=sha256(fit/'breadth-protocol.json');save(fit/'checked-freeze.json',frozen)
    process=psutil.Process();save(fit/'worker.json',dict(pid=process.pid,created=process.create_time()))
    save(fit/'pipeline.json',dict(status='processing',kind='checked_fit'));started=time.perf_counter()
    try:
        from run_contact_edit import run as edit
        verify_fit(fit)
        edit(fit/'source-take',fit/'checked-plan/bound-contact-spec.json',fit/'result',checked_plan=fit/'checked-plan',**plan['fit'])
        verify_fit(fit);verify_suite(folder)
        save(fit/'pipeline.json',dict(status='complete',kind='checked_fit'))
        save(fit/'breadth-result.json',dict(elapsed_s=time.perf_counter()-started,summary_sha256=sha256(fit/'result/summary.json'),quality_approved=False))
        from study_root_height_feasibility import run as repair_run
        repair_run(fit,repair)
        before=read(fit/'result/takes'/case['take_id']/'checked-export-audit.json')
        after=read(repair/'candidate/checked-export-audit.json');completion=read(repair/'completion.json')
        verify_fit(fit);verify_fit(repair);verify_suite(folder)
        save(result_path,dict(id=case_id,status='complete',family=case['family'],elapsed_s=time.perf_counter()-started,
            fit_job=str(fit),repair_job=str(repair),before=before,after=after,repair=completion,quality_approved=False))
        print('case',case_id,'complete','contact screen',completion['checked_contact_export_screen_passed'],flush=True)
    except BaseException as exc:
        save(result_path,dict(id=case_id,status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False))
        # Keep a completed fit distinct from a later correction failure.
        if read(fit/'pipeline.json')['status']!='complete':save(fit/'pipeline.json',dict(status='failed',kind='checked_fit',error=str(exc)))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','checks','case']);parser.add_argument('folder',type=Path)
    parser.add_argument('--protocol',type=Path);parser.add_argument('--case-id');args=parser.parse_args()
    with threadpool_limits(limits=1):
        if args.command=='prepare':
            if args.protocol is None:parser.error('--protocol required')
            prepare(args.protocol,args.folder.resolve())
        elif args.command=='checks':prepare_cases(args.folder.resolve())
        else:
            if args.case_id is None:parser.error('--case-id required')
            run_case(args.folder.resolve(),args.case_id)
