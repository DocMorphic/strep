"""Joint native proposals preserve original rates and moving-partner contacts."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_affine_key_pose import affine_setup
from native_pair_key_guides import PairKeyGuides
from native_key_interval_model import KeyIntervalModel
from native_scene_contacts import SceneContacts
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from strep import read,save,sha256


def make_inputs(folder,*,contacts_enabled=True):
    _,scene,contacts,policy,request=affine_setup(folder)
    spec=read(contacts);spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    native_clock=next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(3,'rotation'))
    contact_time=float((native_clock[3]+native_clock[4])/2)
    spec['contacts'][0].update(actor='A',mode='touch',interval_s=[contact_time,contact_time],
        target=dict(space='actor',actor='B',vertices=spec['contacts'][0]['vertices'],reduction=spec['contacts'][0]['reduction']),limits=dict(position_m=.03))
    if not contacts_enabled:spec['contacts']=[]
    save(contacts,spec);scene=SceneContacts(spec,folder);policy['contacts_sha256']=sha256(contacts);gp=folder/'geometry.json';save(gp,policy)
    models={}
    for name in ('A','B'):
        target=folder/name;target.mkdir();declaration=copy.deepcopy(request);declaration.update(actor=name,contacts_sha256=sha256(contacts))
        rp=target/'authoring.json';save(rp,declaration)
        clock=next(c[2] for c in scene.actors[name]['sampler'].channels if c[:2]==(3,'rotation'))
        zero=target/'zero.npz';np.savez_compressed(zero,times_s=clock,controls=np.zeros((len(clock),1,3)))
        paths=dict(contacts=contacts,geometry=gp,request=rp,controls=zero)
        models[name]=KeyIntervalModel.from_inputs(**paths,active_keys=[3,4],output=target/'seed',expected_sha256={k:sha256(p) for k,p in paths.items()})
    m=models['A'];ids=np.unique(__import__('native_scene_geometry').faces_for(m.rig)[0]);stamp=float(m.clock[3]);index=int(np.searchsorted(m.times,stamp));vertex=int(ids[0])
    point=m.points(m.source_world,np.array([vertex]),np.array([index]))[0,0]
    guide=dict(time_s=stamp,left_actor='A',right_actor='B',axis_world=[1.,0.,0.],vertices=dict(A=[vertex],B=[vertex]),
        midpoint_m=float(point[0]),maximum_shift_m=.05,clearance_m=.001,reserve_m=.0005)
    return models,[guide]


@pytest.fixture(scope='module')
def inputs(tmp_path_factory):
    return make_inputs(tmp_path_factory.mktemp('pair-key-guides'))


def test_both_moving_actors_determine_contact_error_instead_of_fixed_partner(inputs):
    models,guides=inputs;p=PairKeyGuides(models,guides);value=p.initial.copy()
    value[:sum(p.sizes)]=np.tile([.01,-.02,.015],4)
    worlds=p.worlds(value);_,contact=p.norms(value,worlds)
    np.testing.assert_allclose(contact.vectors,0,atol=1e-13,rtol=0)
    single=dict(worlds);single['B']=models['B'].source_world
    _,other=p.norms(value,single)
    # Contact lies within the changed native keys' interpolation interval.
    assert np.linalg.norm(other.vectors)>1e-6


def test_complete_original_native_rows_and_caps_are_exact_in_joint_model(inputs):
    models,guides=inputs;p=PairKeyGuides(models,guides);native,contacts=p.norms(p.initial,p.source_worlds)
    expected=[]
    for name in ('A','B'):
        m=models[name];r=m.rows(m.initial,m.source_world);stop=len(m.times)*(len(m.nodes)+len(m.rig.joints))
        ids=np.r_[np.arange(stop),np.arange(m.edit_count,len(r.caps))];expected.append((r,ids))
    for key in ('vectors','caps','scales'):
        np.testing.assert_array_equal(getattr(native,key),np.concatenate([getattr(r,key)[ids] for r,ids in expected]))
    assert np.all(native.residual()<=0) and np.all(contacts.residual()<=0)


def test_joint_sparse_model_holds_every_original_native_row_hard(inputs):
    models,guides=inputs;p=PairKeyGuides(models,guides);system,jac,record=p.linearize(p.initial,p.source_worlds,.02)
    native,contacts=p.norms(p.initial,p.source_worlds)
    assert record['native_rows']==len(native.caps) and record['contact_rows']==len(contacts.caps)
    assert record['floor_rows']==sum(len(p.source_floor[n]) for n in p.names)
    assert record['hard_rows']==len(native.caps)+len(contacts.caps)+record['floor_rows']
    np.testing.assert_array_equal(system.caps[:len(native.caps)],native.caps)
    np.testing.assert_array_equal(system.scales[:len(native.caps)],native.scales)
    assert jac.shape==(len(system.caps)*3,p.size) and np.all(system.residual()[:record['hard_rows']]<=0)
    # The two actor blocks both reach the same real contact rows.
    first=3*len(native.caps);last=first+3*len(contacts.caps)
    assert jac[first:last,:p.sizes[0]].nnz and jac[first:last,p.sizes[0]:sum(p.sizes)].nnz
    with pytest.raises(ValueError,match='no entries discarded'):p.linearize(p.initial,p.source_worlds,.02,maximum_nonzeros=1)


def test_common_plane_coordinate_has_opposite_unit_effect_on_both_regions(inputs):
    models,guides=inputs;p=PairKeyGuides(models,guides);a=p.guide_gaps(p.initial,p.source_worlds);value=p.initial.copy();value[-1]=.1
    b=p.guide_gaps(value,p.source_worlds)
    np.testing.assert_allclose(b-a,[.005,-.005],atol=1e-15,rtol=0)


def test_serialized_both_actor_worlds_feed_the_same_complete_native_and_contact_model(inputs,tmp_path):
    models,guides=inputs;p=PairKeyGuides(models,guides);value=p.initial.copy();value[:sum(p.sizes)]=np.tile([.005,-.004,.003],4)
    preview=p.worlds(value);actual={}
    for i,name in enumerate(p.names):
        m=models[name];path=tmp_path/f'{name}.glb';index=m.export(value[p.offsets[i]:p.offsets[i+1]],path)
        rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,index)
        actual[name]=np.array([sampler.sample(float(t)) for t in p.times]);np.testing.assert_allclose(actual[name],preview[name],atol=1e-12,rtol=0)
    before=p.norms(value,preview);after=p.norms(value,actual)
    for a,b in zip(before,after):
        np.testing.assert_allclose(a.vectors,b.vectors,atol=1e-9,rtol=0);np.testing.assert_array_equal(a.caps,b.caps)


@pytest.mark.parametrize('fault',['axis','bool-axis','time','vertices','duplicate','same-actor','extra','shift','bool-shift'])
def test_malformed_guidance_cannot_silently_drop_or_change_population(inputs,fault):
    models,guides=inputs;g=copy.deepcopy(guides)
    if fault=='axis':g[0]['axis_world']=[2.,0.,0.]
    elif fault=='bool-axis':g[0]['axis_world']=[True,False,False]
    elif fault=='time':g[0]['time_s']=-1.
    elif fault=='vertices':g[0]['vertices']['A']=[]
    elif fault=='duplicate':g[0]['vertices']['A']*=2
    elif fault=='same-actor':g[0]['right_actor']='A'
    elif fault=='extra':g[0]['automatic']=True
    elif fault=='shift':g[0]['maximum_shift_m']=0.
    else:g[0]['maximum_shift_m']=True
    with pytest.raises(ValueError):PairKeyGuides(models,g)


@pytest.mark.parametrize('fault',['controls','worlds','caps'])
def test_changed_complete_observations_or_original_caps_reject(inputs,fault):
    models,guides=inputs;p=PairKeyGuides(models,guides)
    if fault=='controls':
        with pytest.raises(ValueError):p.worlds(p.initial[:-1])
    elif fault=='worlds':
        with pytest.raises(ValueError):p.norms(p.initial,dict(A=models['A'].source_world))
    else:
        cap=models['A'].rate.caps[0];saved=cap.copy()
        try:
            cap[0,0]+=1
            with pytest.raises(ValueError,match='source-rate caps changed'):p.norms(p.initial,p.source_worlds)
        finally:cap[:]=saved
