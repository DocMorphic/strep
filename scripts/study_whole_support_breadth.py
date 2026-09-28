"""Fixed eight-action, three-rig development study of combined support correction."""
import argparse
import os
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now
from study_breadth_contact import SOURCES as BASE_SOURCES

FAMILIES=['locomotion','dance_and_performance','gestures_and_expression','parkour',
          'ground_and_recovery','everyday_tasks','stylized_and_capability','combat']
RIGS=['rig-01','rig-02','rig-03']
SOURCES=sorted(set(BASE_SOURCES+['strep.py','breadth_transfer_study.py','support_reference_fit.py',
    'support_clip_boundary.py','support_clip_start.py','support_curvature.py','relax_whole_support.py',
    'support_whole_clip.py','support_velocity_traces.py','study_whole_support_breadth.py','audit_paired_guides.py']))


def select(protocol,seed=1301):
    """Do not silently drop a missing, duplicate or ineligible declared family."""
    first=[m for m in protocol['motions'] if m['seed']==seed]
    selected=[]
    if [r['id'] for r in protocol['rigs']]!=RIGS:
        raise ValueError('Require the three declared rigs in order')
    for family in FAMILIES:
        matches=[m for m in first if m['family']==family]
        if len(matches)!=1:raise ValueError('Require exactly one first-seed action for '+family)
        m=matches[0]
        if m['flat_floor_screen_applicable'] is not True or m['fps']!=30 or m['frames']<3:
            raise ValueError('Action is not eligible for the declared floor/clock protocol: '+family)
        selected.append(m)
    if {m['id'] for m in first if m['flat_floor_screen_applicable']}!={m['id'] for m in selected}:
        raise ValueError('Unexpected eligible first-seed action; revise protocol explicitly')
    return selected,[m for m in first if m not in selected]


def prepare(source,output,wait_for):
    from breadth_transfer_study import validate as transfer_validate
    from build_soma_preview import ASSET
    source,output,wait_for=[Path(p).resolve() for p in [source,output,wait_for]]
    if output.exists():raise ValueError('Preserve earlier study')
    if read(source/'pipeline.json')['status']!='complete':raise ValueError('Transfer baseline incomplete')
    baseline=transfer_validate(source);motions,excluded=select(baseline);data=read(source/'results.json')
    owner=read(wait_for/'request.json');cases=[]
    for motion in motions:
        group=next(g for g in data['engine_groups'] if g['motion']==motion['id'])
        if group['status']!='complete':raise ValueError('Baseline engine evidence incomplete')
        proof=read(group['verification'])
        if proof['checks']!=group['checks']:raise ValueError('Baseline engine checks changed')
        for rig in RIGS:
            identifier=motion['id']+'-'+rig;row=next(r for r in data['rows'] if r['id']==identifier)
            if row['status']!='complete':raise ValueError('Missing declared transfer '+identifier)
            check=next(c for c in proof['checks'] if c['id']==identifier)
            if check['source_sha256']!=row['files']['character.glb'] or check['frames']!=motion['frames']:
                raise ValueError('Baseline engine source/clock mismatch')
            cases.append(dict(id=identifier,motion=motion,rig=rig,source=str(source/'takes'/identifier),files=row['files'],
                baseline_engine_proof=group['verification'],baseline_engine_sha256=sha256(group['verification'])))
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in SOURCES:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    protocol=dict(at=now(),source=str(source),source_protocol_sha256=sha256(source/'protocol.json'),
        source_results_sha256=sha256(source/'results.json'),cases=cases,excluded_context_cases=excluded,rigs=baseline['rigs'],
        wait_for=dict(folder=str(wait_for),pid=owner['pid'],created=owner['created'],request_sha256=sha256(wait_for/'request.json')),
        implementation={n:sha256(output/'implementation'/n) for n in SOURCES},
        resources={str(ASSET):sha256(ASSET),str(engine):sha256(engine)},
        method='whole_support_curvature_10',initialization='zero edits on raw transfer',sweeps=6,root_curvature_weight=10.,support_weight=40.,
        planned_candidates=len(cases),planned_engine_actor_frames=sum(c['motion']['frames']*2 for c in cases),
        selection='All eight floor-eligible first-seed actions, all three pre-existing rigs, fixed noncombat-first order. Weight10 chosen in earlier combat development comparisons; not held-out evaluation.',
        scope='Development breadth only. Flat-floor foot proxies do not validate kneeling hand/knee contact, jumping semantics, scene/partner interactions or realism. Retain all failures; no per-case tuning or release approval.',quality_approved=False)
    save(output/'protocol.json',protocol);save(output/'freeze.json',dict(protocol_sha256=sha256(output/'protocol.json')))
    save(output/'results.json',dict(rows=[dict(id=c['id'],status='pending') for c in cases],engine_groups=[],quality_approved=False))
    save(output/'pipeline.json',dict(status='prepared',at=now(),quality_approved=False))
    validate(output)
    return protocol


def validate(output):
    output=Path(output);p=read(output/'protocol.json')
    if sha256(output/'protocol.json')!=read(output/'freeze.json')['protocol_sha256']:raise ValueError('Study protocol changed')
    for name,digest in p['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:
            raise ValueError('Frozen implementation changed: '+name)
    for path,digest in p['resources'].items():
        if sha256(path)!=digest:raise ValueError('Resource changed: '+path)
    source=Path(p['source'])
    for name,key in [('protocol.json','source_protocol_sha256'),('results.json','source_results_sha256')]:
        if sha256(source/name)!=p[key]:raise ValueError('Baseline evidence changed')
    dependency=p['wait_for']
    if sha256(Path(dependency['folder'])/'request.json')!=dependency['request_sha256']:raise ValueError('Dependency identity changed')
    for case in p['cases']:
        for name,digest in case['files'].items():
            if sha256(Path(case['source'])/name)!=digest:raise ValueError('Baseline artifact changed: '+case['id']+'/'+name)
        if sha256(case['baseline_engine_proof'])!=case['baseline_engine_sha256']:raise ValueError('Baseline engine proof changed')
        m=case['motion']
        if sha256(m['source'])!=m['source_sha256']:raise ValueError('Raw motion changed')
    return p


def check_engine(proof,checks):
    if len(proof['checks'])!=len(checks):raise ValueError('Incomplete engine population')
    for actual,expected in zip(proof['checks'],checks):
        if actual['id']!=expected['id'] or actual['frames']!=expected['frames'] or actual['source_sha256']!=expected['sha256']:
            raise ValueError('Engine input/clock mismatch')
    return sum(c['frames'] for c in proof['checks'])


def run(output):
    output=Path(output).resolve();p=validate(output)
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Study already started; inspect exact owner')
    os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
    process=psutil.Process();save(output/'runner.json',dict(pid=process.pid,created=process.create_time(),at=now()))
    def phase(status,**kw):
        save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**kw));print(status,kw,flush=True)
    try:
        from audit_paired_guides import await_owner
        dependency=p['wait_for'];phase('waiting_for_exact_endpoint_batch',dependency=dependency)
        await_owner(dependency,'pid','created',Path(dependency['folder']),{'complete'})
        validate(output)
        from support_whole_clip import run as fit
        from support_velocity_traces import run as trace
        from verify_breadth_contact import verify
        from run_godot_rig_import import run as engine
        from threadpoolctl import threadpool_limits
        data=read(output/'results.json')
        with threadpool_limits(limits=1):
            for case,row in zip(p['cases'],data['rows']):
                validate(output);dest=output/'takes'/case['id'];motion=case['motion']
                row.update(status='running',started_at=now());save(output/'results.json',data);phase('fitting',case=case['id'])
                checks=[dict(id=case['id']+'-input',path=str(Path(case['source'])/'character.glb'),sha256=case['files']['character.glb'],frames=motion['frames'],fps=30)]
                try:
                    fit(case['source'],dest);proof=verify(dest);traces=trace(dest)
                    for v in traces['variants']:
                        if abs(v['root_acceleration_max_m_s2']-proof['metrics'][v['variant']]['root_acceleration_max_m_s2'])>1e-7:
                            raise ValueError('Independent acceleration trace disagrees')
                    row.update(status='verified_pending_engine',verification=proof,verification_sha256=sha256(dest/'verification.json'),traces_sha256=sha256(dest/'traces.json'))
                    checks.append(dict(id=case['id']+'-candidate',path=str(dest/'candidate/character.glb'),sha256=proof['candidate_sha256'],frames=motion['frames'],fps=30))
                except Exception as exc:row.update(status='failed',error=str(exc),traceback=traceback.format_exc())
                save(output/'results.json',data)
                group=output/'engine-groups'/case['id'];group.mkdir(parents=True);save(group/'manifest.json',dict(cases=checks));phase('engine',case=case['id'])
                try:
                    engine(group,group/'audit');eproof=read(group/'audit/verification.json');frames=check_engine(eproof,checks)
                    data['engine_groups'].append(dict(case=case['id'],status='complete',proof=eproof,proof_sha256=sha256(group/'audit/verification.json'),engine_actor_frames=frames))
                    if row['status']=='verified_pending_engine':row.update(status='complete',engine_actor_frames=frames)
                except Exception as exc:
                    data['engine_groups'].append(dict(case=case['id'],status='failed',error=str(exc),traceback=traceback.format_exc()))
                    row.update(status='failed',engine_error=str(exc))
                row['finished_at']=now();save(output/'results.json',data);print(case['id']+' '+row['status'],flush=True)
        validate(output)
        failed=any(r['status']!='complete' for r in data['rows'])
        total=sum(g.get('engine_actor_frames',0) for g in data['engine_groups'])
        if not failed and total!=p['planned_engine_actor_frames']:raise ValueError('Final engine frame count mismatch')
        save(output/'completion.json',dict(at=now(),results_sha256=sha256(output/'results.json'),engine_actor_frames=total,quality_approved=False))
        phase('complete_with_failures' if failed else 'complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run']);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source',type=Path,default=ROOT/'reports/breadth-transfer-v1')
    parser.add_argument('--wait-for',type=Path,default=ROOT/'reports/support-endpoint-batch-v1');args=parser.parse_args()
    if args.command=='prepare':print(prepare(args.source,args.output,args.wait_for)['planned_candidates'])
    else:run(args.output)
