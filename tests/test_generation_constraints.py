import copy
import sys
from pathlib import Path
import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from strep import ROOT, sha256, read
from generation_constraints import validate_guides, compile_guides, load_guides
from action_requests import validate_batch, request_digest
from kimodo.skeleton import SOMASkeleton30


def request():
    value = copy.deepcopy(read(ROOT / 'reports/action-coverage-v1/request.json')['requests'][3])
    path = 'reports/action-coverage-v1/raw/wave/seed-11/attempt-001/motion.npz'
    value['generation_constraints'] = [dict(type='right-hand', motion=path, sha256=sha256(ROOT / path), source_frames=[40, 40], frame_indices=[59, 60])]
    return value


def test_exact_pose_conversion_and_sequence_frame_boundary():
    value = request(); compiled, provenance = compile_guides(value)
    skeleton = SOMASkeleton30()
    guide = load_guides(compiled, skeleton)[0]
    with np.load(ROOT / value['generation_constraints'][0]['motion']) as source:
        local = skeleton.from_SOMASkeleton77(torch.tensor(source['local_rot_mats'][[40, 40]]))
        rotations, positions, _ = skeleton.fk(local, torch.tensor(source['root_positions'][[40, 40]]))
    # Upstream float32 matrix/axis-angle roundtrip has micrometre-scale error.
    torch.testing.assert_close(guide.global_joints_positions, positions, atol=1e-5, rtol=0)
    torch.testing.assert_close(guide.global_joints_rots, rotations, atol=1e-5, rtol=0)
    torch.testing.assert_close(guide.root_y_pos, positions[:, 0, 1])
    assert guide.crop_move(0, 60).frame_indices.tolist() == [59]
    assert guide.crop_move(60, 120).frame_indices.tolist() == [0]
    assert guide.crop_move(120, 180).frame_indices.tolist() == []
    assert 'hip height' in provenance[0]['scope']


@pytest.mark.parametrize('change', [dict(frame_indices=[120, 121]), dict(frame_indices=[True, 60]), dict(frame_indices=[60, 59]), dict(frame_indices=[60, 60]), dict(source_frames=[0]), dict(motion='../secret.npz'), dict(motion='C:/secret.npz'), dict(type={}), dict(joint_names=['RightHand']), dict(sha256='wrong')])
def test_invalid_guides_are_not_silently_ignored(change):
    value = request(); value['generation_constraints'][0].update(change)
    with pytest.raises(ValueError): validate_guides(value['generation_constraints'], 120)


def test_hash_source_frame_and_overlapping_root_conflicts():
    value = request(); value['generation_constraints'][0]['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'): compile_guides(value)
    value = request(); value['generation_constraints'][0]['source_frames'] = [999, 999]
    with pytest.raises(ValueError, match='valid source frames'): compile_guides(value)
    value = request(); value['generation_constraints'] *= 2
    with pytest.raises(ValueError, match='Overlapping'): compile_guides(value)


def test_all_supported_upstream_guide_types_and_digest():
    value = request(); batch = dict(schema_version=1, requests=[value])
    original = request_digest(batch)
    for kind in ['root2d', 'fullbody', 'left-hand', 'right-hand', 'left-foot', 'right-foot', 'end-effector']:
        value['generation_constraints'][0]['type'] = kind
        if kind == 'end-effector': value['generation_constraints'][0]['joint_names'] = ['RightHand', 'LeftHand']
        validate_batch(batch)
        compiled, _ = compile_guides(value)
        assert len(load_guides(compiled, SOMASkeleton30())) == 1
    assert original != request_digest(batch)


@pytest.mark.skipif(not torch.cuda.is_available(), reason='CUDA constraint interoperability test')
def test_cuda_crop_sparse_indices_match_upstream_transition_convention():
    from kimodo.motion_rep.conditioning import build_condition_dicts, get_unique_index_and_data
    value = request()
    for kind in ['root2d', 'fullbody', 'right-hand', 'end-effector']:
        value['generation_constraints'][0]['type'] = kind
        if kind == 'end-effector': value['generation_constraints'][0]['joint_names'] = ['RightHand', 'LeftHand']
        compiled, _ = compile_guides(value)
        guide = load_guides(compiled, SOMASkeleton30().to('cuda'), device='cuda')[0]
        indices, data = build_condition_dicts([guide.crop_move(60, 120)])
        for name in indices:
            ix = torch.cat(indices[name]).to('cuda'); values = torch.cat(data[name])
            assert values.device.type == 'cuda'
            _, selected = get_unique_index_and_data(ix, values)
            assert torch.isfinite(selected).all()


def test_audit_detects_root_and_effector_displacement():
    from audit_generation_guides import audit
    value = request(); value['generation_constraints'][0]['frame_indices'] = [40, 41]
    value['generation_constraints'][0]['source_frames'] = [40, 41]
    compiled, _ = compile_guides(value)
    with np.load(ROOT / value['generation_constraints'][0]['motion']) as source: motion = dict(source)
    assert audit(motion, compiled)['numerical_screen_passed']
    motion['root_positions'] = motion['root_positions'].copy()
    motion['root_positions'][40, 1] += .1
    result = audit(motion, compiled)
    assert not result['numerical_screen_passed']
    assert result['guides'][0]['maximum']['hip_height_error_m'] == pytest.approx(.1, abs=1e-5)


def test_invalid_pose_source_fails_before_text_encoding(tmp_path, monkeypatch):
    import run_actions
    from strep import save
    value=request();value['generation_constraints'][0]['sha256']='0'*64
    path=tmp_path/'request.json';save(path,dict(schema_version=1,requests=[value]))
    def forbidden(*args,**kwargs):raise AssertionError('Invalid pose guide reached model subprocess')
    monkeypatch.setattr(run_actions.subprocess,'Popen',forbidden)
    with pytest.raises(ValueError,match='checksum'):run_actions.run(path,tmp_path/'output')
    assert read(tmp_path/'output/pipeline.json')['failed_stage']=='pose_source_validation'


@pytest.mark.parametrize('selected', [['Head'],['LeftShin','RightShin'],
                                     ['Hips','Chest','LeftForeArm'],['LeftHand']])
def test_selected_body_channels_reach_real_condition_masks_without_chain_expansion(selected):
    from kimodo.motion_rep.reps.kimodo_motionrep import KimodoMotionRep
    value=request();value['generation_constraints'][0].update(type='joint-set',joint_names=selected)
    compiled,provenance=compile_guides(value);skeleton=SOMASkeleton30()
    guide=load_guides(compiled,skeleton)[0]
    indices=[skeleton.bone_index[j] for j in selected]
    assert guide.joint_names==selected and guide.pos_indices.tolist()==guide.rot_indices.tolist()==indices
    representation=KimodoMotionRep(skeleton,30)
    observed,mask=representation.create_conditions_from_constraints([guide],120,False,'cpu')
    for name,width in [('global_rot_data',6),('local_joints_positions',3)]:
        actual=mask[:,representation.slice_dict[name]].reshape(120,30,width)
        expected=torch.zeros_like(actual);expected[torch.tensor([59,60])[:,None],torch.tensor(indices)[None,:]]=True
        torch.testing.assert_close(actual,expected,rtol=0,atol=0)
    assert torch.isfinite(observed).all() and 'No automatic hand/foot chain expansion' in provenance[0]['scope']


def test_selected_joint_crop_and_saved_constraint_retain_the_exact_selection():
    value=request();value['generation_constraints'][0].update(type='joint-set',joint_names=['LeftShin','Head'])
    compiled,_=compile_guides(value);skeleton=SOMASkeleton30();guide=load_guides(compiled,skeleton)[0]
    cropped=guide.crop_move(60,120)
    assert cropped.name=='joint-set' and cropped.frame_indices.tolist()==[0] and cropped.joint_names==['LeftShin','Head']
    assert cropped.pos_indices.tolist()==guide.pos_indices.tolist()
    empty=guide.crop_move(80,90);assert empty.frame_indices.numel()==0 and empty.joint_names==guide.joint_names
    info=guide.get_save_info()
    def plain(v):
        if isinstance(v,torch.Tensor):return v.tolist()
        if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
        return v
    restored=load_guides([plain(info)],skeleton)[0]
    assert restored.joint_names==guide.joint_names and restored.name==guide.name
    torch.testing.assert_close(restored.global_joints_positions,guide.global_joints_positions,rtol=0,atol=1e-5)


def test_selected_joint_audit_catches_orientation_error_when_position_is_unchanged():
    from audit_generation_guides import audit
    from scipy.spatial.transform import Rotation
    from kimodo.skeleton import SOMASkeleton77
    value=request();value['generation_constraints'][0].update(type='joint-set',joint_names=['Head'])
    value['generation_constraints'][0].update(frame_indices=[40],source_frames=[40])
    compiled,_=compile_guides(value)
    with np.load(ROOT/value['generation_constraints'][0]['motion']) as archive:motion=dict(archive)
    assert audit(motion,compiled)['numerical_screen_passed']
    head=SOMASkeleton77().bone_index['Head'];motion['local_rot_mats']=motion['local_rot_mats'].copy()
    motion['local_rot_mats'][40,head]=motion['local_rot_mats'][40,head]@Rotation.from_rotvec([0,.5,0]).as_matrix()
    result=audit(motion,compiled)
    assert not result['numerical_screen_passed']
    row=result['guides'][0];assert row['position_joint_names']==row['rotation_joint_names']==['Head']
    assert row['maximum']['joint_position_error_m']<1e-4 and row['maximum']['effector_rotation_error_degrees']>28


@pytest.mark.skipif(not torch.cuda.is_available(),reason='Requires CUDA')
def test_selected_joint_cuda_crop_reaches_real_condition_assembly():
    from kimodo.motion_rep.reps.kimodo_motionrep import KimodoMotionRep
    value=request();value['generation_constraints'][0].update(type='joint-set',joint_names=['Head','LeftShin'])
    compiled,_=compile_guides(value);skeleton=SOMASkeleton30().to('cuda')
    guide=load_guides(compiled,skeleton,device='cuda')[0].crop_move(60,120)
    assert guide.frame_indices.device.type==guide.pos_indices.device.type==guide.rot_indices.device.type=='cpu'
    observed,mask=KimodoMotionRep(skeleton,30).create_conditions_from_constraints([guide],60,False,'cuda')
    assert observed.device.type==mask.device.type=='cuda' and torch.isfinite(observed).all()
