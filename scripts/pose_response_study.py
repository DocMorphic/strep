"""Explicit native target response across four action families; no semantic certification."""
import argparse,copy,itertools,os,shutil,zipfile
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from strep import model_directory
from action_requests import validate_batch,request_digest,conditioning_texts
from inspect_motion import skeleton_metadata

STUDY=ROOT/'reports/pose-response-v1'
JOB=ROOT/'reports/action-jobs/pose-response-v1'
REQUEST=ROOT/'benchmarks/pose-response-v1.json'
CASES=[('jump-land','RightFoot',45,[0,.06,0]),('crawl','LeftHand',60,[.06,0,0]),('dance','RightHand',75,[0,.08,0]),('get-up','LeftFoot',90,[0,.06,0])]
CONDITIONS=['free','captured','offset']
SEEDS=[501,502,503]

def freeze():
    from pose_target import author
    if STUDY.exists() or JOB.exists() or REQUEST.exists():raise ValueError('Frozen study already exists')
    sources=read(ROOT/'benchmarks/action-coverage-v1.json')['requests'];requests=[];cases=[]
    for action,joint,frame,offset in CASES:
        source=ROOT/'reports/action-coverage-v1/takes'/f'{action}-seed-11'/'motion.npz'
        payload=dict(motion=source.relative_to(ROOT).as_posix(),sha256=sha256(source),source_frame=frame,effector=joint,offset_m=offset,max_edit_degrees=45)
        folder=STUDY/'targets'/action;result=author(payload,folder)
        if not result['reached']:raise ValueError('Target infeasible; preserve result and amend study before generation')
        base=next(r for r in sources if r['id']==action)
        for condition in CONDITIONS:
            request=dict(id=action+'-'+condition,label=action+' / target '+condition,segments=copy.deepcopy(base['segments']),seeds=SEEDS,scene_requirements=[])
            if condition!='free':
                path=folder/('candidate.npz' if condition=='offset' else 'original.npz')
                request['generation_constraints']=[dict(type='end-effector',joint_names=[joint],motion=path.relative_to(ROOT).as_posix(),sha256=sha256(path),source_frames=[0],frame_indices=[frame])]
            requests.append(request)
        cases.append(dict(action=action,joint=joint,opposite_joint=('Left' if joint.startswith('Right') else 'Right')+('Hand' if joint.endswith('Hand') else 'Foot'),frame=frame,offset_m=offset,source=payload,target_folder=folder.relative_to(ROOT).as_posix(),target_audit_sha256=sha256(folder/'audit.json')))
    batch=validate_batch(dict(schema_version=1,requests=requests));save(REQUEST,batch)
    save(STUDY/'protocol.json',dict(created_at=now(),request_sha256=request_digest(batch),request_file_sha256=sha256(REQUEST),cases=cases,conditions=CONDITIONS,seeds=SEEDS,expected_takes=36,
        status='development_generalization_study_not_release_holdout',inference='Unchanged checkpoint100steps; no movement profile or postprocessing; same text and seed within each triple.',
        preflight='Source seed11 fixed. Target/frame/offset feasibility was checked once before freezing; all four reached within45degree budget. No generated study output was examined.',
        primary='At fixed authored frame, project offset-minus-captured generated effector displacement onto requested offset direction. Require at least half requested offset and offset-target error<=30mm in at least2/3 seeds per action.',
        minimum_response_fraction=.5,maximum_target_error_m=.03,minimum_passing_seeds=2,
        secondary=['All three variants error to offset target and original captured target','Selected/opposite effector displacement and travel; diagnostic only, not an action or limb-identity classifier','Source/target hashes, native guide errors, full eight-weight floor, predicted support speed'],
        release_floor_screen_m=read(ROOT/'benchmarks/project-release-v1.json')['gates']['absolute_surface_penetration_max_m'],
        human_review=dict(status='not_collected',required=['Requested action occurs throughout','Intended side/limb matches','No extra action or identity change','Naturalness and cleanup time']),
        limitations=['Single hand/foot guide includes implicit root/heading/hip channels. Free-vs-guided differences cannot be attributed solely to effector.','Captured-vs-offset static targets differ only selected chain and descendants; terminal orientation/root remain fixed.','Four source poses, one offset per action, three new seeds do not prove general reliability.','These actions are held out from target-editor development, not from model training or all prior project experiments.','Floor screen is provisional; target success is not contact, anatomical validity or semantic approval.']))
    shutil.copyfile(__file__,STUDY/'frozen-analysis.py')
    print('Frozen36takes',request_digest(batch))

def response_screen(rows,offset,minimum_fraction=.5,max_error=.03,minimum_seeds=2):
    offset=np.asarray(offset,dtype=float);length=float(np.linalg.norm(offset))
    if offset.shape!=(3,) or not np.isfinite(offset).all() or length<=0:raise ValueError('Invalid offset')
    by={(r['condition'],r['seed']):r for r in rows};seeds=sorted({r['seed'] for r in rows})
    if not seeds or len(by)!=len(rows) or set(by)!=set(itertools.product(CONDITIONS,seeds)):raise ValueError('Incomplete matched triples')
    pairs=[]
    for seed in seeds:
        a,b=by['captured',seed],by['offset',seed]
        change=np.asarray(b['effector_position_m'])-a['effector_position_m']
        fraction=float(np.dot(change,offset)/length**2);error=b['offset_target_error_m']
        if not np.isfinite(change).all() or not np.isfinite(error):raise ValueError('Nonfinite response')
        pairs.append(dict(seed=seed,response_m=float(np.dot(change,offset)/length),response_fraction=fraction,offset_target_error_m=error,
            numerical_pass=bool(fraction>=minimum_fraction and error<=max_error)))
    return dict(pairs=pairs,numerical_response_screen_pass=sum(p['numerical_pass'] for p in pairs)>=minimum_seeds,semantic_review_complete=False,quality_approved=False)

def analyze():
    from generation_constraints import compile_guides
    from audit_generation_guides import audit
    protocol=read(STUDY/'protocol.json');batch=validate_batch(read(JOB/'request.json'))
    assert read(JOB/'pipeline.json')['status']=='complete' and request_digest(batch)==protocol['request_sha256'] and sha256(REQUEST)==protocol['request_file_sha256']
    cache=read(JOB/'conditioning/manifest.json');assert cache['request_sha256']==protocol['request_sha256'] and sorted(cache['entries'])==conditioning_texts(batch)
    for item in cache['entries'].values():assert sha256(JOB/'conditioning'/item['file'])==item['sha256']
    checkpoint=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1'];assert sha256(model_directory(checkpoint)/'model.safetensors')==checkpoint['files_sha256']['model.safetensors']
    summary=read(JOB/'summary.json');floor={r['id']:r for r in read(JOB/'ground-audit.json')['trials']}
    expected={(r['id'],s) for r in batch['requests'] for s in r['seeds']};seen=set();rows=[];manifest=[];names,_,_=skeleton_metadata(77)
    for trial in summary['trials']:
        dest=JOB/'takes'/trial['id'];request=trial['request'];record=read(dest/'generation-record.json');action,condition=request['id'].rsplit('-',1)
        spec=next(c for c in protocol['cases'] if c['action']==action);target=ROOT/spec['target_folder'];assert sha256(target/'audit.json')==spec['target_audit_sha256']
        source=spec['source'];assert sha256(ROOT/source['motion'])==source['sha256']
        key=(request['id'],trial['seed']);assert key in expected and key not in seen;seen.add(key)
        assert request==record['request']==next(r for r in batch['requests'] if r['id']==request['id'])
        assert record['request_sha256']==protocol['request_sha256'] and record['seed']==trial['seed']
        assert record['checkpoint_sha256']==checkpoint['files_sha256']['model.safetensors'] and record['checkpoint_revision']==checkpoint['revision']
        assert record['diffusion_steps']==100 and record['postprocessing'] is False and 'motion_profile' not in request
        compiled,provenance=compile_guides(request);assert record['constraints']==compiled and record['constraint_sources']==provenance
        for filename,digest in trial['hashes'].items():assert sha256(dest/filename)==digest
        with zipfile.ZipFile(dest/'animation-pack.zip') as archive:
            assert archive.testzip() is None
            for filename in archive.namelist():assert archive.read(filename)==(ROOT/'vendor/kimodo/LICENSE' if filename=='LICENSE.txt' else dest/filename).read_bytes()
        data=dict(np.load(dest/'motion.npz',allow_pickle=False));p=data['posed_joints'];f=spec['frame'];j=names.index(spec['joint']);other=names.index(spec['opposite_joint'])
        assert sha256(dest/'motion.npz')==record['npz_sha256']==floor[trial['id']]['source_sha256']
        if compiled:assert audit(data,compiled)==read(dest/'constraint-audit.json')
        with np.load(target/'original.npz',allow_pickle=False) as raw:original=raw['posed_joints'][0,j].copy()
        with np.load(target/'candidate.npz',allow_pickle=False) as raw:desired=raw['posed_joints'][0,j].copy()
        rows.append(dict(id=trial['id'],action=action,condition=condition,seed=trial['seed'],joint=spec['joint'],frame=f,frames=len(p),
            effector_position_m=p[f,j].tolist(),opposite_effector_position_m=p[f,other].tolist(),original_target_m=original.tolist(),offset_target_m=desired.tolist(),
            captured_target_error_m=float(np.linalg.norm(p[f,j]-original)),offset_target_error_m=float(np.linalg.norm(p[f,j]-desired)),
            effector_travel_m=float(np.linalg.norm(np.diff(p[:,j],axis=0),axis=1).sum()),opposite_effector_travel_m=float(np.linalg.norm(np.diff(p[:,other],axis=0),axis=1).sum()),
            source_sha256=sha256(dest/'motion.npz'),mesh_floor_depth_m=floor[trial['id']]['mesh_max_depth_m'],exceeds_proposed_floor=bool(floor[trial['id']]['mesh_max_depth_m']>protocol['release_floor_screen_m']),
            guidance=trial.get('generation_constraints'),metrics=trial['metrics'],semantic_review=None))
        manifest.append(dict(id=trial['id'],path=(dest/'soma.glb').relative_to(JOB).as_posix(),sha256=sha256(dest/'soma.glb'),frames=len(p),fps=30))
    assert seen==expected and len(rows)==protocol['expected_takes']
    results={s['action']:response_screen([r for r in rows if r['action']==s['action']],s['offset_m'],protocol['minimum_response_fraction'],protocol['maximum_target_error_m'],protocol['minimum_passing_seeds']) for s in protocol['cases']}
    save(STUDY/'analysis.json',dict(created_at=now(),verification_passed=True,cases=rows,actions=results,quality_approved=False,analysis_sha256=sha256(Path(__file__)),frozen_analysis_sha256=sha256(STUDY/'frozen-analysis.py')))
    save(JOB/'manifest.json',dict(cases=manifest));print(results)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','analyze']);a=p.parse_args();freeze() if a.command=='freeze' else analyze()
