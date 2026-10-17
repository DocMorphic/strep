"""All original scalar hashes, coupled derivatives, holds, anchors and budgets."""
from pathlib import Path
import sys,hashlib,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_scene_world_rows.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts'),str(root/'tests')]
from native_scene_world_derivatives import SceneWorldDerivatives
from native_scene_world_rows import SceneWorldRows
from native_scene_contacts import SceneContacts
from test_native_scene_world_rows import fixture


def prepare(tmp_path,space='world',centroid=False,coupled=True,short_hold=False):
    scene,edits,legacy,caps=fixture(tmp_path,True,space,centroid)
    if space=='actor' and coupled:caps['B']=.03
    if short_hold:scene.rows[0]['authored']['interval_s']=[1.,1.000001]
    caps={name:np.linspace(.02,.04,len(scene.actors[name]['rig'].joints)) for name in caps}
    oracle=SceneWorldRows(scene,caps);model=SceneWorldDerivatives(oracle,4,temperature=.03);base=oracle.source_worlds();lookup={float(t):i for i,t in enumerate(oracle.times)}
    def callbacks(point):
        result={}
        for actor_index,name in enumerate(caps):
            def sample(time,derivatives,name=name,actor_index=actor_index):
                original=base[name][lookup[time]];factor=(1+actor_index)*(.2+np.sin(time));angle=factor*point[3]
                rotation=Rotation.from_euler('z',angle).as_matrix();transform=np.eye(4);transform[:3,:3]=rotation;transform[:3,3]=factor*np.asarray(point[:3])
                world=transform@original;jac=None
                if derivatives:
                    jac=np.zeros(world.shape+(4,))
                    for axis in range(3):jac[:,axis,3,axis]=factor
                    hat=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,0.]])*factor
                    jac[:,:3,:,3]=np.einsum('ij,njk->nik',rotation@hat,original[:,:3,:])
                return world,jac
            result[name]=sample
        return result
    return scene,oracle,model,callbacks,base


@pytest.mark.parametrize('space',['world','object','actor'])
@pytest.mark.parametrize('centroid',[False,True])
def test_every_original_scalar_and_full_coupled_smooth_gradient_matches_independent_differences(tmp_path,space,centroid):
    scene,oracle,model,callbacks,base=prepare(tmp_path,space,centroid);point=np.array([.012,-.018,.027,.008]);result=model.evaluate(callbacks(point))
    worlds={name:np.stack([callbacks(point)[name](float(t),False)[0] for t in oracle.times]) if name in callbacks(point) else world for name,world in base.items()}
    original=oracle.violations(worlds);assert result['original_violations'].tobytes()==original.tobytes()
    assert result['composition']['rows']==len(original) and sum(g['rows'] for g in model.partition)==len(original)
    for group,report in zip(model.partition,result['report']['groups']):
        values=original[group['first']:group['last']]
        assert report['rows_seen']==report['rows']==len(values)
        assert report['values_sha256']==hashlib.sha256(values.astype('<f8').tobytes()).hexdigest()
        assert result['exact_margins'][int(group['id'][1:])]==-values.max()
    assert bool(np.all(result['exact_margins']>=0))==bool(np.all(original<=0))
    for column in range(4):
        delta=np.eye(4)[column]*2e-6;plus=model.values(callbacks(point+delta));minus=model.values(callbacks(point-delta))
        finite=(plus['smooth_margins']-minus['smooth_margins'])/4e-6
        np.testing.assert_allclose(result['smooth_jacobian'][:,column],finite,atol=5e-3,rtol=3e-4)
    assert result['composition']['peak_world_cache_bytes']<=model.report['maximum_world_cache_bytes']
    assert not result['composition']['quality_approved'] and not result['composition']['release_approved']
    assert not result['composition']['native_parameter_conditions_included'] and not result['composition']['surface_geometry_included']


def test_unedited_partner_remains_original_with_known_zero_derivatives(tmp_path):
    _,oracle,model,callbacks,base=prepare(tmp_path,'actor',coupled=False);point=np.array([.01,.02,-.01,.003])
    result=model.evaluate(callbacks(point));worlds={name:np.stack([callbacks(point)[name](float(t),False)[0] for t in oracle.times]) if name=='A' else world for name,world in base.items()}
    np.testing.assert_array_equal(result['original_violations'],oracle.violations(worlds))
    assert model.report['columns']==4 and np.any(result['smooth_jacobian'])


def test_snapshots_and_returned_metadata_do_not_change_original_source_caps_or_partition(tmp_path):
    _,oracle,model,callbacks,_=prepare(tmp_path);point=np.array([.01,.02,-.01,.003]);before=model.values(callbacks(point))
    oracle._problem.edits.actors['A']['displacement'][:]=9
    model.report['columns']=9;model.partition[0]['first']=999;model.times[:]=0
    with pytest.raises(AttributeError):model.columns=9
    np.testing.assert_array_equal(before['original_violations'],model.values(callbacks(point))['original_violations'])
    assert model.columns==4 and model.partition[0]['first']==0


@pytest.mark.parametrize('fault',['missing','extra','not_callable','not_pair','world_shape','world_nan','world_bool','world_bottom','value_jac','missing_jac','jac_shape','jac_bool','jac_nan','jac_bottom','changed_pose'])
def test_incomplete_or_changed_callback_rejected_without_partial_result(tmp_path,fault):
    _,_,model,make,_=prepare(tmp_path);callbacks=make(np.array([.01,.02,-.01,.003]));original=callbacks['A']
    if fault=='missing':callbacks={}
    elif fault=='extra':callbacks['B']=original
    elif fault=='not_callable':callbacks['A']=1
    else:
        def bad(time,derivatives):
            world,jac=original(time,derivatives)
            if fault=='not_pair':return world
            if fault=='world_shape':world=world[:-1]
            if fault=='world_nan':world[0,0,0]=np.nan
            if fault=='world_bool':world=world.astype(bool)
            if fault=='world_bottom':world[0,3,0]=.1
            if fault=='value_jac' and not derivatives:jac=np.zeros(world.shape+(4,))
            if derivatives:
                if fault=='missing_jac':jac=None
                if fault=='jac_shape':jac=jac[...,:3]
                if fault=='jac_bool':jac=jac.astype(bool)
                if fault=='jac_nan':jac[0,0,0,0]=np.nan
                if fault=='jac_bottom':jac[0,3,0,0]=.1
                if fault=='changed_pose':world[0,0,3]+=.001
            return world,jac
        callbacks['A']=bad
    with pytest.raises(ValueError):model.evaluate(callbacks)


@pytest.mark.parametrize('settings',[dict(columns=True),dict(columns=0),dict(columns=769),dict(maximum_jacobian_bytes=1),dict(maximum_world_cache_bytes=1),dict(maximum_contact_cache_bytes=1),dict(maximum_skin_bytes=1),dict(temperature=0)])
def test_complete_budget_admission_rejects_before_callbacks(tmp_path,settings):
    _,oracle,_,_,_=prepare(tmp_path);args=dict(columns=4);args.update(settings)
    with pytest.raises(ValueError):SceneWorldDerivatives(oracle,**args)


def test_source_file_change_rejected_before_any_callback(tmp_path):
    scene,_,model,callbacks,_=prepare(tmp_path);path=Path(next(iter(scene.inputs)));path.write_bytes(path.read_bytes()+b'x')
    called=[]
    def bad(*args):called.append(1);raise AssertionError('callback ran after source mutation')
    for operation in [model.values,model.evaluate]:
        with pytest.raises(ValueError):operation({'A':bad})
    assert not called


def test_short_hold_retains_every_unavailable_speed_population_as_fixed_failed_rows(tmp_path):
    _,_,model,callbacks,_=prepare(tmp_path,short_hold=True);point=np.array([.01,.02,-.01,.003]);result=model.evaluate(callbacks(point));count=0
    for data in model._p.rows:
        for population in data['populations']:
            if len(population['times_s'])>=2:continue
            groups=[g for g in model.partition if g['kind']=='contact_speed' and g['detail']==(population['rate_hz'],population['phase_offset_frames'])]
            assert len(groups)==1;group=groups[0];index=int(group['id'][1:]);count+=1
            np.testing.assert_array_equal(result['original_violations'][group['first']:group['last']],[1.])
            assert not np.any(result['smooth_jacobian'][index]) and result['exact_margins'][index]==-1
    assert count>0 and not result['report']['original_scalar_conditions_pass']


def test_minimum_complete_cache_evicts_without_changing_any_scalar_or_gradient(tmp_path):
    _,oracle,model,callbacks,base=prepare(tmp_path,'actor');budget=3*max(world[0].nbytes*5 for world in base.values())
    small=SceneWorldDerivatives(oracle,4,temperature=.03,maximum_world_cache_bytes=budget);point=np.array([.01,.02,-.01,.003])
    expected=model.evaluate(callbacks(point));actual=small.evaluate(callbacks(point))
    assert actual['original_violations'].tobytes()==expected['original_violations'].tobytes()
    np.testing.assert_allclose(actual['smooth_jacobian'],expected['smooth_jacobian'],atol=1e-11,rtol=1e-12)
    assert actual['composition']['peak_world_cache_bytes']<=budget


def test_value_only_never_requests_or_invents_derivatives(tmp_path):
    _,_,model,callbacks,_=prepare(tmp_path);original=callbacks(np.array([.01,.02,-.01,.003]));seen=[]
    def value(time,derivatives):
        seen.append(derivatives);assert not derivatives;return original['A'](time,derivatives)
    result=model.values({'A':value});assert seen and not any(seen) and result['smooth_jacobian'] is None
    assert result['report']['derivative_columns']==0 and result['report']['total_original_rows']==model.report['rows']


def test_source_mutated_after_value_pass_is_rejected_before_returning_derivatives(tmp_path):
    scene,_,model,callbacks,_=prepare(tmp_path);original=callbacks(np.array([.01,.02,-.01,.003]));path=Path(next(iter(scene.inputs)));changed=[]
    def mutation(time,derivatives):
        if derivatives and not changed:path.write_bytes(path.read_bytes()+b'x');changed.append(True)
        return original['A'](time,derivatives)
    with pytest.raises(ValueError):model.evaluate({'A':mutation})
    assert changed
