from pathlib import Path
import shutil,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_interval_pair_restore_job import setup,declaration
import native_interval_pair_restore_job as original
import native_interval_pair_retry_job as module
from strep import read,save,sha256


@pytest.fixture(scope='module')
def parent(setup,tmp_path_factory):
    folder=tmp_path_factory.mktemp('frozen-pair-parent');path,r=declaration(setup,folder,nonzero=True)
    old=original.direction;original.direction=lambda *a,**kw:(None,dict(status='TestNoDirection'))
    try:original.run(path,folder/'job')
    finally:original.direction=old
    return folder/'job'


def recipe(parent,tmp_path):
    path=tmp_path/'retry.json';r=dict(schema=module.SCHEMA,parent=dict(path=str(parent/'request.json'),sha256=sha256(parent/'request.json')),rate_headroom=.002,objective='sum-positive-excess');save(path,r);return path,r


def test_frozen_retry_only_tightens_native_search_caps(parent,tmp_path):
    path,_=recipe(parent,tmp_path);data=module.frozen(path,tmp_path/'out');system,jac,identity,value=data[-5:-1]
    with np.load(parent/'affine-observations.npz') as z:
        n=identity['native_rows'];np.testing.assert_array_equal(system.vectors,z['vectors']);np.testing.assert_array_equal(system.scales,z['scales'])
        assert np.all(system.caps[:n]<=z['caps'][:n]);np.testing.assert_array_equal(system.caps[n:],z['caps'][n:])
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('fault',['hash','headroom','loosen','objective','unknown'])
def test_bad_recipe_rejects_without_output(parent,tmp_path,fault):
    path,r=recipe(parent,tmp_path)
    if fault=='hash':r['parent']['sha256']='0'*64
    elif fault=='headroom':r['rate_headroom']=True
    elif fault=='loosen':r['rate_headroom']=0
    elif fault=='objective':r['objective']='approve'
    else:r['approved']=True
    save(path,r)
    with pytest.raises(ValueError):module.frozen(path,tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('fault',['source-cap','search-cap','vector','implementation','layout','actor-order','layout-nodes','reference-proof'])
def test_changed_frozen_problem_is_rejected(parent,tmp_path,fault):
    copied=tmp_path/'parent';shutil.copytree(parent,copied)
    if fault=='implementation':
        name=next(iter(read(copied/'request.json')['implementation_sha256']));(copied/'implementation'/name).write_text('changed')
    elif fault=='actor-order':
        value=read(copied/'actor-order.json');value['actors'].reverse();save(copied/'actor-order.json',value)
    elif fault=='layout-nodes':
        value=read(copied/'layouts.json');value['A']['nodes'][0]+=1;save(copied/'layouts.json',value)
    elif fault=='reference-proof':
        value=read(copied/'source-reference.json');value['original_source_reference_exact']=False;save(copied/'source-reference.json',value)
    elif fault=='layout':
        value=read(copied/'linearization.json');value['hard_rows']-=1;save(copied/'linearization.json',value)
    else:
        target=copied/('search-reserves.npz' if fault=='source-cap' else 'affine-observations.npz')
        with np.load(target) as z:values={k:z[k] for k in z.files}
        if fault=='source-cap':values['original_native_caps'][0]+=.001
        elif fault=='search-cap':values['caps'][0]+=.001
        else:values['vectors'][0,0]+=.001
        np.savez_compressed(target,**values)
    path,_=recipe(copied,tmp_path)
    with pytest.raises(ValueError):module.frozen(path,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_parent_result_population_is_immutable(parent,tmp_path):
    path,_=recipe(parent,tmp_path)
    with pytest.raises(ValueError,match='immutable'):module.frozen(path,parent/'new-output')


@pytest.mark.parametrize('mode',['none','unsafe'])
def test_no_direction_or_infeasible_solved_label_never_exports(parent,tmp_path,monkeypatch,mode):
    path,_=recipe(parent,tmp_path)
    def proposal(system,jac,value,*args,**kwargs):return (None if mode=='none' else np.full(len(value),2.)),dict(status='Solved')
    monkeypatch.setattr(module,'aggregate',proposal);out=tmp_path/'out';r=module.run(path,out)
    assert not r['affine_pass'] and r['candidate_contacts'] is None and r['original_selected'] and not r['quality_approved']
    assert read(out/'pipeline.json')['status']=='complete'
    if mode=='unsafe':assert (out/'proposed-direction.npz').is_file() and not read(out/'affine-postcheck.json')['original_boxes_and_trust_pass']


def test_existing_incomplete_output_is_not_modified_on_bind_failure(parent,tmp_path):
    path,_=recipe(parent,tmp_path);out=tmp_path/'out';out.mkdir();save(out/'request.json',dict(existing=True));before=(out/'request.json').read_bytes()
    with pytest.raises(ValueError):module.run(path,out)
    assert (out/'request.json').read_bytes()==before and not (out/'pipeline.json').exists()


def test_parent_change_after_first_validation_cannot_replace_the_pin(parent,tmp_path,monkeypatch):
    copied=tmp_path/'parent';shutil.copytree(parent,copied);path,_=recipe(copied,tmp_path);bind=module.bind_original
    def changed(*args,**kwargs):
        result=bind(*args,**kwargs);value=read(copied/'request.json');value['controls']+=1;save(copied/'request.json',value);return result
    monkeypatch.setattr(module,'bind_original',changed)
    with pytest.raises(ValueError,match='binding'):module.frozen(path,tmp_path/'out')
    assert not (tmp_path/'out').exists()
