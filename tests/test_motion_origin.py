import copy
import sys
import shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read, save, sha256
from motion_origin import describe, snapshot, verify


@pytest.fixture
def take(tmp_path):
    source=ROOT/'reports/action-jobs/profile-response-v1/takes/kick-high-seed-301'
    folder=tmp_path/'take';folder.mkdir()
    for name in ['motion.npz','generation-record.json','request.json','motion-brief.json']:
        shutil.copyfile(source/name,folder/name)
    return folder


def test_real_profile_and_generation_bytes_are_preserved(take,tmp_path):
    expected=describe(take/'motion.npz');out=tmp_path/'origin'
    assert expected['status']=='recorded' and expected['has_movement_profile']
    snapshot(take/'motion.npz',out,expected)
    for name,digest in expected['files'].items():
        assert sha256(out/name)==digest
        assert (out/name).read_bytes()==(take/name).read_bytes()
    assert verify(take/'motion.npz',out,expected)==expected
    # Absolute historical generation paths are retained as data, never followed.
    record=read(take/'generation-record.json');record['npz']='Z:/unavailable/motion.npz'
    save(take/'generation-record.json',record)
    assert describe(take/'motion.npz')['status']=='recorded'


def test_missing_record_is_explicitly_unavailable(tmp_path):
    motion=tmp_path/'motion.npz';motion.write_bytes(b'opaque motion fixture')
    result=describe(motion)
    assert result['status']=='unavailable' and result['files']=={}
    snapshot(motion,tmp_path/'origin',result)
    assert verify(motion,tmp_path/'origin')==result


@pytest.mark.parametrize('change',['motion','request','seed','brief','resolution','orphan','missing_brief','no_record_brief'])
def test_inconsistent_provenance_is_rejected(take,change):
    record=read(take/'generation-record.json')
    if change=='motion':(take/'motion.npz').write_bytes(b'changed')
    elif change=='request':
        request=read(take/'request.json');request['label']='Other';save(take/'request.json',request)
    elif change=='seed':record['seed']=999;save(take/'generation-record.json',record)
    elif change=='brief':
        brief=read(take/'motion-brief.json');brief['description']='Other';save(take/'motion-brief.json',brief)
    elif change=='resolution':
        record['motion_brief']['description']='Other';save(take/'generation-record.json',record);save(take/'motion-brief.json',record['motion_brief'])
    elif change=='orphan':(take/'generation-record.json').unlink()
    elif change=='missing_brief':(take/'motion-brief.json').unlink()
    else:record.pop('motion_brief');save(take/'generation-record.json',record)
    with pytest.raises(ValueError):describe(take/'motion.npz')


def test_validation_to_snapshot_changes_are_rejected(take,tmp_path):
    expected=describe(take/'motion.npz')
    record=read(take/'generation-record.json');record['generation_time_s']+=1;save(take/'generation-record.json',record)
    with pytest.raises(ValueError,match='after request validation'):snapshot(take/'motion.npz',tmp_path/'origin',expected)
    assert not (tmp_path/'origin').exists()


def test_copied_manifest_is_pinned_and_derived_sources_keep_original_intent(take,tmp_path):
    expected=describe(take/'motion.npz');source=tmp_path/'source';source.mkdir()
    shutil.copyfile(take/'motion.npz',source/'motion.npz');snapshot(take/'motion.npz',source/'motion-origin',expected)
    derived=tmp_path/'derived';shutil.copytree(source,derived)
    assert verify(derived/'motion.npz',derived/'motion-origin')['scope'].startswith('Original source')
    record=read(derived/'motion-origin/generation-record.json');record['generation_time_s']+=1
    save(derived/'motion-origin/generation-record.json',record)
    with pytest.raises(ValueError):verify(derived/'motion.npz',derived/'motion-origin',expected)


def test_plain_generated_clip_does_not_gain_a_profile(take):
    record=read(take/'generation-record.json');record.pop('motion_brief');record['request'].pop('motion_profile')
    save(take/'generation-record.json',record);save(take/'request.json',record['request']);(take/'motion-brief.json').unlink()
    result=describe(take/'motion.npz')
    assert result['status']=='recorded' and not result['has_movement_profile']
    assert 'motion-brief.json' not in result['files']
