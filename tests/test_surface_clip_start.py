"""Explicit initial-pose repair without an invented accepted prefix."""
import numpy as np
import pytest
from test_surface_clip_job import fixture,config,attempt
from test_surface_clip_boundaries import key_values
from surface_clip import SurfaceClip
import surface_clip_job as jobs
from strep import read,save,sha256


def starting_contact(tmp_path,count=5,offset=.025):
    source,rig,reader,_=fixture(tmp_path,count);cfg=config()
    target=rig.vertices(reader.sample(0.))[0].copy();target[1]+=offset
    cfg['clip']['limits']['contact_error_m']=.002
    cfg['clip']['contacts']=[dict(vertex=0,target_m=target.tolist(),start_time_s=0.,end_time_s=0.)]
    return source,rig,cfg


def test_repaired_start_survives_resume_and_matches_uninterrupted_result(tmp_path):
    source,rig,cfg=starting_contact(tmp_path);original=source.read_bytes()
    folder=jobs.prepare(tmp_path/'resumed',source,source,**cfg,start_policy='edit',acknowledge_changed_start=True)
    full=jobs.prepare(tmp_path/'full',source,source,**cfg,start_policy='edit',acknowledge_changed_start=True)
    first=attempt(folder,1);assert first['status']=='checkpointed' and first['state']['validated_through']==2
    path=folder/first['state']['current_clip'];start=key_values(path,0)
    assert start!=key_values(source,0) and key_values(path,-1)==key_values(source,-1)
    record=jobs.artifact(folder,first['state']['accepted'][0]['path'])
    export=read(record.parent/'export.json');assert export['edited_keys']==[0,1,2] and export['preserved_through']==-1
    resumed=attempt(folder);whole=attempt(full)
    assert resumed['status']==whole['status']=='complete_numerical_candidate'
    assert resumed['state']['clip_sha256']==whole['state']['clip_sha256']
    assert key_values(folder/resumed['state']['current_clip'],0)==start
    assert source.read_bytes()==original and resumed['transition_review_required']


def test_failed_opening_is_retained_without_a_checkpoint(tmp_path):
    source,_,cfg=starting_contact(tmp_path,3,5.);cfg['solver']['epochs']=1;cfg['solver']['iterations_per_epoch']=4
    folder=jobs.prepare(tmp_path/'failed',source,source,**cfg,start_policy='edit',acknowledge_changed_start=True)
    result=attempt(folder)
    assert result['status']=='unresolved' and result['reason']=='unresolved_window' and result['state'] is None
    assert not (folder/'state.json').exists()
    candidate=next(folder.glob('attempts/*/window-*/candidate.glb'))
    assert not read(candidate.parent/'decoded-audit.json')['passed']
    assert not read(candidate.parent/'result.json')['passed']


def test_acknowledged_start_can_change_with_protected_end_in_two_key_clip(tmp_path):
    source,_,cfg=starting_contact(tmp_path,2)
    folder=jobs.prepare(tmp_path/'two',source,source,**cfg,start_policy='edit',acknowledge_changed_start=True)
    result=attempt(folder);assert result['status']=='complete_numerical_candidate'
    output=folder/result['state']['current_clip']
    assert key_values(output,0)!=key_values(source,0) and key_values(output,-1)==key_values(source,-1)
    export=read(next(folder.glob('attempts/*/window-*/export.json')));assert export['edited_keys']==[0]


def test_both_endpoints_can_be_edited_only_with_their_separate_acknowledgments(tmp_path):
    source,rig,cfg=starting_contact(tmp_path,3)
    context=SurfaceClip(rig,**cfg['clip']);t=float(context.keys[-1]);target=rig.vertices(context.reader.sample(t))[0].copy();target[1]+=.025
    cfg['clip']['contacts'].append(dict(vertex=0,target_m=target.tolist(),start_time_s=t,end_time_s=t))
    folder=jobs.prepare(tmp_path/'both',source,source,**cfg,start_policy='edit',acknowledge_changed_start=True,end_policy='edit',acknowledge_changed_end=True)
    result=attempt(folder);assert result['status']=='complete_numerical_candidate'
    output=folder/result['state']['current_clip']
    assert key_values(output,0)!=key_values(source,0) and key_values(output,-1)!=key_values(source,-1)
    assert read(next(folder.glob('attempts/*/window-*/export.json')))['edited_keys']==[0,1,2]


def test_accepted_opening_recovers_after_checkpoint_write_interruption(tmp_path,monkeypatch):
    source,_,cfg=starting_contact(tmp_path)
    folder=jobs.prepare(tmp_path/'interrupt',source,source,**cfg,start_policy='edit',acknowledge_changed_start=True)
    original_save=jobs.save
    def interrupt(path,value):
        original_save(path,value)
        if path==folder/'state.json':raise RuntimeError('simulated interruption after atomic save')
    monkeypatch.setattr(jobs,'save',interrupt)
    with pytest.raises(RuntimeError,match='simulated'):attempt(folder,1)
    checkpoint=read(folder/'state.json');assert checkpoint['accepted']
    opening=key_values(folder/checkpoint['current_clip'],0)
    monkeypatch.setattr(jobs,'save',original_save)
    final=attempt(folder);assert final['status']=='complete_numerical_candidate'
    assert key_values(folder/final['state']['current_clip'],0)==opening


def test_unaccepted_start_cannot_be_forged_as_a_saved_checkpoint(tmp_path):
    source,_,cfg=starting_contact(tmp_path)
    folder=jobs.prepare(tmp_path/'forged',source,source,**cfg,start_policy='edit',acknowledge_changed_start=True)
    save(folder/'state.json',dict(request_sha256=sha256(folder/'request.json'),accepted=[]))
    with pytest.raises(ValueError,match='accepted opening'):attempt(folder)


@pytest.mark.parametrize('policy,ack',[('edit',False),('preserve',True),('edit',1),(False,False),('unknown',True)])
def test_invalid_start_policy_rejected_before_any_copy(tmp_path,policy,ack):
    with pytest.raises(ValueError):jobs.prepare(tmp_path/'bad',tmp_path/'missing',tmp_path/'missing',**config(),start_policy=policy,acknowledge_changed_start=ack)
    assert not (tmp_path/'bad').exists()


def test_only_the_initial_window_can_unfreeze_its_first_key(tmp_path):
    _,rig,_,_=fixture(tmp_path);context=SurfaceClip(rig,**config()['clip'])
    for frames,value in [([1,2,3],False),([0,1,2],0)]:
        with pytest.raises(ValueError,match='initial window'):context.build_window(frames,context.controls(rig,frames),preserve_first=value)
    frames=[0,1,2];window,_,_,_=context.build_window(frames,context.controls(rig,frames),preserve_first=False)
    bounds=np.asarray(window.bounds).reshape(3,12,2);assert np.any(bounds[0,:,0]!=bounds[0,:,1])
