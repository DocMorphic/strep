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
