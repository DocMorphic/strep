import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_kneel_start_study import condition_bindings
from strep import ROOT, read


def test_saved_legacy_study_labels_and_guides_still_bind():
    plan = ROOT / 'reports/kneel-timed-phases-plan-v1'
    protocol = read(plan / 'protocol.json')
    batch = read(ROOT / protocol['request'])
    snapshot = read(plan / 'compiled-guides.json')
    labels, guides = condition_bindings(protocol, batch, snapshot)
    assert labels == {'kneel-baseline': 'baseline', 'kneel-upright-start': 'upright-start'}
    assert guides['kneel-baseline'] == []
    assert guides['kneel-upright-start'] == snapshot['constraints']


def setup_pair():
    protocol = dict(conditions=['final-frame', 'held-ending'], seed_pairs=[1, 2],
                    condition_by_request={'end-one': 'final-frame', 'end-hold': 'held-ending'})
    batch = dict(requests=[dict(id='end-one', seeds=[1, 2]), dict(id='end-hold', seeds=[1, 2])])
    snapshot = dict(by_request={'end-one': dict(constraints=[{'frame_indices': [0, 179]}]),
                                'end-hold': dict(constraints=[{'frame_indices': [0, 170, 179]}])})
    return protocol, batch, snapshot


def test_two_guided_conditions_are_not_mislabeled_as_no_guide():
    labels, guides = condition_bindings(*setup_pair())
    assert set(labels.values()) == {'final-frame', 'held-ending'}
    assert all(guides.values())


@pytest.mark.parametrize('mutation', ['swapped_labels', 'missing_guides', 'different_seeds'])
def test_mismatched_experiment_bindings_fail(mutation):
    protocol, batch, snapshot = copy.deepcopy(setup_pair())
    if mutation == 'swapped_labels':
        protocol['conditions'].reverse()
    elif mutation == 'missing_guides':
        del snapshot['by_request']['end-hold']
    else:
        batch['requests'][1]['seeds'] = [2, 3]
    with pytest.raises(ValueError):
        condition_bindings(protocol, batch, snapshot)
