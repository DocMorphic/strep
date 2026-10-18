"""Sufficient certificates must survive independent exact source checks."""
from pathlib import Path
import sys,copy
from fractions import Fraction as Q
import numpy as np
import pytest
import trimesh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import fixed_grip_box_obstruction as module
from fixed_grip_box_obstruction import certificate,verify,discover,box_model
from native_mesh_prop_obstruction_preflight import preflight
from test_native_mesh_prop_pose import setup
from strep import read,save,sha256


def fixture():
    box=trimesh.creation.box(extents=[2.,2.,2.]);world=np.array([[.1,.1,.1],[.1,-.1,-.1],[-.1,.1,-.1],[-.1,-.1,.1],[5.,0.,0.]])
    faces=np.array([[0,1,2],[0,3,1],[0,2,3],[1,3,2],[0,1,4]])
    args=(box.vertices.copy(),box.faces.copy(),[-1.,0.,0.],[0.,0.,0.],.001,{'A':(world,faces)})
    return args,[['A',i] for i in range(4)]


def test_exact_proof_and_direct_verifier_do_not_call_discovery(monkeypatch):
    args,refs=fixture();proof=certificate(*args,refs)
    monkeypatch.setattr(module,'Delaunay',lambda *a:pytest.fail('Discovery must not run during verification'))
    result=verify(*args,proof)
    assert result['fixed_geometry_rigid_grip_obstruction_proved'] and result['contained_ball_radius_lower_m']>args[4]
    assert sum(map(Q,proof['barycentric_rational']))==1 and all(path[0]==i and path[-1]==4 for i,path in enumerate(proof['connected_paths']))
    assert not result['character_edits_covered'] and not result['earlier_rounding_certified'] and not result['release_approved']


@pytest.mark.parametrize('axis,side',[(0,-1),(0,1),(1,-1),(1,1),(2,-1),(2,1)])
def test_all_six_face_grips_admit_same_proof(axis,side):
    args,refs=fixture();args=list(args);args[2]=[0.,0.,0.];args[2][axis]=float(side)
    assert verify(*args,certificate(*args,refs))['fixed_geometry_rigid_grip_obstruction_proved']


@pytest.mark.parametrize('fault',['weight','zero-weight','ball','reference','boolean-reference','duplicate-reference','path-edge','path-end','boolean-path','missing-path','extra','schema'])
def test_tampered_certificate_rejects(fault):
    args,refs=fixture();proof=certificate(*args,refs)
    if fault=='weight':proof['barycentric_rational'][0]='1/3'
    elif fault=='zero-weight':proof['barycentric_rational'][0]='0'
    elif fault=='ball':proof['contained_ball_radius_lower_rational']='1'
    elif fault=='reference':proof['references'][0][0]='B'
    elif fault=='boolean-reference':proof['references'][0][1]=False
    elif fault=='duplicate-reference':proof['references'][1]=proof['references'][0]
    elif fault=='path-edge':proof['connected_paths'][2]=[2,4]
    elif fault=='path-end':proof['connected_paths'][0]=[0,1]
    elif fault=='boolean-path':proof['connected_paths'][0]=[False,4]
    elif fault=='missing-path':proof['connected_paths'].pop()
    elif fault=='extra':proof['quality_approved']=True
    else:proof['schema']='arbitrary'
    with pytest.raises(ValueError):verify(*args,proof)


@pytest.mark.parametrize('fault',['duplicate-face','inward-face','corner','edge-grip','outside-grip','tolerance','nan','boolean'])
def test_invalid_box_or_grip_never_certifies(fault):
    args,refs=fixture();args=list(args)
    if fault=='duplicate-face':args[1][0]=args[1][1]
    elif fault=='inward-face':args[1][0]=args[1][0][::-1]
    elif fault=='corner':args[0][0,0]+=.01
    elif fault=='edge-grip':args[2]=[-1.,1.,0.]
    elif fault=='outside-grip':args[2]=[-1.,2.,0.]
    elif fault=='tolerance':args[4]=True
    elif fault=='nan':args[0][0,0]=np.nan
    else:args[2]=[False,0.,0.]
    with pytest.raises(ValueError):certificate(*args,refs)


def test_changed_world_geometry_or_original_connectivity_invalidates_proof():
    args,refs=fixture();proof=certificate(*args,refs);args=list(args);args[5]['A'][0][0,0]+=.01
    with pytest.raises(ValueError):verify(*args,proof)
    args,refs=fixture();proof=certificate(*args,refs);args=list(args);args[5]['A']=(args[5]['A'][0],args[5]['A'][1][:-1])
    with pytest.raises(ValueError):verify(*args,proof)


def test_discovery_proposes_then_exactly_verifies_and_retains_unknown():
    args,_=fixture();result=discover(*args)
    assert result['status']=='proved_fixed_geometry_obstruction' and verify(*args,result['proof'])['fixed_geometry_rigid_grip_obstruction_proved']
    moved=list(args);moved[3]=[20.,0.,0.];unknown=discover(*moved)
    assert unknown['status']=='unknown' and unknown['proof'] is None
    budget=discover(*args,maximum_candidates=3)
    assert budget['status']=='unknown' and budget['reason']=='candidate_budget_exceeded_without_truncation'


def test_no_outside_connected_surface_cannot_certify():
    args,refs=fixture();args=list(args);args[5]['A']=(args[5]['A'][0][:-1],args[5]['A'][1][:-1])
    with pytest.raises(ValueError,match='outside every box'):certificate(*args,refs)
    assert discover(*args)['status']=='unknown'


def test_exact_contact_vertex_does_not_poison_discovery_tetrahedra():
    args,_=fixture();args=list(args);world,faces=args[5]['A'];args[5]['A']=(np.vstack([world,[0.,0.,0.]]),np.vstack([faces,[0,1,5]]))
    result=discover(*args)
    assert result['status']=='proved_fixed_geometry_obstruction' and result['candidates']==4
    assert all(i!=5 for name,i in result['proof']['references'])


@pytest.mark.parametrize('budget',[0,True,10001])
def test_invalid_discovery_budget_rejects(budget):
    args,_=fixture()
    with pytest.raises(ValueError):discover(*args,maximum_candidates=budget)


def test_source_bound_preflight_preserves_all_inputs_and_unknown_means_unknown(tmp_path):
    pp,_,_,_,_=setup(tmp_path);before={str(p):sha256(p) for p in tmp_path.iterdir() if p.is_file()};out=tmp_path/'preflight'
    result=preflight(pp,out)
    assert result['job_status']=='complete' and result['status']=='unknown' and result['proof'] is None
    assert not result['body_edit_domain_blocked'] and not result['quality_approved'] and not result['release_approved']
    assert all(sha256(p)==h for p,h in before.items()) and read(out/'input.json')['assumption']=='fixed-character-world-geometry-at-contact'
    with pytest.raises(ValueError,match='Fresh'):preflight(pp,out)


def test_source_hash_mutation_rejects_before_output(tmp_path):
    pp,_,path,_,_=setup(tmp_path);value=read(path);value['props']['crate']['keyframes'][1]['translation_m'][0]+=.01;save(path,value)
    with pytest.raises(ValueError):preflight(pp,tmp_path/'no')
    assert not (tmp_path/'no').exists()


def test_edited_key_outside_authored_contact_cannot_certify(tmp_path):
    pp,_,path,value,permissions=setup(tmp_path);value['mesh_contacts'][0]['interval_s']=[.5,.5];save(path,value);permissions['mesh_scene_sha256']=sha256(path);save(pp,permissions)
    result=preflight(pp,tmp_path/'preflight')
    assert result['status']=='unknown' and result['reason']=='edited_key_outside_required_contact_interval'
