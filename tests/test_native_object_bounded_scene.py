"""Complete scene orchestration with mocked engine observations, not realism."""
from pathlib import Path
from types import SimpleNamespace
import sys,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from strep import save,read,sha256
from native_scene_contacts import SceneContacts
from native_object_asset import ObjectAsset
from native_object_bounded_fit import run as fit_run
from native_object_bounded_handoff import run as handoff_run
from native_object_bounded_scene import run,validate_handoff
from test_native_object_bounded_fit import fixture,request
from test_native_scene_geometry import policy
from test_native_scene_engine import mock_actor,serialized


def inputs(tmp_path,monkeypatch,*,actor_drift=False,static_fixture=True,default_drift=.02):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'fixture-lock')
    source,path,spec,_,value=fixture(tmp_path)
    if static_fixture:
        # A constant original path makes exterior preservation exactly
        # representable. The earlier moving fixture fails that input gate.
        from gltf_tools import read_glb,write_glb,accessor,append_accessor
        doc,binary=read_glb(source);binary=bytearray(binary)
        for sampler in doc['animations'][0]['samplers']:
            old=sampler['output'];values=accessor(doc,binary,old)
            sampler['output']=append_accessor(doc,binary,np.repeat(values[:1],len(values),axis=0),doc['accessors'][old]['type'])
        write_glb(source,doc,binary);spec['actors']['A']['sha256']=sha256(source)
        actor=SceneContacts(spec,tmp_path).actors['A'];center=actor['rig'].vertices(actor['sampler'].sample(0.)).mean(0)+[.4,.002,0.]
        spec['objects']['item']['keyframes']=[dict(time_s=t,translation_m=center.tolist(),rotation_xyzw=[0.,0.,0.,1.]) for t in [0.,2.]]
        save(path,spec);value['contacts_sha256']=sha256(path);value['edit_window_s']=[.5,1.5]
    value=request(value);rp=tmp_path/'request.json';save(rp,value)
    pp=tmp_path/'policy.json';save(pp,policy(path));fit=tmp_path/'fit';fit_run(path,rp,pp,fit)
    exe=tmp_path/'fixture-engine';exe.write_bytes(b'Explicitly mocked engine')
    def execute(command,**kwargs):
        req=read(command[-2])
        if 'cases' in req:
            scene=SceneContacts(read(tmp_path/'handoff/candidate-contacts.json'),tmp_path/'handoff');cases=[]
            for c in req['cases']:
                a=scene.actors[c['id']];row=mock_actor(a['rig'],a['sampler'],req['sample_times_s'],path=c['path'],animation_index=c['animation_index']);row['id']=c['id']
                if actor_drift:
                    for frame in row['frames']:
                        for bone in frame['bones']:bone[3][0]+=.001
                cases.append(row);Path(c['animation_output']).write_bytes(b'mocked actor resource')
            objects=[]
            for name in scene.objects:
                p,r=scene.object_poses(name,req['sample_times_s']);frames=[]
                for t,v,m in zip(req['sample_times_s'],p,r):
                    world=np.eye(4);world[:3,:3]=m;world[:3,3]=v
                    frames.append(dict(requested_time_s=t,matrix=serialized(world),rotation_xyzw=Rotation.from_matrix(m).as_quat().tolist()))
                objects.append(dict(id=name,frames=frames))
            save(command[-1],dict(engine=dict(string='mocked only'),cases=cases,objects=objects))
        else:
            asset=ObjectAsset(req['asset_path']);times=req['payload']['sample_times_s'];native={};default={}
            for name in asset.objects:
                p,r=asset.object_poses(name,times);q=Rotation.from_matrix(r).as_quat()
                native[name]=[dict(time_s=t,translation_m=v.tolist(),rotation_xyzw=w.tolist()) for t,v,w in zip(times,p,q)]
                default[name]=copy.deepcopy(native[name])
                for row in default[name]:row['translation_m'][0]+=default_drift
            Path(req['resource_path']).write_bytes(b'mocked object resource')
            save(command[-1],{'engine':dict(string='mocked only'),'default-import':default,'native-authoring':native})
        return SimpleNamespace(returncode=0)
    import subprocess
    monkeypatch.setattr(subprocess,'run',execute)
    handoff=tmp_path/'handoff';handoff_run(fit,handoff,exe)
    assert read(handoff/'result.json')['object_handoff_conditions_pass']==static_fixture
    return fit,handoff,exe


def test_complete_scene_checks_and_replay_preserve_original_and_default_failure(tmp_path,monkeypatch):
    fit,handoff,exe=inputs(tmp_path,monkeypatch);before=sha256(handoff/'result.json');out=tmp_path/'scene'
    result=run(fit,handoff,out,exe)
    assert result['bounded_scene_conditions_pass'] and result['combined_scene_conditions_pass'] and result['saved_scene_replay_pass']
    assert result['actor_engine_import_checked'] and result['complete_imported_skin_checked'] and result['complete_sampled_scene_geometry_checked']
    assert not result['default_import_contacts_pass'] and result['original_selected']
    assert not result['quality_approved'] and not result['release_approved'] and not result['training_admitted'] and not result['gpu_render_checked']
    assert sha256(handoff/'result.json')==before
    for n,h in result['files_sha256'].items():assert sha256(out/n)==h
    with pytest.raises(ValueError,match='Fresh'):run(fit,handoff,out,exe)


def test_passing_rigid_handoff_cannot_hide_failed_actor_motion(tmp_path,monkeypatch):
    fit,handoff,exe=inputs(tmp_path,monkeypatch,actor_drift=True);result=run(fit,handoff,tmp_path/'scene',exe)
    assert result['object_handoff_conditions_pass'] and not result['combined_scene_conditions_pass']
    assert not result['saved_scene_replay_pass'] and not result['bounded_scene_conditions_pass']
    assert result['original_selected'] and not result['quality_approved']


def test_original_moving_fixture_with_failed_exterior_preservation_is_rejected(tmp_path,monkeypatch):
    fit,handoff,exe=inputs(tmp_path,monkeypatch,static_fixture=False)
    assert not read(handoff/'native-authoring-epoch.json')['actual_protected_originals'][0]['passed']
    with pytest.raises(ValueError,match='Passing object handoff required'):run(fit,handoff,tmp_path/'scene',exe)


def test_default_contact_pass_does_not_hide_object_fidelity_failure(tmp_path,monkeypatch):
    fit,handoff,exe=inputs(tmp_path,monkeypatch,default_drift=.002)
    assert read(handoff/'candidate-engine/default-import-audit.json')['contacts']['passed']
    assert not read(handoff/'result.json')['object_engine_contact_conditions']['default-import']
    _,times=validate_handoff(fit,handoff,exe)
    assert len(times)>2


@pytest.mark.parametrize('fault',['pending','failed','engine','epoch','original','clock','method'])
def test_changed_or_incomplete_object_handoff_rejects_before_actor_import(tmp_path,monkeypatch,fault):
    fit,handoff,exe=inputs(tmp_path,monkeypatch)
    if fault=='pending':save(handoff/'pipeline.json',dict(status='processing'))
    elif fault=='failed':value=read(handoff/'result.json');value['object_handoff_conditions_pass']=False;save(handoff/'result.json',value)
    elif fault=='engine':exe.write_bytes(b'Another mocked executable')
    elif fault=='method':(handoff/'implementation/native_object_asset.py').write_bytes(b'changed')
    else:
        if fault=='epoch':p=handoff/'native-authoring-epoch.json';value=read(p);value['maximum_original_relative_translation_m']+=.01
        elif fault=='original':p=handoff/'original-contacts.json';value=read(p);value['objects']['item']['keyframes'][0]['translation_m'][0]+=.01
        else:p=handoff/'candidate-engine/engine-output.json';value=read(p);value['native-authoring']['item'][0]['time_s']+=.001
        save(p,value);receipt=read(handoff/'result.json');receipt['files_sha256'][p.relative_to(handoff).as_posix()]=sha256(p);save(handoff/'result.json',receipt)
    import native_object_bounded_scene as module
    monkeypatch.setattr(module,'import_actors',lambda *args,**kwargs:pytest.fail('Changed handoff must not launch actor import'))
    with pytest.raises(ValueError):run(fit,handoff,tmp_path/'scene',exe)
    assert not (tmp_path/'scene').exists()
