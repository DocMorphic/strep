"""Read-only decoded audit of the completed fixed-root gesture trial."""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from study_support_release import compare
from study_whole_support_breadth import check_engine


def run(folder,output):
    folder,output=folder.resolve(),output.resolve()
    if output.exists():raise ValueError('Preserve earlier audit')
    if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Study incomplete')
    request=read(folder/'request.json');done=read(folder/'completion.json');dest=folder/'take';prior=Path(request['prior'])
    if sha256(folder/'request.json')!=done['request_sha256']:raise ValueError('Study request changed')
    for name,digest in done['files'].items():
        if sha256(folder/name)!=digest:raise ValueError('Completed artifact changed')
    for path,digest in request['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Prior input changed')
    for name,digest in request['implementation'].items():
        if sha256(folder/'implementation'/name)!=digest:raise ValueError('Implementation snapshot changed')
    spec=read(dest/'spec.json');fps=spec['fps'];count=spec['frames'];root=spec['root_node']
    parameters=np.load(dest/'fit.npz',allow_pickle=False)['parameters']
    np.testing.assert_array_equal(parameters[:,:3],np.broadcast_to(request['root_offset_m'],(count,3)))
    annotations=read(dest/'input/contacts.json');proof=read(dest/'verification.json');old=read(prior/'verification.json')
    dynamics=read(dest/'release-dynamics.json');traces=read(dest/'traces.json');old_traces=read(prior/'traces.json')
    tracks={};rows=[]
    for variant,path,metrics,trace in [('input',dest/'input/character.glb',proof['metrics']['input'],traces['variants'][0]),
        ('prior',prior/'candidate/character.glb',old['metrics']['candidate'],old_traces['variants'][1]),
        ('candidate',dest/'candidate/character.glb',proof['metrics']['candidate'],traces['variants'][1])]:
        rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
        worlds=np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)])
        vertices=np.array([rig.vertices(w) for w in worlds]);tracks[variant]=worlds[:,root,:3,3]
        floor=max(0.,-float(vertices[:,:,1].min()))
        half=max(max(0.,-float(rig.vertices(sampler.sample((f+.5)/fps))[:,1].min())) for f in range(count-1))
        root_acc=float(np.linalg.norm(np.diff(tracks[variant],n=2,axis=0)*fps**2,axis=1).max())
        if abs(floor-metrics['floor_depth_max_m'])>1e-10 or abs(half-metrics['half_frame_floor_depth_max_m'])>1e-10 or abs(root_acc-metrics['root_acceleration_max_m_s2'])>1e-9:
            raise ValueError('Decoded floor/root metrics differ')
        feet={}
        for side,patch in spec['patches'].items():
            centroids=vertices[:,patch['vertices']].mean(axis=1)
            np.testing.assert_allclose(centroids,dynamics[variant]['feet'][side]['centroids_m'],rtol=0,atol=1e-12)
            active=np.zeros(count,bool)
            for interval in annotations['intervals']:
                if interval['joint'] in [side+'Foot',side+'ToeBase']:active[interval['start_frame']:interval['end_frame_exclusive']]=True
            steps=active[:-1]&active[1:];speed=np.linalg.norm(np.diff(centroids[:,[0,2]],axis=0),axis=1)*fps
            maximum=float(speed[steps].max());p95=float(np.percentile(speed[steps],95))
            if abs(maximum-trace['feet'][side]['predicted_support_max_m_s'])>1e-10 or abs(p95-trace['feet'][side]['predicted_support_p95_m_s'])>1e-10:raise ValueError('Foot-speed metric differs')
            feet[side]=dict(max_m_s=maximum,p95_m_s=p95,peak_step_end_frame=int(np.argmax(speed))+1)
        rows.append(dict(variant=variant,floor_m=max(floor,half),root_acceleration_m_s2=root_acc,feet=feet))
    root_error=float(np.abs(np.diff(tracks['candidate']-tracks['input'],n=2,axis=0)*fps**2).max())
    decision=compare(old,proof,old_traces,traces,dynamics)
    decision['checks']['decoded_source_root_acceleration_preserved']=root_error<=1e-4
    decision['decoded_root_acceleration_vector_error_m_s2']=root_error
    decision['passes_development_screen']=all(decision['checks'].values())
    if decision!=done['decision'] or decision!=read(dest/'comparison.json'):raise ValueError('Decision differs')
    checks=read(folder/'engine/manifest.json')['cases'];engine=read(folder/'engine/audit/verification.json')
    frames=check_engine(engine,checks)
    if frames!=450:raise ValueError('Incomplete engine population')
    for item in checks:
        if sha256(item['path'])!=item['sha256']:raise ValueError('Engine input changed')
    save(output,dict(at=now(),completion_sha256=sha256(folder/'completion.json'),implementation_sha256=sha256(__file__),
        rows=rows,engine_actor_frames=frames,decoded_root_acceleration_vector_error_m_s2=root_error,
        failed_checks=[k for k,v in decision['checks'].items() if not v],
        right_support_peak_increase_m_s=rows[2]['feet']['Right']['max_m_s']-rows[1]['feet']['Right']['max_m_s'],
        quality_approved=False,scope='Fresh decoded all-frame and half-frame floor/root/foot audit of input,prior,candidate plus engine/provenance checks. No threshold changes, perceptual/semantic/force-balance or release approval.'))
    print(dict(engine_frames=frames,rows=rows,failed_checks=[k for k,v in decision['checks'].items() if not v]))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder,a.output)
