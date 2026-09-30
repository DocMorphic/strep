"""Local licensed-fixture binding checks; no regeneration or animator approval."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read, save
from package_paired_correction import verified_variant

STUDY = ROOT/'reports/coupled-pair-refreshed-v1'
GEOMETRY = ROOT/'reports/coupled-pair-refreshed-geometry-v1'
ENGINE = ROOT/'reports/coupled-pair-refreshed-engine-v1'
SCENE = ROOT/'reports/paired-pose-posture-v1/body_fit_posture-seed-1301.json'
pytestmark = pytest.mark.skipif(not (STUDY/'result.json').exists(), reason='Local licensed development pair required')


def test_exact_exports_and_failed_samples_are_retained():
    actors, summary, inputs = verified_variant(STUDY, GEOMETRY, ENGINE, SCENE)
    assert set(actors) == {'A', 'B'}
    assert summary['pairs'][0]['frames_over_tolerance'] == 24
    assert len(summary['frames_checked']) == 57
    assert summary['quality_approved'] is False
    assert str(SCENE) in inputs


def test_unbound_engine_evidence_cannot_approve_the_pair(tmp_path):
    data = read(ENGINE/'verification.json'); data['checks'] = []
    save(tmp_path/'verification.json', data)
    with pytest.raises(ValueError, match='engine evidence differ'):
        verified_variant(STUDY, GEOMETRY, tmp_path, SCENE)


def test_another_scene_placement_is_rejected(tmp_path):
    data = read(SCENE); data['scene']['actors']['B']['transform']['translation_m'][0] += 1
    save(tmp_path/'scene.json', data)
    with pytest.raises(ValueError, match='placement'):
        verified_variant(STUDY, GEOMETRY, ENGINE, tmp_path/'scene.json')


def test_mutated_geometry_samples_are_rejected(tmp_path):
    for name in ['request.json', 'verification.json', 'samples.json']:
        save(tmp_path/name, read(GEOMETRY/name))
    rows = read(tmp_path/'samples.json'); rows['rows'][0]['candidate_depth_m'] = 1
    save(tmp_path/'samples.json', rows)
    with pytest.raises(ValueError, match='geometry audit'):
        verified_variant(STUDY, tmp_path, ENGINE, SCENE)
