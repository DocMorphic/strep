import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from compare_restoration_scaling import validate_pair


def fixtures():
    return read(ROOT/'reports/frame-capped-restoration-v1/request.json'),read(ROOT/'reports/scaled-frame-restoration-v1/request.json')


def test_actual_matched_requests_are_compatible():
    validate_pair(*fixtures())


@pytest.mark.parametrize('key',['proof','proof_request_sha256','proof_completion_sha256','source','source_request_sha256','frames','maxiter','selection_screen','objective_scale','solver_ftol','method'])
def test_protocol_changes_cannot_be_compared_as_scaling_only(key):
    a,b=fixtures();b=copy.deepcopy(b);b[key]=None
    with pytest.raises(ValueError):validate_pair(a,b)
