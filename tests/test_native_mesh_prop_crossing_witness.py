"""Exact represented-triangle proofs retain every bound scene record."""
from pathlib import Path
import sys,copy
from fractions import Fraction
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from native_mesh_prop_crossing_witness import certify_record,collect
from exact_triangle_crossing_witness import verify
from triangle_crossing import classify
from native_mesh_prop_scene_fit_v2 import fit
from native_observation_archive import ObservationArchive
from native_mesh_prop_pose import GripPoseEdit
from strep import read,save,sha256
from test_native_mesh_prop_pose import setup
from test_exact_triangle_crossing_witness import A,B


def record(a,b):return dict(left_triangle=0,right_triangle=0,**classify(a,b,1e-8))


@pytest.mark.parametrize('reverse',[False,True])
def test_proper_record_reproduces_exact_interior_on_both_triangles(reverse):
    a,b=(B,A) if reverse else (A,B);faces=np.array([[0,1,2]])
    result=certify_record(np.array(a),faces,np.array(b),faces,record(a,b),1e-8)
    assert result['status']=='proved' and verify(result['exact_proof'])['strict_interior_crossing_proved']
    assert all(sum(Fraction(v) for v in w)==1 and min(Fraction(v) for v in w)>0 for w in result['exact_proof']['barycentric_rational'])
    assert result['maximum_float_reconstruction_error_m']<1e-14 and not result['whole_scene_certified']


@pytest.mark.parametrize('a,b',[(A,A),(A,[[.5,.2,0.],[.5,.2,1.],[.5,1.2,0.]])])
def test_boundary_or_coplanar_record_stays_unresolved(a,b):
    faces=np.array([[0,1,2]]);result=certify_record(np.array(a),faces,np.array(b),faces,record(a,b),1e-8)
    assert result['status']=='unresolved' and not result['quality_approved'] and 'barycentric_approx' not in result


@pytest.mark.parametrize('fault',['left-index','boolean-index','kind','overlap','extra'])
def test_modified_record_rejects(fault):
    value=record(A,B)
    if fault=='left-index':value['left_triangle']=1
    elif fault=='boolean-index':value['right_triangle']=False
    elif fault=='kind':value['kind']='disjoint'
    elif fault=='overlap':value['overlap_length_m']+=.1
    else:value['quality_approved']=True
    with pytest.raises(ValueError):certify_record(np.array(A),np.array([[0,1,2]]),np.array(B),np.array([[0,1,2]]),value,1e-8)


def fixture(tmp_path):
    pp,policy_path,path,spec,permission=setup(tmp_path)
    spec['props']['far']=copy.deepcopy(spec['props']['crate']);spec['props']['far']['keyframes']=[dict(time_s=0.,translation_m=[20.,2.,0],rotation_xyzw=[0,0,0,1])]
    save(path,spec);permission['mesh_scene_sha256']=sha256(path);save(pp,permission);policy=read(policy_path);policy['mesh_scene_sha256']=sha256(path);save(policy_path,policy)
    warm=tmp_path/'warm.json';save(warm,dict(schema='strep-prop-source-relative-warm-start-v1',permissions_sha256=sha256(pp),controls=[0.,0,0,0]))
    output=tmp_path/'producer';fit(pp,policy_path,warm,output,maximum_evaluations=1)
    return pp,output/'probe-000'


def test_complete_generated_producer_collects_every_record_and_replays_sources(tmp_path):
    pp,probe=fixture(tmp_path);pins=GripPoseEdit(pp).inputs;output=tmp_path/'witnesses';result=collect(pp,probe,output)
    geometry=read(probe/'geometry.json');expected=sum(len(pair['surface']['records']) for row in geometry['samples'] for pair in row['mesh_pairs'] if ['prop','crate'] in [pair['left'],pair['right']])
    assert result['geometry_times']==3 and result['selected_prop_surface_records']==expected>1 and result['exact_interior_crossings_proved']+result['unresolved_records']==expected
    assert result['all_complete_world_vertex_arrays_byte_identical'] and not result['correction_applied'] and not result['release_approved'] and all(sha256(p)==d for p,d in pins.items())
    records=read(output/'records.json');assert len(records)==expected
    for row in records:assert verify(row['exact_proof'])==row['exact_proof']
    with np.load(output/'witness-observations.npz',allow_pickle=False) as z:
        assert len(z['record_indices'])==result['exact_interior_crossings_proved']
        assert all(records[int(i)]['status']=='proved' for i in z['record_indices']) and z['left_barycentric'].shape==(len(z['record_indices']),3)


def test_record_budget_rejects_instead_of_truncating(tmp_path):
    pp,probe=fixture(tmp_path)
    with pytest.raises(ValueError,match='no record truncation'):collect(pp,probe,tmp_path/'no',maximum_records=1)
    assert not (tmp_path/'no').exists()


@pytest.mark.parametrize('fault',['decision','permission','manifest','metrics','clock','partial','missing-pair','kind','snapshot','world'])
def test_tampered_or_incomplete_producer_rejects(tmp_path,fault):
    pp,probe=fixture(tmp_path)
    if fault=='decision':
        data=read(probe/'decision.json');data['controls'][3]=1.;save(probe/'decision.json',data)
    elif fault=='permission':
        data=read(pp);data['maximum_translation_m']=.9;save(pp,data)
    elif fault=='manifest':
        data=read(probe/'mesh-scene.json');data['props']['crate']['keyframes'][0]['translation_m'][0]+=.01;save(probe/'mesh-scene.json',data)
    elif fault=='snapshot':
        p=probe.parent/'implementation/native_mesh_prop_scene_fit_v2.py';p.write_bytes(p.read_bytes()+b'\n# changed\n')
    elif fault=='world':
        archive=probe/'geometry-observations.npz'
        with np.load(archive,allow_pickle=False) as z:arrays={k:z[k] for k in z.files}
        arrays['mesh_frame_0_actor_A_world_m'][0,0]+=.01
        archive.unlink();Path(str(archive)+'.receipt.json').unlink()
        with ObservationArchive(archive) as sink:
            for k,v in arrays.items():sink[k]=v
    else:
        data=read(probe/'geometry.json')
        if fault=='metrics':data['samples'][1]['passed']=True
        elif fault=='clock':data['samples'][0]['time_s']=.01
        elif fault=='partial':data['all_policy_samples_evaluated']=False
        elif fault=='missing-pair':data['samples'][0]['mesh_pairs'].pop()
        else:next(p for row in data['samples'] for p in row['mesh_pairs'] if p['surface']['records'])['surface']['records'][0]['kind']='disjoint'
        save(probe/'geometry.json',data)
    with pytest.raises(ValueError):collect(pp,probe,tmp_path/'rejected')


@pytest.mark.parametrize('limit',[0,4097,True])
def test_invalid_budget_rejects_without_reading_sources(tmp_path,limit):
    with pytest.raises(ValueError):collect(tmp_path/'absent',tmp_path/'probe',tmp_path/'no',maximum_records=limit)
    assert not (tmp_path/'no').exists()
