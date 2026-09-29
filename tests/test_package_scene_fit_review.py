import sys
import shutil
import tempfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from scene_region_job import JOBS
from package_scene_fit_review import build,verified_study
from action_studio_server import allowed_file

STUDY=ROOT/'reports/region-box-export-rates-control-v1'
AUDIT=ROOT/'reports/region-box-export-rates-control-v1-audit/verification.json'
ENGINE=ROOT/'reports/region-export-rate-comparison-v1/engine/verification.json'


@pytest.fixture
def work():
    path=Path(tempfile.mkdtemp(prefix='test-scene-review-',dir=JOBS)).resolve()
    yield path
    assert path.parent==JOBS.resolve() and path.name.startswith('test-scene-review-')
    shutil.rmtree(path)


def test_failed_contact_is_published_with_unchanged_scene_and_assets(work):
    output=work.with_name(work.name+'-packet')
    try:
        build(STUDY,AUDIT,ENGINE,output,'Failure preserved')
        candidate=read(output/'candidate.json');source=read(output/'source.json')
        original=read(STUDY/'authored-scene.json')
        assert candidate['scene']['contacts']==source['scene']['contacts']==original['contacts']
        assert candidate['scene']['objects']==source['scene']['objects']==original['objects']
        assert candidate['region_fit']['contact_failures']==1
        assert candidate['region_fit']['contact_geometry_passed'] is False
        assert read(output/'pipeline.json')['quality_approved'] is False
        assert sha256(output/'candidate/actor.glb')==sha256(STUDY/'candidate.glb')
        for p,digest in read(output/'provenance.json')['files'].items():assert sha256(output/p)==digest
        for row in read(output/'manifest.json')['scenes']:
            for link in row['downloads']:
                url='/files/scene-region-jobs/'+output.name+'/'+link['path']
                assert allowed_file(url)==output/link['path'] and (output/link['path']).is_file()
        with pytest.raises(ValueError):build(STUDY,AUDIT,ENGINE,output,'Existing')
    finally:
        assert output.parent==JOBS.resolve() and output.name.startswith('test-scene-review-')
        if output.exists():shutil.rmtree(output)


def test_wrong_engine_or_audit_binding_is_rejected(work):
    engine=read(ENGINE);engine['checks']=[];save(work/'engine.json',engine)
    with pytest.raises(ValueError,match='engine evidence'):verified_study(STUDY,AUDIT,work/'engine.json')
    engine=read(ENGINE)
    for check in engine['checks']:check['frames']=1
    save(work/'engine.json',engine)
    with pytest.raises(ValueError,match='full-frame engine evidence'):verified_study(STUDY,AUDIT,work/'engine.json')
    audit=read(AUDIT);audit['result_sha256']='0'*64;save(work/'audit.json',audit)
    with pytest.raises(ValueError,match='matching independent audit'):verified_study(STUDY,work/'audit.json',ENGINE)


def test_changed_export_is_rejected(work):
    folder=work/'copy';folder.mkdir()
    for name in ['result.json','protocol.json','authored-scene.json','recipe.json','source.glb','candidate.glb','motion.npz']:
        shutil.copyfile(STUDY/name,folder/name)
    with (folder/'candidate.glb').open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='artifact changed'):verified_study(folder,AUDIT,ENGINE)


def test_wrong_rate_report_and_output_location_do_not_publish(work):
    save(work/'rates.json',dict(result_sha256='0'*64))
    output=work.with_name(work.name+'-rejected')
    with pytest.raises(ValueError,match='another fit'):
        build(STUDY,AUDIT,ENGINE,output,'Bad rates',work/'rates.json')
    assert not output.exists()
    with pytest.raises(ValueError,match='review directory'):
        build(STUDY,AUDIT,ENGINE,work/'nested','Wrong location')
    assert not (work/'nested').exists()
