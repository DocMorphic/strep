"""Previous-key preference never changes the current original pose bounds."""
from pathlib import Path
import sys,time
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_affine_key_pose import affine_setup
from native_key_contact_initializer import KeyPose


def pose(scene,planes=None,ids=None):
    return KeyPose(scene,'A',.5,[3],[30.],.22,{} if planes is None else planes,0.,0.,
        pose_representation='native-trs-v1',plane_vertices=ids)


def guide(scene,*,required=False):
    probe=pose(scene);reference=np.array([.18,-.12,.08]);zero=probe.evaluate(np.zeros(3))[3];other=probe.evaluate(reference)[3]
    used=probe.used;differences=other[used]-zero[used];j=int(np.linalg.norm(differences,axis=1).argmax());node=int(used[j])
    delta=differences[j];assert np.linalg.norm(delta)>.002
    normal=-delta/np.linalg.norm(delta);offset=float(zero[node]@normal)+(.001 if required else -.001)
    return pose(scene,{'guide':dict(normal_world=normal.tolist(),offset_m=offset)},{'guide':[node]}),reference


def test_feasible_previous_controls_are_retained_exactly_without_aliasing(tmp_path):
    _,scene,*_=affine_setup(tmp_path);problem=pose(scene);reference=np.array([.01,-.02,.03]);saved=reference.copy()
    value,record=problem.solve(40,time.monotonic()+30,reference_controls=reference)
    assert record['pose_conditions_pass'] and not record['solved'] and record['reference_conditioned']
    np.testing.assert_array_equal(value,saved);reference[:]=0.;np.testing.assert_array_equal(value,saved)
    assert record['reference_controls']==saved.tolist() and problem.displacement==.22


def test_infeasible_previous_controls_are_projected_under_current_source_bounds(tmp_path):
    _,scene,*_=affine_setup(tmp_path);problem,reference=guide(scene)
    assert problem.evaluate(reference)[0].min()<0 and problem.evaluate(np.zeros(3))[0].min()>=0
    value,record=problem.solve(60,time.monotonic()+30,reference_controls=reference)
    assert record['pose_conditions_pass'] and np.all(problem.evaluate(value)[0]>=-1e-7)
    assert np.linalg.norm(value-reference)<np.linalg.norm(reference) and np.linalg.norm(value)>0
    assert record['reference_controls']==reference.tolist() and problem.displacement==.22


@pytest.mark.parametrize('required',[False,True])
def test_explicit_zero_reference_matches_existing_default_controls_and_observations(tmp_path,required):
    _,scene,*_=affine_setup(tmp_path);default,_=guide(scene,required=required);explicit,_=guide(scene,required=required)
    a,ar=default.solve(60,time.monotonic()+30);b,br=explicit.solve(60,time.monotonic()+30,reference_controls=np.zeros(3))
    np.testing.assert_array_equal(a,b)
    assert ar=={k:v for k,v in br.items() if k not in ('reference_conditioned','reference_controls')}
    assert ar['pose_conditions_pass'] and ar['solved'] is required
    for left,right in zip(default.evaluate(a),explicit.evaluate(b)):np.testing.assert_array_equal(left,right)


@pytest.mark.parametrize('fault',['shape','nan','infinite','outside','boolean','text','complex'])
def test_invalid_reference_cannot_be_clipped_or_normalized_into_a_proposal(tmp_path,fault):
    _,scene,*_=affine_setup(tmp_path);problem=pose(scene);reference=np.zeros(3)
    if fault=='shape':reference=reference[:2]
    elif fault=='nan':reference[0]=np.nan
    elif fault=='infinite':reference[0]=np.inf
    elif fault=='outside':reference[0]=1.00001
    elif fault=='boolean':reference=np.zeros(3,dtype=bool)
    elif fault=='text':reference=['0','0','0']
    elif fault=='complex':reference=np.zeros(3,dtype=complex)
    with pytest.raises(ValueError):problem.solve(40,time.monotonic()+30,reference_controls=reference)


def test_failed_reference_proposal_retains_original_instead_of_previous_key(tmp_path):
    _,scene,*_=affine_setup(tmp_path);probe=pose(scene);node=int(probe.used[0]);vertex=probe.evaluate(np.zeros(3))[3][node]
    # Both unit planes address the same real vertex, with contradictory bounds.
    # This fixture has no surface vertex completely independent of edited node3.
    problem=pose(scene,dict(lower=dict(normal_world=[1.,0.,0.],offset_m=float(vertex[0])+1.),
        upper=dict(normal_world=[-1.,0.,0.],offset_m=-float(vertex[0])-.5)),dict(lower=[node],upper=[node]))
    reference=np.array([.01,.02,-.03]);value,record=problem.solve(8,time.monotonic()+30,reference_controls=reference)
    assert not record['pose_conditions_pass'] and record['failed_pose_retains_original']
    np.testing.assert_array_equal(value,np.zeros(3));assert record['reference_controls']==reference.tolist()
