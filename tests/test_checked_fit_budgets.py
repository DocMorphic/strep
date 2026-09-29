import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from study_checked_point_scaling import run


@pytest.mark.parametrize('options', [dict(stages=0), dict(stages=True), dict(iterations=1001), dict(iterations=0)])
def test_invalid_budget_is_rejected_before_reading_or_creating_job(tmp_path, options):
    output = tmp_path/'never-created'
    with pytest.raises(ValueError, match='count|Iterations'):
        run('unused-check', output, tmp_path/'unused-control', **options)
    assert not output.exists()
