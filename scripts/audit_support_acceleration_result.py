"""Fresh four-track audit of the frozen actual-foot acceleration pilot."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from support_release_metrics import release_windows
from summarize_support_release import run as summarize


def run(study,output):
    study,output=study.resolve(),output.resolve()
    if read(study/'pipeline.json')['status']!='complete':raise ValueError('Study incomplete')
    request=read(study/'request.json');case=request['cases'][0]
    if len(request['cases'])!=1:raise ValueError('Expected frozen one-case pilot')
    for name,digest in request['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Implementation snapshot changed')
    summarize(study,output)
    folder=study/'takes'/case['id'];prior=Path(case['prior']);held=Path(case['baseline_dynamics']).parent
    spec=read(folder/'spec.json');fit=read(folder/'request.json');fps=spec['fps'];count=spec['frames']
    annotations=read(folder/'input/contacts.json');stored=read(folder/'release-dynamics.json')
    paths={'input':folder/'input/character.glb','prior':prior/'candidate/character.glb',
           'held':held/'candidate/character.glb','candidate':folder/'candidate/character.glb'}
    tracks={};rows=[];fresh={}
    for variant,path in paths.items():
        rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
        worlds=np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)])
        vertices=np.array([rig.vertices(w) for w in worlds])
        root=worlds[:,spec['root_node'],:3,3]
        floor=max(0.,-float(vertices[:,:,1].min()))
        half=max(max(0.,-float(rig.vertices(sampler.sample((f+.5)/fps))[:,1].min())) for f in range(count-1))
        foot_rows={};centers=[];fresh[variant]={}
        for side,patch in spec['patches'].items():
            points=vertices[:,patch['vertices']].mean(axis=1);centers.append(points)
            data=release_windows(points,[i for i in fit['support']['intervals'] if i['side']==side],fps)
            reference=(read(held/'release-dynamics.json')['candidate'] if variant=='held' else stored[variant])['feet'][side]
            np.testing.assert_allclose(points,reference['centroids_m'],atol=1e-12,rtol=0)
            np.testing.assert_allclose(data['acceleration_m_s2'],reference['acceleration_m_s2'],atol=1e-9,rtol=0)
            fresh[variant][side]=data
            active=np.zeros(count,bool)
            for interval in annotations['intervals']:
                if interval['joint'] in [side+'Foot',side+'ToeBase']:active[interval['start_frame']:interval['end_frame_exclusive']]=True
            speed=np.linalg.norm(np.diff(points[:,[0,2]],axis=0),axis=1)*fps;steps=active[:-1]&active[1:]
            foot_rows[side]=dict(support_max_m_s=float(speed[steps].max()),support_p95_m_s=float(np.percentile(speed[steps],95)),
                acceleration_max_m_s2=data['global_acceleration_max_m_s2'],releases=data['releases'])
        tracks[variant]=np.stack(centers,axis=1)
        rows.append(dict(variant=variant,glb_sha256=sha256(path),floor_m=max(floor,half),root_acceleration_max_m_s2=float(np.linalg.norm(np.diff(root,n=2,axis=0)*fps**2,axis=1).max()),feet=foot_rows))
    accelerations={v:np.linalg.norm(np.diff(t,n=2,axis=0)*fps**2,axis=2) for v,t in tracks.items()}
    caps=np.maximum(accelerations['input'],accelerations['prior'])+1e-5
    np.testing.assert_allclose(caps,fit['acceleration_caps_m_s2'],rtol=0,atol=1e-9)
    sides=list(spec['patches']);excess={}
    for variant in ['held','candidate']:
        delta=np.maximum(accelerations[variant]-caps,0);indices=np.argwhere(delta>0)
        excess[variant]=dict(exceeding_foot_frames=len(indices),sum_squared_excess=float(np.sum(delta**2)),max_excess_m_s2=float(delta.max()),
            rows=[dict(frame=int(f+1),side=sides[s],cap_m_s2=float(caps[f,s]),acceleration_m_s2=float(accelerations[variant][f,s]),excess_m_s2=float(delta[f,s])) for f,s in indices])
    save(output/'decoded-audit.json',dict(at=now(),rows=rows,acceleration_excess=excess,request_sha256=sha256(study/'request.json'),
        results_sha256=sha256(study/'results.json'),implementation_sha256=sha256(__file__),decoded_integer_poses=4*count,half_frame_floor_poses=4*(count-1),
        quality_approved=False,scope='Fresh decoded four-track dynamics and full/half-frame floor audit. Caps fixed to raw/original prior. Failed screens retained; no animator approval or extra fitting.'))
    print(dict(rows=[{k:v for k,v in row.items() if k!='feet'} for row in rows],excess={v:{k:x for k,x in d.items() if k!='rows'} for v,d in excess.items()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.output)
