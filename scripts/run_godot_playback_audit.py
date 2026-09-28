"""Independent engine event-dispatch and root-delta audit on existing exports."""
import argparse
import shutil
import subprocess
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb,accessor


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep playback audit"\n',encoding='utf8')
    scripts=['godot_playback_audit.gd','godot_clip_adapter.gd']
    for name in scripts:shutil.copyfile(ROOT/'scripts'/name,project/name)
    cases=[]
    for seed in [11,22]:
        source=ROOT/f'reports/object-attachment-v1/palm-attached-box-seed-{seed}'
        cases.append(dict(id=f'attached-box-{seed}',path=(source/'portable/scene.glb').as_posix(),events=(source/'events.json').as_posix(),frames=180))
    cases.append(dict(id='high-five',path=(ROOT/'reports/scene-fitting-v4/assets/high-five-seed-11/A/soma.glb').as_posix(),frames=120))
    save(output/'synthetic-boundary-events.json',dict(fps=30,events=[dict(type='test_boundary',actor='A',frame=f,time_s=f/30) for f in [0,60,119]],provenance='Synthetic adapter boundary tests, not action events'))
    cases.append(dict(**{**cases[-1],'id':'synthetic-event-boundaries'},events=(output/'synthetic-boundary-events.json').as_posix()))
    save(output/'request.json',dict(cases=cases));save(output/'pipeline.json',dict(status='processing'))
    executable=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    try:
        with (output/'engine.log').open('w',encoding='utf8') as log:
            result=subprocess.run([str(executable),'--headless','--path',str(project),'--script','godot_playback_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
        if result.returncode:raise RuntimeError('Engine script failed; inspect engine.log')
        report=read(output/'engine-output.json');checks=[]
        for case,actual in zip(cases,report['cases'],strict=True):
            if case['id']!=actual['id']:raise ValueError('Case order mismatch')
            doc,binary=read_glb(case['path']);hip=next(i for i,n in enumerate(doc['nodes']) if n.get('name')=='Hips');tracks={}
            for channel in doc['animations'][0]['channels']:
                if channel['target']['node']==hip:
                    sampler=doc['animations'][0]['samplers'][channel['sampler']]
                    tracks[channel['target']['path']]=accessor(doc,binary,sampler['output'])
            expected_events=read(case['events'])['events'] if 'events' in case else []
            if actual['seek_events']:raise ValueError('Seeking dispatched gameplay events')
            for playback in actual['runs']:
                delivered=[r['event'] for r in playback['events']]
                if len(delivered)!=len(expected_events):raise ValueError('Missing or duplicate event')
                for event,expected_event in zip(delivered,expected_events):
                    if {k:v for k,v in event.items() if k!='time_s'}!={k:v for k,v in expected_event.items() if k!='time_s'} or abs(event['time_s']-expected_event['time_s'])>1e-12:
                        raise ValueError('Reordered or corrupted event')
                event_delay=max([r['dispatched_at_s']-r['event']['time_s'] for r in playback['events']]+[0.])
                if any(not -1e-6<=r['dispatched_at_s']-r['event']['time_s']<=playback['stride_frames']/30+1e-6 for r in playback['events']):raise ValueError('Event outside crossing update')
                position_error=0.;rotation_error=0.
                for frame in playback['root_motion']:
                    a,b=frame['from_frame'],frame['to_frame']
                    expected=tracks['translation'][b].astype(float)-tracks['translation'][a]
                    position_error=max(position_error,float(np.max(np.abs(np.array(frame['position_delta'])-expected))))
                    expected_r=Rotation.from_quat(tracks['rotation'][a]).inv()*Rotation.from_quat(tracks['rotation'][b])
                    error=expected_r.inv()*Rotation.from_quat(frame['rotation_delta'])
                    rotation_error=max(rotation_error,float(error.magnitude()))
                if position_error>1e-4 or rotation_error>1e-4:raise ValueError(f'Root delta mismatch: {position_error}, {rotation_error}')
                np.testing.assert_allclose(playback['terminal_position_delta'],[0,0,0],atol=1e-6)
                if Rotation.from_quat(playback['terminal_rotation_delta']).magnitude()>1e-6:raise ValueError('Terminal hold root drift')
                checks.append(dict(id=case['id'],stride_frames=playback['stride_frames'],source_sha256=sha256(case['path']),events=len(expected_events),max_event_delay_s=event_delay,
                    root_intervals=len(playback['root_motion']),max_position_delta_error_m=position_error,max_rotation_delta_error_rad=rotation_error,seek_events=0,
                    imported_duration_s=actual['imported_duration_s'],playback_duration_s=actual['playback_duration_s']))
        save(output/'verification.json',dict(created_at=now(),engine=report['engine'],checks=checks,implementation={n:sha256(ROOT/'scripts'/n) for n in scripts},
            scope='Actual Godot forward playback at 30 Hz and coarse 17-frame steps, authored marker signals and native Hips root deltas. No game-world application, physics, blending, reverse/loop behavior or naturalness approval.'))
        save(output/'pipeline.json',dict(status='complete'));print(checks)
    except Exception as error:
        save(output/'pipeline.json',dict(status='failed',error=str(error)));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();run(args.output)
