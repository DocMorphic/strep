import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_scene_orientation as module


def test_world_point_can_have_independently_audited_normal(tmp_path,monkeypatch):
    np.savez(tmp_path/'actor.npz',sample=[1])
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'transform_motion',lambda motion,transform:motion)
    monkeypatch.setattr(module,'surface_normal_track',lambda motion,skin,vertex:np.array([[0.,0.,1.],[0.,1.,0.]]))
    contact=dict(id='palm',actor='A',effector=dict(surface_vertex=1),target=dict(space='world',point_m=[0,0,0]),
        start_frame=0,end_frame=1,normal_target=dict(space='world',direction=[0,0,1]))
    scene=dict(id='test',frame_count=2,actors=dict(A=dict(motion='actor.npz',transform={})),contacts=[contact])
    result=module.audit(scene,{})['contacts'][0]
    assert result['max_error_degrees']==90
    assert result['frames_over_tolerance']==1
    contact['normal_target']['direction']=[0,0,2]
    with pytest.raises(ValueError,match='unit'):module.audit(scene,{})
