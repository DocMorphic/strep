"""Current-point restoration binds and preserves the original acceptance epoch."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_key_guides import make_inputs
from test_native_interval_pair_fit_job import recipe as fit_recipe
from native_pair_key_guides import PairKeyGuides
from native_interval_pair_restore_job import bind,current,reference,run,SCHEMA
from strep import read,save,sha256


@pytest.fixture(scope='module')
def setup(tmp_path_factory):
    root=tmp_path_factory.mktemp('pair-current-restore');models,_=make_inputs(root);pair=PairKeyGuides(models,[],fit_contacts=True)
    source,_=fit_recipe(models,root);native,contact=pair.norms(pair.initial,pair.source_worlds)
    ref=root/'reference.npz';np.savez_compressed(ref,controls=pair.initial,times_s=pair.times,native_vectors=native.vectors,native_caps=native.caps,native_scales=native.scales,contact_vectors=contact.vectors,contact_caps=contact.caps,contact_scales=contact.scales,protected_contact_caps=pair.protected_contact_caps,**{f'source_floor_{n}':pair.source_floor[n] for n in pair.names})
    def exported(label,value):
        folder=root/label;folder.mkdir();spec=copy.deepcopy(models['A'].spec)
        for i,name in enumerate(pair.names):
            path=folder/f'{name}.glb';index=models[name].export(value[pair.offsets[i]:pair.offsets[i+1]],path);spec['actors'][name].update(glb=str(path),sha256=sha256(path),animation_index=index)
        cp=folder/'contacts.json';save(cp,spec);return cp
    point=np.tile([.08,-.06,.04],4)
    return pair,source,ref,exported('zero',pair.initial),exported('nonzero',point),point


def declaration(setup,tmp_path,*,nonzero=False):
    pair,source,ref,zero,changed,point=setup;pin=lambda p:dict(path=str(p),sha256=sha256(p))
    r=dict(schema=SCHEMA,source_recipe=pin(source),reference=pin(ref),current_contacts=pin(changed if nonzero else zero),value=(point if nonzero else pair.initial).tolist(),trust=.02,difference_step=.001,rate_headroom=.001,maximum_nonzeros=6000000)
    path=tmp_path/'restore.json';save(path,r);return path,r


@pytest.mark.parametrize('fault',['hash','point-bool','point-shape','point-box','trust','headroom','budget','field'])
def test_bad_request_rejects_before_creating_output(setup,tmp_path,fault):
    path,r=declaration(setup,tmp_path)
    if fault=='hash':r['reference']['sha256']='0'*64
    elif fault=='point-bool':r['value'][0]=True
    elif fault=='point-shape':r['value'].pop()
    elif fault=='point-box':r['value'][0]=1.1
    elif fault=='trust':r['trust']=0
    elif fault=='headroom':r['rate_headroom']=.02
    elif fault=='budget':r['maximum_nonzeros']=6000001
    else:r['approve']=True
    save(path,r);out=tmp_path/'output'
    with pytest.raises(ValueError):bind(path,out)
    assert not out.exists()


def test_source_cap_change_and_current_pose_mismatch_reject(setup,tmp_path):
    pair,_,ref,zero,_,point=setup
    with np.load(ref) as z:values={k:z[k] for k in z.files}
    values['native_caps']=values['native_caps'].copy();values['native_caps'][0]+=.001;bad=tmp_path/'bad.npz';np.savez_compressed(bad,**values)
    with pytest.raises(ValueError,match='reference'):reference(pair,bad)
    with pytest.raises(ValueError,match='declared'):current(pair,point,zero,Path(next(iter(pair.scene.inputs))).parent)


def test_changed_contact_contract_and_immutable_parent_reject(setup,tmp_path):
    pair,_,_,zero,_,_=setup;spec=read(zero);spec['contacts'][0]['limits']['position_m']+=.001
    cp=tmp_path/'changed.json';save(cp,spec)
    with pytest.raises(ValueError,match='contract'):current(pair,pair.initial,cp,zero.parent)
    folder=tmp_path/'immutable';folder.mkdir();save(folder/'result.json',dict(status='complete'));copy_cp=folder/'contacts.json';save(copy_cp,read(zero));path,r=declaration(setup,tmp_path);r['current_contacts']=dict(path=str(copy_cp),sha256=sha256(copy_cp));save(path,r)
    with pytest.raises(ValueError,match='immutable'):bind(path,folder/'output')


def test_already_motion_feasible_input_remains_unselected(setup,tmp_path):
    path,_=declaration(setup,tmp_path);result=run(path,tmp_path/'output')
    assert result['solver_status']=='NoNativeMotionRestorationNeeded' and result['original_native_failures_before']==0
    assert result['candidate_contacts'] is None and result['original_selected'] and not result['quality_approved']
    assert read(tmp_path/'output/source-reference.json')['original_source_reference_exact']


def test_fresh_current_linearization_keeps_source_caps_and_rejects_no_direction(setup,tmp_path,monkeypatch):
    import native_interval_pair_restore_job as module
    path,_=declaration(setup,tmp_path,nonzero=True);pair=setup[0];before={p:sha256(p) for m in pair.models.values() for p in m.pins}
    monkeypatch.setattr(module,'direction',lambda *args,**kwargs:(None,dict(status='TestNoDirection')))
    output=tmp_path/'restore';result=run(path,output)
    assert result['original_native_failures_before']>0 and result['solver_status']=='TestNoDirection' and result['candidate_contacts'] is None
    assert result['original_selected'] and not result['quality_approved']
    with np.load(setup[2]) as source,np.load(output/'search-reserves.npz') as reserve,np.load(output/'affine-observations.npz') as affine:
        caps=source['native_caps'];np.testing.assert_array_equal(reserve['original_native_caps'],caps)
        assert np.all(reserve['native_reserve']>=0)
        np.testing.assert_array_equal(affine['caps'][:len(caps)],caps-reserve['native_reserve'])
    assert not read(output/'surface-linearization.json')['linearization_at_source_zero']
    assert all(sha256(p)==h for p,h in before.items())


def test_current_static_rig_metadata_cannot_change_with_matching_animation(setup,tmp_path):
    from rig_asset import RigAsset
    from gltf_tools import write_glb
    pair,_,_,zero,_,_=setup;spec=read(zero);actor=spec['actors']['A'];rig=RigAsset.load(actor['glb']);doc=copy.deepcopy(rig.document)
    doc['asset']['generator']='unexpected replacement';glb=tmp_path/'changed.glb';write_glb(glb,doc,rig.binary)
    actor.update(glb=str(glb),sha256=sha256(glb));cp=tmp_path/'current.json';save(cp,spec)
    with pytest.raises(ValueError,match='static'):current(pair,pair.initial,cp,zero.parent)
