import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from verify_palm_region import measure,triangle_witness


def test_parallel_patch_contact_has_separated_area_and_opposing_normals():
    a=np.array([[-.01,-.01,0],[.01,-.01,0],[.01,.01,0],[-.01,.01,0]])
    b=a.copy();b[:,0]*=-1;b[:,2]=.001
    faces=np.array([[0,1,2],[0,2,3]]);patch=dict(vertices=[0,1,2,3],face_ids=[0,1])
    out=measure([a,b],[patch,patch],faces,.003)
    assert out['opposing_normal_degrees']<1e-6
    for d in out['directions']:
        assert d['within_tolerance_count']==4
        assert abs(d['minimum_distance_m']-.001)<1e-10
        assert d['source_area_witness']['area_m2']>=.0002-1e-12
        assert d['target_area_witness']['area_m2']>=.0002-1e-12
    b[:,2]=.004
    assert all(d['within_tolerance_count']==0 for d in measure([a,b],[patch,patch],faces,.003)['directions'])


def test_point_or_line_contact_is_not_area_coverage():
    assert triangle_witness(np.array([[0,0,0]]))['area_m2']==0
    assert triangle_witness(np.array([[0,0,0],[.01,0,0],[.02,0,0]]))['area_m2']==0
