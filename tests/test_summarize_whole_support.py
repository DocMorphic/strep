from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from summarize_whole_support import population


def test_failures_and_pending_remain_in_denominator():
    cases=[dict(id=str(i)) for i in range(4)]
    rows=[dict(id=str(i),status=s) for i,s in enumerate(['complete','failed','pending','verified_pending_engine'])]
    assert population(cases,rows)==dict(planned=4,complete=1,failed=1,pending=2)


@pytest.mark.parametrize('rows',[
    [dict(id='a',status='complete')],
    [dict(id='a',status='complete'),dict(id='a',status='complete')],
    [dict(id='a',status='complete'),dict(id='c',status='complete')],
    [dict(id='a',status='complete'),dict(id='b',status='made_up')],
])
def test_dropped_duplicate_unexpected_or_unknown_rows_rejected(rows):
    with pytest.raises(ValueError):population([dict(id='a'),dict(id='b')],rows)
