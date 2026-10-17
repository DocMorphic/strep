"""Source-bound native limits independent of any surface separation heuristic."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_affine_pose_bounds import PoseBoundsRows
from test_native_affine_region_pose import inputs


@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('homogeneous',[False,True])
def test_complete_pose_limits_and_native_derivatives_without_surface_rows(tmp_path,reverse,homogeneous):
    model,base,active,caps,_=inputs(tmp_path)
    if reverse:active.reverse()
    if homogeneous:model.skin.points[:,:,3]*=np.linspace(.95,1.05,model.skin.points.shape[1])
    p=PoseBoundsRows(model,1.,base,active,caps);value=base[p.coordinates]+np.linspace(-.01,.02,p.size)
    rows,jac,world,points,full=p.evaluate(value)
    reference=base.copy();reference[p.coordinates]=value
    expected_world,local,*_=model.evaluate(reference);pos,rot=model.actor['placement']
    np.testing.assert_array_equal(world,expected_world);np.testing.assert_array_equal(points,local@rot.T+pos)
    delta=world[model.rig.joints,:3,3]-model.source[model.rig.joints,:3,3]
    np.testing.assert_allclose(rows,np.r_[1-np.linalg.norm(full.reshape(-1,3),axis=1)**2,1-(np.linalg.norm(delta,axis=1)/caps)**2],atol=1e-12,rtol=0)
    for column in range(p.size):
        step=np.eye(p.size)[column]*1e-6
        fd=(p.evaluate(value+step)[0]-p.evaluate(value-step)[0])/2e-6
        np.testing.assert_allclose(jac[:,column],fd,atol=3e-7,rtol=3e-6)
    assert len(rows)==p.hard_rows==len(model.nodes)+len(model.rig.joints)
    assert jac.shape==(len(rows),p.size) and p.report['jacobian_bytes']==jac.nbytes
    assert 'regions' not in vars(p) and 'scale' not in vars(p)
    assert not p.report['quality_approved'] and not p.report['release_approved']


def test_exact_complete_budget_and_original_reference_are_retained(tmp_path):
    model,base,active,caps,_=inputs(tmp_path);count=len(model.nodes)+len(model.rig.joints);required=count*len(active)*3*8
    p=PoseBoundsRows(model,1.,base,active,caps,maximum_rows=count,maximum_jacobian_bytes=required)
    value=base[p.coordinates].copy();original=p.evaluate(value)
    base[:]=0;caps[:]=1;active.reverse();p.evaluate(value+.03)
    for a,b in zip(original,p.evaluate(value)):np.testing.assert_array_equal(a,b)
    original[-1][:]=0
    assert np.any(p.evaluate(value)[-1])
    assert np.array_equal(p.source,model.source)
    assert all(not v.flags.writeable for v in [p.base,p.caps,p.source,p.local,p.coordinates,*p.placement])
    with pytest.raises(ValueError,match='budget'):PoseBoundsRows(model,1.,p.base,list(reversed(active)),p.caps,maximum_rows=count-1)
    with pytest.raises(ValueError,match='budget'):PoseBoundsRows(model,1.,p.base,list(reversed(active)),p.caps,maximum_jacobian_bytes=required-1)


def test_failed_rotation_ball_remains_a_row_instead_of_clipping_the_proposal(tmp_path):
    model,base,active,caps,_=inputs(tmp_path);p=PoseBoundsRows(model,1.,base,active,caps)
    value=base[p.coordinates].copy();value[:3]=[1.01,0,0];rows,jac,*_=p.evaluate(value)
    assert rows[p.node_indices[0]]<0 and jac[p.node_indices[0],0]==pytest.approx(-2.02)
    fixed=sorted(set(range(len(model.nodes)))-set(p.node_indices))
    assert np.count_nonzero(jac[fixed])==0


@pytest.mark.parametrize('field',['source','local','caps','nodes','placement','derivative_budget'])
def test_mutated_source_bindings_reject_without_recentering(tmp_path,field):
    model,base,active,caps,_=inputs(tmp_path);p=PoseBoundsRows(model,1.,base,active,caps)
    if field=='source':model.source[0,0,3]+=.01
    elif field=='local':model.local[0,0,3]+=.01
    elif field=='caps':model.caps[0]*=.9
    elif field=='nodes':model.nodes.reverse()
    elif field=='placement':model.actor['placement'][0][0]+=.01
    else:model.maximum_derivative_controls-=1
    with pytest.raises(ValueError,match='reference changed'):p.evaluate(base[p.coordinates])


@pytest.mark.parametrize('fault',['time','no_active','duplicate','base_shape','outside','cap_zero','nan','row_bool','jac_small'])
def test_incomplete_or_invalid_bounds_reject_before_pose_evaluation(tmp_path,monkeypatch,fault):
    model,base,active,caps,_=inputs(tmp_path);stamp=1.;settings={}
    if fault=='time':stamp=True
    elif fault=='no_active':active=[]
    elif fault=='duplicate':active=[active[0]]*2
    elif fault=='base_shape':base=base[:-1]
    elif fault=='outside':base[:3]=[1.01,0,0]
    elif fault=='cap_zero':caps[0]=0
    elif fault=='nan':caps[0]=np.nan
    elif fault=='row_bool':settings['maximum_rows']=True
    else:settings['maximum_jacobian_bytes']=1
    def forbidden(*args):raise AssertionError('Invalid condition evaluated')
    monkeypatch.setattr(model,'evaluate_columns',forbidden)
    with pytest.raises(ValueError):PoseBoundsRows(model,stamp,base,active,caps,**settings)
