import copy
import numpy as np
import pytest
from test_surface_clip import options,fixture,SurfaceClip


@pytest.mark.parametrize('end',[.1234567,.1234568])
def test_off_grid_contact_is_sampled_and_fails_exact_target(tmp_path,end):
    path,rig,reader,_=fixture(tmp_path);p=options();start=.1234567
    target=rig.vertices(reader.sample(start))[0].tolist();target[0]+=1.
    p['contacts']=[dict(vertex=0,target_m=target,start_time_s=start,end_time_s=end)]
    clip=SurfaceClip(rig,**p);audit=clip.audit(path,[0,1])
    assert not audit['passed']
    for t in {start,end}:
        row=next(row for row in audit['samples'] if row['time_s']==t)
        assert row['contact_error_m']>.99 and not row['numerical_pose_pass']
    assert start not in clip.clock([1,2])
    seed=clip.controls(rig,[0,1]);native,checks,_,clock=clip.build_window([0,1],seed)
    assert start in checks and end in checks
    assert not clip.dense_check(native,checks,clock,[0,1],seed.reshape(-1))[2]


def test_contact_boundary_budget_is_reserved_without_dropping_samples(tmp_path):
    _,rig,_,_=fixture(tmp_path);p=options();baseline=SurfaceClip(rig,**p)
    p['sampling']['maximum_samples']=len(baseline.keys)+7*(len(baseline.keys)-1)+int(np.floor(baseline.keys[-1]*20))+1
    SurfaceClip(rig,**p)
    p['contacts']=[dict(vertex=0,target_m=[0,0,0],start_time_s=.1234567,end_time_s=.1234568)]
    with pytest.raises(ValueError,match='contact-boundary'):SurfaceClip(rig,**p)
