import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import diagnostic_mesh_comparison as implementation


def stub(monkeypatch):
    monkeypatch.setattr(implementation,'audit',lambda *args:dict(left_faces=1,right_faces=1,records=[],counts={'disjoint':1},candidate_pairs=1,degenerate_faces=[[],[]],tolerance_m=1e-8))
    monkeypatch.setattr(implementation,'penetration',lambda a,b,f:dict(vertices_checked=len(a),max_depth_m=0.))


def test_even_passing_geometry_diagnostic_never_approves_motion(monkeypatch):
    stub(monkeypatch);saved={};seen=[]
    result=implementation.run([np.array([[0,1,2]])]*2,[3,3],[0.,1.],lambda label,i:[np.zeros((3,3))]*2,
        lambda name,row:saved.update({name:row}),seen.append)
    assert result['mesh_regression']['passed'] and result['diagnostic_only']
    assert not any(result[k] for k in ['accepted_for_publication','quality_approved','collision_free_certified','selected_for_studio'])
    assert len(seen)==4 and len(saved)==7
    assert all(label+'-geometry-01.json' in saved for label in ['baseline','rejected'])


def test_incomplete_mesh_population_cannot_be_audited(monkeypatch):
    stub(monkeypatch)
    with pytest.raises(ValueError,match='Complete finite'):
        implementation.run([np.array([[0,1,2]])]*2,[3,3],[0.],lambda *args:[np.zeros((2,3))]*2,lambda *args:None)


def test_clock_must_be_complete_and_ordered(monkeypatch):
    stub(monkeypatch)
    with pytest.raises(ValueError,match='clock'):
        implementation.run([np.array([[0,1,2]])]*2,[3,3],[1.,0.],lambda *args:[np.zeros((3,3))]*2,lambda *args:None)
