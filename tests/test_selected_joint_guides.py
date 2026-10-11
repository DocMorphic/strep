"""Model-free admission of selective body guides; actual channels checked locally."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generation_constraints import SELECTABLE_JOINTS, validate_guides, validate_selected_joints


def guide(names):
    return dict(type='joint-set',motion='reports/source.npz',sha256='a'*64,
                source_frames=[1,2],frame_indices=[10,20],joint_names=names)


@pytest.mark.parametrize('names', [['Head'],['Hips','Head','LeftShin','RightShin'],
                                 ['Chest','LeftForeArm','RightForeArm'],list(SELECTABLE_JOINTS)])
def test_selective_body_guides_keep_explicit_channels_and_clock(names):
    g=guide(names);old=copy.deepcopy(g)
    assert validate_guides([g],30)==[old] and g==old


@pytest.mark.parametrize('names', [None,[],['Head','Head'],['LeftKnee'],['head'],['LeftHandIndex1'],
                                  ['LeftHand','anything'],[True],[{}],['Head']*31,'Head'])
def test_unknown_duplicate_empty_and_unmodeled_channels_reject(names):
    with pytest.raises(ValueError,match='SOMA30'):validate_guides([guide(names)],30)


def test_body_guides_do_not_silently_extend_end_effector_groups():
    g=guide(['Head']);g['type']='end-effector'
    with pytest.raises(ValueError,match='hand/foot'):validate_guides([g],30)
    g['joint_names']=['LeftHand','RightFoot'];assert validate_guides([g],30)==[g]


def test_selected_and_existing_guides_share_root_overlap_rule():
    a=guide(['LeftShin']);b=guide(['Head']);b['type']='fullbody';del b['joint_names']
    with pytest.raises(ValueError,match='Overlapping'):validate_guides([a,b],30)


def test_frame_origin_hash_and_bounds_are_still_required():
    for change in (dict(frame_indices=[20,10]),dict(frame_indices=[10,30]),
                   dict(sha256='wrong'),dict(motion='../outside.npz'),dict(source_frames=[1])):
        with pytest.raises(ValueError):validate_guides([{**guide(['Head']),**change}],30)


def test_selection_validation_leaves_author_input_unchanged():
    names=['Head','LeftShin'];assert validate_selected_joints(names)==names
    assert names==['Head','LeftShin'] and len(SELECTABLE_JOINTS)==30


def test_studio_serves_the_composer_dependency_and_rejects_neighbor_paths():
    from action_studio_server import allowed_file
    root=Path(__file__).resolve().parents[1]
    assert allowed_file('/selected-joint-guides.mjs')==root/'scripts/selected-joint-guides.mjs'
    for path in ('/selected_joint_constraints.py','/selected-joint-guides.mjs/../generation_constraints.py',
                 '/scripts/selected-joint-guides.mjs'):
        assert allowed_file(path) is None
