import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_sphere_region_support import contact_triangle


def test_region_requires_spread_area_and_world_target_locality():
    limits = dict(clearance_m=.002, contact_gap_m=.003, spacing_m=.006, area_m2=.000025, centroid_error_m=.005, local_radius_m=.020)
    points = np.array([[-.004, -.003, .0021], [.004, -.003, .0021], [0, .005, .0021]])
    chosen = contact_triangle(points, np.array([5, 6, 7]), np.zeros(3), np.full(3, .0021), limits)
    assert chosen and chosen['area_m2'] > limits['area_m2'] and chosen['vertices'] == [5, 6, 7]
    assert contact_triangle(points+np.array([.01, 0, 0]), np.array([5, 6, 7]), np.zeros(3), np.full(3, .0021), limits) is None
    assert contact_triangle(points*.1, np.array([5, 6, 7]), np.zeros(3), np.full(3, .0021), limits) is None
    assert contact_triangle(points, np.array([5, 6, 7]), np.zeros(3), np.array([.0021, .001, .0021]), limits) is None
