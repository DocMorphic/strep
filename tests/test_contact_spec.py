import sys
from pathlib import Path
import copy
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_spec import validate,apply_overrides
from support_contact import infer_support,regions
from support_contact_v2 import bounded_rotation,bounded_lift
from build_soma_preview import ASSET
from strep import ROOT


def test_hard_parameter_bounds_and_gradients_at_extremes():
    x=torch.tensor([[0.,0.,0.],[1e6,-1e6,1e6]],dtype=torch.float64,requires_grad=True)
    r=bounded_rotation(x,.7)
    assert torch.linalg.vector_norm(r,dim=-1).max()<=.7
    r.sum().backward();assert torch.isfinite(x.grad).all()
    z=torch.tensor([-1e6,0.,1e6],dtype=torch.float64,requires_grad=True)
    y=bounded_lift(z,.22)
    assert y.min()>=0 and y.max()<=.22
    y.sum().backward();assert torch.isfinite(z.grad).all()


@pytest.fixture(scope='module')
def fixture():
    source=dict(np.load(ROOT/'reports/body-contact-v1/takes/crawl-seed-11/limb/motion.npz'))
    short={k:v[25:40].copy() for k,v in source.items()};skin=dict(np.load(ASSET))
    return short,skin,infer_support(short,skin)


def spec(entry):return dict(schema_version=1,fps=30,frame_count=15,regions={'LeftHand':entry})


def test_world_target_pins_one_vertex_and_does_not_mutate_inference(fixture):
    base,skin,inferred=fixture;snapshot=copy.deepcopy(inferred)
    request=spec(dict(mode='explicit',segments=[dict(start_frame=2,end_frame=10,space='world',position_m=[.1,.002,.3])]))
    result=apply_overrides(inferred,base,skin,request)
    c=result['LeftHand'];assert np.unique(c['vertex_ids']).size==1
    np.testing.assert_array_equal(c['targets'],np.tile([.1,.002,.3],(15,1)))
    assert c['active'].sum()==9
    for name in inferred:
        for k,v in inferred[name].items():
            if isinstance(v,np.ndarray):np.testing.assert_array_equal(v,snapshot[name][k])


def test_disable_only_removes_requested_region(fixture):
    base,skin,inferred=fixture
    result=apply_overrides(inferred,base,skin,spec(dict(mode='disabled')))
    assert not result['LeftHand']['weights'].any()
    for name in inferred:
        if name!='LeftHand':np.testing.assert_array_equal(result[name]['weights'],inferred[name]['weights'])


@pytest.mark.parametrize('segments',[
    [dict(start_frame=-1,end_frame=4,space='baseline')],
    [dict(start_frame=0,end_frame=15,space='baseline')],
    [dict(start_frame=0,end_frame=4,space='baseline'),dict(start_frame=4,end_frame=8,space='baseline')],
    [dict(start_frame=0,end_frame=4,space='world',position_m=[0,float('nan'),0])],
    [dict(start_frame=0,end_frame=4,space='world',position_m=[0,-.1,0])],
    [dict(start_frame=0,end_frame=4,space='baseline',vertex_id=999999)],
])
def test_invalid_constraints_fail_before_optimization(fixture,segments):
    _,skin,_=fixture
    with pytest.raises(ValueError):validate(spec(dict(mode='explicit',segments=segments)),15,regions(skin))


def test_independent_target_measurement_detects_known_translation(fixture):
    from evaluate_contact_spec import evaluate
    from floor_contact import Surface
    base,skin,_=fixture
    still={k:np.repeat(v[:1],15,axis=0) for k,v in base.items()}
    still['root_positions'][:,1]+=3;still['posed_joints'][:,:,1]+=3
    vertex=int(regions(skin)['LeftHand'][0])
    target=Surface(skin).vertices(still['global_rot_mats'][0],still['posed_joints'][0],[vertex])[0].tolist()
    request=spec(dict(mode='explicit',segments=[dict(start_frame=2,end_frame=10,space='world',position_m=target,vertex_id=vertex)]))
    result=evaluate(still,still,skin,request)
    assert result['all_explicit_targets_within_tolerance']
    moved={k:v.copy() for k,v in still.items()}
    moved['root_positions'][:,0]+=.2;moved['posed_joints'][:,:,0]+=.2
    result=evaluate(still,moved,skin,request)
    assert not result['all_explicit_targets_within_tolerance']
    assert result['intervals'][0]['max_error_m']==pytest.approx(.2,abs=1e-6)


def test_no_authored_targets_cannot_claim_target_success(fixture):
    from evaluate_contact_spec import evaluate
    base,skin,_=fixture
    assert not evaluate(base,base,skin,spec(dict(mode='disabled')))['all_explicit_targets_within_tolerance']


def test_moving_target_uses_inclusive_samples_and_clamps_fade(fixture):
    from evaluate_contact_spec import evaluate
    from floor_contact import Surface
    base,skin,inferred=fixture
    vertex=int(regions(skin)['LeftHand'][0])
    shifted={k:v.copy() for k,v in base.items()}
    shifted['root_positions'][:,1]+=3;shifted['posed_joints'][:,:,1]+=3
    track=[Surface(skin).vertices(r,p,[vertex])[0].tolist() for r,p in zip(shifted['global_rot_mats'],shifted['posed_joints'])]
    segment=dict(start_frame=2,end_frame=10,space='track',positions_m=track[2:11],vertex_id=vertex)
    request=spec(dict(mode='explicit',segments=[segment]));request['schema_version']=2
    result=apply_overrides(inferred,base,skin,request)['LeftHand']
    np.testing.assert_allclose(result['targets'][2:11],track[2:11])
    np.testing.assert_allclose(result['targets'][:2],np.tile(track[2],(2,1)))
    np.testing.assert_allclose(result['targets'][11:],np.tile(track[10],(4,1)))
    assert result['active'].sum()==9
    measured=evaluate(base,shifted,skin,request)
    assert measured['all_explicit_targets_within_tolerance']
    wrong=copy.deepcopy(request);wrong['regions']['LeftHand']['segments'][0]['positions_m'][4][0]+=.2
    measured=evaluate(base,shifted,skin,wrong)['intervals'][0]
    assert measured['frames_outside_tolerance']==1
    assert measured['per_frame_error_m'][4]==pytest.approx(.2)


@pytest.mark.parametrize('version,points,extra',[
    (1,[[0,1,0]]*3,{}),(2,[[0,1,0]]*2,{}),(2,[[0,1,0],[0,float('inf'),0],[0,1,0]],{}),
    (2,[[0,-1,0]]*3,{}),(2,[[True,1,0]]*3,{}),(2,[[0,1,0]]*3,{'position_m':[0,1,0]}),
])
def test_invalid_moving_tracks_are_rejected(fixture,version,points,extra):
    _,skin,_=fixture
    request=spec(dict(mode='explicit',segments=[dict(start_frame=2,end_frame=4,space='track',positions_m=points,**extra)]))
    request['schema_version']=version
    with pytest.raises(ValueError):validate(request,15,regions(skin))


@pytest.mark.parametrize('tolerance',[0,-.001,float('nan'),float('inf'),True,'0.001',None])
def test_invalid_interval_tolerances_reject(fixture,tolerance):
    _,skin,_=fixture
    request=spec(dict(mode='explicit',segments=[dict(start_frame=2,end_frame=4,space='baseline',tolerance_m=tolerance)]))
    with pytest.raises(ValueError):validate(request,15,regions(skin))


def test_authored_tolerance_overrides_looser_evaluator_fallback_per_interval(fixture):
    from evaluate_contact_spec import evaluate
    from floor_contact import Surface
    base,skin,_=fixture
    shifted={key:value.copy() for key,value in base.items()}
    shifted['posed_joints'][:,:,0]+=.004
    request=spec(dict(mode='explicit',segments=[
        dict(start_frame=2,end_frame=4,space='baseline',tolerance_m=.001),
        dict(start_frame=7,end_frame=9,space='baseline',tolerance_m=.01)]))
    # Exact recorded surface tracks avoid the baseline floor-clamp policy.
    vertex=int(regions(skin)['LeftHand'][0]);surface=Surface(skin)
    request['schema_version']=2
    for segment in request['regions']['LeftHand']['segments']:
        segment.update(space='track',vertex_id=vertex,positions_m=[
            surface.vertices(base['global_rot_mats'][f],base['posed_joints'][f],[vertex])[0].tolist()
            for f in range(segment['start_frame'],segment['end_frame']+1)])
    snapshot=copy.deepcopy(request)
    result=evaluate(base,shifted,skin,request,tolerance_m=.1)
    assert request==snapshot and not result['all_explicit_targets_within_tolerance']
    assert [r['tolerance_m'] for r in result['intervals']]==[.001,.01]
    assert [r['frames_outside_tolerance'] for r in result['intervals']]==[3,0]
    with pytest.raises(ValueError):evaluate(base,base,skin,request,tolerance_m=float('nan'))


def test_solver_tolerances_tighten_only_authored_keys_and_keep_original_limits():
    from contact_spec import solver_point_tolerances
    contacts={'RightHand':{},'LeftHand':{},'LeftFoot':{}}
    request=dict(regions={'LeftHand':dict(mode='explicit',segments=[
        dict(start_frame=2,end_frame=4,tolerance_m=.001),
        dict(start_frame=7,end_frame=9,tolerance_m=.1)]),
        'RightHand':dict(mode='disabled')})
    values=solver_point_tolerances(contacts,request,12,.005)
    expected=np.full((12,3),.005);expected[2:5,1]=.001
    np.testing.assert_array_equal(values,expected)
    np.testing.assert_array_equal(solver_point_tolerances(contacts,None,12,.005),np.full((12,3),.005))
