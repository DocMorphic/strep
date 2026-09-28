from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read, save
from authored_root_correction import export, load_motion
from verify_authored_root_correction import inspect, preserved_channels


JOB = ROOT/'reports/rig-jobs/20260926-195612-5047106e'
STUDY = ROOT/'reports/authored-root-correction-v1'


def test_fresh_export_passes_independent_target_and_geometry_checks():
    policy = read(STUDY/'request.json')['policy']
    candidate = STUDY/JOB.name/'candidate-1.0.glb'
    result = inspect(JOB/'corrected/character.glb', candidate, JOB/'transfer/character.glb',
                     JOB/'contact-spec.json', 180, policy)
    assert result['all_checks_passed']
    assert result['root_peak_after_m_s2'] < result['root_peak_before_m_s2']


def test_root_shift_cannot_silently_break_authored_intent(tmp_path):
    rig, _ = load_motion(JOB/'corrected/character.glb', 180)
    offsets = np.zeros((180, 3))
    offsets[:, 0] = .1
    candidate = tmp_path/'bad.glb'
    export(rig, 3, offsets, candidate)
    result = inspect(JOB/'corrected/character.glb', candidate, JOB/'transfer/character.glb',
                     JOB/'contact-spec.json', 180, read(STUDY/'request.json')['policy'])
    assert not result['all_checks_passed']
    assert not result['checks']['targets']
    assert not result['checks']['root_radius']
    assert not result['checks']['endpoints']


def test_changed_rotation_channel_is_detected():
    source, _ = load_motion(JOB/'corrected/character.glb', 180)
    candidate, _ = load_motion(JOB/'corrected/character.glb', 180)
    animation = candidate.document['animations'][0]
    channel = next(c for c in animation['channels'] if c['target']['path'] == 'rotation')
    animation['samplers'][channel['sampler']]['interpolation'] = 'STEP'
    assert not preserved_channels(source, candidate, 3)


def test_surface_guard_rejects_previous_root_only_tradeoff_in_inactive_patch(tmp_path):
    job = ROOT/'reports/rig-jobs/20260926-210755-7717c78e'
    candidate = STUDY/job.name/'candidate-1.0.glb'
    policy = read(STUDY/'request.json')['policy']
    spec = read(job/'contact-spec.json')
    assert 'A-left-heel' in spec['patches']
    # Make a test-only recipe with this patch declared but inactive. Never
    # modify the actual authored recipe or pretend it originally was inactive.
    spec['contacts'] = [c for c in spec['contacts'] if c['patch'] != 'A-left-heel']
    recipe = tmp_path/'inactive-patch.json'
    save(recipe, spec)
    # v1's recorded policy remains v1. The new guard must detect its known
    # tradeoff even for a patch with no active target interval.
    policy['preserve_patch_acceleration'] = True
    result = inspect(job/'corrected/character.glb', candidate, job/'transfer/character.glb',
                     recipe, 133, policy)
    assert not result['checks']['whole_clip_patch_acceleration']
    assert not result['all_checks_passed']
    heel = next(p for p in result['patch_dynamics'] if p['patch'] == 'A-left-heel')
    assert heel['frame_cap_excess_m_s2'] > 5
