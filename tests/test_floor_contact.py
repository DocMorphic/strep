import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from floor_contact import correct,reconstruct,smooth_lift,Surface
from build_soma_preview import ASSET
from inspect_motion import skeleton_metadata
from strep import ROOT


def fixture():
    return dict(np.load(ROOT/'reports/action-coverage-v1/takes/crawl-seed-11/motion.npz')),dict(np.load(ASSET))


def test_lift_envelope_is_bounded_and_spreads_impulses():
    required=np.zeros(30);required[15]=.03;result=smooth_lift(required,.05)
    assert np.all(result>=required-1e-9) and result.max()<=.05
    assert 0<result[14]<result[15] and 0<result[16]<result[15]
    np.testing.assert_array_equal(smooth_lift(np.zeros(30),.05),0)
    assert smooth_lift(np.ones(30),.05).max()<=.05


def test_correction_preserves_root_bones_fingers_and_source():
    motion,skin=fixture();snapshot={k:v.copy() for k,v in motion.items()}
    corrected,recipe=correct(motion,skin);names,parents,_=skeleton_metadata(77)
    for k in snapshot:np.testing.assert_array_equal(motion[k],snapshot[k])
    for k in ['root_positions','foot_contacts','smooth_root_pos','global_root_heading']:np.testing.assert_array_equal(motion[k],corrected[k])
    fingers=[j for j,n in enumerate(names) if 'Hand' in n and not n.endswith('Hand')]
    np.testing.assert_allclose(corrected['local_rot_mats'][:,fingers],motion['local_rot_mats'][:,fingers],atol=1e-6)
    for j,parent in enumerate(parents):
        if parent<0:continue
        a=np.linalg.norm(motion['posed_joints'][:,j]-motion['posed_joints'][:,parent],axis=-1)
        b=np.linalg.norm(corrected['posed_joints'][:,j]-corrected['posed_joints'][:,parent],axis=-1)
        np.testing.assert_allclose(a,b,atol=2e-6)
    r=corrected['global_rot_mats'];np.testing.assert_allclose(r@r.swapaxes(-1,-2),np.broadcast_to(np.eye(3),r.shape),atol=2e-6)
    surface=Surface(skin)
    for side in ['Left','Right']:
        assert surface.heights(corrected,side+'Hand').min()>surface.heights(motion,side+'Hand').min()+.02


def test_floor_misses_airborne_motion_without_anchoring():
    motion,skin=fixture()
    motion['root_positions'][:,1]+=3;motion['posed_joints'][:,:,1]+=3
    corrected,recipe=correct(motion,skin)
    np.testing.assert_allclose(corrected['posed_joints'],motion['posed_joints'],atol=4e-6)
    assert all(np.max(v)==0 for v in recipe['lift_requested_m'].values())


def test_study_paths_stay_in_allowlist():
    from action_studio_server import allowed_file
    assert allowed_file('/files/floor-contact-v1-reviewed/takes/crawl-seed-11/raw/soma.glb')
    assert allowed_file('/files/floor-contact-v1-reviewed/../../models/manifest.json') is None
    assert allowed_file('/files/floor-contact-v1-reviewed-fake/summary.json') is None
