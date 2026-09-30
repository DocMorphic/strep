"""Complete motion-only temporal comparison without waiting for surface queries."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from audit_scene_joint_rates import compare_rates
from verify_paired_stage_rates import verify_rates
from paired_temporal_neighbor import placed_joint_positions


def validate_engine(exports,checks):
    expected={v+'-'+a:e['sha256'] for v,actors in exports.items() for a,e in actors.items()}
    if len(checks)!=len(expected) or {c['id'] for c in checks}!=set(expected):
        raise ValueError('Complete distinct engine clip population required')
    for c in checks:
        if c['source_sha256']!=expected[c['id']] or c['frames']!=150 or c['bones']!=77:
            raise ValueError('Engine clip identity or frame population changed')
        if not c['sampled_original_by_time'] or c['imported_loop_mode']!=0 or c['imported_skinned_surfaces']!=1:
            raise ValueError('Engine sampling or import mode changed')
    return sum(c['frames'] for c in checks)


def run(study,engine,output):
    study,engine,output=map(lambda p:Path(p).resolve(),[study,engine,output])
    if output.exists():raise ValueError('Preserve earlier motion audit')
    protocol,result=read(study/'protocol.json'),read(study/'result.json')
    if result['status']!='complete' or result['protocol_sha256']!=sha256(study/'protocol.json'):raise ValueError('Unchanged completed trial required')
    engine_frames=validate_engine(result['exports'],read(engine/'verification.json')['checks'])
    inputs={**protocol['inputs'],str(study/'protocol.json'):sha256(study/'protocol.json'),
            str(study/'result.json'):sha256(study/'result.json'),str(engine/'verification.json'):sha256(engine/'verification.json')}
    inputs.update({str(study/e['path']):e['sha256'] for actors in result['exports'].values() for e in actors.values()})
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Bound input changed')
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['audit_paired_temporal_rates.py','audit_scene_joint_rates.py','verify_paired_stage_rates.py','rig_clip_import.py','rig_asset.py','gltf_tools.py','strep.py','paired_temporal_neighbor.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    request=dict(at=now(),inputs=inputs,implementation={n:sha256(snapshot/n) for n in methods},quality_approved=False)
    save(output/'request.json',request)
    times=np.arange(597)/4;first,event,last=[protocol[k] for k in ['first','event','last']]
    windows=dict(whole_clip=[0,149],edited_interval=[first,last],event=[event-2,event+2],entry_join=[first-2,first+2],exit_join=[last-2,last+2])
    scene=read(ROOT/protocol['source_scene'])['scene'];rows=[];count=0;error=0.;artifacts={};preservation_error=0.
    for actor in ['A','B']:
        tracks={};names=None;source_world=None;placement=scene['actors'][actor]['transform']
        r=Rotation.from_quat(placement['rotation_xyzw']).as_matrix();shift=np.asarray(placement['translation_m'])
        for variant in protocol['variants']:
            doc,binary=read_glb(study/result['exports'][variant][actor]['path']);sampler=AnimationSampler(doc,binary,0);joints=doc['skins'][0]['joints']
            current=[doc['nodes'][j]['name'] for j in joints]
            if names is not None and current!=names:raise ValueError('Joint identity changed')
            names=current;world=np.array([sampler.sample(t/30) for t in times])
            if variant=='input':source_world=world
            else:
                locked=(times<first)|(times>last)|(times==event)
                drift=float(np.abs(world[locked]-source_world[locked]).max());preservation_error=max(preservation_error,drift)
                np.testing.assert_allclose(world[locked],source_world[locked],atol=1e-12,rtol=0)
            tracks[variant]=placed_joint_positions(world,joints,r,shift)
        path=output/(actor+'-positions.npz');np.savez_compressed(path,**tracks);artifacts[path.name]=sha256(path)
        for variant in ['body','body_fingers']:
            rates=compare_rates(tracks['input'],tracks[variant],names,windows)
            n,e=verify_rates(tracks['input'],tracks[variant],rates,names);count+=n;error=max(error,e)
            path=output/(variant+'-'+actor+'-rates.json');save(path,rates);artifacts[path.name]=sha256(path)
            for metric in ['speed','acceleration']:
                for window in rates[metric]['windows']:
                    rows.append(dict(actor=actor,variant=variant,metric=metric,window=window['window'],
                        source_peak=window['source_peak'],candidate_peak=window['candidate_peak'],
                        increased_joints=window['increased_joints_over_1e_5'],largest_increase=max(window['joints'],key=lambda j:j['change'])))
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input changed during audit')
    for name,digest in request['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during audit')
    save(output/'verification.json',dict(at=now(),request_sha256=sha256(output/'request.json'),artifacts=artifacts,
        actor_samples=6*597,verified_peak_values=count,maximum_replay_error=error,rows=rows,
        protected_world_matrix_max_error=preservation_error,protected_world_matrix_tolerance=1e-12,
        reused_engine_actor_frames=engine_frames,new_engine_actor_frames=0,quality_approved=False,
        scope='Motion-only decoded comparison with independent direct-difference peak replay. Surface audit is separate and may remain pending. No naturalness, semantic, anatomical, collision or release approval.'))
    print(dict(actor_samples=6*597,verified_peak_values=count,maximum_replay_error=error),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['study','engine','output']:p.add_argument(n,type=Path)
    a=p.parse_args();run(a.study,a.engine,a.output)
