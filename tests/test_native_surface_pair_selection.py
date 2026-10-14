"""Public search selection preserves actual exports, source caps and provenance."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_fit import run
from native_fit_component_storage import FitComponentStorage
from native_component_pair_search import search as paired_search
from strep import read,save,sha256
from test_native_component_storage import fixture
from test_native_fit_storage import fixture as rotation_fixture


@pytest.mark.parametrize('mode',[None,True,[], 'unknown'])
def test_unknown_search_rejects_before_loading_sources_or_creating_output(tmp_path,mode):
    output=tmp_path/'output'
    with pytest.raises(ValueError,match='single or paired'):
        run(tmp_path/'missing',tmp_path/'missing',output,storage_repair_search=mode)
    assert not output.exists()


def test_paired_requires_explicit_original_component_policy(tmp_path):
    with pytest.raises(ValueError,match='explicit repair policy'):
        run(tmp_path/'missing',tmp_path/'missing',tmp_path/'no-policy',storage_repair_search='paired')
    _,_,_,contacts,permissions,boundary,policy=rotation_fixture(tmp_path)
    with pytest.raises(ValueError,match='component repair policy'):
        run(contacts,permissions,tmp_path/'rotation-only',proposal_model='surface-vector',
            geometry_policy=tmp_path/'unused-geometry.json',boundary_edit=boundary,
            storage_repair_policy=policy,storage_repair_search='paired')
    assert not (tmp_path/'rotation-only').exists()


def test_public_paired_selection_replays_same_complete_feasible_original(tmp_path,monkeypatch):
    base,policy,_,contacts,permissions,boundary=fixture(tmp_path)
    policy_path=tmp_path/'repair.json';save(policy_path,policy)
    geometry=tmp_path/'geometry.json';save(geometry,dict(schema='strep-native-scene-geometry-v1',
        contacts_sha256=sha256(contacts),clock=dict(mode='native-and-frame-populations',times_s=[0.,2.]),
        limits=dict(penetration_m=.005,depth_resolution_m=1e-6,surface_tolerance_m=1e-8),
        planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-1.))))
    helpers=[];original_init=FitComponentStorage.__init__
    def capture(self,*args,**kwargs):
        original_init(self,*args,**kwargs);helpers.append(self)
    monkeypatch.setattr(FitComponentStorage,'__init__',capture)
    results=[]
    for mode in ('single','paired'):
        folder=tmp_path/mode
        result=run(contacts,permissions,folder,iterations=1,proposal_model='surface-vector',
            geometry_policy=geometry,boundary_edit=boundary,storage_repair_policy=policy_path,
            storage_repair_stages=2,storage_repair_probes=8,storage_repair_search=mode)
        request=read(folder/'request.json')
        assert request['storage_repair_search']==result['storage_repair_search']==mode
        assert result['native_constraints_pass'] and result['sampled_geometry_conditions_pass']
        assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
        if mode=='paired':
            assert helpers[-1].search_method is paired_search
            name='native_component_pair_search.py'
            assert request['implementation_sha256'][name]==sha256(folder/'implementation'/name)
        results.append(folder)
    assert sha256(results[0]/'source-rate-caps.npz')==sha256(results[1]/'source-rate-caps.npz')
    assert sha256(results[0]/'proposal/actor-0.glb')==sha256(results[1]/'proposal/actor-0.glb')
    for label in ('start','final'):
        with np.load(results[0]/'probes'/label/'storage-search/start/observations.npz') as left, np.load(results[1]/'probes'/label/'storage-search/start/observations.npz') as right:
            assert left.files==right.files
            for name in left.files:np.testing.assert_array_equal(left[name],right[name])
    assert all(sha256(path)==digest for path,digest in base.scene.inputs.items())
