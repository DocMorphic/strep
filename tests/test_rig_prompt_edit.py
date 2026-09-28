import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,sha256
from rig_prompt_edit import validate,weights
from rig_motion_bridge import to_soma
from target_rig_contact import RigAsset,baseline
from action_requests import validate_request


def payload():
    job='20260926-202128-ecb5f088';file=ROOT/'reports/rig-jobs'/job/'transfer/character.glb'
    return dict(source_job=job,variant='transfer',edit=dict(schema='strep-rig-prompt-edit-v1',glb_sha256=sha256(file),label='Regeneration test',prompt='A person crouches.',start_frame=10,last_frame=50,blend_frames=8,seed=203))


@pytest.mark.parametrize('change',[dict(start_frame=True),dict(last_frame=61),dict(last_frame=20),dict(blend_frames=3),dict(blend_frames=21),dict(seed=-1),dict(seed=True),dict(prompt=' '),dict(glb_sha256='bad')])
def test_invalid_regeneration_is_rejected_before_inference(change):
    p=payload();p['edit'].update(change)
    with pytest.raises(ValueError):validate(p)


def test_envelope_preserves_two_boundary_samples_and_has_full_interior():
    w=weights(41,8);assert np.array_equal(w[:2],[0,0]) and np.array_equal(w[-2:],[0,0])
    assert np.all(w[7:-7]==1) and np.array_equal(w,w[::-1])
    assert np.all(np.diff(w[:8])>=0)


def test_imported_pose_bridge_preserves_mapped_root_and_orientation():
    folder=ROOT/'reports/rig-jobs/20260926-202128-ecb5f088'
    world,_=baseline(RigAsset.load(folder/'transfer/character.glb'),4)
    data,audit=to_soma(RigAsset.load(folder/'source/character.glb'),read(folder/'source/rig-profile.json'),world)
    assert data['posed_joints'].shape==(4,77,3)
    assert not data['foot_contacts'].any()
    assert max(audit['root_error_m'],audit['mapped_rotation_matrix_error'])<1e-5
    assert audit['roundtrip_mesh_error_max_m']<.005


@pytest.mark.parametrize('heading',[True,float('nan'),4,'0'])
def test_invalid_model_initial_heading(heading):
    r=copy.deepcopy(read(ROOT/'reports/action-coverage-v1/request.json')['requests'][0]);r['first_heading_angle']=heading
    with pytest.raises(ValueError):validate_request(r)
