import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import save,sha256
from package_support_developer_review import verified_pair, review_landmarks


@pytest.fixture
def files(tmp_path):
    before=tmp_path/'before.glb';before.write_bytes(b'original selected asset')
    after=tmp_path/'after.glb';after.write_bytes(b'later selected asset')
    source=tmp_path/'source.json';source.write_text('source protocol')
    save(tmp_path/'timeline.json',dict(rows=[dict(frame=0)]))
    save(tmp_path/'completion.json',dict(case='case-a',before_sha256=sha256(before),after_sha256=sha256(after),
        inputs={str(source):sha256(source)},timeline_sha256=sha256(tmp_path/'timeline.json')))
    return tmp_path,before,after,source


def test_pair_evidence_binds_exact_selected_versions(files):
    folder,before,after,_=files
    assert verified_pair(folder,'case-a',before,after)['case']=='case-a'
    with pytest.raises(ValueError):verified_pair(folder,'case-a',after,before)
    with pytest.raises(ValueError):verified_pair(folder,'different-case',before,after)
    with pytest.raises(ValueError):verified_pair(folder,'case-a',before,after,'backtracking')


@pytest.mark.parametrize('changed',['after.glb','source.json','timeline.json'])
def test_changed_motion_input_or_timeline_cannot_enter_review(files,changed):
    folder,before,after,_=files
    (folder/changed).write_bytes(b'changed after audit')
    with pytest.raises(ValueError):verified_pair(folder,'case-a',before,after)


def test_review_witnesses_preserve_subframes_and_terminal_frame():
    audit=dict(floor=dict(worsened_samples=1,worst=dict(frame=2.25)),
        root_acceleration=dict(maximum_pointwise_increase=.02,maximum_increase_frame=3),
        feet={'Left':dict(candidate_peak_frame=4),'Right':dict(candidate_peak_frame=None)})
    assert [r['frame'] for r in review_landmarks(audit,5)] == [2.25,3,4]
    assert review_landmarks(None,5) == []
    audit['floor']['worst']['frame']=5
    with pytest.raises(ValueError):review_landmarks(audit,5)
    audit['floor']['worst']['frame']=float('nan')
    with pytest.raises(ValueError):review_landmarks(audit,5)
