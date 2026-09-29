from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_pose_preflight import analyze,describe


@pytest.fixture
def fixture(monkeypatch):
    import floor_contact,contact_spec,support_contact,inspect_motion
    class Surface:
        def __init__(self,skin):
            self.inverse=np.eye(4)[None]
            self.indices=np.zeros((1,8),dtype=int)
            self.weights=np.array([[1.,0,0,0,0,0,0,0]])
            self.points=np.array([[0.,0,0,1.]])
    monkeypatch.setattr(floor_contact,'Surface',Surface)
    monkeypatch.setattr(contact_spec,'validate',lambda *args:None)
    monkeypatch.setattr(support_contact,'regions',lambda skin:{})
    monkeypatch.setattr(inspect_motion,'validate_motion',lambda *args:None)
    motion=dict(root_positions=np.zeros((2,3)),posed_joints=np.zeros((2,1,3)))
    spec=dict(schema_version=1,fps=30,frame_count=2,regions={'LeftFoot':dict(mode='explicit',segments=[
        dict(start_frame=0,end_frame=0,vertex_id=0,space='world',position_m=[.2,.2,0])])})
    return dict(raw=motion,limb=motion),{},spec


def test_diagonal_conflict_reaches_preflight_and_readable_explanation(fixture):
    references,skin,spec=fixture
    report=analyze(references,skin,spec)
    assert report['status']=='incompatible_with_pose_screen'
    assert report['conflicting_frame_reference_pairs']==2
    assert all(not any(a['conflict_verified'] for a in row['axes']) for row in report['rows'])
    assert all(row['sphere']['conflict_verified'] for row in report['rows'])
    assert report['worst']['joint_displacement_lower_bound_m']>.27
    assert '22.00 cm' in describe(report) and not report['quality_approved']


def test_nonconflict_stays_unproven_and_request_is_unchanged(fixture):
    import copy
    references,skin,spec=fixture;spec['regions']['LeftFoot']['segments'][0]['position_m']=[.02,.02,0]
    before=copy.deepcopy(spec)
    report=analyze(references,skin,spec)
    assert report['status']=='not_ruled_out' and report['conflicting_frame_reference_pairs']==0
    assert 'does not establish' in describe(report) and spec==before


def test_axis_certificate_is_preserved(fixture):
    references,skin,spec=fixture;spec['regions']['LeftFoot']['segments'][0]['position_m']=[.5,0,0]
    report=analyze(references,skin,spec)
    assert report['conflicting_frame_reference_pairs']==2
    assert all(row['axes'][0]['conflict_verified'] for row in report['rows'])
