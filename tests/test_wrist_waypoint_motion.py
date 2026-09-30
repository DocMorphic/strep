import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from wrist_waypoint_motion import bump,peak_window


def test_waypoint_envelope_preserves_boundaries_and_has_smooth_returns():
    assert bump(1,1,2,4)==0 and bump(4,1,2,4)==0 and bump(2,1,2,4)==1
    assert bump(0,1,2,4)==0 and bump(5,1,2,4)==0
    values=[bump(t,1,2,4) for t in np.linspace(1,4,200)]
    assert min(values)>=0 and max(values)<=1
    for stamp in [1,2,4]:
        h=1e-4
        assert abs((bump(stamp+h,1,2,4)-bump(stamp-h,1,2,4))/(2*h))<1e-6
        assert abs((bump(stamp+h,1,2,4)-2*bump(stamp,1,2,4)+bump(stamp-h,1,2,4))/h**2)<.01


def test_window_excludes_later_collision_cluster_instead_of_hiding_it():
    rows=[dict(sample=i,time_s=i/10,candidate_depth_m=.01 if i in [2,3,4,8,9] else 0.) for i in range(11)]
    assert peak_window(rows,3,[.1,1.])==pytest.approx([.1,.3,.6])
    with pytest.raises(ValueError):peak_window(rows,6,[.1,1.])
    rows[0]['sample']=4
    with pytest.raises(ValueError):peak_window(rows,3,[.1,1.])


@pytest.mark.parametrize('scheduled',[False,True,'native'])
def test_native_waypoint_bake_protects_keys_shared_sampler_and_contact(tmp_path,scheduled):
    from types import SimpleNamespace
    from scipy.spatial.transform import Rotation
    from test_elbow_swivel import arm
    from gltf_tools import append_accessor,read_glb
    from rig_clip_import import AnimationSampler
    from paired_temporal_neighbor import rotation_channels
    from wrist_waypoint_motion import bake
    parents,local,_=arm()
    nodes=[dict(name=str(i),translation=m[:3,3].tolist(),rotation=Rotation.from_matrix(m[:3,:3]).as_quat().tolist(),
                children=[j for j,p in enumerate(parents) if p==i]) for i,m in enumerate(local)]
    doc=dict(asset=dict(version='2.0'),nodes=nodes,buffers=[{}],bufferViews=[],accessors=[],animations=[dict(channels=[],samplers=[])])
    binary=bytearray();clock=np.linspace(0,2,61,dtype=np.float32);time=append_accessor(doc,binary,clock,'SCALAR')
    for node in [1,2,3]:
        values=np.tile(nodes[node]['rotation'],(len(clock),1))
        values=(Rotation.from_quat(values)*Rotation.from_euler('y',clock*.02)).as_quat()
        output=append_accessor(doc,binary,values,'VEC4');animation=doc['animations'][0]
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path='rotation')))
        animation['samplers'].append(dict(input=time,output=output,interpolation='LINEAR'))
    animation['channels'].append(dict(sampler=0,target=dict(node=6,path='rotation')))
    rig=SimpleNamespace(document=doc,binary=binary,parents=parents);path=tmp_path/'motion.glb'
    window=[.2,.6,1.1];offset=np.array([-.01,0.,0.])
    from waypoint_lattice import LinearGuide
    guide=LinearGuide([.2,.5,.8,1.1],[[0,0,0],[.006,9,0],[.01,15,0],[0,0,0]],[.8,300,300])
    if scheduled=='native':
        from native_waypoint_clock import guide_clock
        native=guide_clock([clock]*3,window,[[1.5,1.5]])
        weights=np.array([bump(t,native[0],.6,native[-1]) for t in native])
        guide=LinearGuide(native,weights[:,None]*np.array([.01,15,0]),[.8,300,300])
    curve=lambda t:np.r_[[-guide(t)[0],0,0],guide(t)[1]]
    report=bake(rig,[1,2,3],offset,np.eye(3),15.,window,[[1.5,1.5]],path,control_curve=curve if scheduled else None)
    changed,payload=read_glb(path);before=rotation_channels(doc,binary);after=rotation_channels(changed,payload)
    for node,(_,times,q) in before.items():
        np.testing.assert_array_equal(after[node][1],times)
        frozen=np.setdiff1d(np.arange(len(times)),report['nodes'].get(str(node),[]))
        np.testing.assert_array_equal(after[node][2][frozen],q[frozen])
    original=AnimationSampler(doc,binary,0);edited=AnimationSampler(changed,payload,0)
    for stamp in np.r_[np.linspace(0,.2,11),np.linspace(1.1,2,101),1.5]:
        np.testing.assert_array_equal(edited.sample(stamp),original.sample(stamp))
    if scheduled=='native':
        for stamp in guide.times[[0,-1]]:
            np.testing.assert_array_equal(edited.sample(stamp),original.sample(stamp))
    for key in report['nodes']['1']:
        stamp=float(clock[key]);a=original.sample(stamp);b=edited.sample(stamp)
        target_offset=curve(stamp)[:3] if scheduled else offset*bump(stamp,*window)
        np.testing.assert_allclose(b[3,:3,3],a[3,:3,3]+target_offset,atol=2e-7,rtol=0)
        np.testing.assert_allclose(b[3,:3,:3],a[3,:3,:3],atol=2e-7,rtol=0)
    assert max(r['maximum_edit_degrees'] for r in report['observations'])>10
