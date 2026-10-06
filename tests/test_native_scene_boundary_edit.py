"""New explicit clip endpoints, protected interpolation, original-library export."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_fit import prepare
from native_scene_boundary_edit import BoundarySceneEdits, SCHEMA
from native_support_clock import NativeSupportSampler
from native_scene_fit import SceneProblem
from rig_asset import RigAsset
from strep import sha256


def request(permissions,start='preserve',end='preserve'):
    return dict(schema=SCHEMA,permissions=copy.deepcopy(permissions),boundary_keys={n:dict(start=start,end=end) for n in permissions['actors']},
        acknowledge_changed_boundary_compatibility=start=='edit' or end=='edit')


def test_preserved_boundary_contract_is_byte_identical_to_legacy_export(tmp_path):
    _,_,contacts,p,_,scene,legacy=prepare(tmp_path)
    new=BoundarySceneEdits(request(p),scene,sha256(contacts));x=legacy.initial.copy();x.reshape(-1,3)[:,1]=.1
    assert new.size==legacy.size
    a,b=tmp_path/'old.glb',tmp_path/'new.glb';legacy.export('A',x,a);new.export('A',x,b)
    assert a.read_bytes()==b.read_bytes() and p==request(p)['permissions']


@pytest.mark.parametrize('start,end',[('edit','preserve'),('preserve','edit'),('edit','edit')])
@pytest.mark.parametrize('rotation',[False,True])
def test_opted_boundaries_export_decode_and_append_preserve_originals(tmp_path,start,end,rotation):
    source,_,contacts,p,_,scene,_=prepare(tmp_path,rotation=rotation);before=source.read_bytes()
    edits=BoundarySceneEdits(request(p,start,end),scene,sha256(contacts))
    value=edits.initial.copy();value.reshape(-1,3)[:,0 if rotation else 1]=.05
    output=tmp_path/'probe.glb';edits.export('A',value,output);report=edits.audit('A',output,0)
    assert report['passed'] and not report['previous_start_end_transition_approval_inherited']
    rig=RigAsset.load(output);reader=NativeSupportSampler(rig.document,rig.binary,0);old=scene.actors['A']['sampler']
    for key,t in [('start',0.),('end',scene.duration)]:
        assert (not np.array_equal(reader.sample(t),old.sample(t))) == (dict(start=start,end=end)[key]=='edit')
    times=np.unique(np.concatenate([np.linspace(0,scene.duration,131),np.array([.0001,scene.duration-.0001,.853725])]+[c[2] for c in old.channels]))
    np.testing.assert_allclose(edits.worlds('A',value,times),np.array([reader.sample(float(t)) for t in times]),atol=2e-12,rtol=0)
    candidate=tmp_path/'appended.glb';index=edits.append_candidate('A',value,candidate,'Revised boundaries')
    changed=RigAsset.load(candidate);original=scene.actors['A']['rig']
    assert index==len(original.document['animations']) and changed.document['animations'][:-1]==original.document['animations']
    assert changed.binary[:len(original.binary)]==original.binary and source.read_bytes()==before
    appended=NativeSupportSampler(changed.document,changed.binary,index)
    for t in times:np.testing.assert_array_equal(appended.sample(float(t)),reader.sample(float(t)))


def test_endpoint_only_controls_leave_locked_interior_motion_unchanged(tmp_path):
    _,_,contacts,p,_,scene,_=prepare(tmp_path)
    clock=next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(0,'translation'))
    p['actors']['A']['protected_s']=[[float(clock[1]),float(clock[-2])]]
    edits=BoundarySceneEdits(request(p,'edit','edit'),scene,sha256(contacts));entry=edits.actors['A']['tracks'][0]
    assert entry['ids'].tolist()==[0,len(clock)-1]
    value=edits.initial.copy();value.reshape(-1,3)[:,1]=.1
    output=tmp_path/'endpoints.glb';edits.export('A',value,output)
    changed=RigAsset.load(output);reader=NativeSupportSampler(changed.document,changed.binary,0);old=scene.actors['A']['sampler']
    for t in np.linspace(float(clock[1]),float(clock[-2]),73):np.testing.assert_array_equal(reader.sample(float(t)),old.sample(float(t)))


@pytest.mark.parametrize('boundary',['start','end'])
def test_single_segment_boundary_window_needs_no_interior_editable_key(tmp_path,boundary):
    _,_,contacts,p,_,scene,_=prepare(tmp_path)
    clock=next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(0,'translation'))
    window=[float(clock[0]),float(clock[1])] if boundary=='start' else [float(clock[-2]),float(clock[-1])]
    a=p['actors']['A'];a['window_s']=window;a['knots_s']=[window[0],sum(window)/2,window[1]]
    edits=BoundarySceneEdits(request(p,'edit' if boundary=='start' else 'preserve','edit' if boundary=='end' else 'preserve'),scene,sha256(contacts))
    entry=edits.actors['A']['tracks'][0];assert entry['ids'].tolist()==[0 if boundary=='start' else len(clock)-1]
    x=edits.initial.copy();x.reshape(-1,3)[:,1]=.1;output=tmp_path/'single-segment.glb';edits.export('A',x,output)
    changed=RigAsset.load(output);reader=NativeSupportSampler(changed.document,changed.binary,0);old=scene.actors['A']['sampler']
    for t in np.linspace(0,scene.duration,97):
        if not window[0] <= t <= window[1]:np.testing.assert_array_equal(reader.sample(float(t)),old.sample(float(t)))


def test_two_key_native_channel_can_edit_boundary_without_invented_key(tmp_path):
    source,spec,contacts,p,_,scene,_=prepare(tmp_path)
    from gltf_tools import append_accessor,write_glb
    from native_scene_contacts import SceneContacts
    from strep import save
    rig=RigAsset.load(source);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=doc['animations'][0]
    channel=next(c for c in animation['channels'] if c['target']==dict(node=0,path='translation'));sampler=animation['samplers'][channel['sampler']]
    native=next(c for c in scene.actors['A']['sampler'].channels if c[:2]==(0,'translation'))
    sampler['input']=append_accessor(doc,binary,native[2][[0,-1]],'SCALAR');sampler['output']=append_accessor(doc,binary,native[3][[0,-1]],'VEC3')
    write_glb(source,doc,binary);spec['actors']['A']['sha256']=sha256(source);save(contacts,spec);p['contacts_sha256']=sha256(contacts)
    scene=SceneContacts(spec,tmp_path);edits=BoundarySceneEdits(request(p,'edit','edit'),scene,sha256(contacts))
    assert edits.actors['A']['tracks'][0]['ids'].tolist()==[0,1]
    x=edits.initial.copy();x.reshape(-1,3)[:,1]=.1;output=tmp_path/'two-keys.glb';edits.export('A',x,output)
    changed=RigAsset.load(output);reader=NativeSupportSampler(changed.document,changed.binary,0)
    assert len(next(c[2] for c in reader.channels if c[:2]==(0,'translation')))==2 and edits.audit('A',output,0)['passed']
    times=np.array([0.,.0001,.853725,1.9999,2.]);np.testing.assert_allclose(edits.worlds('A',x,times),np.array([reader.sample(float(t)) for t in times]),atol=2e-12,rtol=0)


def test_point_protection_freezes_its_entire_interpolation_support(tmp_path):
    _,_,contacts,p,_,scene,_=prepare(tmp_path,rotation=True);p['actors']['A']['protected_s']=[[.853725,.853725]]
    edits=BoundarySceneEdits(request(p,'edit','edit'),scene,sha256(contacts));x=edits.initial.copy();x.reshape(-1,3)[:,0]=.1
    output=tmp_path/'protected.glb';edits.export('A',x,output);rig=RigAsset.load(output)
    np.testing.assert_array_equal(NativeSupportSampler(rig.document,rig.binary,0).sample(.853725),scene.actors['A']['sampler'].sample(.853725))


def test_decoded_motion_constraints_still_enforce_source_rates_and_displacement(tmp_path):
    _,_,contacts,p,_,scene,_=prepare(tmp_path)
    edits=BoundarySceneEdits(request(p,'edit','edit'),scene,sha256(contacts));problem=SceneProblem(scene,edits)
    x=edits.initial.copy();x.reshape(-1,3)[:,1]=.1;out=tmp_path/'probe.glb';edits.export('A',x,out)
    decoded,_=problem.decoded({'A':out},x);np.testing.assert_allclose(problem.model(x),decoded,atol=5e-7,rtol=0)
    assert problem.protected_rows>0 and all(np.isfinite(v).all() for v in problem.caps['A'].caps)


@pytest.mark.parametrize('fault',['schema','extra','missing-policy','extra-policy','boolean-policy','ack-missing','ack-alias',
    'ack-unneeded','interior-start','interior-end','protected-start','protected-start-segment','protected-end','protected-end-segment'])
def test_invalid_or_unacknowledged_boundary_freedom_rejects(tmp_path,fault):
    _,_,contacts,p,_,scene,_=prepare(tmp_path);r=request(p,'edit','edit');a=r['permissions']['actors']['A']
    if fault=='schema':r['schema']='legacy'
    elif fault=='extra':r['override_contacts']=True
    elif fault=='missing-policy':r['boundary_keys']={}
    elif fault=='extra-policy':r['boundary_keys']['B']=dict(start='edit',end='edit')
    elif fault=='boolean-policy':r['boundary_keys']['A']['start']=True
    elif fault=='ack-missing':r['acknowledge_changed_boundary_compatibility']=False
    elif fault=='ack-alias':r['acknowledge_changed_boundary_compatibility']=1
    elif fault=='ack-unneeded':r['boundary_keys']['A']=dict(start='preserve',end='preserve')
    elif fault=='interior-start':a['window_s'][0]=.2;a['knots_s'][0]=.2
    elif fault=='interior-end':a['window_s'][-1]=1.8;a['knots_s'][-1]=1.8
    elif fault=='protected-start':a['protected_s']=[[0.,0.]]
    elif fault=='protected-start-segment':a['protected_s']=[[.0001,.0001]]
    elif fault=='protected-end':a['protected_s']=[[2.,2.]]
    else:a['protected_s']=[[1.9999,1.9999]]
    with pytest.raises(ValueError):BoundarySceneEdits(r,scene,sha256(contacts))


def test_appended_candidate_rejects_radial_overbudget_and_existing_output(tmp_path):
    _,_,contacts,p,_,scene,_=prepare(tmp_path);edits=BoundarySceneEdits(request(p,'edit','edit'),scene,sha256(contacts))
    x=np.ones(edits.size);out=tmp_path/'bad.glb'
    with pytest.raises(ValueError,match='bounds'):edits.append_candidate('A',x,out,'bad')
    assert not out.exists()
    out.write_bytes(b'existing')
    with pytest.raises(ValueError,match='Fresh'):edits.append_candidate('A',edits.initial,out,'fresh')
    assert out.read_bytes()==b'existing'


@pytest.mark.parametrize('fault',['binding','permission-schema','permission-extra','track-duplicate','node-bool','node-missing',
    'path','static-track','maximum-bool','maximum-large','window-outside','knots-duplicate','protected-outside','displacement-bool','step-channel'])
def test_boundary_freedom_cannot_bypass_original_track_and_scope_rules(tmp_path,fault):
    _,_,contacts,p,_,scene,_=prepare(tmp_path);r=request(p,'edit','edit');p=r['permissions'];a=p['actors']['A'];t=a['tracks'][0]
    if fault=='binding':p['contacts_sha256']='0'*64
    elif fault=='permission-schema':p['schema']='other'
    elif fault=='permission-extra':p['edit_anything']=True
    elif fault=='track-duplicate':a['tracks']*=2
    elif fault=='node-bool':t['node']=True
    elif fault=='node-missing':t['node']=999
    elif fault=='path':t['path']='scale'
    elif fault=='static-track':t['node']=5
    elif fault=='maximum-bool':t['maximum_change']=True
    elif fault=='maximum-large':t['maximum_change']=.22001
    elif fault=='window-outside':a['window_s']=[0.,3.]
    elif fault=='knots-duplicate':a['knots_s']=[0.,1.,1.,2.]
    elif fault=='protected-outside':a['protected_s']=[[2.,3.]]
    elif fault=='displacement-bool':a['maximum_joint_displacement_m']=True
    else:scene.actors['A']['sampler'].channels=[(*c[:4],'STEP') if c[:2]==(0,'translation') else c for c in scene.actors['A']['sampler'].channels]
    with pytest.raises(ValueError):BoundarySceneEdits(r,scene,sha256(contacts))
