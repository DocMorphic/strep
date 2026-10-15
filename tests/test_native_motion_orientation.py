"""Analytic affine orientation, unchanged geometry and actual native exports."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
from scipy.linalg import polar
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_motion_orientation import extract
from sampled_motion_caps import features,measures
from test_native_vertical_root import recipe
from rig_asset import RigAsset
from gltf_tools import write_glb
from rig_floor_comparison import compare
from strep import read,save,sha256
import native_vertical_root as root


def affine_motion():
    times=np.arange(41)/20
    rotation=Rotation.from_euler('z',.7*times).as_matrix()
    # Changing symmetric positive stretch includes shear; dividing by a single
    # scalar cannot recover the known orientation.
    stretch=np.repeat(np.array([[1.7,.2,0],[.2,.8,.1],[0,.1,1.2]])[None],len(times),axis=0)
    stretch[:,0,0]+=.1*times
    world=np.repeat(np.eye(4)[None,None],len(times),axis=0)
    world[:,0,:3,:3]=rotation@stretch;world[:,0,:3,3]=np.c_[times,2*times,np.zeros(len(times))]
    return times,world,rotation,stretch


def test_known_changing_stretch_yields_true_orientation_without_mutating_transforms():
    times,world,rotation,stretch=affine_motion();before=world.copy()
    payload,receipt,arrays=extract(world,[0],'right-polar-v1')
    np.testing.assert_allclose(payload['rotations'][:,0],rotation,atol=2e-15,rtol=0)
    np.testing.assert_allclose(arrays['right_stretch'][:,0],stretch,atol=3e-15,rtol=0)
    assert np.array_equal(world,before) and np.array_equal(payload['positions'],features(world,[0])['positions'])
    rates=measures(payload,.05)
    np.testing.assert_allclose(rates[0],np.sqrt(5),atol=2e-14,rtol=0)
    np.testing.assert_allclose(rates[2],.7,atol=5e-14,rtol=0)
    assert rates[3].max()<2e-12 and not receipt['asset_transforms_modified']
    for i in range(len(world)):
        q,h=polar(world[i,0,:3,:3],side='right')
        np.testing.assert_allclose(q,payload['rotations'][i,0],atol=2e-15,rtol=0)
        np.testing.assert_allclose(h,arrays['right_stretch'][i,0],atol=3e-15,rtol=0)


def test_strict_default_measurement_still_rejects_the_same_affine_input():
    _,world,_,_=affine_motion();payload,receipt,arrays=extract(world,[0],'strict')
    assert arrays=={} and receipt['mode']=='strict'
    np.testing.assert_array_equal(payload['rotations'],world[:,[0],:3,:3])
    with pytest.raises(ValueError,match='Proper joint rotations'):
        measures(payload,.05)


@pytest.mark.parametrize('fault',['reflection','singular','ill-conditioned','nan','mode'])
def test_ambiguous_or_invalid_polar_measurement_is_rejected(fault):
    world=np.repeat(np.eye(4)[None,None],3,axis=0);mode='right-polar-v1'
    if fault=='reflection':world[:,0,0,0]=-1
    elif fault=='singular':world[:,0,0,0]=0
    elif fault=='ill-conditioned':world[:,0,0,0]=1e-10
    elif fault=='nan':world[:,0,0,0]=np.nan
    else:mode='automatic-waiver'
    with pytest.raises(ValueError):extract(world,[0],mode)


def test_explicit_polar_recipe_exports_without_repairing_the_stored_affine_rig(recipe,tmp_path):
    path,value,source,floor=recipe;rig=RigAsset.load(source)
    document=copy.deepcopy(rig.document);node=value['source']['root_node']
    document['nodes'][node]['scale']=[1.000002,.999998,1.]
    write_glb(source,document,rig.binary);value['source']['sha256']=sha256(source)
    prior=read(floor);save(floor,compare(source,source,prior['times_s'],floor_y_m=prior['floor_y_m'],tolerance_m=prior['tolerance_m']))
    value['floor_reference']['sha256']=sha256(floor);save(path,value);original=source.read_bytes()
    with pytest.raises(ValueError,match='Proper joint rotations'):
        root.run(path,tmp_path/'strict-rejection')
    value['orientation_mode']='right-polar-v1';save(path,value)
    result=root.run(path,tmp_path/'polar-proposal')
    diagnostics={key:result.get(key) for key in ('sampled_conditions_pass','solver_success','solver_status','solver_message',
        'rate_failures','floor_failed_samples','peak_floor_depth_m','minimum_vertical_joint_shift_m',
        'maximum_joint_displacement_m','maximum_horizontal_joint_drift_m','all_linear_transforms_preserved',
        'unaffected_joint_world_transforms_preserved','frozen_keys_and_other_tracks_preserved','dependencies')}
    print('Actual polar export observations:',diagnostics)
    assert result['sampled_conditions_pass'] and result['rate_failures']==[0,0,0,0],diagnostics
    assert result['floor_failed_samples']==0 and result['orientation_mode']=='right-polar-v1'
    assert result['all_linear_transforms_preserved'] and result['frozen_keys_and_other_tracks_preserved']
    assert result['original_selected'] and not result['quality_approved'] and source.read_bytes()==original
    decoded=RigAsset.load(tmp_path/'polar-proposal/character.glb')
    assert decoded.document['nodes']==document['nodes']
    ref=np.load(tmp_path/'polar-proposal/reference.npz');obs=np.load(tmp_path/'polar-proposal/decoded-observations.npz')
    assert np.array_equal(ref['right_stretch'],obs['right_stretch'])


def test_recipe_does_not_infer_or_accept_an_unknown_orientation_mode(recipe,tmp_path):
    path,value,source,floor=recipe;value['orientation_mode']='automatic-waiver';save(path,value)
    with pytest.raises(ValueError,match='orientation mode'):
        root.run(path,tmp_path/'invalid')
    assert not (tmp_path/'invalid').exists()
