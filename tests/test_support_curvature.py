from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_curvature import root_curvature_pair,root_curvature_energy


@pytest.mark.parametrize('frame',[0,1,4,7,8])
def test_coordinate_energy_change_matches_full_track_and_derivative(frame):
    rng=np.random.default_rng(5201);values=rng.normal(0,.02,(9,9));candidate=values[frame]+rng.normal(0,.01,9)
    old,_=root_curvature_pair(values,frame,values[frame],30.)
    residual,jac=root_curvature_pair(values,frame,candidate,30.)
    altered=values.copy();altered[frame]=candidate
    assert float(residual@residual-old@old)==pytest.approx(root_curvature_energy(altered,30.)-root_curvature_energy(values,30.),abs=1e-12)
    eps=1e-7;identity=np.eye(len(candidate))
    numerical=np.column_stack([(root_curvature_pair(values,frame,candidate+eps*d,30.)[0]-root_curvature_pair(values,frame,candidate-eps*d,30.)[0])/(2*eps) for d in identity])
    np.testing.assert_allclose(jac,numerical,atol=1e-8)
    assert np.array_equal(jac[:,3:],np.zeros_like(jac[:,3:]))


def test_constant_velocity_correction_has_zero_curvature_and_weight_zero_is_control():
    values=np.arange(10)[:,None]*np.array([[.01,.02,-.03,0,0,0]])
    assert root_curvature_energy(values,30.)<1e-25
    residual,jac=root_curvature_pair(values,4,values[4]+.1,0.)
    assert not residual.any() and not jac.any()


def test_nonfinite_parameters_or_weight_are_rejected():
    values=np.zeros((9,6))
    for weight in [-1,float('nan')]:
        with pytest.raises(ValueError):root_curvature_pair(values,4,values[4],weight)
    values[1,0]=float('nan')
    with pytest.raises(ValueError):root_curvature_pair(values,4,np.zeros(6),30.)
