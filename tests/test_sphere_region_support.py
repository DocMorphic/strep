import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_sphere_region_support import contact_triangle, declared_azimuths
from audit_sphere_region import triangle_audit


def test_region_requires_spread_area_and_world_target_locality():
    limits = dict(clearance_m=.002, contact_gap_m=.003, spacing_m=.006, area_m2=.000025, centroid_error_m=.005, local_radius_m=.020)
    points = np.array([[-.004, -.003, .0021], [.004, -.003, .0021], [0, .005, .0021]])
    chosen = contact_triangle(points, np.array([5, 6, 7]), np.zeros(3), np.full(3, .0021), limits)
    assert chosen and chosen['area_m2'] > limits['area_m2'] and chosen['vertices'] == [5, 6, 7]
    assert contact_triangle(points+np.array([.01, 0, 0]), np.array([5, 6, 7]), np.zeros(3), np.full(3, .0021), limits) is None
    assert contact_triangle(points*.1, np.array([5, 6, 7]), np.zeros(3), np.full(3, .0021), limits) is None
    assert contact_triangle(points, np.array([5, 6, 7]), np.zeros(3), np.array([.0021, .001, .0021]), limits) is None


def test_explicit_azimuths_preserve_defaults_and_reject_invalid_trials():
    assert declared_azimuths(None, 9.5) == list(range(0, 360, 45))
    assert declared_azimuths([337.5], 9.5) == [337.5]
    for values, tilt in [([0, 0], 9.5), ([360], 9.5), ([-1], 9.5), ([np.nan], 9.5), ([], 9.5), ([337.5], 0)]:
        with pytest.raises(ValueError): declared_azimuths(values, tilt)


def test_scalar_audit_agrees_on_selection_and_failure_with_varied_geometry():
    limits = dict(clearance_m=.002, contact_gap_m=.003, spacing_m=.006, area_m2=.000025, centroid_error_m=.005, local_radius_m=.020)
    rng = np.random.default_rng(722); passes = 0; failures = 0
    for _ in range(40):
        points = rng.uniform(-.01, .01, (9, 3)); points[:, 2] = .0021
        gaps = rng.uniform(.0018, .0032, len(points)); ids = np.arange(20, 29)
        generated = contact_triangle(points, ids, np.zeros(3), gaps, limits)
        audited, diagnostic = triangle_audit(points, ids, np.zeros(3), gaps, limits)
        assert generated == audited
        passes += generated is not None; failures += generated is None
    assert passes and failures
