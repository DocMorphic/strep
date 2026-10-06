"""Nonlinear nine-pair equivalence, changing extrema, complete mixed queries."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_compact_surface_rows import build,CompactSurfaceRows
from native_partner_surface_rows import build as expanded
from native_scene_contacts import SceneContacts
from test_native_partner_surface_rows import scene_fixture
from test_native_object_surface_rows import fixture,SHAPES
from test_native_scene_geometry import policy
from strep import read,save,sha256


def identity(row):
    return (row['time_s'],row['left']['actor'],row['right']['actor'],row['left_triangle'],row['right_triangle'],row['observed_kind'])


def compare(large,small,vertices=None):
    original=large.gaps(vertices);compact=small.gaps(vertices);groups={};other=[]
    for i,row in enumerate(large.rows):
        if row['kind']=='triangle-separation':groups.setdefault(identity(row),[]).append(original[i])
        else:other.append((row,original[i]))
    assert all(len(g)==9 for g in groups.values())
    seen=[];nontriangle=[]
    for i,row in enumerate(small.rows):
        if row['kind']=='triangle-support-separation':
            seen.append(identity(row));assert compact[i]==pytest.approx(min(groups[identity(row)]),abs=2e-12)
            assert len(row['left']['vertices'])==len(row['right']['vertices'])==3
        else:nontriangle.append((row,compact[i]))
    assert len(seen)==len(groups) and set(seen)==set(groups) and len(other)==len(nontriangle)
    for (a,ga),(b,gb) in zip(other,nontriangle):assert a==b and ga==gb
    assert small.report['expanded_total_rows']==len(large.rows) and small.report['triangle_support_blocks']==len(groups)


def test_all_record_blocks_and_unchanged_containment_rows_match_expansion(tmp_path):
    scene,p,digest=scene_fixture(tmp_path);large,small=expanded(scene,p,digest),build(scene,p,digest)
    compare(large,small)
    assert small.report['samples']==large.report['samples']
    assert small.report['complete_triangle_populations']==large.report['complete_triangle_populations']
    assert not small.report['quality_approved'] and not small.report['release_approved']
    assert not small.report['affine_linearization_equivalence']
    for shift in [[.03,.001,-.007],[-.02,.004,.015]]:
        def moved(name,time):
            a=scene.actors[name];position,rotation=a['placement'];points=a['rig'].vertices(a['sampler'].sample(time))@rotation.T+position
            return points+shift if name=='A' else points
        compare(large,small,moved)


def test_new_extreme_vertex_is_reduced_instead_of_frozen_to_previous_witness():
    scene=SimpleNamespace(actors={n:dict(skin=SimpleNamespace(nodes=np.arange(3))) for n in ['A','B']},check_inputs=lambda:None)
    row=dict(kind='triangle-support-separation',time_s=0.,normal_world=[1.,0,0],left=dict(actor='A',vertices=[0,1,2]),right=dict(actor='B',vertices=[0,1,2]))
    rows=CompactSurfaceRows(scene,[row],{})
    points={'A':np.array([[1.,0,0],[2.,0,0],[3.,0,0]]),'B':np.array([[0.,0,0],[.1,0,0],[.2,0,0]])}
    assert rows.gaps(lambda n,t:points[n])[0]==pytest.approx(.8)
    points['A'][2,0]=-5.;assert rows.gaps(lambda n,t:points[n])[0]==pytest.approx(-5.2)
    points['B'][0,0]=9.;assert rows.gaps(lambda n,t:points[n])[0]==pytest.approx(-14.)


def test_compaction_clears_budget_without_dropping_times_pairs_or_triangles(tmp_path):
    scene,p,digest=scene_fixture(tmp_path);small=build(scene,p,digest)
    assert small.report['expanded_total_rows']>len(small.rows)
    complete=build(scene,p,digest,maximum_rows=len(small.rows));assert complete.report['samples']==small.report['samples']
    with pytest.raises(ValueError,match='resource budget'):expanded(scene,p,digest,maximum_rows=len(small.rows))
    with pytest.raises(ValueError,match='resource budget'):build(scene,p,digest,maximum_rows=len(small.rows)-1)


@pytest.mark.parametrize('shape',SHAPES)
def test_all_primitive_and_plane_witness_forms_survive_compaction(tmp_path,shape):
    path,spec,scene,p=fixture(tmp_path,shape)
    spec['actors']['B']=copy.deepcopy(spec['actors']['A']);spec['actors']['B']['placement']['translation_m']=[.05,.05,.05]
    key=copy.deepcopy(spec['objects']['item']['keyframes'][0]);key.update(time_s=2.,translation_m=[.1,.2,.1]);spec['objects']['item']['keyframes'].append(key)
    save(path,spec);scene=SceneContacts(spec,tmp_path);p=policy(path,planes={'authored-plane':dict(normal_world=[0,1,0],offset_m=1.)})
    large,small=expanded(scene,p,sha256(path)),build(scene,p,sha256(path));compare(large,small)
    assert small.report['samples']==large.report['samples'] and small.report['objects_included']
    assert any(r['kind']=='world-plane' for r in small.rows)
    assert any(r['kind'].startswith('primitive-') for r in small.rows)


@pytest.mark.parametrize('fault',['missing-vertices','nonfinite','source-changed'])
def test_incomplete_or_changed_surfaces_cannot_yield_a_gap_population(tmp_path,fault):
    scene,p,digest=scene_fixture(tmp_path);rows=build(scene,p,digest)
    if fault=='source-changed':
        source=next(iter(scene.inputs));Path(source).write_bytes(Path(source).read_bytes()+b'changed')
        with pytest.raises(ValueError):rows.gaps()
    else:
        with pytest.raises(ValueError,match='population'):rows.gaps(lambda n,t:np.zeros((1,3)) if fault=='missing-vertices' else np.full((8,3),np.nan))


@pytest.mark.parametrize('settings',[dict(maximum_rows=True),dict(maximum_rows=100001),dict(maximum_rows=0),dict(clearance=True),dict(clearance=-.1)])
def test_invalid_resource_or_guidance_limits_reject_before_query(settings):
    with pytest.raises(ValueError):build(None,None,None,**settings)
