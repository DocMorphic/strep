"""Explicit surface guidance never replaces the default complete population."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_affine_key_pose import affine_setup
from native_key_contact_initializer import KeyPose


def make(scene,policy,ids=None):
    return KeyPose(scene,'A',1.,[3],[30.],.22,policy['planes'],.005,.0005,
        pose_representation='native-trs-v1',plane_vertices=ids)


def test_explicit_complete_selection_is_identical_to_default(tmp_path):
    _,scene,_,policy,_=affine_setup(tmp_path);default=make(scene,policy)
    explicit=make(scene,policy,{n:default.used.tolist() for n in policy['planes']})
    value=np.array([.03,-.1,.06])
    for a,b in zip(default.evaluate(value),explicit.evaluate(value)):np.testing.assert_array_equal(a,b)


def test_guidance_subset_keeps_original_order_all_other_bounds_and_full_skin(tmp_path):
    _,scene,_,policy,_=affine_setup(tmp_path);full=make(scene,policy);name=next(iter(policy['planes']))
    assert len(policy['planes'])==1
    ids=full.used[[2,0]].tolist();selected=make(scene,policy,{name:ids});value=np.array([.03,-.1,.06])
    rows,jac,world,vertices=selected.evaluate(value);allrows,alljac,allworld,allvertices=full.evaluate(value)
    prefix=len(full.nodes)+len(full.rig.joints);count=len(full.used)
    np.testing.assert_array_equal(rows[:prefix],allrows[:prefix]);np.testing.assert_array_equal(rows[prefix+2:],allrows[prefix+count:])
    np.testing.assert_array_equal(rows[prefix:prefix+2],allrows[prefix+np.searchsorted(full.used,ids)])
    np.testing.assert_array_equal(jac[prefix:prefix+2],alljac[prefix+np.searchsorted(full.used,ids)])
    np.testing.assert_array_equal(world,allworld);np.testing.assert_array_equal(vertices,allvertices)
    assert len(vertices)==len(scene.actors['A']['skin'].nodes)
    differences=[]
    for d in np.eye(3)*1e-6:differences.append((selected.evaluate(value+d)[0]-selected.evaluate(value-d)[0])/2e-6)
    np.testing.assert_allclose(jac,np.array(differences).T,atol=2e-5,rtol=2e-7)


def test_caller_mutation_cannot_change_selected_guidance(tmp_path):
    _,scene,_,policy,_=affine_setup(tmp_path);full=make(scene,policy);name=next(iter(policy['planes']))
    ids={name:full.used[:2].tolist()};pose=make(scene,policy,ids);saved=pose.evaluate(np.zeros(3))[0].copy()
    ids[name][:]=full.used[-2:].tolist()
    np.testing.assert_array_equal(pose.evaluate(np.array([1e-3,0.,0.]))[0],make(scene,policy,{name:full.used[:2].tolist()}).evaluate(np.array([1e-3,0.,0.]))[0])
    np.testing.assert_array_equal(pose.evaluate(np.zeros(3))[0],saved)


@pytest.mark.parametrize('fault',['not-map','missing-plane','unknown-plane','empty','not-list','float','bool','negative','out-of-range','duplicate'])
def test_invalid_guidance_populations_reject(tmp_path,fault):
    _,scene,_,policy,_=affine_setup(tmp_path);full=make(scene,policy);name=next(iter(policy['planes']));ids={name:[int(full.used[0])]}
    if fault=='not-map':ids=[]
    elif fault=='missing-plane':ids={}
    elif fault=='unknown-plane':ids['unknown']=ids[name]
    elif fault=='empty':ids[name]=[]
    elif fault=='not-list':ids[name]=tuple(ids[name])
    elif fault=='float':ids[name]=[float(ids[name][0])]
    elif fault=='bool':ids[name]=[True]
    elif fault=='negative':ids[name]=[-1]
    elif fault=='out-of-range':ids[name]=[len(full.skin.nodes)]
    elif fault=='duplicate':ids[name]*=2
    with pytest.raises(ValueError):make(scene,policy,ids)
