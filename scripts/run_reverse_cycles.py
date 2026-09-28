"""Actual engine bidirectional cycle traversal against immutable repeated clips."""
import argparse
import re
from pathlib import Path
import shutil
import subprocess
import traceback
import numpy as np
from strep import ROOT,read,save,sha256,now
from run_godot_cycles import matrices,payload_error
from rig_runtime_cycle import write
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def scenarios(period):
    result=[]
    for stride in [.5,17.,2.*period+3.]:
        cursor=3.*period;dest=[]
        while cursor>0:
            cursor=max(0.,cursor-stride);dest.append(cursor)
        result.append(dict(id='reverse-'+str(stride),start_frame=3.*period,destinations=dest,notify_reverse=True))
    half=period//2
    result.append(dict(id='direction-changes',start_frame=0.,destinations=[half,half+1,half,half-1,half,period+.5,0.,2.*period,period,3.*period,period+3.,0.,0.],notify_reverse=True))
    result.append(dict(id='silent-reverse',start_frame=3.*period,destinations=[period,0.],notify_reverse=False))
    return result


def expected_events(markers,period,scenario):
    # Independent frame-domain oracle. No floating-point seconds comparison.
    instances=[]
    for cycle in range(4):
        for marker in markers:
            if cycle>=marker['first_cycle']:
                frame=cycle*period+marker['phase_frame']
                instances.append((frame,{**marker,'cycle':cycle,'time_s':frame/30.}))
    forward=[];reverse=[];cursor=scenario['start_frame']
    for dest in scenario['destinations']:
        if dest>cursor:forward.extend(e for frame,e in instances if cursor<frame<=dest)
        if dest<cursor and scenario['notify_reverse']:
            reverse.extend({**e,'direction':-1} for frame,e in reversed(instances) if dest<=frame<cursor)
        cursor=dest
    return forward,reverse


def run(output,fixtures=None):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier attempt')
    output.mkdir(parents=True);project=output/'project';project.mkdir();save(output/'pipeline.json',dict(status='preparing',at=now()))
    names=['godot_cycle_adapter.gd','godot_reverse_cycle_audit.gd','run_reverse_cycles.py','rig_runtime_cycle.py','run_godot_cycles.py','rig_asset.py','rig_clip_import.py','rig_events.py']
    (output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    try:
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep reverse-cycle audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
        for name in ['godot_cycle_adapter.gd','godot_reverse_cycle_audit.gd']:shutil.copyfile(ROOT/'scripts'/name,project/name)
        if fixtures is None:
            baseline=read(ROOT/'reports/runtime-cycles-v3/request.json')['cases'][:3]
            baseline.append(read(ROOT/'reports/runtime-authored-events-v2/request.json')['cases'][-1])
        else:
            fixtures=Path(fixtures).resolve();baseline=read(fixtures)['cases']
            save(output/'fixture-source.json',dict(path=str(fixtures),sha256=sha256(fixtures),scope='Explicitly supplied input data; no source code or Python environment loaded from this path.'))
        if not baseline or len({c['id'] for c in baseline})!=len(baseline) or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',c['id']) for c in baseline):
            raise ValueError('Unique simple fixture identifiers required')
        cases=[]
        for old in baseline:
            source=Path(old['metadata']).parent;target=output/old['id'];target.mkdir()
            if sha256(old['path'])!=read(old['metadata'])['glb_sha256'] or sha256(old['repeated'])!=old['repeated_sha256']:
                raise ValueError('Immutable cycle reference changed')
            for name in ['character.glb','report.json','timeline.json','root-motion.json','events.json','authoring-source.zip']:
                shutil.copyfile(source/name,target/name)
            if sha256(target/'character.glb')!=sha256(old['path']):raise ValueError('Fixture source path disagrees with metadata directory')
            shutil.copyfile(old['repeated'],target/'reference.glb')
            if sha256(target/'reference.glb')!=old['repeated_sha256']:raise ValueError('Copied reference changed')
            data=write(target);period=data['period_frames']
            probes=data['markers']+[dict(name=n,phase_frame=f,first_cycle=0) for n,f in [('probe_start',0),('probe_mid_a',period//2),('probe_mid_b',period//2),('probe_last',period-1)]]
            probes.sort(key=lambda e:e['phase_frame'])
            cases.append(dict(id=old['id'],path=str(target/'character.glb'),metadata=str(target/'runtime-cycle.json'),
                glb_sha256=sha256(target/'character.glb'),metadata_sha256=sha256(target/'runtime-cycle.json'),
                repeated=str(target/'reference.glb'),repeated_sha256=old['repeated_sha256'],probe_markers=probes,scenarios=scenarios(period)))
        save(output/'request.json',dict(at=now(),cases=cases,implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False))
        save(output/'pipeline.json',dict(status='engine',at=now()))
        engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
        with (output/'engine.log').open('w',encoding='utf8') as log:
            result=subprocess.run([str(engine),'--headless','--path',str(project),'--script','godot_reverse_cycle_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        log=(output/'engine.log').read_text(encoding='utf8')
        if result.returncode or 'ERROR:' in log:raise ValueError('Engine failed; inspect engine.log')
        actual=read(output/'engine-output.json');checks=[]
        if len(actual['cases'])!=len(cases):raise ValueError('Missing engine cases')
        for case,observed in zip(cases,actual['cases']):
            assert case['id']==observed['id'] and len(observed['runs'])==10
            data=read(case['metadata']);rig=RigAsset.load(case['repeated']);sampler=AnimationSampler(rig.document,rig.binary,0)
            root=data['root_node'];anchor=sampler.sample(0)[root];desc=set(data['descendant_nodes']);runchecks=[]
            for got in observed['runs']:
                scenario=next(s for s in case['scenarios'] if s['id']==got['scenario']);want_forward,want_reverse=expected_events(case['probe_markers'],data['period_frames'],scenario)
                payload_error(got['forward_events'],want_forward);payload_error(got['reverse_events'],want_reverse)
                names_by_node={rig.document['nodes'][n]['name']:n for n in rig.joints};order=[names_by_node[n] for n in got['bone_names']]
                assert set(order)==set(rig.joints) and len(got['frames'])==len(scenario['destinations'])
                placement=matrices(got['placement']);error=skin_error=root_error=clock_error=0.
                for frame,destination in zip(got['frames'],scenario['destinations']):
                    assert frame['at_frame']==destination
                    t=destination/30.;clock_error=max(clock_error,abs(frame['clock_s']-t));expected=sampler.sample(t)
                    motion=expected[root]@np.linalg.inv(anchor);found=matrices(frame['bones']);desired=placement@expected[order]
                    for j,n in enumerate(order):
                        if got['extracted'] and n not in desc:desired[j]=placement@motion@expected[n]
                    error=max(error,float(np.abs(found-desired).max()))
                    root_error=max(root_error,float(np.abs(matrices(frame['motion'])-motion).max()),float(np.abs(matrices(frame['accumulated_delta'])-motion).max()))
                    actual_world=expected.copy();actual_world[order]=np.linalg.inv(placement)@found
                    skin_error=max(skin_error,float(np.linalg.norm(rig.vertices(actual_world)-rig.vertices(expected),axis=1).max()))
                assert max(error,root_error,skin_error)<1e-4,(case['id'],got['scenario'],error,root_error,skin_error)
                assert clock_error<1e-12 and got['invalid_rewind_preserves_state']
                runchecks.append(dict(scenario=got['scenario'],extracted=got['extracted'],samples=len(got['frames']),forward_events=len(want_forward),reverse_events=len(want_reverse),max_transform_error=error,max_root_error=root_error,max_cpu_skin_error_m=skin_error,max_clock_error_s=clock_error,invalid_rewind_preserves_state=True))
            checks.append(dict(id=case['id'],glb_sha256=case['glb_sha256'],reference_sha256=case['repeated_sha256'],runs=runchecks))
        for name,digest in read(output/'request.json')['implementation'].items():assert sha256(ROOT/'scripts'/name)==digest
        save(output/'verification.json',dict(at=now(),request_sha256=sha256(output/'request.json'),engine_output_sha256=sha256(output/'engine-output.json'),engine=actual['engine'],engine_exe_sha256=sha256(engine),checks=checks,quality_approved=False,
            scope='Actual Godot reverse/mixed/silent traversal, exact frame-domain marker oracle, all weighted-bone transforms and CPU skin compared to immutable three-cycle references. No GPU rendering, inverse gameplay, crossfade, physics or motion-quality approval.'))
        save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False));print([(c['id'],sum(r['samples'] for r in c['runs'])) for c in checks])
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--fixtures',type=Path);a=p.parse_args();run(a.output,a.fixtures)
