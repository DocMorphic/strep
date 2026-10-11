"""Actual serialized rates and fitting retain contacts, clocks and edit caps."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_rotation_speed_fit import serialized_rates, SpeedLimitedSceneProblem,optimize_speed_limited,speed_seed
from native_scene_fit import SceneProblem,optimize
from native_scene_edit import SceneEdits
from native_scene_contacts import SceneContacts
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from test_native_scene_fit import prepare
from gltf_tools import append_accessor,write_glb
from strep import sha256,save


@pytest.mark.parametrize('angles',[[0,0,0],[0,1e-8,1e-7],[0,179.99999,180],[0,180,0],[0,90,190]])
def test_independent_rates_match_relative_rotations_including_half_turns(angles):
    q=Rotation.from_euler('z',angles,degrees=True).as_quat();q[1]*=-3
    expected=np.rad2deg((Rotation.from_quat(q[:-1]).inv()*Rotation.from_quat(q[1:])).magnitude())/np.diff([0,.1,.3])
    np.testing.assert_allclose(serialized_rates(q,[0,.1,.3]),expected,atol=1e-10)


@pytest.mark.parametrize('fault',['zero','nan','clock','shape','bool'])
def test_invalid_serialized_input_rejects(fault):
    q=np.tile([0.,0.,0.,1.],(3,1));times=[0,1,2]
    if fault=='zero':q[1]=0
    elif fault=='nan':q[1,0]=np.nan
    elif fault=='clock':times=[0,0,2]
    elif fault=='shape':q=q[:,:3]
    else:q=q.astype(bool)
    with pytest.raises(ValueError):serialized_rates(q,times)


def test_model_and_fresh_decoded_rows_agree_and_detect_new_speed_violation(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path,rotation=True)
    problem=SpeedLimitedSceneProblem(scene,edits,rotation_speed_limits={('A',3):1})
    zero=edits.initial.copy();changed=zero.copy();changed.reshape(-1,3)[:,1]=.5
    original_rows=SceneProblem.constraints(problem,changed)
    np.testing.assert_array_equal(problem.model(changed)[:len(original_rows)],original_rows)
    assert np.max(problem.speed_rows(zero))<=0 and np.max(problem.speed_rows(changed))>0
    output=tmp_path/'changed.glb';edits.export('A',changed,output)
    decoded,_=problem.decoded({'A':output},changed)
    np.testing.assert_allclose(decoded,problem.model(changed),atol=5e-7)
    assert not problem.last_speed_output_audit['passed']
    assert problem.last_speed_output_audit['tracks'][0]['neighbor_comparisons']==10


def test_output_check_uses_serialized_motion_even_when_controls_predict_no_edit(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path,rotation=True)
    problem=SpeedLimitedSceneProblem(scene,edits,rotation_speed_limits={('A',3):1})
    value=edits.initial.copy();value.reshape(-1,3)[:,0]=.5
    output=tmp_path/'changed.glb';edits.export('A',value,output)
    zero=edits.initial.copy();decoded,_=problem.decoded({'A':output},zero)
    assert np.max(problem.speed_rows(zero))<=0 and np.max(decoded[-10:])>0
    assert not problem.last_speed_output_audit['passed']


def test_failed_existing_edit_audit_rejects_without_speed_tradeoff(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path,rotation=True)
    problem=SpeedLimitedSceneProblem(scene,edits,rotation_speed_limits={('A',3):1000})
    value=np.ones(edits.size);output=tmp_path/'outside-cap.glb';edits.export('A',value,output)
    with pytest.raises(ValueError,match='original native edit permissions'):problem.decoded({'A':output},value)
    assert output.exists()


def test_real_fit_reduces_authored_speeds_and_rechecks_exported_clock_and_contacts(tmp_path):
    source,spec,contacts,permissions,_,_,_=prepare(tmp_path)
    # This fixture isolates speed editing; the base prepare helper deliberately
    # adds a separate 2-mm target mismatch for contact-correction tests.
    spec['contacts'][0]['target']['points_m'][0][1]-=.002
    rig=RigAsset.load(source);doc=copy.deepcopy(rig.document);data=bytearray(rig.binary)
    animation=doc['animations'][0];clock=np.array([0,.5,1,1.5,2],np.float32)
    q=Rotation.from_euler('z',[0,4,8,4,0],degrees=True).as_quat()
    animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=5,path='rotation')))
    animation['samplers'].append(dict(input=append_accessor(doc,data,clock,'SCALAR'),output=append_accessor(doc,data,q,'VEC4'),interpolation='LINEAR'))
    write_glb(source,doc,data);spec['actors']['A']['sha256']=sha256(source)
    save(contacts,spec);permissions['contacts_sha256']=sha256(contacts)
    scene=SceneContacts(spec,tmp_path);permissions['actors']['A']['tracks']=[dict(node=5,path='rotation',maximum_change=9.)]
    edits=SceneEdits(permissions,scene,permissions['contacts_sha256'])
    problem=SpeedLimitedSceneProblem(scene,edits,rotation_speed_limits={('A',5):1.})
    raw=source.read_bytes();initial=problem.speed_rows(problem.initial)
    assert np.max(initial)>6
    output=tmp_path/'fit.glb'
    def evaluate(value,label):
        edits.export('A',value,output)
        return problem.decoded({'A':output},value)[0]
    value,fit=optimize_speed_limited(problem,evaluate,iterations=8,trust=.5)
    # Re-export the selected controls, not the last rejected optimizer probe.
    edits.export('A',value,output);residual,_=problem.decoded({'A':output},value)
    assert np.max(residual)<=0 and problem.last_speed_output_audit['passed']
    assert fit['final_merit'][0]==0 and fit['seed_accepted'] and source.read_bytes()==raw
    reader=NativeSupportSampler(RigAsset.load(output).document,RigAsset.load(output).binary,0)
    np.testing.assert_array_equal(next(c[2] for c in reader.channels if c[:2]==(5,'rotation')),clock)
    assert not problem.last_speed_output_audit['quality_approved']


def test_all_edited_actor_exports_are_required(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path,rotation=True)
    problem=SpeedLimitedSceneProblem(scene,edits,rotation_speed_limits={('A',3):1})
    with pytest.raises(ValueError):problem.audit_outputs({})


def test_speed_seed_does_not_move_unselected_controls_or_grant_feasibility(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path,rotation=True)
    problem=SpeedLimitedSceneProblem(scene,edits,rotation_speed_limits={('A',0):100})
    value,report=speed_seed(problem)
    np.testing.assert_array_equal(value,problem.initial)
    assert report['tracks']==[] and not report['feasibility_claimed']


def test_failed_full_scene_seed_is_not_adopted(tmp_path,monkeypatch):
    _,_,_,_,_,scene,edits=prepare(tmp_path,rotation=True)
    problem=SpeedLimitedSceneProblem(scene,edits,rotation_speed_limits={('A',3):100})
    seed=np.full(edits.size,.1);calls=[]
    import native_rotation_speed_fit as module
    monkeypatch.setattr(module,'speed_seed',lambda p:(seed,{}))
    def evaluate(value,label):
        calls.append(label)
        return np.array([1. if np.array_equal(value,seed) else -1.])
    value,fit=optimize_speed_limited(problem,evaluate,iterations=1)
    assert not fit['seed_accepted'] and calls[:2]==['speed-original','speed-seed']
    np.testing.assert_array_equal(value,problem.initial)
