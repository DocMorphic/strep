"""Measure the existing matched profile response after character transfer."""
import argparse
import ast
from pathlib import Path
import itertools
import shutil
import traceback
import numpy as np
from strep import ROOT,read,save,sha256,now
from breadth_transfer_study import IMPLEMENTATION,run as transfer_run,validate
from profile_response_study import descriptors,direction_screen


def target_descriptors(positions,mapping):
    required=['Hips','Neck1','RightArm','RightForeArm','RightLeg','RightShin','RightFoot','LeftLeg','LeftShin','LeftFoot']
    if any(role not in mapping for role in required):raise ValueError('Metric requires explicit mapped semantic joints')
    indices=[mapping[role] for role in required]
    if len(set(indices))!=len(indices):raise ValueError('Metric roles must be distinct')
    positions=np.asarray(positions)
    if positions.ndim!=3 or positions.shape[2]!=3 or any(isinstance(i,(bool,np.bool_)) or not isinstance(i,(int,np.integer)) or not 0<=i<positions.shape[1] for i in indices):raise ValueError('Metric mapping outside joint array')
    return descriptors(np.asarray(positions)[:,indices],required)


def prepare(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous study')
    study=ROOT/'reports/profile-response-v1';job=ROOT/'reports/action-jobs/profile-response-v1'
    analysis=read(study/'analysis.json');protocol=read(study/'protocol.json');summary=read(job/'summary.json')
    if read(job/'pipeline.json')['status']!='complete' or not analysis['verification_passed']:raise ValueError('Complete source profile study required')
    executed=study/'executed-analysis.py'
    if sha256(executed)!=analysis['analysis_sha256']:raise ValueError('Executed source analysis changed')
    # The current module only changed model-directory resolution after this
    # study. Require identical metric/scoring functions, not an obsolete path.
    definitions=[]
    for path in [executed,ROOT/'scripts/profile_response_study.py']:
        tree=ast.parse(path.read_text(encoding='utf-8'))
        definitions.append({node.name:ast.dump(node,include_attributes=False) for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ['angle','span','descriptors','direction_screen']})
    if definitions[0]!=definitions[1] or len(definitions[0])!=4:raise ValueError('Source metric/scoring implementation differs')
    expected=set(itertools.product(protocol['actions'],protocol['conditions'],protocol['seeds']))
    if len(analysis['cases'])!=36 or {(r['action'],r['condition'],r['seed']) for r in analysis['cases']}!=expected:raise ValueError('Require full36 source population')
    output.mkdir(parents=True);(output/'implementation').mkdir()
    shutil.copyfile(executed,output/'source-executed-analysis.py')
    fixture=ROOT/'reports/breadth-transfer-v1';fixture_protocol=read(fixture/'protocol.json');rigs=fixture_protocol['rigs']
    if len(rigs)!=3:raise ValueError('Require all three existing rig fixtures')
    for rig in rigs:
        folder=output/rig['directory'];folder.mkdir(parents=True)
        for name,digest in rig['files'].items():
            source=fixture/rig['directory']/name
            if sha256(source)!=digest:raise ValueError('Rig fixture changed')
            shutil.copyfile(source,folder/name)
        if 'Neck1' not in read(folder/'profile.json')['mapping']:raise ValueError('Required metric landmark missing')
    motions=[]
    for source_row in analysis['cases']:
        trial=next(r for r in summary['trials'] if r['id']==source_row['id']);folder=job/'takes'/source_row['id'];record=read(folder/'generation-record.json')
        if record['request_sha256']!=protocol['request_sha256'] or trial['seed']!=source_row['seed'] or trial['request']['id']!=source_row['action']+'-'+source_row['condition']:raise ValueError('Source request identity differs')
        for name,digest in trial['hashes'].items():
            if sha256(folder/name)!=digest:raise ValueError('Source output changed')
        if sha256(folder/'motion.npz')!=source_row['source_sha256']:raise ValueError('Source analysis motion differs')
        motions.append(dict(id=source_row['id'],request_id=trial['request']['id'],seed=source_row['seed'],case=source_row['action'],action=source_row['action'],condition=source_row['condition'],family='profile-response',prompt=trial['request']['segments'][0]['prompt'],frames=120,fps=30,source=str(folder/'motion.npz'),source_sha256=source_row['source_sha256'],native_glb=str(folder/'soma.glb'),native_glb_sha256=sha256(folder/'soma.glb'),flat_floor_screen_applicable=True,scene_validation='No object or partner geometry in source requests',native_mesh_depth_m=source_row['mesh_floor_depth_m']))
    names=sorted(set(IMPLEMENTATION)|{'profile_transfer_study.py','profile_response_study.py','rig_clip_import.py','strep.py'})
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    spec=dict(schema=1,created_at=now(),source_study=str(study),source_analysis_sha256=sha256(study/'analysis.json'),source_executed_analysis_sha256=sha256(executed),descriptor_functions_match_executed_source=True,source_protocol_sha256=sha256(study/'protocol.json'),source_summary_sha256=sha256(job/'summary.json'),rig_fixture_protocol_sha256=sha256(fixture/'protocol.json'),rigs=rigs,motions=motions,cpu_threads=1,gpu_enabled=False,floor_screen_m=.01,planned_transfers=108,planned_engine_clips=144,
        implementation={n:sha256(output/'implementation'/n) for n in names},metric='Same whole-clip segment-angle p95-p5 definitions and semantic landmarks as source profile-response-v1',numerical_direction_screen=dict(margin_degrees=protocol['margin_degrees'],minimum_matching_seeds=protocol['minimum_matching_seeds']),
        scope='All36 previously generated profile takes, three existing rigs/two rig families. No new generation, corrections or profile changes. Measure response retention alongside floor/support/export defects. Development only: no held-out/style/action/physical approval; source squat and kick responses already failed.')
    save(output/'protocol.json',spec);save(output/'freeze.json',dict(protocol_sha256=sha256(output/'protocol.json')))
    save(output/'results.json',dict(rows=[dict(id=m['id']+'-'+r['id'],motion=m['id'],rig=r['id'],status='pending',quality_approved=False) for m in motions for r in rigs],engine_groups=[],quality_approved=False))
    save(output/'pipeline.json',dict(status='prepared',planned_transfers=108,quality_approved=False))
    return spec


def analyze(output):
    from inspect_motion import validate_motion
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    output=Path(output).resolve();spec=validate(output);data=read(output/'results.json');source_study=Path(spec['source_study'])
    if sha256(source_study/'analysis.json')!=spec['source_analysis_sha256'] or sha256(source_study/'protocol.json')!=spec['source_protocol_sha256']:raise ValueError('Source profile evidence changed')
    baseline=read(source_study/'analysis.json');source_by={r['id']:r for r in baseline['cases']};rows=[]
    expected={(m['id'],r['id']) for m in spec['motions'] for r in spec['rigs']}
    if len(data['rows'])!=len(expected) or {(r['motion'],r['rig']) for r in data['rows']}!=expected:raise ValueError('Transfer population differs')
    native={}
    for motion in spec['motions']:
        if sha256(motion['source'])!=motion['source_sha256']:raise ValueError('Source motion changed')
        raw=dict(np.load(motion['source'],allow_pickle=False));names,_,_=validate_motion(raw,30);desc=descriptors(raw['posed_joints'],names)
        if abs(desc[motion['action']]-source_by[motion['id']]['primary_excursion_degrees'])>1e-4:raise ValueError('Original descriptor does not reproduce')
        native[motion['id']]=desc
    motions={m['id']:m for m in spec['motions']}
    for row in data['rows']:
        m=motions[row['motion']];result=dict(id=row['id'],rig=row['rig'],motion=row['motion'],action=m['action'],condition=m['condition'],seed=m['seed'],status=row['status'],source_primary_excursion_degrees=native[m['id']][m['action']],semantic_review=None,style_response_validated=False)
        if row['status']=='complete':
            folder=output/'takes'/row['id']
            for name,digest in row['files'].items():
                if sha256(folder/name)!=digest:raise ValueError('Transfer evidence changed')
            report=read(folder/'report.json')
            if report['source_sha256']!=m['source_sha256'] or report['frames']!=m['frames']:raise ValueError('Retargeted source/clock differs')
            rig=RigAsset.load(folder/'character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
            positions=np.array([sampler.sample(float(np.float32(f/30)))[:,:3,3] for f in range(m['frames'])])
            desc=target_descriptors(positions,report['mapping'])
            result.update(primary_excursion_degrees=desc[m['action']],descriptors=desc,excursion_change_degrees=desc[m['action']]-native[m['id']][m['action']],target_mesh_floor_depth_max_m=row['result']['target_mesh_floor_depth_max_m'])
        else:result['error']=row.get('error','Missing completed transfer')
        rows.append(result)
    groups={}
    for rig in spec['rigs']:
        for action in ['wave','squat','kick']:
            selected=[r for r in rows if r['rig']==rig['id'] and r['action']==action];key=rig['id']+'/'+action
            groups[key]=direction_screen(selected,spec['numerical_direction_screen']['margin_degrees'],spec['numerical_direction_screen']['minimum_matching_seeds']) if all(r['status']=='complete' for r in selected) else dict(numerical_direction_screen_pass=None,reason='Incomplete transfer population',style_response_validated=False)
    engine=[]
    if len(data['engine_groups'])!=len(motions) or {g['motion'] for g in data['engine_groups']}!=set(motions):raise ValueError('Engine group population differs')
    for group in data['engine_groups']:
        if group['status']!='complete':engine.append(dict(motion=group['motion'],status=group['status'],error=group.get('error')));continue
        path=Path(group['verification']);proof=read(path)
        if proof['checks']!=group['checks'] or len(proof['checks'])!=group['verified_clips']:raise ValueError('Engine population mismatch')
        expected_checks={group['motion']+'-native':motions[group['motion']]['native_glb_sha256']}
        for rig in spec['rigs']:
            identifier=group['motion']+'-'+rig['id']
            if next(r for r in data['rows'] if r['id']==identifier)['status']=='complete':expected_checks[identifier]=sha256(output/'takes'/identifier/'character.glb')
        if {c['id'] for c in proof['checks']}!=set(expected_checks):raise ValueError('Engine clips differ')
        for c in proof['checks']:
            if c['frames']!=120 or c['source_sha256']!=expected_checks[c['id']]:raise ValueError('Engine source/frame mismatch')
        engine.append(dict(motion=group['motion'],status='complete' if len(expected_checks)==4 else 'incomplete',actor_frames=120*len(expected_checks),expected_clips=4,verified_clips=len(expected_checks),verification_sha256=sha256(path)))
    save(output/'profile-analysis.json',dict(at=now(),planned=108,complete=sum(r['status']=='complete' for r in rows),rows=rows,target_response=groups,source_response=baseline['actions'],engine=engine,protocol_sha256=sha256(output/'protocol.json'),results_sha256=sha256(output/'results.json'),quality_approved=False,style_response_validated=False))
    return rows,groups


def run(output):
    try:
        transfer_run(output);analyze(output)
    except BaseException as exc:
        save(Path(output)/'profile-analysis-failure.json',dict(at=now(),error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run','analyze']);p.add_argument('output',type=Path);a=p.parse_args()
    {'prepare':prepare,'run':run,'analyze':analyze}[a.command](a.output)
