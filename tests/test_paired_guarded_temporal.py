import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gltf_tools import append_accessor,read_glb
from paired_temporal_neighbor import rotation_channels
from rig_clip_import import AnimationSampler
from paired_guarded_temporal import GuardedEdit,world_from_local
from study_paired_guarded_temporal import motion_guard
from audit_scene_joint_rates import compare_rates


def fixture():
    # Parent deliberately follows its child numerically.
    nodes=[dict(name='Tip',translation=[0,1,0]),dict(name='Arm',children=[0],translation=[0,1,0])]
    animation=dict(channels=[],samplers=[])
    doc=dict(asset=dict(version='2.0'),nodes=nodes,skins=[dict(joints=[1,0])],animations=[animation],
             accessors=[],bufferViews=[],buffers=[dict(byteLength=0)])
    binary=bytearray();clock=append_accessor(doc,binary,np.arange(150,dtype=np.float32)/30,'SCALAR')
    angles=np.sin(np.arange(150)*.11)*.15
    output=append_accessor(doc,binary,Rotation.from_euler('z',angles).as_quat(),'VEC4')
    animation['samplers'].append(dict(input=clock,output=output,interpolation='LINEAR'))
    animation['channels'].append(dict(sampler=0,target=dict(node=1,path='rotation')))
    return doc,binary


def test_batched_fk_handles_parent_order_and_rejects_cycles():
    local=np.tile(np.eye(4),(3,2,1,1));local[:,0,1,3]=2;local[:,1,0,3]=3
    world=world_from_local(local,[1,-1])
    np.testing.assert_array_equal(world[:,0,:3,3],np.tile([3,2,0],(3,1)))
    with pytest.raises(ValueError,match='Cyclic'):world_from_local(local,[1,0])


def test_batch_sampling_and_export_agree_with_independent_decoder(tmp_path):
    doc,binary=fixture();frames=np.arange(67,83.001,.25)
    problem=GuardedEdit(doc,binary,['Arm'],[74,76],frames,dict(edited=[70,80],event=[73,77]))
    zero=np.zeros(problem.size);cost,slack=problem.evaluate(zero)
    assert cost==pytest.approx(1.,abs=1e-10) and slack.min()>-1e-8
    parameters=np.array([.02,-.01,.01,-.01,.02,-.01]);path=tmp_path/'edited.glb';problem.export(parameters,path)
    after,payload=read_glb(path);sampler=AnimationSampler(after,payload,0)
    decoded=np.array([sampler.sample(t/30)[problem.joints,:3,3] for t in frames])
    np.testing.assert_allclose(problem.positions(parameters),decoded,atol=1e-7,rtol=0)
    source=AnimationSampler(doc,binary,0)
    for t in [68,72,73,75,77,78,82]:
        np.testing.assert_array_equal(sampler.sample(t/30),source.sample(t/30))
    assert np.linalg.norm(sampler.sample(74/30)-source.sample(74/30))>1e-5


def test_per_joint_guard_detects_regression_hidden_by_global_peak():
    source=np.zeros((17,2,3));source[8,0,0]=.02
    candidate=source.copy();candidate[8,0,0]=.01;candidate[8,1,0]=.001
    rates=compare_rates(source,candidate,['Shoulder','Finger'],dict(event=[0,4]))
    assert rates['acceleration']['windows'][0]['candidate_peak']<rates['acceleration']['windows'][0]['source_peak']
    failures=motion_guard(rates)
    assert any(r['metric']=='acceleration' and r['joint']=='Finger' for r in failures)


def test_zero_edit_keeps_original_keys_and_full_vector_budget_is_enforced(tmp_path):
    doc,binary=fixture();problem=GuardedEdit(doc,binary,['Arm'],[74,76],np.arange(67,83.001,.25),dict(event=[73,77]))
    path=tmp_path/'zero.glb';problem.export(np.zeros(problem.size),path)
    after,payload=read_glb(path)
    np.testing.assert_array_equal(rotation_channels(doc,binary)[1][2],rotation_channels(after,payload)[1][2])
    parameters=np.array([.8,.8,0,0,0,0]);_,slack=problem.evaluate(parameters)
    assert slack[-2]==pytest.approx(1-2*.8**2) and slack[-2]<0


def test_samplewise_constraints_keep_original_peak_feasible_set():
    doc,binary=fixture();problem=GuardedEdit(doc,binary,['Arm'],[74,76],np.arange(67,83.001,.25),dict(event=[73,77]))
    parameters=np.array([.01,-.03,.02,-.01,.02,-.03])
    _,slack=problem.evaluate(parameters)
    expected=(problem.caps-problem.peaks(problem.positions(parameters)))/problem.normalizer+1e-9
    assert len(slack)>len(expected)
    assert slack[:-2].min()==pytest.approx(expected.min(),abs=1e-12)
    reserved=problem.evaluate(parameters,reserve=True)[1]
    assert np.all(reserved<=slack+1e-14)
