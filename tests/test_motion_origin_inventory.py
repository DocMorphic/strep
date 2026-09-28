import copy
from pathlib import Path
import shutil
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from motion_origin import describe,snapshot
from motion_origin_inventory import collect,write


def source(folder,level='high'):
    take=ROOT/f'reports/action-jobs/profile-response-v1/takes/kick-{level}-seed-301'
    folder.mkdir(parents=True);shutil.copyfile(take/'motion.npz',folder/'motion.npz')
    snapshot(take/'motion.npz',folder/'motion-origin',describe(take/'motion.npz'))
    return folder


def test_distinct_donors_and_duplicate_history_keep_all_locations(tmp_path):
    primary=source(tmp_path/'source');donor=source(tmp_path/'following/source','low')
    shutil.copytree(donor,tmp_path/'source/transition-history/example/following/source')
    result=write(tmp_path)
    assert result['distinct_source_records']==2 and result['retained_locations']==3 and result['recorded_sources']==2
    assert result['applies_to']=='retained_source_snapshots' and not result['quality_approved']
    assert sorted(len(e['locations']) for e in result['entries'])==[1,2]
    assert {e['motion_sha256'] for e in result['entries']}=={sha256(primary/'motion.npz'),sha256(donor/'motion.npz')}
    for e in result['entries']:
        assert e['has_movement_profile'] and e['seed']==301
        for location in e['locations']:
            assert not Path(location['motion']).is_absolute()
            for p,digest in location['metadata_files'].items():assert sha256(tmp_path/p)==digest
    assert collect(tmp_path)==result==read(tmp_path/'generation-sources.json')


def test_direct_section_generation_records_are_also_verified(tmp_path):
    take=ROOT/'reports/action-jobs/profile-response-v1/takes/kick-low-seed-301'
    p=tmp_path/'generation/takes/section';p.mkdir(parents=True)
    for name in ['motion.npz','request.json','generation-record.json','motion-brief.json']:shutil.copyfile(take/name,p/name)
    r=collect(tmp_path);assert r['recorded_sources']==1
    assert 'manifest' not in r['entries'][0]['locations'][0]


def test_legacy_missing_metadata_is_unavailable_not_invented(tmp_path):
    p=tmp_path/'source';p.mkdir();(p/'motion.npz').write_bytes(b'legacy')
    r=collect(tmp_path);assert r['unavailable_sources']==1 and r['recorded_sources']==0
    assert not r['entries'][0]['has_movement_profile']


@pytest.mark.parametrize('change',['motion','record','missing_manifest','missing_motion'])
def test_corrupt_historical_origin_is_not_silently_ignored(tmp_path,change):
    p=source(tmp_path/'source/transition-history/old/following/source')
    if change=='motion':(p/'motion.npz').write_bytes(b'changed')
    elif change=='record':
        r=read(p/'motion-origin/generation-record.json');r['seed']=999;save(p/'motion-origin/generation-record.json',r)
    elif change=='missing_manifest':(p/'motion-origin/manifest.json').unlink()
    else:(p/'motion.npz').unlink()
    with pytest.raises((ValueError,FileNotFoundError)):collect(tmp_path)


def test_empty_import_has_no_fabricated_generation(tmp_path):
    (tmp_path/'source').mkdir();(tmp_path/'source/character.glb').write_bytes(b'character')
    r=collect(tmp_path);assert r['entries']==[] and r['recorded_sources']==0


def test_same_motion_with_distinct_generation_records_is_not_merged(tmp_path):
    a=source(tmp_path/'source');b=tmp_path/'following/source';shutil.copytree(a,b)
    record=read(b/'motion-origin/generation-record.json');record['generation_time_s']+=1
    save(b/'motion-origin/generation-record.json',record)
    save(b/'motion-origin/manifest.json',describe(b/'motion.npz',b/'motion-origin'))
    r=collect(tmp_path)
    assert r['distinct_source_records']==2 and len({e['motion_sha256'] for e in r['entries']})==1
