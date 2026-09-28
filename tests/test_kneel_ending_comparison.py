import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_kneel_endings import validate_requests
from strep import ROOT, read


def requests():
    return (read(ROOT/'benchmarks/kneel-timed-phases-v1.json'),
            read(ROOT/'benchmarks/kneel-ending-guides-v1.json'))


def test_actual_prepared_comparison_changes_only_guide_timing():
    assert len(validate_requests(*requests())) == 3


@pytest.mark.parametrize('mutation',['text','seed','source','frames'])
def test_confounded_request_fails(mutation):
    start, ending = copy.deepcopy(requests())
    request = ending['requests'][1]
    if mutation == 'text':
        request['segments'][2]['prompt'] = 'Jump up.'
    elif mutation == 'seed':
        request['seeds'][0] = 9999
    elif mutation == 'source':
        request['generation_constraints'][0]['sha256'] = '0'*64
    else:
        request['generation_constraints'][0]['frame_indices'][-1] = 178
    with pytest.raises(ValueError):
        validate_requests(start,ending)
