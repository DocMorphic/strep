import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from strep import ROOT, read
from target_rig_contact import RigAsset, SkinEvaluator, baseline, Fitter, validate, audit
from target_rig_contact import floor_lower_bound
from target_rig_contact import prepare_animated_node
from gltf_tools import local_matrix,global_matrices


@pytest.fixture
def fixture():
    spec = read(ROOT / 'reports/target-rig-contact-v1/specs/wave.json')
    rig = RigAsset.load(ROOT / 'reports/rig-axis-calibration-v1/wave/character.glb')
    world, local = baseline(rig, spec['frames'])
    return rig, spec, world, local


def test_cached_skin_matches_independent_skin_evaluator(fixture):
    rig, _, world, _ = fixture
    skin = SkinEvaluator(rig)
    for frame in (0, 25, 119):
        np.testing.assert_allclose(skin.vertices(world[frame]), rig.vertices(world[frame]), atol=1e-12)


def test_zero_edit_preserves_motion_and_joint_lengths(fixture):
    rig, spec, before, local = fixture
    fitter = Fitter(rig, spec, local)
    values = np.zeros(len(fitter.bounds))
    world, changed = fitter.pose(60, values)
    np.testing.assert_allclose(world, before[60], atol=1e-12)
    values[1] = .07; values[3:] = fitter.bounds[3:] * .9
    world, changed = fitter.pose(60, values)
    for node, parent in enumerate(rig.parents):
        if parent >= 0 and node != spec['root_node']:
            np.testing.assert_allclose(np.linalg.norm(world[node,:3,3]-world[parent,:3,3]), np.linalg.norm(before[60,node,:3,3]-before[60,parent,:3,3]), atol=1e-6)
    np.testing.assert_allclose(world[spec['root_node'],:3,3]-before[60,spec['root_node'],:3,3], [0,.07,0],atol=1e-12)
    # Chest and arms retain their original local transforms.
    for node in [12,13,14,17,18,19]:
        np.testing.assert_allclose(changed[node],local[60,node],atol=1e-12)


@pytest.mark.parametrize('fault',['patch','overlap','outside','root','ancestor','limit','nonfinite'])
def test_invalid_contact_specs_rejected(fixture,fault):
    rig,spec,_,_=fixture
    spec=copy.deepcopy(spec)
    if fault=='patch':spec['patches']['Left-heel']['vertices']=[999999]
    if fault=='overlap':spec['contacts'].append(copy.deepcopy(spec['contacts'][0]))
    if fault=='outside':spec['contacts'][0]['end_frame_exclusive']=999
    if fault=='root':spec['root_node']=999
    if fault=='ancestor':spec['edit_joints']['LeftFoot']['node']=0
    if fault=='limit':spec['limits']['root_vertical_m']=-1
    if fault=='nonfinite':spec['contacts'][0]['target_position_m']=[0,np.nan,0]
    with pytest.raises(ValueError):validate(spec,rig)


def test_norm_budgets_and_independent_audit_detect_over_edit(fixture):
    rig,spec,before,local=fixture
    fitter=Fitter(rig,spec,local)
    values=np.tile(fitter.bounds,(len(before),1))
    for i,limit in enumerate(fitter.angles):
        assert np.linalg.norm(values[0,3+i*3:6+i*3])==pytest.approx(limit)
    after=before.copy();after[:,:,1,3]+=.13
    result=audit(rig,spec,before,after,values,[dict(success=True)]*len(before))
    assert 'root_vertical_max_m_bound_exceeded' in result['flags']
    assert not result['numerical_screen_passed']


def test_invariant_body_surface_can_prove_floor_budget_infeasible(fixture):
    rig,spec,before,_=fixture
    assert not floor_lower_bound(rig,spec,before)['floor_infeasible_under_declared_edits']
    lowered=before[:2].copy();lowered[:,:,1,3]-=2
    diagnostic=floor_lower_bound(rig,spec,lowered)
    assert diagnostic['floor_infeasible_under_declared_edits']
    assert diagnostic['unavoidable_floor_depth_lower_bound_m']>1
    # Permitting every descendant to rotate makes this limited proof silent.
    spec=copy.deepcopy(spec)
    spec['edit_joints']={str(n):dict(node=n,limit_degrees=25) for n in rig.joints}
    assert floor_lower_bound(rig,spec,lowered)['rotation_invariant_vertex_count']==0


def test_newly_animated_matrix_joint_preserves_reference_transform(fixture):
    rig,_,_,_=fixture
    doc=copy.deepcopy(rig.document);node=11
    matrix=local_matrix(doc['nodes'][node]);name=doc['nodes'][node].get('name')
    doc['nodes'][node]={'matrix':matrix.T.ravel().tolist(),'name':name}
    expected=global_matrices(doc)
    prepare_animated_node(doc,node)
    assert 'matrix' not in doc['nodes'][node]
    assert set(('translation','rotation','scale'))<=set(doc['nodes'][node])
    np.testing.assert_allclose(global_matrices(doc),expected,atol=1e-7)
