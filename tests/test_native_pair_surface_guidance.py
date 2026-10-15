"""Local triangle/material witnesses couple both native actors without plane proxies."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_key_guides import inputs,make_inputs
from test_native_partner_surface_rows import scene_fixture
from native_scene_geometry import policy_for
from native_partner_surface_rows import SurfaceRows,build
from native_pair_key_guides import PairKeyGuides


def explicit_row(models,guides):
    vertex=guides[0]['vertices']['A'][0]
    return dict(kind='triangle-separation',time_s=guides[0]['time_s'],normal_world=[1.,0.,0.],constant_m=0.,clearance_m=.0005,
        left=dict(actor='A',vertices=[vertex],weights=[1.]),right=dict(actor='B',vertices=[vertex],weights=[1.]))


def surface(models,row):return SurfaceRows(models['A'].scene,[row],dict(rows=1,quality_approved=False))


def test_local_material_gap_tracks_both_edited_characters_and_copies_witnesses(inputs):
    models,guides=inputs;original=explicit_row(models,guides);source=surface(models,original)
    p=PairKeyGuides(models,[],surface_rows=source);value=p.initial.copy();value[:]=np.tile([.01,-.02,.015],4)
    worlds=p.worlds(value);np.testing.assert_allclose(p.guide_gaps(value,worlds),[-.0005],atol=1e-14,rtol=0)
    one=dict(worlds);one['B']=models['B'].source_world
    assert abs(p.guide_gaps(value,one)[0]+.0005)>1e-6
    source.rows[0]['clearance_m']=.004
    np.testing.assert_allclose(p.guide_gaps(value,worlds),[-.0005],atol=1e-14,rtol=0)
    assert p.size==sum(p.sizes) and not p.guides


def test_surface_only_linearization_retains_all_original_native_and_floor_conditions(inputs):
    models,guides=inputs;p=PairKeyGuides(models,[],surface_rows=surface(models,explicit_row(models,guides)))
    rows,jac,info=p.linearize(p.initial,p.source_worlds,.02)
    native,contact=p.norms(p.initial,p.source_worlds)
    assert info['local_surface_rows']==info['guide_rows']==1
    assert info['hard_rows']==len(native.caps)+len(contact.caps)+info['floor_rows']
    np.testing.assert_array_equal(rows.caps[:len(native.caps)],native.caps)
    assert np.all(rows.residual()[:info['hard_rows']]<=0)
    # The final local halfspace responds to both native actor control blocks.
    assert jac[-3:,:p.sizes[0]].nnz and jac[-3:,p.sizes[0]:].nnz


def test_contact_free_scene_keeps_zero_contact_rows_without_invented_passing_evidence(tmp_path):
    models,guides=make_inputs(tmp_path,contacts_enabled=False)
    p=PairKeyGuides(models,[],surface_rows=surface(models,explicit_row(models,guides)))
    native,contact=p.norms(p.initial,p.source_worlds);assert contact is None and len(p.contact_caps)==0
    rows,jac,info=p.linearize(p.initial,p.source_worlds,.02)
    assert info['contact_rows']==0 and info['hard_rows']==len(native.caps)+info['floor_rows']
    assert np.all(rows.residual()[:info['hard_rows']]<=0)


@pytest.mark.parametrize('fault',['normal','weights','negative','boolean','vertex','actor','time','constant','kind','foreign-scene'])
def test_invalid_or_foreign_local_surface_rows_reject(inputs,fault):
    models,guides=inputs;row=explicit_row(models,guides);s=surface(models,row)
    if fault=='normal':row['normal_world']=[0.,0.,0.]
    elif fault=='weights':row['left']['weights']=[.8]
    elif fault=='negative':row['left']['weights']=[-1.]
    elif fault=='boolean':row['right']['weights']=[True]
    elif fault=='vertex':row['left']['vertices']=[-1]
    elif fault=='actor':row['right']['actor']='missing'
    elif fault=='time':row['time_s']=-1.
    elif fault=='constant':row['constant_m']=True
    elif fault=='kind':row['kind']='automatic'
    else:s.scene=models['B'].scene
    with pytest.raises(ValueError):PairKeyGuides(models,[],surface_rows=s)


def test_selected_proposal_clock_keeps_complete_pair_topology_and_marks_partial_time_scope(tmp_path):
    scene,policy,digest=scene_fixture(tmp_path)
    full=build(scene,policy,digest,include_world_planes=False)
    partial=build(scene,policy,digest,sample_indices=[0],include_world_planes=False)
    assert not partial.report['complete_declared_time_population'] and partial.report['sample_indices']==[0]
    assert partial.report['complete_triangle_populations']==full.report['complete_triangle_populations']==dict(A=12,B=12)
    assert partial.rows==[r for r in full.rows if r['time_s']==0.]
    assert partial.report['samples']==full.report['samples'][:1]
    assert not partial.report['world_planes_included'] and partial.report['world_plane_guidance_rows']==0


def test_provided_posed_vertices_create_new_anchor_witnesses_without_changing_source_scene(tmp_path):
    scene,policy,digest=scene_fixture(tmp_path);before={n:a['placement'][0].copy() for n,a in scene.actors.items()}
    def posed(name,time):
        a=scene.actors[name];p,r=a['placement'];points=a['rig'].vertices(a['sampler'].sample(time))@r.T+p
        return points+np.array([10.,0,0]) if name=='B' else points
    partial=build(scene,policy,digest,sample_indices=[0],actor_vertices=posed,include_world_planes=False)
    assert partial.report['provided_actor_vertices'] and not partial.rows
    for n in scene.actors:np.testing.assert_array_equal(scene.actors[n]['placement'][0],before[n])
    with pytest.raises(ValueError,match='population'):build(scene,policy,digest,sample_indices=[0],actor_vertices=lambda *x:np.zeros((1,3)))


@pytest.mark.parametrize('indices',[[],[False,1],(0,True),[1,0],[0,0],[-1],[999999],[.5],[[0]]])
def test_invalid_proposal_sample_indices_cannot_select_an_easier_clock(tmp_path,indices):
    scene,policy,digest=scene_fixture(tmp_path)
    with pytest.raises(ValueError):build(scene,policy,digest,sample_indices=indices)


@pytest.mark.parametrize('selection',[None,'last'])
def test_reported_clock_indices_do_not_alias_canonical_vertex_indices(tmp_path,selection):
    scene,policy,digest=scene_fixture(tmp_path);clock=policy_for(policy,scene,digest)[0]
    indices=None if selection is None else [len(clock)-1]
    result=build(scene,policy,digest,sample_indices=indices,include_world_planes=False)
    expected=list(range(len(clock))) if indices is None else indices
    assert result.report['sample_indices']==expected
    assert result.report['complete_declared_time_population']==(len(expected)==len(clock))
    assert [s['time_s'] for s in result.report['samples']]==clock[expected].tolist()
