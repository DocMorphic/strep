"""Actual affine interval previews, bounded seed lineage and streamed floor rows."""
from pathlib import Path
import copy
import numpy as np
import pytest
from test_native_affine_key_pose import affine_setup
from native_key_interval_model import KeyIntervalModel
from native_motion_orientation import extract
from sampled_motion_caps import measures
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb
from strep import read,save,sha256


def inputs(tmp_path,animated=False,boundary=False):
    source,scene,contacts,policy,request=affine_setup(tmp_path)
    if animated:
        rig=scene.actors['A']['rig'];document=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
        animation=document['animations'][0];rotation=next(c for c in animation['channels'] if c['target']==dict(node=3,path='rotation'))
        clock=animation['samplers'][rotation['sampler']]['input'];count=document['accessors'][clock]['count']
        scales=np.tile(document['nodes'][3]['scale'],(count,1));scales[:,0]+=np.linspace(0.,.000002,count)
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=3,path='scale')))
        animation['samplers'].append(dict(input=clock,output=append_accessor(document,binary,scales,'VEC3'),interpolation='LINEAR'))
        write_glb(source,document,binary);spec=read(contacts);spec['actors']['A']['sha256']=sha256(source);save(contacts,spec)
        request['contacts_sha256']=policy['contacts_sha256']=sha256(contacts)
    if boundary:request.update(boundary_keys=dict(start='edit',end='preserve'),acknowledge_changed_boundary_compatibility=True,frozen_times_s=[scene.duration])
    request['contact_reserve_m']=.000001
    paths=dict(contacts=contacts,geometry=tmp_path/'geometry.json',request=tmp_path/'request.json',controls=tmp_path/'controls.npz')
    save(paths['geometry'],policy);save(paths['request'],request)
    clock=next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(3,'rotation'))
    controls=np.zeros((len(clock),1,3));controls[3:6,0]=[.012,-.009,.006];controls[7,0]=[.01,0.,0.]
    np.savez_compressed(paths['controls'],times_s=clock,controls=controls)
    return paths


def model(paths,tmp_path,active=None):
    return KeyIntervalModel.from_inputs(**paths,active_keys=[3,4,5] if active is None else active,
        output=tmp_path/'seed',expected_sha256={k:sha256(p) for k,p in paths.items()})


@pytest.mark.parametrize('animated',[False,True])
def test_affine_interval_preview_matches_native_export_with_original_scale(tmp_path,animated):
    paths=inputs(tmp_path,animated);problem=model(paths,tmp_path);value=problem.initial.copy()+.003
    output=tmp_path/'candidate.glb';index=problem.export(value,output);rig=RigAsset.load(output)
    reader=NativeSupportSampler(rig.document,rig.binary,index);actual=np.array([reader.sample(float(t)) for t in problem.times])
    np.testing.assert_allclose(problem.worlds(value),actual,atol=1e-12,rtol=0)
    assert rig.document['nodes']==problem.rig.document['nodes'] and rig.binary[:len(problem.rig.binary)]==problem.rig.binary
    assert np.array_equal(actual[:,0],problem.source_world[:,0])
    assert np.array_equal(problem.controls(value)[7],problem.seed[7])
    rows=problem.rows(value,actual);payload,_,_=extract(actual[problem.rate_ids],problem.rig.joints,'right-polar-v1')
    start=problem.edit_count
    np.testing.assert_allclose(np.linalg.norm(rows.vectors[start:],axis=1),np.concatenate([a.ravel() for a in measures(payload,problem.rate.dt)]),atol=1e-11,rtol=1e-12)
    np.testing.assert_array_equal(rows.caps[start:],np.concatenate([(c+1e-5).ravel() for c in problem.original_caps]))
    assert read(tmp_path/'seed/seed.json')['quality_approved'] is False


def test_streamed_floor_keeps_every_time_vertex_plane_and_witness(tmp_path,monkeypatch):
    paths=inputs(tmp_path);policy=read(paths['geometry']);policy['planes']['wall']=dict(normal_world=[1.,0.,0.],offset_m=-2.);save(paths['geometry'],policy)
    problem=model(paths,tmp_path);worlds=problem.initial_world;points=problem.points(worlds,problem.used,problem.geometry_ids)
    expected=[];witnesses=[]
    for plane in policy['planes'].values():
        d=points@np.array(plane['normal_world'])-plane['offset_m'];ids=d.argmin(axis=1)
        expected.append(d[np.arange(len(ids)),ids]+policy['limits']['penetration_m']);witnesses.append(problem.used[ids])
    original=problem.points;calls=[]
    def bounded(worlds,ids,stamps):
        assert len(stamps)<=32;np.testing.assert_array_equal(ids,problem.used);calls.extend(stamps.tolist())
        return original(worlds,ids,stamps)
    monkeypatch.setattr(problem,'points',bounded);gaps,actual=problem.floor(worlds)
    np.testing.assert_allclose(gaps,np.concatenate(expected),atol=1e-14,rtol=0)
    np.testing.assert_array_equal(actual,witnesses);assert calls==problem.geometry_ids.tolist()
    np.testing.assert_allclose(gaps,problem.witness_gaps(worlds,actual),atol=1e-14,rtol=0)


@pytest.mark.parametrize('fault',['digest','clock','frozen','norm','boolean'])
def test_unbound_or_invalid_original_clock_seed_rejects(tmp_path,fault):
    paths=inputs(tmp_path);hashes={k:sha256(p) for k,p in paths.items()}
    if fault=='digest':hashes['controls']='0'*64
    else:
        with np.load(paths['controls']) as data:clock=data['times_s'].copy();controls=data['controls'].copy()
        if fault=='clock':clock[2]+=.00001
        elif fault=='frozen':controls[0]=.1
        elif fault=='norm':controls[3,0]=[2.,0.,0.]
        else:controls=controls.astype(bool)
        np.savez_compressed(paths['controls'],times_s=clock,controls=controls);hashes['controls']=sha256(paths['controls'])
    with pytest.raises((ValueError,AssertionError)):
        KeyIntervalModel.from_inputs(**paths,active_keys=[3,4,5],output=tmp_path/'seed',expected_sha256=hashes)
    assert not (tmp_path/'seed').exists()


def test_declared_start_edit_is_allowed_but_does_not_change_fixed_root(tmp_path):
    paths=inputs(tmp_path,boundary=True);problem=model(paths,tmp_path,[0,1])
    value=problem.initial.copy()+.005;worlds=problem.worlds(value)
    assert np.array_equal(worlds[:,0],problem.source_world[:,0])
    assert np.array_equal(problem.controls(value)[-1],problem.seed[-1])


def test_scale_changes_and_reference_mutation_cannot_pass_as_rotation_edits(tmp_path):
    paths=inputs(tmp_path);problem=model(paths,tmp_path);worlds=problem.initial_world.copy();worlds[:,3,:3,:3]*=1.001
    with pytest.raises(ValueError,match='source TRS scale'):problem.rows(problem.initial,worlds)
    problem.rate.caps[0][0,0]+=1
    with pytest.raises(ValueError,match='source-rate caps changed'):problem.check()


@pytest.mark.parametrize('dtype',[np.int64,np.float32,np.float64])
def test_numeric_seed_types_allow_fractional_edits_without_truncation(tmp_path,dtype):
    paths=inputs(tmp_path)
    with np.load(paths['controls']) as data:clock=data['times_s'];controls=np.zeros(data['controls'].shape,dtype=dtype)
    np.savez_compressed(paths['controls'],times_s=clock,controls=controls)
    problem=model(paths,tmp_path);value=problem.initial.copy()+.0125;full=problem.controls(value)
    assert full.dtype==np.float64
    np.testing.assert_array_equal(full[problem.active],np.full((3,1,3),.0125))
    output=tmp_path/'fractional.glb';index=problem.export(value,output);rig=RigAsset.load(output)
    sampler=NativeSupportSampler(rig.document,rig.binary,index)
    actual=np.array([sampler.sample(float(t)) for t in problem.times])
    np.testing.assert_allclose(actual,problem.worlds(value),atol=1e-12,rtol=0)
