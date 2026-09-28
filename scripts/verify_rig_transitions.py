"""Reload baked transitions, verify source contributions and independent engine inputs."""
import argparse
import hashlib
import io
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from urllib.request import urlopen
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from gltf_tools import sample_animation
from rig_clip_import import AnimationSampler


def verify(job):
    folder=ROOT/'reports/rig-jobs'/job;recipe=read(folder/'transition.json');result=read(folder/'result.json');timeline=read(folder/'transfer/timeline.json')
    assert read(folder/'pipeline.json')['status']=='complete'
    rigs=[RigAsset.load(folder/name/'character.glb') for name in ('input','following','transfer')]
    sources=[np.array([sample_animation(r.document,r.binary,0,f) for f in range(c['first_frame'],c['last_frame']+1)]) for r,c in zip(rigs,recipe['clips'])]
    root=result['root_node'];t=np.array(timeline['second_alignment_matrix']);k=recipe['blend_frames'];offset=len(sources[0])-k;n=sum(map(len,sources))-k
    assert result['frames']==n
    expected_yaw=Rotation.from_euler('y',recipe['yaw_degrees'],degrees=True).as_matrix();np.testing.assert_allclose(t[:3,:3],expected_yaw)
    target=sources[0][offset,root,:3,3]-expected_yaw@sources[1][0,root,:3,3];target[1]=0;np.testing.assert_allclose(t[:3,3],target,atol=1e-7)
    for node in range(len(rigs[0].parents)):
        ancestor=node
        while ancestor>=0 and ancestor!=root:ancestor=rigs[0].parents[ancestor]
        if ancestor==root:sources[1][:,node]=t@sources[1][:,node]
    local=[]
    for world in sources:
        values=world.copy()
        for node,parent in enumerate(rigs[0].parents):
            if parent>=0:values[:,node]=np.linalg.inv(world[:,parent])@world[:,node]
        local.append(values)
    maximum=0.;root_error=0.;track=read(folder/'transfer/root-motion.json');blended=[]
    for f in range(n):
        if f<offset:expected=local[0][f];contributors=[dict(source=0,frame=recipe['clips'][0]['first_frame']+f,weight=1.)]
        elif f>=len(sources[0]):expected=local[1][f-offset];contributors=[dict(source=1,frame=recipe['clips'][1]['first_frame']+f-offset,weight=1.)]
        else:
            u=(f-offset)/(k-1);w=u*u*(3-2*u);a,b=local[0][f],local[1][f-offset];expected=a.copy()
            expected[:,:3,3]=a[:,:3,3]*(1-w)+b[:,:3,3]*w
            for node in range(len(a)):expected[node,:3,:3]=Slerp([0,1],Rotation.from_matrix(np.array([a[node,:3,:3],b[node,:3,:3]])))(w).as_matrix()
            contributors=[dict(source=0,frame=recipe['clips'][0]['first_frame']+f,weight=1-w),dict(source=1,frame=recipe['clips'][1]['first_frame']+f-offset,weight=w)]
            blended.append(f)
        assert len(contributors)==len(timeline['contributors'][f])
        for a,b in zip(contributors,timeline['contributors'][f]):
            assert a['source']==b['source'] and a['frame']==b['frame'];assert abs(a['weight']-b['weight'])<1e-10
        actual=sample_animation(rigs[2].document,rigs[2].binary,0,f);found=actual.copy()
        for node,parent in enumerate(rigs[2].parents):
            if parent>=0:found[node]=np.linalg.inv(actual[parent])@actual[node]
        maximum=max(maximum,float(np.abs(found-expected).max()));root_error=max(root_error,float(np.abs(actual[root,:3,3]-track['positions_m'][f]).max()))
    assert max(maximum,root_error)<1e-5
    sampler=AnimationSampler(rigs[2].document,rigs[2].binary,0)
    half_floor=[max(0.,-float(rigs[2].vertices(sampler.sample((f+.5)/30))[:,1].min())) for f in range(n-1)]
    data=urlopen('http://127.0.0.1:8768'+result['package']).read();assert hashlib.sha256(data).hexdigest()==result['package_sha256']
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            if name!='README.txt':assert archive.read(name)==(folder/name).read_bytes()
        entries=len(archive.namelist())
    cases=[]
    for i,name in enumerate(('input','following','transfer')):
        path=folder/name/'character.glb';count=read(folder/name/'report.json')['frames'];hash=sha256(path)
        assert hashlib.sha256(urlopen('http://127.0.0.1:8768/files/rig-jobs/'+job+'/'+name+'/character.glb').read()).hexdigest()==hash
        cases.append(dict(id=job+'-'+name,path='../rig-jobs/'+job+'/'+name+'/character.glb',sha256=hash,frames=count,fps=30))
    return dict(job=job,frames=n,maximum_local_matrix_error=maximum,root_track_error_m=root_error,half_frame_floor_depth_max_m=max(half_floor),package_entries=entries,audit=read(folder/'transfer/transition-audit.json')),cases


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study');p.add_argument('jobs',nargs='+');a=p.parse_args();checks=[];cases=[]
    for job in a.jobs:
        check,items=verify(job);checks.append(check);cases.extend(items)
    save(ROOT/a.study/'verification.json',dict(checks=checks,scope='Decoded GLB source clocks, per-node Slerp oracle, root tracks, half-frame skin depth, HTTP hashes and archive bytes. Not realism or contact approval.'))
    save(ROOT/a.study/'manifest.json',dict(cases=cases));print(checks)
