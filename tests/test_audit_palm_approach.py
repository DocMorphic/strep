import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import trimesh
import pytest
from audit_palm_approach import sample_frames
from rig_clip_import import AnimationSampler
from bounded_partner_surface import penetration


def test_midframe_sample_catches_crossing_missed_at_integer_frames():
    moving=trimesh.creation.box(extents=[.2,.2,.2]);target=trimesh.creation.box(extents=[1.,1.,1.])
    times=np.array([0,1/30],dtype=np.float32);positions=np.array([[-2.,0,0],[2.,0,0]])
    depths=[]
    for frame in sample_frames(2,0,1,2):
        position=AnimationSampler.value('translation',times,positions,'LINEAR',float(np.float32(frame/30)))
        depths.append(penetration(moving.vertices+position,target.vertices,target.faces)['max_depth_m'])
    assert depths[0]==depths[2]==0
    assert depths[1]==pytest.approx(.4,abs=1e-6)


def test_audit_window_includes_both_edges_and_contact_without_leaving_clip():
    frames=sample_frames(150,75,15,2)
    assert len(frames)==61 and frames[0]==60 and frames[-1]==90 and 75 in frames
    assert np.all(np.diff(frames)==.5)
    np.testing.assert_array_equal(sample_frames(3,2,15,2),[0,.5,1,1.5,2])
    for args in [(0,0,1,2),(3,3,1,2),(3,0,0,2),(3,0,1,3),(3,0,1,True)]:
        with pytest.raises(ValueError):sample_frames(*args)
