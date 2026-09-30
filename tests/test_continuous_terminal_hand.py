import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scipy.spatial.transform import Rotation
from test_decoded_motion_edges import rig_fixture
from continuous_terminal_hand import VectorTerminalMotion,HandWitnessObjective,solve
from native_waypoint_clock import guide_clock
from waypoint_lattice import LinearGuide
from wrist_waypoint_motion import bake
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


@pytest.mark.parametrize('actor',[0,1])
def test_oblique_vector_controls_match_actual_bake_and_frozen_suffix(actor,tmp_path):
    rig,clock=rig_fixture();rig.document['skins']=[dict(joints=rig.joints)]
    window=[.15,.5,.85];native=guide_clock([clock]*6,window,[]);times=np.arange(241)/120
    ids=np.flatnonzero((times>=native[-2])&(times<=native[-1]+.02))
    placement=Rotation.from_euler('y',37,degrees=True).as_matrix()
    model=VectorTerminalMotion(rig,[1,2,3],native[-3:],times[ids],[],placement,actor)
    controls=np.array([.0012,-.0007,.003,1.2,-1.1]);amount=np.linalg.norm(controls[:3]);axis=controls[:3]/amount
    parameters=np.zeros((len(native),3));parameters[-2]=np.r_[amount,controls[3:]];guide=LinearGuide(native,parameters,[.8,300,300])
    curve=lambda t:np.r_[axis*guide(t)[0]*(1 if actor==0 else -1),guide(t)[actor+1]]
    path=tmp_path/'candidate.glb';bake(rig,[1,2,3],[0,0,0],placement,0,window,[],path,control_curve=curve)
    doc,binary=read_glb(path);reader=AnimationSampler(doc,binary,0)
    world,maximum=model.evaluate_vector(controls)
    np.testing.assert_allclose(world,[reader.sample(t) for t in times[ids]],atol=2e-12,rtol=0)
    np.testing.assert_allclose(world[times[ids]>=native[-1]],model.model.source_world[times[ids]>=native[-1]],atol=2e-12,rtol=0)
    assert maximum>0
    np.testing.assert_array_equal(model.evaluate_vector(np.zeros(5))[0],model.model.source_world)
    with pytest.raises(ValueError):model.evaluate_vector([0,0,0,0])


def test_witness_objective_moves_both_surfaces_and_uses_global_skin_vertex_ids():
    skin=SimpleNamespace(evaluate=lambda w,f,v:w[f,v,:3,3])
    a=np.tile(np.eye(4),(1,4,1,1));b=a.copy();a[0,3,:3,3]=[.2,.2,-.02]
    b[0,:3,:3,3]=[[0,0,0],[1,0,0],[0,1,0]]
    row=dict(source=0,target=1,frame=0,vertex=3,target_vertices=[0,1,2],barycentric=[.6,.2,.2],normal=[0,0,1])
    placement=dict(rotation=np.eye(3),translation=np.array([10.,20.,30.]))
    objective=HandWitnessObjective([skin,skin],[placement,placement],[row])
    assert objective.gaps([a,b])[0]==pytest.approx(-.02)
    b[:,:,:3,3]+=[0,0,.01]
    assert objective.gaps([a,b])[0]==pytest.approx(-.03)
    a[:,:,:3,3]+=[0,0,.03]
    assert objective.gaps([a,b])[0]==pytest.approx(0,abs=1e-12)


def evaluate_toy(c):return max(0.,.01-c[0]),np.array([.004-c[0],c[0]+.04])


def test_continuous_search_retains_feasible_improvement_with_infeasible_start():
    scale=np.array([.04]*3+[15.]*2)
    best,reports,records=solve(evaluate_toy,scale,[np.zeros(5),np.array([.008,0,0,0,0])],iterations=25)
    assert 0<best['controls'][0]<=.004 and .006<=best['witness_peak_m']<.0061
    assert any(not r['motion_domain_feasible'] for r in records)
    assert len(reports)==2


def test_optimizer_success_and_false_epigraph_cannot_approve_infeasible_controls(monkeypatch):
    def fake(*args,**kwargs):return SimpleNamespace(x=np.array([.2,0,0,0,0,0.]),success=True,status=0,message='synthetic',nit=1,nfev=1)
    monkeypatch.setattr('continuous_terminal_hand.minimize',fake)
    best,reports,_=solve(lambda c:(max(0.,.01-c[0]),np.array([-abs(c[0])])),np.array([.04]*3+[15.]*2),[np.zeros(5)])
    assert best['controls']==[0.]*5 and best['witness_peak_m']==.01
    assert reports[0]['success'] and reports[0]['returned_minimum_margin']<0
    assert reports[0]['returned_epigraph_m']==0 and reports[0]['returned_witness_peak_m']>0



def test_eighty_four_control_solve_uses_final_component_and_preserves_hard_margin():
    def objective(c):return max(0.,.01-c[-1]),np.array([.004-c[-1],c[-1]+.04])
    best,reports,records=solve(objective,np.full(84,.04),[np.zeros(84)],iterations=25)
    assert len(best['controls'])==84 and 0<best['controls'][-1]<=.004
    assert .006<=best['witness_peak_m']<.0061
    assert reports and records and best['motion_domain_feasible']
