import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coupled_continuation_checkpoint import checkpoint


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value),encoding='utf-8')


def origin(tmp_path):
    folder=tmp_path/'origin';folder.mkdir();(folder/'linearization.npz').write_bytes(b'bound reference fixture')
    write(folder/'request.json',dict(inputs={},penetrating_surface_norms=True,fitting_reserve=str(tmp_path/'reserve')))
    write(folder/'solver.json',dict(controls=[.1,.2,.3],linearization_sha256=digest(folder/'linearization.npz')))
    write(folder/'result.json',dict(status='complete',selected=dict(factor=.5),request_sha256=digest(folder/'request.json'),solver_sha256=digest(folder/'solver.json')))
    return folder


def test_first_checkpoint_uses_its_selected_control_fraction(tmp_path):
    first=origin(tmp_path);state=checkpoint(first)
    assert state['origin']==first
    np.testing.assert_array_equal(state['controls'],np.array([.1,.2,.3])*.5)


def test_repeated_resume_keeps_original_reference_and_cumulative_controls(tmp_path):
    first=origin(tmp_path);previous=first
    for index in range(2):
        folder=tmp_path/f'resume-{index}';folder.mkdir();values=[.7+index,.8,.9]
        write(folder/'request.json',dict(inputs={},start=str(previous),origin=str(first),reserve=str(tmp_path/'reserve')))
        write(folder/'result.json',dict(status='complete',selected=dict(iteration=8),total_controls=values,request_sha256=digest(folder/'request.json')))
        state=checkpoint(folder)
        assert state['origin']==first
        np.testing.assert_array_equal(state['controls'],values)
        previous=folder


def test_changed_original_reference_is_rejected_on_resume(tmp_path):
    first=origin(tmp_path);(first/'linearization.npz').write_bytes(b'changed reference')
    with pytest.raises(ValueError,match='original full-vector'):
        checkpoint(first)
