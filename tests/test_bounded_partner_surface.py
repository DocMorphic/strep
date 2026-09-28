import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import trimesh
import pytest
from audit_partner_surface import penetration as original
from bounded_partner_surface import penetration


def test_partitioned_query_matches_unpartitioned_depths_and_counts():
    mesh=trimesh.creation.icosphere(subdivisions=2,radius=1)
    points=np.random.default_rng(23).uniform(-1.2,1.2,(143,3))
    before=original(points,mesh.vertices,mesh.faces);after=penetration(points,mesh.vertices,mesh.faces)
    assert before.keys()==after.keys()
    for key in before:
        if key=='max_depth_m':assert after[key]==pytest.approx(before[key],abs=1e-12)
        else:assert before[key]==after[key]


def test_batches_never_exceed_32_and_keep_global_deepest_index(monkeypatch):
    mesh=trimesh.creation.box();points=np.zeros((97,3));points[:,0]=np.linspace(-.4,.4,97)
    original_signed=trimesh.proximity.signed_distance;calls=[]
    def observed(mesh,points):
        calls.append(len(points));return original_signed(mesh,points)
    monkeypatch.setattr(trimesh.proximity,'signed_distance',observed)
    result=penetration(points,mesh.vertices,mesh.faces)
    assert calls==[32,32,32,1]
    assert result['deepest_vertex']==48 and result['vertices_over_tolerance']==97
