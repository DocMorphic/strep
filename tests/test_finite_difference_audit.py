import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from finite_difference_audit import audit


GROUPS = [dict(name='margin', start=0, stop=2, is_margin=True)]


def run(function, **kwargs):
    arguments = dict(point=np.zeros(2), steps=[1e-4, 1e-3], directions=[[1., -1.]],
                     radii=[2e-4], groups=GROUPS)
    arguments.update(kwargs)
    return audit(function, **arguments)


def test_affine_predictions_and_call_count():
    count = []
    result = run(lambda x: np.array([1., .1]) + np.array([[2., 3.], [4., -2.]]) @ x,
                 observe=count.append)
    assert result['evaluations'] == 10 == len(count)
    for step in result['steps']:
        group = step['groups'][0]
        assert group['forward_central_difference']['maximum_absolute'] < 1e-11
        assert all(p['residual']['maximum_absolute'] < 1e-12 for p in group['predictions'])
    assert not result['quality_approved']


def test_quantized_plateau_can_hide_a_negative_margin():
    result = run(lambda x: np.array([.0001, 1.]) - np.round(x, 3),
                 directions=[[1., 0.]], radii=[.0007])
    small = result['steps'][0]['groups'][0]['predictions']
    assert all(p['missed_negative_rows'] == 1 for p in small)
    large = result['steps'][1]['groups'][0]['predictions']
    assert all(p['missed_negative_rows'] == 0 for p in large)
    assert result['steps'][1]['groups'][0]['central_difference_from_previous_step']['maximum_absolute'] == pytest.approx(1.)


def test_nonsmooth_norm_has_forward_central_disagreement():
    result = run(lambda x: np.abs(x))
    assert result['steps'][0]['groups'][0]['forward_central_difference']['maximum_absolute'] == pytest.approx(1.)


@pytest.mark.parametrize('change', [dict(point=[1., 0.]), dict(steps=[0.]), dict(steps=[.1, .01]),
    dict(radii=[float('nan')]), dict(directions=[[0., 0.]]), dict(directions=[[1.]]),
    dict(directions=[[1e6, 0.]]), dict(groups=[]),
    dict(groups=[dict(name='bad', start=1, stop=2, is_margin=True)])])
def test_invalid_configuration_rejected(change):
    with pytest.raises(ValueError): run(lambda x: x, **change)


@pytest.mark.parametrize('function', [lambda x: [float('nan'), 0.], lambda x: [[0., 0.]],
    lambda x: [0.] if np.any(x) else [0., 0.]])
def test_invalid_or_changing_output_rejected(function):
    with pytest.raises(ValueError): run(function)
