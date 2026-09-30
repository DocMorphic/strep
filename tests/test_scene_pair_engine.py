import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_pair_engine import copy_verified_engine
from strep import ROOT,save,read,sha256


def fixture(tmp_path):
    study=tmp_path/'study'; previous=tmp_path/'engine'; study.mkdir();previous.mkdir()
    clip=study/'actor.glb';clip.write_bytes(b'explicit test fixture')
    case=dict(id='input-Actor',path=clip.name,sha256=sha256(clip),frames=3,fps=30,sample_by_time=True)
    save(study/'manifest.json',dict(cases=[case]))
    save(previous/'pipeline.json',dict(status='complete'))
    save(previous/'engine-output.json',dict(test_fixture=True))
    save(previous/'request.json',dict(cases=[dict(id=case['id'],path=str(clip),frames=3,sample_by_time=True)]))
    save(previous/'verification.json',dict(runner_sha256=sha256(ROOT/'scripts/run_godot_rig_import.py'),engine_script_sha256=sha256(ROOT/'scripts/godot_import_audit.gd'),
        checks=[dict(id=case['id'],source_sha256=case['sha256'],frames=3,bones=77,imported_skinned_surfaces=1,imported_loop_mode=0,sampled_original_by_time=True,
            max_position_error_m=1e-7,max_basis_element_error=1e-7)]))
    return study,previous,tmp_path/'copy'


def test_reuses_exact_observations_with_all_raw_evidence(tmp_path):
    study,old,out=fixture(tmp_path);copy_verified_engine(study,old,out)
    record=read(out/'reused-evidence.json');assert record['matched_cases']==['input-Actor']
    for name,digest in record['files'].items():assert sha256(out/name)==digest==sha256(old/name)
    with pytest.raises(ValueError,match='Fresh'):copy_verified_engine(study,old,out)


@pytest.mark.parametrize('fault',['clip','frames','duplicate','method','failed','looping','fps','index_sampling'])
def test_different_or_incomplete_import_cannot_be_reused(tmp_path,fault):
    study,old,out=fixture(tmp_path)
    if fault=='clip':(study/'actor.glb').write_bytes(b'different')
    elif fault=='failed':save(old/'pipeline.json',dict(status='failed'))
    elif fault in ['fps','index_sampling']:
        data=read(study/'manifest.json');data['cases'][0]['fps' if fault=='fps' else 'sample_by_time']=60 if fault=='fps' else False;save(study/'manifest.json',data)
    else:
        path=old/'verification.json';data=read(path)
        if fault=='frames':data['checks'][0]['frames']=4
        if fault=='duplicate':data['checks'].append(data['checks'][0].copy())
        if fault=='method':data['runner_sha256']='different'
        if fault=='looping':data['checks'][0]['imported_loop_mode']=1
        save(path,data)
    with pytest.raises(ValueError):copy_verified_engine(study,old,out)
    assert not out.exists()
