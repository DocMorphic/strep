import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from imported_skin_evidence import compare_surface


def fixture():
    positions = np.array([[0.,0,0],[0,0,0],[1,0,0]])
    weights = np.array([[1.,0],[0,1],[.4,.6]])
    inverse = np.tile(np.eye(4),(2,1,1)); inverse[1,0,3] = .25
    # Vertex order and bind order both differ; coincident source positions
    # deliberately carry distinct skinning. Duplicate influences accumulate.
    matrix = lambda m: np.vstack([m[:3,:3].T,m[:3,3]]).tolist()
    observed = dict(positions=positions[[1,2,0]].tolist(),
        bones=[0,1,1,0,0,0,0,0]*3,
        weights=[1.,0,0,0,0,0,0,0, .6,.1,.3,0,0,0,0,0, 0,1,0,0,0,0,0,0],
        binds=[dict(bone='B',pose=matrix(inverse[1])),dict(bone='A',pose=matrix(inverse[0]))])
    return positions,weights,['A','B'],inverse,observed


def test_reordered_vertices_binds_and_coincident_distinct_weights():
    args = fixture(); result = compare_surface(*args)
    assert result['passed'] and result['source_vertex_coverage'] and result['influences'] == 8
    assert result['maximum_bind_matrix_error'] == 0 and result['maximum_rest_position_error_m'] == 0
    assert result['maximum_effective_weight_error'] < 1e-15


@pytest.mark.parametrize('fault',['bind','position','weight','missing_duplicate'])
def test_deformation_evidence_changes_fail_without_relaxing_limits(fault):
    args = list(fixture()); observed = args[-1]
    if fault == 'bind': observed['binds'][0]['pose'][3][0] += .05
    elif fault == 'position': observed['positions'][1][0] += .001
    elif fault == 'weight': observed['weights'][0] -= .01; observed['weights'][1] += .01
    else:
        observed['positions'] = observed['positions'][1:]
        observed['bones'] = observed['bones'][8:]; observed['weights'] = observed['weights'][8:]
    assert not compare_surface(*args)['passed']


def test_16_bit_import_rounding_is_reported_with_bounded_tolerance():
    args = list(fixture()); args[1][-1] = [.413,.587]
    args[-1]['weights'][8:11] = [.587,.113,.3]
    values = np.array(args[-1]['weights'])
    args[-1]['weights'] = (np.round(values*65535)/65535).tolist()
    result = compare_surface(*args)
    assert result['passed'] and result['maximum_effective_weight_error'] > 0
    args[-1]['weights'][9] += .0001
    assert not compare_surface(*args)['passed']


@pytest.mark.parametrize('fault',['name','nan','bone','negative','layout'])
def test_invalid_skin_observations_rejected(fault):
    args = list(fixture()); observed = args[-1]
    if fault == 'name': observed['binds'][0]['bone'] = 'Unknown'
    elif fault == 'nan': observed['weights'][0] = float('nan')
    elif fault == 'bone': observed['bones'][0] = 2
    elif fault == 'negative': observed['weights'][0] = -.1
    else: observed['bones'] = observed['bones'][:-1]
    with pytest.raises(ValueError): compare_surface(*args)
