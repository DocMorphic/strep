import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from test_paired_hand_fit import setup
from paired_hand_fit import PairFitter
from paired_hand_clearance import SurfaceObjective,SkinPoints
from paired_finger_fit import FingerHandActor,expand_arm_seed,contact_pair
from build_soma_preview import ASSET


def finger_setup():
    old,scene=setup();faces=np.load(ASSET)['faces']
    actors=[FingerHandActor(a.rig,a.local,a.hand,int(a.vertices[a.palm]),faces,scene['actors'][name]['transform']) for a,name in zip(old,['A','B'])]
    return actors,old


def test_finger_coordinates_preserve_arm_seed_and_independent_skin():
    actors,old=finger_setup();values=np.random.default_rng(135).normal(size=24)*.02
    x=expand_arm_seed(values,actors)
    for i,(a,b) in enumerate(zip(actors,old)):
        actual=a.pose(75,x[i*a.dim:(i+1)*a.dim]);expected=b.pose(75,values[i*12:(i+1)*12])
        np.testing.assert_allclose(actual,expected,atol=1e-12)
        assert a.dim==69 and len(a.nodes)==23
        ids=np.array([14712,1427,14945]);p,_=SkinPoints(a).evaluate(75,x[i*a.dim:(i+1)*a.dim],ids)
        np.testing.assert_allclose(p,a.rig.vertices(actual)[ids]@a.rotation.T+a.translation,atol=1e-10)


def test_finger_contact_and_surface_derivatives_include_downstream_motion():
    actors,_=finger_setup();fitter=PairFitter(*actors,event=75)
    x=np.random.default_rng(156).normal(size=len(fitter.bounds))*.01
    records=[dict(source=a,target=b,points=[(14712,[1427,14945,14712],[.2,.3,.5],[0.,1.,0.]),
        (14945,[14712,1427,14945],[.1,.6,.3],[1.,0.,0.])]) for a,b in [(0,1),(1,0)]]
    objective=SurfaceObjective(fitter,records,margin=2.)
    _,jac=objective.pair(x);_,contact_jac=contact_pair(fitter,x)
    assert np.linalg.norm(jac[-4:,12:69])>0 and np.linalg.norm(jac[-4:,81:])>0
    for col in range(len(x)):
        delta=np.eye(len(x))[col]*1e-7
        numeric=(objective.pair(x+delta)[0]-objective.pair(x-delta)[0])/2e-7
        np.testing.assert_allclose(jac[:,col],numeric,atol=5e-5,rtol=3e-4)
        numeric_contact=(contact_pair(fitter,x+delta)[0]-contact_pair(fitter,x-delta)[0])/2e-7
        np.testing.assert_allclose(contact_jac[:,col],numeric_contact,atol=5e-7,rtol=3e-4)
