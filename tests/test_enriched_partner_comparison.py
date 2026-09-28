from copy import deepcopy
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_enriched_partner_path import FIXED, protocol, changes
from contact_witness_clock import enrich


def curve(failures):
    clock = [i*.5 for i in range(299)]
    return dict(frames=clock, body_depth_m=[.02 if f in failures else 0. for f in clock], floor_depth_m=[.012]*299)


def audits():
    request = {k:0 for k in FIXED}
    request.update(frames=[45, 65, 75, 105], selection_screen=dict(max_sample_penetration_m=.005))
    assets = {'assets/'+a+'/raw/'+f:dict(sha256=a+f) for a in ['A', 'B'] for f in ['character.glb', 'motion.npz']}
    strict = dict(request=request, initial=dict(controls=[0]), manifest=dict(assets=assets),
                  variants=dict(raw=dict(curve=curve([67])), candidate=dict(curve=curve([66.5]))))
    screen = deepcopy(strict)
    screen['variants']['candidate']['curve'] = curve([66.5, 69.5])
    plan = enrich(request['frames'], dict(raw=strict['variants']['raw']['curve'], strict=strict['variants']['candidate']['curve'], screen=screen['variants']['candidate']['curve']))
    candidate = deepcopy(screen)
    candidate['request'].update(frames=plan['frames'], sampling_plan=plan)
    return strict, screen, candidate


def test_enriched_clock_allowed_without_changing_fixed_protocol():
    _, plan = protocol(*audits())
    assert 66.5 in plan['added_frames'] and 69.5 in plan['added_frames']


@pytest.mark.parametrize('fault', ['omit_witness', 'change_budget', 'change_screen', 'change_initial', 'change_raw_asset', 'change_raw_geometry'])
def test_comparison_rejects_confounded_or_incomplete_trial(fault):
    strict, screen, candidate = audits()
    if fault == 'omit_witness':
        candidate['request']['frames'].remove(69.5)
    if fault == 'change_budget':
        candidate['request']['iterations'] = 4
    if fault == 'change_screen':
        candidate['request']['selection_screen']['max_sample_penetration_m'] = .01
    if fault == 'change_initial':
        candidate['initial']['controls'] = [1]
    if fault == 'change_raw_asset':
        candidate['manifest']['assets']['assets/B/raw/character.glb']['sha256'] = 'different'
    if fault == 'change_raw_geometry':
        candidate['variants']['raw']['curve']['body_depth_m'][0] = .01
    with pytest.raises(ValueError):
        protocol(strict, screen, candidate)


def test_improved_peak_cannot_hide_new_collisions_outside_fit():
    before = curve([66.5])
    after = curve([])
    after['body_depth_m'][133] = .009
    after['body_depth_m'][140] = .006
    after['body_depth_m'][141] = .007
    result = changes(before, after, [66.5, 70])
    assert result['peak_change_m'] < 0
    assert result['newly_failing_frames'] == [70, 70.5]
    assert result['newly_failing_in_fit'] == [70]
    assert result['newly_failing_outside_fit'] == [70.5]
    assert result['floor_curve_unchanged']


def test_missing_geometry_cannot_be_summarized_as_success():
    before, after = curve([]), curve([])
    after['body_depth_m'].pop()
    with pytest.raises(ValueError):
        changes(before, after, [75])
