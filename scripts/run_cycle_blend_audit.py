"""Verify actual-engine crossfade bones/root/skin and event ownership independently."""
import argparse
from pathlib import Path
import shutil
import subprocess
import traceback
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from run_godot_cycles import matrices, payload_error


def interpolate(a, b, weight):
    result=np.eye(4)
    scales_a=np.linalg.norm(a[:3,:3],axis=0);scales_b=np.linalg.norm(b[:3,:3],axis=0)
    rotations=Rotation.from_matrix(np.stack([a[:3,:3]/scales_a,b[:3,:3]/scales_b]))
    result[:3,:3]=Slerp([0.,1.],rotations)(weight).as_matrix()*((1-weight)*scales_a+weight*scales_b)
    result[:3,3]=(1-weight)*a[:3,3]+weight*b[:3,3]
    return result


def periodic(sampler, metadata, frame):
    period=metadata['period_frames'];cycles=int(frame//period)
    world=sampler.sample((frame-cycles*period)/30.)
    placement=np.linalg.matrix_power(np.asarray(metadata['cycle_transform']),cycles)
    world[metadata['descendant_nodes']]=placement@world[metadata['descendant_nodes']]
    return world


def blend_worlds(parents, worlds, root, alignment, weight):
    blended=np.zeros_like(worlds[0]);done=set();active=set()
    def visit(n):
        if n in done:return
        if n in active:raise ValueError('Cyclic skeleton')
        active.add(n);parent=int(parents[n])
        if parent>=0:visit(parent)
        local=[np.linalg.inv(w[parent])@w[n] if parent>=0 else w[n] for w in worlds]
        local_blend=interpolate(*local,weight)
        blended[n]=blended[parent]@local_blend if parent>=0 else local_blend
        if n==root:blended[n]=interpolate(worlds[0][root],alignment@worlds[1][root],weight)
        active.remove(n);done.add(n)
    for n in range(len(parents)):visit(n)
    return blended


def expected_events(case, policy):
    result=[]
    for label in ['a','b']:
        source=case[label];period=read(source['metadata'])['period_frames'];start=case['start_'+label]
        for cycle in range(int((start+case['total_frames'])//period)+1):
            for marker in source['probe_markers']:
                frame=cycle*period+marker['phase_frame'];elapsed=frame-start
                if cycle<marker['first_cycle'] or not 0<elapsed<=case['total_frames']:continue
                weight=min(1.,elapsed/case['duration_frames'])
                if elapsed>case['duration_frames']:accept=label=='b'
                elif policy=='silent':accept=False
                elif policy=='incoming':accept=label=='b'
                else:accept=(label=='b' and 2*elapsed>=case['duration_frames']) or (label=='a' and 2*elapsed<case['duration_frames'])
                if accept:result.append((elapsed,dict(**marker,cycle=cycle,time_s=frame/30.,source_clip=label,source_weight=weight if label=='b' else 1-weight)))
    return [row for _,row in sorted(result,key=lambda x:x[0])]


def verify(case, observed):
    a,b=[RigAsset.load(case[k]['path']) for k in ['a','b']]
    assert np.array_equal(a.parents,b.parents)
    assert [n.get('name') for n in a.document['nodes']]==[n.get('name') for n in b.document['nodes']]
    samplers=[AnimationSampler(r.document,r.binary,0) for r in [a,b]]
    metadata=[read(case[k]['metadata']) for k in ['a','b']];root=metadata[0]['root_node']
    assert root==metadata[1]['root_node']
    initial=[periodic(s,m,case['start_'+k]) for s,m,k in zip(samplers,metadata,['a','b'])]
    anchor=initial[0][root];alignment=anchor@np.linalg.inv(initial[1][root]);desc=set(metadata[0]['descendant_nodes'])
    assert len(observed['runs'])==18
    assert {(r['extracted'],r['policy'],r['stride']) for r in observed['runs']}=={(e,p,s) for e in [False,True] for p in ['dominant','incoming','silent'] for s in [.5,7.,90.]}
    checks=[]
    # Pose expectations depend on time, not the event policy or extraction mode.
    cache={}
    for run in observed['runs']:
        names={n.get('name'):i for i,n in enumerate(a.document['nodes'])};order=[names[n] for n in run['bone_names']]
        assert set(order)==set(a.joints)
        placement=matrices(run['placement']);error=root_error=skin_error=0.
        want=[];cursor=0.
        while cursor<case['total_frames']:cursor=min(cursor+run['stride'],case['total_frames']);want.append(cursor)
        assert [s['at_frame'] for s in run['frames']]==want
        for sample in run['frames']:
            frame=sample['at_frame']
            if frame not in cache:
                worlds=[periodic(s,m,case['start_'+k]+frame) for s,m,k in zip(samplers,metadata,['a','b'])]
                weight=min(1.,frame/case['duration_frames'])
                blended=blend_worlds(a.parents,worlds,root,alignment,weight)
                motion=blended[root]@np.linalg.inv(anchor);cache[frame]=(blended,motion)
            expected,motion=cache[frame];desired=placement@expected[order]
            if run['extracted']:
                for j,n in enumerate(order):
                    if n not in desc:desired[j]=placement@motion@expected[n]
            found=matrices(sample['bones'])
            error=max(error,float(np.max(np.abs(desired-found))))
            root_error=max(root_error,float(np.max(np.abs(matrices(sample['motion'])-motion))),float(np.max(np.abs(matrices(sample['accumulated'])-motion))))
            skin=expected.copy();skin[order]=np.linalg.inv(placement)@found
            skin_error=max(skin_error,float(np.linalg.norm(a.vertices(skin)-a.vertices(expected),axis=1).max()))
        assert max(error,root_error,skin_error)<1e-4,(case['id'],run['policy'],run['stride'],error,root_error,skin_error)
        want_events=expected_events(case,run['policy']);payload_error(run['events'],want_events)
        assert run['invalid_requests_preserve_state']
        checks.append(dict(extracted=run['extracted'],policy=run['policy'],stride=run['stride'],samples=len(want),marker_count=len(want_events),max_transform_error=error,max_root_error=root_error,max_cpu_skin_error_m=skin_error))
    return dict(id=case['id'],runs=checks)


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    project=output/'project';project.mkdir();(output/'implementation').mkdir()
    names=['godot_cycle_blend.gd','godot_cycle_adapter.gd','godot_cycle_blend_audit.gd','run_cycle_blend_audit.py','run_godot_cycles.py','rig_asset.py','rig_clip_import.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    def phase(status,**details):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**details));print(status,flush=True)
    try:
        phase('preparing')
        baseline=read(ROOT/'reports/runtime-reverse-v2/request.json')['cases']
        sources=[]
        for old in baseline[:3]:
            assert sha256(old['path'])==old['glb_sha256']
            sources.append(dict(path=old['path'],metadata=old['metadata'],glb_sha256=old['glb_sha256'],metadata_sha256=sha256(old['metadata'])))
        cases=[]
        for identifier,ia,ib,start_a,start_b in [('two_clips',0,1,17,7),('reverse_order',1,0,7,17),('other_rig_phase',2,2,3,9)]:
            pair=[]
            for source,start in [(sources[ia],start_a),(sources[ib],start_b)]:
                source=dict(source);period=read(source['metadata'])['period_frames']
                markers=[dict(name=name,phase_frame=phase,first_cycle=0) for name,phase in [('zero',0),('tie_a',(start+10)%period),('tie_b',(start+10)%period),('last',period-1)]]
                source['probe_markers']=sorted(markers,key=lambda m:m['phase_frame']);pair.append(source)
            incompatible=dict(sources[2 if ia!=2 else 0]);incompatible['probe_markers']=[]
            cases.append(dict(id=identifier,a=pair[0],b=pair[1],incompatible=incompatible,start_a=start_a,start_b=start_b,duration_frames=20,total_frames=90))
        save(output/'request.json',dict(at=now(),cases=cases,implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False))
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep crossfade audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        for name in names:
            if name.endswith('.gd'):shutil.copyfile(ROOT/'scripts'/name,project/name)
        phase('engine')
        engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
        with (output/'engine.log').open('w',encoding='utf8') as log:
            result=subprocess.run([str(engine),'--headless','--path',str(project),'--script','godot_cycle_blend_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or 'ERROR:' in (output/'engine.log').read_text(encoding='utf8'):raise ValueError('Godot failed; inspect engine.log')
        phase('verifying')
        actual=read(output/'engine-output.json');assert len(actual['cases'])==len(cases)
        checks=[]
        for case,observed in zip(cases,actual['cases']):
            assert case['id']==observed['id'];checks.append(verify(case,observed))
        for name,digest in read(output/'request.json')['implementation'].items():assert sha256(ROOT/'scripts'/name)==digest
        save(output/'verification.json',dict(at=now(),request_sha256=sha256(output/'request.json'),engine_output_sha256=sha256(output/'engine-output.json'),engine_exe_sha256=sha256(engine),engine=actual['engine'],checks=checks,quality_approved=False,scope='Two distinct cycle clips in both directions plus phase blending on a second rig. Forward two-donor local TRS crossfade and aligned full pelvis root motion; exact marker ownership against frame-domain oracle. No realism, support correction, physical gameplay, reverse-through-blend or GPU rendering approval.'))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
