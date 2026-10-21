"""Full sampled populations and source binding; fixtures are not motion evidence."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_support_preflight import analyze, SCHEMA


def fixture():
    rig=SimpleNamespace(primitives=[{'positions':np.zeros((2,3))}],
        vertices=lambda t:np.array([[t*.04,.001,0.],[t*.04,.001,.002]]))
    reader=SimpleNamespace(duration=1.,channels=[(0,'rotation',np.array([0.,.5,1.]),None,None)],sample=lambda t:t)
    spec=dict(schema=SCHEMA,glb_sha256='bound',animation_index=0,supports=[dict(id='foot',vertex_ids=[0,1],interval_s=[0.,1.],
        target_xyz_m=[0.,0.,.001],plane=dict(normal_xyz=[0.,1.,0.],offset_m=0.),clearance_m=.001,horizontal_tolerance_m=.003,maximum_vertex_displacement_m=.03)])
    return rig,reader,spec


def test_decoded_complete_population_proves_late_conflict_without_approving_motion():
    rig,reader,spec=fixture();original=copy.deepcopy(spec)
    result=analyze(rig,reader,spec,'bound');row=result['supports'][0]
    assert result['status']=='incompatible_support_target'
    assert len(row['observations'])==121
    assert all(o['vertices']==2 for o in row['observations'])
    assert row['worst_conflict']['time_s']==1.
    assert row['worst_conflict']['minimum_required_vertex_max_displacement_m']==pytest.approx(.037)
    assert spec==original and not result['feasibility_proven'] and not result['release_approved']


def test_inclusive_fractional_interval_endpoints_and_disjoint_contact_windows():
    rig,reader,spec=fixture();spec['supports'][0]['interval_s']=[.123,.223]
    other=copy.deepcopy(spec['supports'][0]);other.update(id='late',interval_s=[.951,.999])
    spec['supports'].append(other);result=analyze(rig,reader,spec,'bound')
    a,b=result['supports']
    assert a['incompatible_samples']==0 and b['incompatible_samples']>0
    for r in (a,b):
        assert [r['observations'][i]['time_s'] for i in (0,-1)]==r['interval_s']
        assert all(r['interval_s'][0]<=o['time_s']<=r['interval_s'][1] for o in r['observations'])


@pytest.mark.parametrize('kind',['hash','bool_index','duplicate_ids','missing_vertex','duplicate_name','backwards','missing_field','bad_plane'])
def test_malformed_or_unbound_spec_rejected(kind):
    rig,reader,spec=fixture();row=spec['supports'][0]
    if kind=='hash':spec['glb_sha256']='changed'
    elif kind=='bool_index':spec['animation_index']=False
    elif kind=='duplicate_ids':row['vertex_ids']=[0,0]
    elif kind=='missing_vertex':row['vertex_ids']=[2]
    elif kind=='duplicate_name':spec['supports'].append(copy.deepcopy(row))
    elif kind=='backwards':row['interval_s']=[1.,0.]
    elif kind=='missing_field':del row['maximum_vertex_displacement_m']
    elif kind=='bad_plane':row['plane']['normal_xyz']=[0,2,0]
    with pytest.raises(ValueError):analyze(rig,reader,spec,'bound')


def test_nonfinite_mesh_cannot_be_dropped_from_population():
    rig,reader,spec=fixture();rig.vertices=lambda t:np.array([[0.,0.,0.],[float('nan'),0.,0.]])
    with pytest.raises(ValueError,match='Complete finite'):analyze(rig,reader,spec,'bound')
