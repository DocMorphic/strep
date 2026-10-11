"""Bound policies, vector parity, Studio snapshots and real correction jobs."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_rotation_speed_policy import policy_for
from native_rotation_speed_fit import SpeedLimitedSceneProblem
from native_scene_norms import rows,linearize
from native_scene_fit import run as fit
from native_scene_resume import ResumeState
from test_native_scene_fit import prepare
from test_studio_native_scene_fit import setup as studio_setup
import studio_native_scene_fit as studio
from strep import read,save,sha256


def policy(digest,node=3,maximum=10):
    return dict(schema='strep-native-rotation-speed-policy-v1',contacts_sha256=digest,
        tracks=[dict(actor='A',node=node,maximum_degrees_per_second=maximum)])


@pytest.mark.parametrize('fault',['binding','schema','empty','extra','duplicate','bool-node','bool-speed','negative','nan','enormous','actor','missing-channel'])
def test_bad_bound_policies_reject(fault,tmp_path):
    _,_,contacts,_,_,_,edits=prepare(tmp_path,rotation=True);value=policy(sha256(contacts))
    if fault=='binding':value['contacts_sha256']='0'*64
    elif fault=='schema':value['schema']='other'
    elif fault=='empty':value['tracks']=[]
    elif fault=='extra':value['tracks'][0]['calibrated']=True
    elif fault=='duplicate':value['tracks']*=2
    elif fault=='bool-node':value['tracks'][0]['node']=True
    elif fault=='bool-speed':value['tracks'][0]['maximum_degrees_per_second']=True
    elif fault=='negative':value['tracks'][0]['maximum_degrees_per_second']=-1
    elif fault=='nan':value['tracks'][0]['maximum_degrees_per_second']=float('nan')
    elif fault=='enormous':value['tracks'][0]['maximum_degrees_per_second']=10**400
    elif fault=='actor':value['tracks'][0]['actor']='missing'
    else:value['tracks'][0]['node']=5
    with pytest.raises(ValueError):policy_for(value,edits,sha256(contacts))


@pytest.mark.parametrize('mode',['stored','continuous','decoded'])
def test_vector_rows_preserve_all_original_rows_and_match_speed_constraints(tmp_path,mode):
    _,_,_,_,_,scene,edits=prepare(tmp_path,rotation=True)
    problem=SpeedLimitedSceneProblem(scene,edits,rotation_speed_limits={('A',3):10})
    value=edits.initial.copy();value.reshape(-1,3)[:,1]=.1
    if mode=='stored':worlds=None
    elif mode=='continuous':worlds=problem.worlds(value,quantized=False)
    else:
        output=tmp_path/'actual.glb';edits.export('A',value,output)
        actual,worlds=problem.decoded({'A':output},value)
    system=rows(problem,value,worlds);expected=problem.constraints(value,worlds)
    np.testing.assert_allclose(system.residual(),expected,atol=1e-8)
    if mode=='decoded':np.testing.assert_allclose(system.residual(),actual,atol=1e-8)
    assert system.vectors.shape[0]==len(expected) and len(expected)>problem.protected_rows+10
    if mode=='continuous':
        base,jac,report=linearize(problem,value,step=.001,difference_source='continuous',difference_scheme='central',base_worlds=worlds)
        assert jac.shape==(base.vectors.size,problem.size) and np.isfinite(jac.data).all()


def speed_draft(tmp_path,monkeypatch,maximum=10):
    payload,source,resolver=studio_setup(tmp_path,monkeypatch)
    payload['schema']='strep-studio-native-scene-fit-v2'
    payload['rotation_speed_limits']=policy('draft',maximum=maximum)['tracks']
    payload['draft']['geometry']['planes']={'floor':dict(normal_world=[0.,1.,0.],offset_m=0.)}
    # The exact source point is reached at one authored instant; no other
    # contact intent or acceptance tolerance is inferred from the prompt.
    row=payload['draft']['scene']['contacts'][0]
    row['mode']='touch';row['interval_s']=[1.,1.];row['limits']={'position_m':1e-6}
    return payload,source,resolver


def test_studio_speed_job_runs_storage_vector_and_preserves_limits_on_resume(tmp_path,monkeypatch):
    payload,source,resolver=speed_draft(tmp_path,monkeypatch);original=source.read_bytes();before=copy.deepcopy(payload)
    folder=studio.folder_for('speed');prepared=studio.prepare(payload,folder,resolver)
    assert prepared['options']['proposal_model']=='storage-vector' and payload==before
    speed=read(folder/'rotation-speed-policy.json');assert speed['contacts_sha256']==sha256(folder/'contacts.json')
    studio.run(folder);review=studio.manifest('speed')
    assert review['native_conditions_pass'] and review['geometry_conditions_pass'] and review['rotation_speed_conditions_pass']
    assert review['authoring_request']['rotation_speed_limits']==payload['rotation_speed_limits']
    assert any(d['label']=='fit/rotation-speed-audit.json' for d in review['downloads'])
    assert source.read_bytes()==original and review['original_selected'] and not review['quality_approved']
    continuation=copy.deepcopy(payload);continuation['resume_from']='speed'
    next_folder=studio.folder_for('speed-next');studio.prepare(continuation,next_folder,resolver);studio.run(next_folder)
    assert studio.manifest('speed-next')['rotation_speed_conditions_pass']
    changed=copy.deepcopy(continuation);changed['rotation_speed_limits'][0]['maximum_degrees_per_second']=9
    with pytest.raises(ValueError,match='exact authored speed'):studio.prepare(changed,studio.folder_for('changed'),resolver)
    assert not studio.folder_for('changed').exists()


def test_studio_rejects_excluded_unedited_track_before_creating_job(tmp_path,monkeypatch):
    payload,_,resolver=speed_draft(tmp_path,monkeypatch)
    payload['rotation_speed_limits'][0].update(node=0,maximum_degrees_per_second=20)
    with pytest.raises(ValueError,match='speed limits conflict'):studio.prepare(payload,studio.folder_for('excluded'),resolver)
    assert not studio.folder_for('excluded').exists()


def test_retained_speed_policy_change_rejects_job_and_downloads(tmp_path,monkeypatch):
    payload,_,resolver=speed_draft(tmp_path,monkeypatch);folder=studio.folder_for('tampered');studio.prepare(payload,folder,resolver)
    value=read(folder/'rotation-speed-policy.json');value['tracks'][0]['maximum_degrees_per_second']=11;save(folder/'rotation-speed-policy.json',value)
    with pytest.raises(ValueError):studio.frozen(folder)


def test_cli_fit_records_bound_speed_policy_and_cannot_resume_without_it(tmp_path):
    _,_,contacts,_,permissions,scene,_=prepare(tmp_path,rotation=True)
    path=tmp_path/'speed.json';save(path,policy(sha256(contacts),maximum=0))
    output=tmp_path/'fit';result=fit(contacts,permissions,output,iterations=1,rotation_speed_policy=path)
    assert 'rotation_speed_conditions_pass' in result and result['original_selected']
    request=read(output/'request.json');assert request['rotation_speed_policy_sha256']==sha256(path)
    assert (output/'rotation-speed-preflight.json').is_file() and (output/'rotation-speed-lower-bounds.npz').is_file()
    with pytest.raises(ValueError,match='exact authored rotation speed'):fit(contacts,permissions,tmp_path/'bad-resume',iterations=1,resume_from=output)


def test_review_replays_exported_speeds_even_after_file_receipts_are_rebound(tmp_path,monkeypatch):
    from native_scene_edit import SceneEdits
    from native_scene_contacts import SceneContacts
    payload,_,resolver=speed_draft(tmp_path,monkeypatch,maximum=1)
    folder=studio.folder_for('rebound');studio.prepare(payload,folder,resolver);studio.run(folder)
    assert studio.manifest('rebound')['rotation_speed_conditions_pass']
    scene=SceneContacts(read(folder/'contacts.json'),folder)
    edits=SceneEdits(read(folder/'permissions.json'),scene,sha256(folder/'contacts.json'))
    value=edits.initial.copy();value.reshape(-1,3)[0,1]=.5;value.reshape(-1,3)[-1,1]=-.5
    target=folder/'fit/probes/final/A.glb';edits.export('A',value,target)
    assert edits.audit('A',target,0)['passed']
    result=read(folder/'fit/result.json');final=next(p for p in result['probes'] if p['label']=='final')
    final['files_sha256']['probes/final/A.glb']=sha256(target)
    save(folder/'fit/probes/final/probe.json',final);save(folder/'fit/result.json',result)
    completion=read(folder/'completion.json');completion['fit_result_sha256']=sha256(folder/'fit/result.json')
    completion['downloads']['fit/result.json']=completion['fit_result_sha256'];completion['downloads']['fit/probes/final/A.glb']=sha256(target)
    save(folder/'completion.json',completion)
    with pytest.raises(ValueError,match='speed evidence differs'):studio.manifest('rebound')
    assert studio.served_file('native-scene-fit-jobs/rebound/fit/probes/final/A.glb') is None
