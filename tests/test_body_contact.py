import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from body_contact import refine
from evaluate_body_contact import midpoints,body_support
from build_soma_preview import ASSET
from floor_contact import Surface
from inspect_motion import skeleton_metadata
from audit_body_ground import measure
from strep import ROOT


@pytest.fixture(scope='module')
def crawl():
    base=dict(np.load(ROOT/'reports/floor-contact-v1-reviewed/takes/crawl-seed-11/motion.npz'))
    skin=dict(np.load(ASSET));snapshot={k:v.copy() for k,v in base.items()}
    candidate,recipe=refine(base,skin)
    return base,skin,snapshot,candidate,recipe


def test_body_cleanup_is_rigid_and_preserves_horizontal_trajectory(crawl):
    base,skin,snapshot,candidate,recipe=crawl
    for k in base:np.testing.assert_array_equal(base[k],snapshot[k])
    np.testing.assert_array_equal(candidate['root_positions'][:,[0,2]],base['root_positions'][:,[0,2]])
    np.testing.assert_array_equal(candidate['foot_contacts'],base['foot_contacts'])
    np.testing.assert_allclose(candidate['global_rot_mats'][:,0],base['global_rot_mats'][:,0],atol=1e-6)
    assert 0<max(recipe['root_lift_m'])<=.22 and 'smooth_root_pos' not in candidate
    names,parents,_=skeleton_metadata(77)
    for j,p in enumerate(parents):
        if p<0:continue
        a=np.linalg.norm(base['posed_joints'][:,j]-base['posed_joints'][:,p],axis=-1)
        b=np.linalg.norm(candidate['posed_joints'][:,j]-candidate['posed_joints'][:,p],axis=-1)
        np.testing.assert_allclose(a,b,atol=3e-6)
    for name in ['LeftHand','RightHand','LeftFoot','RightFoot']:
        j=names.index(name)
        np.testing.assert_allclose(candidate['global_rot_mats'][:,j],base['global_rot_mats'][:,j],atol=1e-6)
    assert measure(candidate,skin)['mesh_max_depth_m']<.002


def test_already_clear_motion_is_exact_no_op(crawl):
    base,skin,_,_,_=crawl
    elevated={k:v.copy() for k,v in base.items()}
    elevated['root_positions'][:,1]+=3;elevated['posed_joints'][:,:,1]+=3
    result,recipe=refine(elevated,skin)
    assert not recipe['applied']
    for k in elevated:np.testing.assert_array_equal(result[k],elevated[k])


def test_halfway_audit_uses_valid_rotations_and_midpoint_root(crawl):
    _,_,_,candidate,_=crawl
    between=midpoints(candidate);r=between['global_rot_mats']
    assert len(r)==len(candidate['root_positions'])-1
    np.testing.assert_allclose(r@r.swapaxes(-1,-2),np.broadcast_to(np.eye(3),r.shape),atol=2e-6)
    np.testing.assert_array_equal(between['root_positions'],(candidate['root_positions'][:-1]+candidate['root_positions'][1:])/2)


def test_support_audit_catches_simple_global_lifting(crawl):
    base,skin,_,_,_=crawl
    still={k:np.repeat(v[33:34],12,axis=0) for k,v in base.items()}
    floating={k:v.copy() for k,v in still.items()};floating['posed_joints'][:,:,1]+=.1;floating['root_positions'][:,1]+=.1
    report=body_support(still,floating,skin)
    assert 'RightKnee_body_support_gap_regression' in report['flags']
