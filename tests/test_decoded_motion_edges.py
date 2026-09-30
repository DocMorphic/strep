import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scipy.spatial.transform import Rotation
from test_elbow_swivel import arm
from gltf_tools import append_accessor,read_glb
from rig_clip_import import AnimationSampler
from native_waypoint_clock import guide_clock
from decoded_motion_edges import DecodedEdges
from wrist_waypoint_motion import bake
from waypoint_lattice import LinearGuide


def rig_fixture():
    parents,local,_=arm()
    nodes=[dict(name=str(i),translation=m[:3,3].tolist(),rotation=Rotation.from_matrix(m[:3,:3]).as_quat().tolist(),
                children=[j for j,p in enumerate(parents) if p==i]) for i,m in enumerate(local)]
    doc=dict(asset=dict(version='2.0'),nodes=nodes,buffers=[{}],bufferViews=[],accessors=[],animations=[dict(channels=[],samplers=[])])
    binary=bytearray();clock=np.linspace(0,2,21,dtype=np.float32);time=append_accessor(doc,binary,clock,'SCALAR')
    animation=doc['animations'][0]
    for node in [1,2,3]:
        values=(Rotation.from_quat(np.tile(nodes[node]['rotation'],(len(clock),1)))*Rotation.from_euler('y',clock*.03)).as_quat()
        output=append_accessor(doc,binary,values,'VEC4')
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path='rotation')))
        animation['samplers'].append(dict(input=time,output=output,interpolation='LINEAR'))
    animation['channels'].append(dict(sampler=0,target=dict(node=6,path='rotation')))
    return SimpleNamespace(document=doc,binary=binary,parents=parents,joints=list(range(len(nodes)))),clock


@pytest.mark.parametrize('one_actor_only',[False,True])
def test_every_edge_matches_actual_float32_glb_bake_and_shared_sampler(tmp_path,one_actor_only):
    rig,clock=rig_fixture();window=[.15,.5,.85];native=guide_clock([clock]*6,window,[])
    times=np.arange(241)/120;states=np.array([[0.,0.,0.],[.004,5.,-5.],[0.,0.,5.]])
    ids=[0]+[2 if one_actor_only else 1]*(len(native)-2)+[0]
    sources=[dict(rig=rig,chain=[1,2,3],rotation=np.eye(3)) for _ in range(2)]
    axis=np.array([0.,0.,1.]);decoder=DecodedEdges(sources,native,times,states,axis,SimpleNamespace(check=lambda p:True))
    guide=LinearGuide(native,states[ids],[.8,300,300]);readers=[]
    for actor in range(2):
        def curve(t):
            controls=guide(t)
            return np.r_[axis*controls[0]*(1 if actor==0 else -1),controls[actor+1]]
        path=tmp_path/f'{actor}.glb'
        bake(rig,[1,2,3],[0,0,0],np.eye(3),0,window,[],path,control_curve=curve)
        doc,binary=read_glb(path);readers.append(AnimationSampler(doc,binary,0))
    for layer,(a,b) in enumerate(zip(ids[:-1],ids[1:])):
        payload=decoder(layer,a,b)
        for actor,reader in enumerate(readers):
            worlds=np.array([reader.sample(t) for t in times[payload['indices']]])
            start=actor*len(rig.joints);end=start+len(rig.joints)
            np.testing.assert_array_equal(payload['positions'][:,start:end],worlds[:,:,:3,3])
            np.testing.assert_array_equal(payload['rotations'][:,start:end],worlds[:,:,:3,:3])
