import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sphere_approach import outward_clearance_shift


def test_shift_resolves_all_overlapping_forbidden_intervals():
    points=np.array([[.2,0,0],[-.1,0,0],[-.4,0,0]])
    # The last point starts safe but enters the sphere during the first escape.
    shift=outward_clearance_shift(points,np.zeros(3),[1,0,0],.25,.002)
    assert shift==pytest.approx(.652)
    assert (np.linalg.norm(points+[shift,0,0],axis=1)>=.252-1e-12).all()


def test_safe_patch_stays_unchanged_and_tangential_points_do_not_force_exit():
    points=np.array([[.3,0,0],[0,.3,0]])
    assert outward_clearance_shift(points,np.zeros(3),[1,0,0],.25,.002)==0
    points=np.array([[.2,0,0],[0,.3,0]])
    assert outward_clearance_shift(points,np.zeros(3),[1,0,0],.25,.002)==pytest.approx(.052)


@pytest.mark.parametrize('points,direction,radius,clearance',[(np.empty((0,3)),[1,0,0],.25,.002),([[np.nan,0,0]],[1,0,0],.25,.002),([[0,0,0]],[0,0,0],.25,.002),([[0,0,0]],[1,0,0],-.25,.002),([[0,0,0]],[1,0,0],.25,-.002)])
def test_invalid_geometry_rejected(points,direction,radius,clearance):
    with pytest.raises(ValueError):outward_clearance_shift(points,np.zeros(3),direction,radius,clearance)
