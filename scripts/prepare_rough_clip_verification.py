"""Freeze original and mixed-interpolation fixtures for independent engine checks."""
import copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb
from rig_clip_import import export


def prepare():
    output=ROOT/'reports/rough-clip-interpolation-v1';output.mkdir(exist_ok=False)
    source=ROOT/'assets/characters/cesium-man/CesiumMan.glb';rig=RigAsset.load(source)
    profile=read(source.parent/'rig-profile-v2.json');document,binary=copy.deepcopy(rig.document),bytearray(rig.binary)
    animation=dict(name='Mixed_interpolation_fixture',channels=[],samplers=[])
    def channel(node,path,times,values,mode):
        a=append_accessor(document,binary,np.asarray(times),'SCALAR');b=append_accessor(document,binary,np.asarray(values),'VEC4' if path=='rotation' else 'VEC3')
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=path)))
        animation['samplers'].append(dict(input=a,output=b,interpolation=mode))
    base=np.asarray(document['nodes'][3].get('translation',[0,0,0]),float)
    channel(3,'translation',[0,.4,1],[[0,0,0],base,[.03,.04,0],[.04,0,0],base+[.03,.02,0],[.1,-.03,0],[.08,0,0],base+[.08,0,0],[0,0,0]],'CUBICSPLINE')
    for node,angles,times,mode in [(13,[0,25,-15],[.1,.37,1],'LINEAR'),(19,[0,30,-20,0],[0,.31,.8,1],'STEP')]:
        rest=Rotation.from_quat(document['nodes'][node].get('rotation',[0,0,0,1]))
        channel(node,'rotation',times,(rest*Rotation.from_euler('z',angles,degrees=True)).as_quat(),mode)
    document['animations']=[animation];write_glb(output/'mixed-source.glb',document,binary)
    profile['character_sha256']=sha256(output/'mixed-source.glb');save(output/'mixed-profile.json',profile)
    report=export(output/'mixed-source.glb',output/'mixed-profile.json',0,output/'sampled')
    save(output/'provenance.json',dict(base_asset=str(source),base_sha256=sha256(source),synthetic=True,source_license='CesiumMan CC BY 4.0 and retained logo terms; see original asset attachments',scope='Engine/interpolation verification fixture, not generated motion or realism evidence',builder_sha256=sha256(__file__)))
    save(output/'manifest.json',dict(cases=[
        dict(id='original-cesium-by-time',path='../../assets/characters/cesium-man/CesiumMan.glb',sha256=sha256(source),fps=30,frames=61,sample_by_time=True),
        dict(id='mixed-source-by-time',path='mixed-source.glb',sha256=sha256(output/'mixed-source.glb'),fps=30,frames=31,sample_by_time=True),
        dict(id='mixed-sampled',path='sampled/character.glb',sha256=report['glb_sha256'],fps=30,frames=report['frames']),
    ]))
    print('Prepared original and mixed interpolation source fixtures')


if __name__=='__main__':prepare()
