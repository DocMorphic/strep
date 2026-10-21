"""Floor clearance alone cannot hide loss of an existing support contact."""
from pathlib import Path
import sys
import numpy as np,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from root_plane_contact_bounds import interval,translation_coefficients


def test_planted_point_blocks_lift_that_would_clear_other_foot():
    result=interval([-.05,0.],[1.,1.],floor_height_m=-.005,lower_m=0.,upper_m=.22,
        contacts=[dict(id='support',error_m=[0,0,0],coefficient=1.,position_limit_m=.005)])
    assert not result['per_pose_interval_nonempty']
    assert result['lower_m']==pytest.approx(.045) and result['upper_m']==.005
    assert result['lower_witness']['vertex']==0 and result['upper_witness']['id']=='support'


def test_floor_only_pass_does_not_establish_clip_or_human_quality():
    result=interval([-.05,0.],[1.,1.],floor_height_m=-.005,lower_m=0.,upper_m=.22)
    assert result['per_pose_interval_nonempty'] and result['lower_m']==pytest.approx(.045)
    assert not result['clip_feasibility_established'] and not result['quality_approved']


def test_unmoving_and_negative_root_influences_are_retained():
    result=interval([-.05,.01],[0.,-1.],floor_height_m=0.,lower_m=0.,upper_m=.22)
    assert not result['per_pose_interval_nonempty'] and result['upper_m']==.01
    assert result['conflicts'][0]['kind']=='immovable-floor'


@pytest.mark.parametrize('coefficient',[1.,-.5])
def test_contact_interval_matches_direct_euclidean_distance(coefficient):
    row=dict(id='point',error_m=[.003,.008,.004],coefficient=coefficient,position_limit_m=.01)
    result=interval([1.],[0.],floor_height_m=0.,lower_m=-1.,upper_m=1.,contacts=[row])
    assert result['per_pose_interval_nonempty']
    for offset in (result['lower_m'],result['upper_m']):
        assert np.linalg.norm(np.asarray(row['error_m'])+[0,coefficient*offset,0])==pytest.approx(.01)


@pytest.mark.parametrize('coefficient',[0.,1.])
def test_horizontal_or_immovable_contact_errors_cannot_be_fixed_by_lift(coefficient):
    result=interval([1.],[1.],floor_height_m=0.,lower_m=0.,upper_m=.22,
        contacts=[dict(id='miss',error_m=[.02,0,0],coefficient=coefficient,position_limit_m=.005)])
    assert not result['per_pose_interval_nonempty']


def test_complete_population_is_not_replaced_by_one_chosen_vertex():
    result=interval([-.01,-.12,.2],[1,1,1],floor_height_m=0.,lower_m=0.,upper_m=.22)
    assert result['vertices']==3 and result['lower_witness']['vertex']==1 and result['lower_m']==.12


@pytest.mark.parametrize('fault',['nan','shape','order','floor-bool'])
def test_invalid_original_inputs_reject(fault):
    heights=[0,1];coefficients=[1,1];args=dict(floor_height_m=0.,lower_m=0.,upper_m=.22)
    if fault=='nan':heights[0]=float('nan')
    elif fault=='shape':coefficients=[1]
    elif fault=='order':args['lower_m']=.23
    else:args['floor_height_m']=False
    with pytest.raises(ValueError):interval(heights,coefficients,**args)


def test_actual_subtree_translation_matches_complete_skin_response(tmp_path):
    from test_native_scene_geometry import closed_fixture
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    source,_,_=closed_fixture(tmp_path);rig=RigAsset.load(source)
    p=rig.primitives[0];p['weights'][:]=[.7,.3,0,0];p['joints'][:]=[3,0,0,0]
    rig.inverse[3,3,0]=1e-6
    coefficient,descendants=translation_coefficients(rig,rig.joints[3])
    world=NativeSupportSampler(rig.document,rig.binary,0).sample(.7);shifted=world.copy();shifted[descendants,1,3]+=.03
    delta=rig.vertices(shifted)-rig.vertices(world)
    np.testing.assert_allclose(delta[:,1],.03*coefficient,atol=2e-15,rtol=0)
    np.testing.assert_allclose(delta[:,[0,2]],0,atol=2e-15,rtol=0)
    assert not np.array_equal(coefficient,np.full(len(coefficient),.7))


def test_float32_weight_residue_can_exceed_unit_translation_response(tmp_path):
    from test_native_scene_geometry import closed_fixture
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    source,_,_=closed_fixture(tmp_path);rig=RigAsset.load(source);p=rig.primitives[0]
    # Valid stored float32 weights can sum to 1 in float32 but exceed it in
    # the decoded Float64 skin evaluation. Never clamp the exact response.
    p['weights']=np.tile(np.array([.1,.2,.3,.4],dtype=np.float32),(len(p['positions']),1))
    p['joints'][:]=[3,3,3,3]
    coefficients,affected=translation_coefficients(rig,rig.joints[3])
    assert np.all(coefficients>1.)
    world=NativeSupportSampler(rig.document,rig.binary,0).sample(.7);delta=np.array([.02,.03,-.01]);changed=world.copy();changed[affected,:3,3]+=delta
    actual=rig.vertices(changed)-rig.vertices(world)
    np.testing.assert_allclose(actual,coefficients[:,None]*delta,atol=2e-15,rtol=0)
    assert np.linalg.norm(actual,axis=1).max()>np.linalg.norm(delta)+1e-10
    budget=.03;bounded=delta/np.linalg.norm(delta)*budget/np.abs(coefficients).max()
    changed=world.copy();changed[affected,:3,3]+=bounded
    assert np.linalg.norm(rig.vertices(changed)-rig.vertices(world),axis=1).max()<=budget+2e-15


def test_two_root_bound_centroids_need_not_have_identical_stored_response(tmp_path):
    from test_native_scene_geometry import closed_fixture
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    source,_,_=closed_fixture(tmp_path);rig=RigAsset.load(source);p=rig.primitives[0];split=len(p['positions'])//2
    assert 0<split<len(p['positions'])
    p['weights']=np.tile(np.array([.25,.25,.25,.25],dtype=np.float32),(len(p['positions']),1))
    p['weights'][:split]=[.1,.2,.3,.4];p['joints'][:]=[3,3,3,3]
    coefficients,affected=translation_coefficients(rig,rig.joints[3]);difference=coefficients[:split].mean()-coefficients[split:].mean()
    assert difference>0
    world=NativeSupportSampler(rig.document,rig.binary,0).sample(.7);delta=np.array([.02,.03,-.01]);changed=world.copy();changed[affected,:3,3]+=delta
    before,after=rig.vertices(world),rig.vertices(changed)
    pair_change=(after[:split].mean(0)-after[split:].mean(0))-(before[:split].mean(0)-before[split:].mean(0))
    np.testing.assert_allclose(pair_change,difference*delta,atol=2e-15,rtol=0)
    # Across two times, a bounded common translation changes a relative
    # centroid vector by at most 2 * root_budget * abs(response_difference).
    assert np.linalg.norm(pair_change)<=2*.03*abs(difference)+2e-15
