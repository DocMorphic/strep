"""Verify saved clip edits against their input GLBs, clocks, annotations and packages."""
import argparse
import hashlib
import io
import os
import urllib.request
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from gltf_tools import sample_animation


def verify(job):
    folder=ROOT/'reports/rig-jobs'/job;result=read(folder/'result.json');recipe=read(folder/'clip-edit.json')
    assert read(folder/'pipeline.json')['status']=='complete'
    input=RigAsset.load(folder/'input/character.glb');output=RigAsset.load(folder/'transfer/character.glb')
    report=read(folder/'transfer/report.json');clock=read(folder/'transfer/timeline.json')
    n=result['frames'];a,b=recipe['start_frame'],recipe['last_frame'];spans=max(1,int(np.floor((b-a)/recipe['speed']+.5)))
    assert n==spans+1
    source_frames=np.arange(n)*(b-a)/spans+a
    np.testing.assert_allclose(clock['source_frames'],source_frames,atol=1e-12)
    sampler=AnimationSampler(input.document,input.binary,0);maximum=0.
    root=read(folder/'transfer/root-motion.json')
    assert len(root['times_s'])==n
    for f,sf in enumerate(source_frames):
        old=sampler.sample(float(np.float32(sf/30)));new=sample_animation(output.document,output.binary,0,f)
        for node,parent in enumerate(input.parents):
            before=old[node] if parent<0 else np.linalg.inv(old[parent])@old[node]
            after=new[node] if parent<0 else np.linalg.inv(new[parent])@new[node]
            expected=before.copy()
            for p in recipe['poses']:
                if p['node']!=node:continue
                start,peak,end=p['start_frame'],p['peak_frame'],p['end_frame']
                u=max(0.,min((sf-start)/(peak-start),(end-sf)/(end-peak),1.))
                weight=u*u*(3-2*u)
                delta=Rotation.from_euler('xyz',p['rotation_degrees'],degrees=True).as_rotvec()*weight
                expected[:3,:3]=expected[:3,:3]@Rotation.from_rotvec(delta).as_matrix()
            maximum=max(maximum,float(np.abs(after-expected).max()))
        np.testing.assert_allclose(new[report['root_node'],:3,3],root['positions_m'][f],atol=1e-5)
        np.testing.assert_allclose(new[report['root_node'],:3,:3],Rotation.from_quat(root['rotations_xyzw'][f]).as_matrix(),atol=1e-5)
    assert maximum<1e-5
    def intervals(source,edited,key):
        expected=[]
        for c in source[key]:
            ids=np.flatnonzero((source_frames>=c['start_frame']-1e-9)&(source_frames<c['end_frame_exclusive']-1e-9))
            if len(ids):expected.append((c,int(ids[0]),int(ids[-1])+1))
        assert len(expected)==len(edited[key])
        for (old,first,last),new in zip(expected,edited[key]):
            assert (new['start_frame'],new['end_frame_exclusive'])==(first,last)
            for k in old:
                if k not in ('start_frame','end_frame_exclusive','start_seconds','end_seconds_exclusive'):assert old[k]==new[k]
    intervals(read(folder/'input/contacts.json'),read(folder/'transfer/contacts.json'),'intervals')
    if (folder/'contact-spec.json').exists():
        spec=read(folder/'contact-spec.json');assert spec['glb_sha256']==sha256(folder/'transfer/character.glb') and spec['frames']==n
        intervals(read(folder/'input/contact-spec.json'),spec,'contacts')
    data=urllib.request.urlopen('http://127.0.0.1:8768'+result['package']).read()
    assert hashlib.sha256(data).hexdigest()==result['package_sha256']==sha256(folder/'character-animation.zip')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            if name!='README.txt':assert archive.read(name)==(folder/name).read_bytes()
        entries=len(archive.namelist())
    cases=[]
    for variant in ('input','transfer'):
        v=result['variants'][variant];path=folder/variant/'character.glb'
        assert hashlib.sha256(urllib.request.urlopen('http://127.0.0.1:8768'+v['glb']).read()).hexdigest()==sha256(path)==v['sha256']
        cases.append(dict(id=job+'-'+variant,path=str(path),sha256=sha256(path),frames=v.get('frames',n),fps=30))
    return dict(job=job,frames=n,input_frames=result['variants']['input']['frames'],max_local_transform_error=maximum,package_entries=entries,passed=True),cases


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('jobs',nargs='+');args=p.parse_args()
    checks=[];cases=[]
    for job in args.jobs:
        check,items=verify(job);checks.append(check);cases.extend(items)
    for item in cases:item['path']=os.path.relpath(item['path'],ROOT/args.output).replace('\\','/')
    save(ROOT/args.output/'verification.json',dict(checks=checks,passed=True,scope='Encoding, edit preservation, source clocks, contact remapping and package bytes; not motion realism.'))
    save(ROOT/args.output/'manifest.json',dict(cases=cases));print(checks)
