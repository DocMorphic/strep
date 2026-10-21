"""Source-bound surface guidance, independent vertex derivatives and full fits."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read,save,sha256
from native_mesh_character_fit import MeshCharacterProblem,fit
from native_mesh_character_surface import collect,add_guards
from native_scene_geometry import faces_for
from native_scene_norms import NormRows
from test_native_mesh_character_fit import prepared


def rotation_source(tmp_path,path,permission,policy):
    from rig_asset import RigAsset
    from gltf_tools import append_accessor,write_glb
    spec=read(path);actor_path=tmp_path/spec['actor_scene'];actors=read(actor_path)
    actor_file=tmp_path/actors['actors']['A']['glb'];rig=RigAsset.load(actor_file)
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=document['animations'][0]
    clock=animation['samplers'][0]['input'];count=document['accessors'][clock]['count']
    values=np.tile(document['nodes'][0].get('rotation',[0.,0.,0.,1.]),(count,1))
    animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=0,path='rotation')))
    animation['samplers'].append(dict(input=clock,output=append_accessor(document,binary,values,'VEC4'),interpolation='LINEAR'))
    write_glb(actor_file,document,binary);actors['actors']['A']['sha256']=sha256(actor_file);save(actor_path,actors)
    spec['actor_scene_sha256']=sha256(actor_path);save(path,spec)
    for target in (permission,policy):
        data=read(target);data['mesh_scene_sha256']=sha256(path);save(target,data)
    data=read(permission);data['actors']['A']['tracks'].append(dict(node=0,path='rotation',maximum_change=3.));save(permission,data)


def overlap(tmp_path):
    path,permission,policy=prepared(tmp_path)
    spec=read(path);actors_path=tmp_path/spec['actor_scene'];actors=read(actors_path)
    actors['actors']['A']['placement']=dict(translation_m=[.4,0.,-.2],rotation_xyzw=Rotation.from_euler('y',.3).as_quat().tolist())
    save(actors_path,actors);spec['actor_scene_sha256']=sha256(actors_path)
    from native_scene_contacts import SceneContacts
    actor=SceneContacts(actors,tmp_path).actors['A'];position,rotation=actor['placement']
    center=actor['rig'].vertices(actor['sampler'].sample(1.)).mean(axis=0)@rotation.T+position
    spec['props']['crate']['keyframes']=[dict(time_s=t,translation_m=(center+[.18+.01*t,0.,0.]).tolist(),rotation_xyzw=Rotation.from_euler('z',.2*t).as_quat().tolist()) for t in [0.,2.]]
    save(path,spec)
    for p in (permission,policy):
        data=read(p);data['mesh_scene_sha256']=sha256(path);save(p,data)
    problem=MeshCharacterProblem(permission);policy=read(policy);report,_=problem.mesh.geometry(policy)
    return problem,policy,report


def empty(problem):return NormRows(np.zeros((1,3)),np.ones(1),np.ones(1)),sparse.csc_matrix((3,problem.size))


def test_collection_retains_all_source_pair_times_and_rejects_wrong_epoch(tmp_path):
    problem,policy,report=overlap(tmp_path);bank={}
    stats=collect(problem.mesh,policy,report,bank)
    expected={(s['time_s'],p['left'][1],p['right'][1],r['left_triangle'],r['right_triangle'])
        for s in report['samples'] for p in s['mesh_pairs'] for r in p['surface']['records']}
    assert expected and set(bank)==expected and stats['new_triangle_time_pairs']==len(expected)
    assert collect(problem.mesh,policy,report,bank)['new_triangle_time_pairs']==0
    before=copy.deepcopy(bank);bad=copy.deepcopy(report);bad['inputs_sha256']={}
    with pytest.raises(ValueError,match='bound geometry'):collect(problem.mesh,policy,bad,bank)
    assert bank==before
    bad=copy.deepcopy(report);bad['samples']=bad['samples'][:-1]
    with pytest.raises(ValueError,match='bound geometry'):collect(problem.mesh,policy,bad,bank)
    assert bank==before


@pytest.mark.parametrize('boundary',[False,True])
def test_all_vertex_comparisons_match_independent_placed_skin_derivatives(tmp_path,boundary):
    problem,policy,report=overlap(tmp_path);bank={};collect(problem.mesh,policy,report,bank)
    value=problem.initial.copy() if not boundary else problem.lower.copy()
    worlds=problem.worlds(value);system,jac=empty(problem)
    result,matrix,hard,info=add_guards(problem,value,worlds,bank,system,jac,1,.02)
    assert info['rows']==9*len(bank) and hard==1+9*len(bank)
    assert np.all(result.residual()[1:]<=1e-12)
    faces=faces_for(problem.scene.actors['A']['rig'])[0]
    def independent(controls,quantized):
        matrices=problem.worlds(controls,quantized=quantized);out=[]
        for record,normal in zip(info['records'],info['directions']):
            actor=problem.scene.actors[record['actor']];p,r=actor['placement'];index=int(np.searchsorted(problem.times,record['time_s']))
            vertices=actor['rig'].vertices(matrices[record['actor']][index])@r.T+p
            a=vertices[faces[record['actor_triangle']]]
            prop=problem.mesh._props[record['prop']];p,r=problem.mesh.prop_poses(record['prop'],np.array([record['time_s']]))
            b=prop['asset'].vertices_m[prop['asset'].faces[record['prop_triangle']]]@r[0].T+p[0]
            out.extend([np.dot(y-x,normal) for x in a for y in b])
        return np.array(out)
    anchored=independent(value,True);caps=np.repeat(info['projected_gap_floors_m'],9)
    np.testing.assert_allclose(result.residual()[1:],-(anchored-caps)/.005,atol=1e-10)
    base=independent(value,False)
    for column,offsets in enumerate(info['stencil_offsets']):
        plus=value.copy();plus[column]+=offsets[0]
        if len(offsets)==2:
            minus=value.copy();minus[column]+=offsets[1]
            expected=(independent(plus,False)-independent(minus,False))/(offsets[0]-offsets[1])
        else:expected=(independent(plus,False)-base)/offsets[0]
        actual=matrix[3::3,column].toarray().ravel()
        np.testing.assert_allclose(actual,-expected,atol=1e-10,rtol=1e-7)
    assert info['all_nine_vertex_comparisons_retained']


def test_empty_guidance_preserves_system_and_full_budget_rejects_before_allocation(tmp_path):
    _,permission,_=prepared(tmp_path);problem=MeshCharacterProblem(permission);system,jac=empty(problem)
    result,matrix,hard,info=add_guards(problem,problem.initial,problem.source_world,{},system,jac,1,.02)
    assert result is system and matrix is jac and hard==1 and info['rows']==0
    with pytest.raises(ValueError,match='no records or columns dropped'):
        add_guards(problem,problem.initial,problem.source_world,{i:{} for i in range(55556)},system,jac,1,.02)


def test_new_floor_vertices_survive_rejection_without_changing_depth_caps(tmp_path):
    from native_mesh_floor_guard import add_floor_guards
    path,permission,policy_path=prepared(tmp_path);rotation_source(tmp_path,path,permission,policy_path)
    problem=MeshCharacterProblem(permission);policy=read(policy_path);original,_=problem.mesh.geometry(policy)
    value=problem.initial.copy();value[9:]=np.tile([.25,0.,0.],3)
    candidate,_,_,_=problem.write(value,tmp_path/'tilted')
    rejected,_=candidate.geometry(dict(policy,mesh_scene_sha256=candidate._manifest_sha256))
    bank={};floors={};collect(problem.mesh,policy,original,bank,floor_bank=floors)
    source_floor_count=len(floors);stats=collect(candidate,policy,rejected,bank,floor_bank=floors)
    assert stats['new_floor_vertex_time_pairs']>0 and len(floors)>source_floor_count
    system,jac=empty(problem)
    _,_,_,before=add_floor_guards(problem,problem.initial,problem.source_world,policy,original,system,jac,1,.02)
    result,_,hard,after=add_floor_guards(problem,problem.initial,problem.source_world,policy,original,system,jac,1,.02,additional_witnesses=list(floors.values()))
    assert after['rows']>before['rows'] and hard==1+after['rows']
    assert after['measured_depth_caps']==before['measured_depth_caps'] and np.all(result.residual()[1:]<=1e-12)
    bad=copy.deepcopy(next(iter(floors.values())));bad['time_s']=.12345
    with pytest.raises(ValueError,match='original actor/plane/time'):
        add_floor_guards(problem,problem.initial,problem.source_world,policy,original,system,jac,1,.02,additional_witnesses=[bad])


@pytest.mark.parametrize('blocked',[False,True])
@pytest.mark.parametrize('compact',[False,True])
def test_opt_in_fit_retains_baseline_and_all_decoded_acceptance_rules(tmp_path,blocked,compact):
    path,permission,policy=prepared(tmp_path)
    if blocked:
        spec=read(path);problem=MeshCharacterProblem(permission)
        point=problem.scene.actor_points('A',np.array([2]),np.array([1.]))[0,0]
        obstacle=copy.deepcopy(spec['props']['crate'])
        obstacle['keyframes']=[dict(time_s=0.,translation_m=(point+[-.105,-.2,.2]).tolist(),rotation_xyzw=[0,0,0,1])]
        spec['props']['obstacle']=obstacle;save(path,spec)
        for p in (permission,policy):
            value=read(p);value['mesh_scene_sha256']=sha256(path);save(p,value)
    sources={p:sha256(p) for p in MeshCharacterProblem(permission).inputs}
    baseline=fit(permission,policy,tmp_path/'baseline',iterations=4,trust=.25,backtracks=4)
    guided=fit(permission,policy,tmp_path/'guided',iterations=4,trust=.25,backtracks=4,surface_guidance=True,linear_axis_rows=compact)
    assert read(tmp_path/'guided/input.json')['linear_axis_rows']==compact
    assert guided['surface_guidance'] and guided['original_selected'] and not guided['props_changed']
    assert not guided['quality_approved'] and not guided['release_approved']
    assert all(sha256(p)==h for p,h in sources.items())
    if not blocked:
        assert baseline['sampled_candidate_pass'] and guided['sampled_candidate_pass']
        assert sha256(tmp_path/'baseline'/baseline['candidate']/'A.glb')==sha256(tmp_path/'guided'/guided['candidate']/'A.glb')
    else:
        assert not baseline['sampled_candidate_pass'] and not guided['sampled_candidate_pass']
        history=read(tmp_path/'guided/history.json');assert any(h['surface_protection']['pairs']>0 for h in history)
        assert any('axis_linear_representation' in h['solver'] for h in history)==compact
        assert any(p['surface_guidance_observation']['new_triangle_time_pairs']>0 for p in read(tmp_path/'guided/probes.json') if p['geometry_evaluated'])
    for row in read(tmp_path/'guided/probes.json'):
        if row['accepted']:
            assert all(row[k] for k in ['source_rows_pass','strict_edit_caps_pass','contact_rows_no_worse','contact_merit_improves','geometry_conditions_no_regression','geometry_metrics_no_worse'])


@pytest.mark.parametrize('value',[None,1,'true'])
def test_guidance_requires_explicit_boolean_before_source_load(tmp_path,value):
    with pytest.raises(ValueError,match='surface guidance choice'):
        fit(tmp_path/'missing',tmp_path/'missing-policy',tmp_path/'missing-output',surface_guidance=value)
