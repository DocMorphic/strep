"""Synthetic engine records only; no Godot launch or real import evidence."""
from contextlib import contextmanager
import copy
from pathlib import Path
import sys

import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import reserved_object_engine as engine
from reserved_object_fixtures import build
from gltf_tools import accessor,read_glb
from strep import read,save,sha256
from test_reserved_object_fixtures import catalog


def fixture(tmp_path):
    path=tmp_path/'catalog.json';save(path,catalog())
    construction=tmp_path/'construction';build(path,construction)
    request,bindings=engine.inputs(construction)
    raw=dict(engine=dict(major=4,minor=7,patch=2,synthetic_fixture=True),compression_disabled=True,objects=[])
    for item in request['objects']:
        doc,binary=read_glb(item['path']);attrs=doc['meshes'][0]['primitives'][0]['attributes']
        p=accessor(doc,binary,attrs['POSITION']).astype(float);n=accessor(doc,binary,attrs['NORMAL']).astype(float)
        raw['objects'].append(dict(id=item['id'],positions=p.tolist(),normals=n.tolist(),indices=[],
            poses=[dict(translation_m=copy.deepcopy(v),basis_columns=np.eye(3).tolist()) for v in ([0.,0.,0.],item['grounded_translation_m'])]))
    return construction,request,bindings,raw


def test_complete_triangle_population_and_placement_checks_without_approval(tmp_path):
    _,request,_,raw=fixture(tmp_path)
    original=copy.deepcopy(raw)
    result=engine.reduce(request,raw)
    assert result['static_import_pass'] and result['placement_observations']==6
    assert all(r['complete_triangle_positions_exact'] and r['maximum_normal_component_error']==0 for r in result['objects'])
    assert not any(result[k] for k in ['physics_checked','gpu_render_checked','contact_reachability_checked',
                                     'motion_trial_executed','quality_approved','release_approved'])
    assert raw==original


def test_exact_geometry_accepts_index_reordering_and_consistent_reversed_winding(tmp_path):
    _,request,_,raw=fixture(tmp_path)
    for row in raw['objects']:
        count=len(row['positions']);order=np.random.default_rng(17).permutation(count)
        inverse=np.argsort(order)
        row['positions']=np.array(row['positions'])[order].tolist()
        row['normals']=np.array(row['normals'])[order].tolist()
        reversed_faces=np.arange(count).reshape(-1,3)[:,[2,1,0]].reshape(-1)
        row['indices']=inverse[reversed_faces].tolist()
    result=engine.reduce(request,raw)
    assert all(r['winding_convention']=='negative' for r in result['objects'])


@pytest.mark.parametrize('fault',['missing_object','duplicate_object','missing_triangle','changed_vertex',
                                 'changed_normal','invalid_index','boolean_index','mixed_winding',
                                 'missing_pose','changed_placement','changed_basis','nonfinite','compressed'])
def test_changed_or_incomplete_engine_population_rejected(tmp_path,fault):
    _,request,_,raw=fixture(tmp_path);row=raw['objects'][0]
    if fault=='missing_object':raw['objects'].pop()
    if fault=='duplicate_object':raw['objects'][1]['id']=row['id']
    if fault=='missing_triangle':row['positions']=row['positions'][:-3];row['normals']=row['normals'][:-3]
    if fault=='changed_vertex':row['positions'][0][0]=float(np.nextafter(np.float32(row['positions'][0][0]),np.float32(np.inf)))
    if fault=='changed_normal':row['normals'][0][0]+=.01
    if fault=='invalid_index':row['indices']=[-1]*len(row['positions'])
    if fault=='boolean_index':row['indices']=[False]*len(row['positions'])
    if fault=='mixed_winding':row['indices']=[2,1,0]+list(range(3,len(row['positions'])))
    if fault=='missing_pose':row['poses'].pop()
    if fault=='changed_placement':row['poses'][1]['translation_m'][0]=.001
    if fault=='changed_basis':row['poses'][1]['basis_columns'][0][0]=1.01
    if fault=='nonfinite':row['positions'][0][0]=float('nan')
    if fault=='compressed':raw['compression_disabled']=False
    with pytest.raises(ValueError):engine.reduce(request,raw)


@pytest.mark.parametrize('fault',['asset','descriptor','verification','request','catalog','methods','result_population'])
def test_changed_source_receipts_are_rejected_before_engine_launch(tmp_path,fault):
    construction,_,_,_=fixture(tmp_path)
    result=read(construction/'result.json');row=result['objects'][0];asset=construction/row['path']
    if fault=='asset':asset.write_bytes(b'changed')
    if fault=='descriptor':(asset.parent/'descriptor.json').write_text('{}')
    if fault=='verification':(asset.parent/'verification.json').write_text('{}')
    if fault=='request':(construction/'request.json').write_text('{}')
    if fault=='catalog':(construction/'catalog.json').write_text('{}')
    if fault=='methods':(construction/'implementation/reserved_object_fixtures.py').write_text('changed')
    if fault=='result_population':
        result['objects']=result['objects'][:-1];save(construction/'result.json',result)
    with pytest.raises(ValueError):engine.inputs(construction)


def test_busy_worker_refuses_before_any_output_or_engine_launch(tmp_path,monkeypatch):
    @contextmanager
    def busy():
        raise RuntimeError('Another local action job is running')
        yield
    monkeypatch.setattr(engine,'worker_lock',busy)
    def forbidden(*args,**kwargs):pytest.fail('Engine must not launch while busy')
    monkeypatch.setattr(engine.subprocess,'run',forbidden)
    output=tmp_path/'uncreated'
    with pytest.raises(RuntimeError,match='Another'):
        engine.run(tmp_path/'unused-construction',output,tmp_path/'unused-engine')
    assert not output.exists()
