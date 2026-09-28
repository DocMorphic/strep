import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from test_paired_hand_fit import setup
from paired_palm_region import region,RegionActor,RegionFitter,CorrespondenceEvaluator,contact_records
from build_soma_preview import ASSET


def make():
    old,_=setup();skin=dict(np.load(ASSET,allow_pickle=False));patch=region(skin,'LeftHand')
    actors=[RegionActor(a.rig,a.local,a.hand,14712,skin['faces'],dict(rotation_xyzw=[0,0,0,1],translation_m=[i*.3,0,0]),patch=patch) for i,a in enumerate(old)]
    return RegionFitter(*actors,event=75),skin


def test_patch_orientation_contact_and_inequality_jacobians():
    fitter,skin=make();x=np.random.default_rng(221).normal(size=24)*.01
    records=[dict(source=i,target=1-i,points=[(14712,[1427,1428,14712],[.2,.3,.5],[0.,1.,0.])]) for i in (0,1)]
    evaluator=CorrespondenceEvaluator(fitter,records)
    for fn in [fitter.objective_pair,evaluator.contact,evaluator.clearance]:
        residual,jac=fn(x)
        for col in range(24):
            d=np.eye(24)[col]*1e-7
            numeric=(fn(x+d)[0]-fn(x-d)[0])/2e-7
            np.testing.assert_allclose(jac[:,col],numeric,atol=3e-5,rtol=3e-4)
    # Outward displacement makes a signed clearance constraint more feasible.
    delta,jac=evaluator.clearance(x)
    direction=jac[0]/np.linalg.norm(jac[0])
    assert evaluator.clearance(x+direction*1e-5)[0][0]>delta[0]


def test_contact_correspondences_stay_in_declared_patches_and_are_separated():
    fitter,skin=make();x=np.zeros(24)
    records,metrics=contact_records(fitter.actors,75,x,skin['faces'])
    assert len(records)==2
    for r,m in zip(records,metrics):
        a=fitter.actors[r['source']];b=fitter.actors[r['target']]
        allowed={tuple(face) for face in skin['faces'][b.patch['face_ids']]}
        p=a.rig.vertices(a.pose(75,x[:12]))@a.rotation.T+a.translation
        ids=[]
        for vertex,tri,bary,normal in r['points']:
            assert vertex in a.patch['vertices'] and tuple(tri) in allowed
            assert min(bary)>-1e-7 and abs(sum(bary)-1)<1e-7
            ids.append(vertex)
        assert len(ids)==3 and min(np.linalg.norm(p[i]-p[j]) for i,j in [(ids[0],ids[1]),(ids[0],ids[2]),(ids[1],ids[2])])>=.006
        assert len(m['distances_m'])==3
