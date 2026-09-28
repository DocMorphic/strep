import numpy as np
from test_paired_palm_region import make
from paired_finger_region import FingerRegionActor
from paired_finger_fit import expand_arm_seed
from paired_palm_region import RegionFitter,CorrespondenceEvaluator


def make_fingers():
    original,skin=make()
    actors=[FingerRegionActor(a.rig,a.local,a.hand,14712,skin['faces'],
        dict(rotation_xyzw=[0,0,0,1],translation_m=[i*.3,0,0]),patch=a.patch)
        for i,a in enumerate(original.actors)]
    return original,RegionFitter(*actors,event=75),skin


def test_expanded_seed_preserves_pose_and_arm_budgets():
    original,fitter,_=make_fingers()
    seed=np.random.default_rng(34).normal(size=24)*.01
    expanded=expand_arm_seed(seed,fitter.actors)
    assert expanded.shape==(138,)
    for i,(a,b) in enumerate(zip(original.actors,fitter.actors)):
        np.testing.assert_array_equal(a.pose(75,seed[i*12:(i+1)*12]),b.pose(75,expanded[i*69:(i+1)*69]))
        np.testing.assert_array_equal(original.bounds[i*12:(i+1)*12],fitter.bounds[i*69:i*69+12])
        assert not expanded[i*69+12:(i+1)*69].any()
    np.testing.assert_array_equal(original.envelope,fitter.envelope)


def test_all_finger_region_derivatives():
    _,fitter,skin=make_fingers();x=np.random.default_rng(52).normal(size=138)*.01
    # Use vertices driven by distal fingers, so finger columns are exercised.
    from target_rig_contact import SkinEvaluator
    actor=fitter.actors[0];nodes,_,weights=SkinEvaluator(actor.rig).parts[0]
    dominant=nodes[np.arange(len(nodes)),np.argmax(weights,axis=1)]
    ids=[int(np.flatnonzero(dominant==node)[0]) for node in actor.nodes[4:] if np.any(dominant==node)]
    triangles=np.asarray(skin['faces'])[np.linspace(0,len(skin['faces'])-1,len(ids),dtype=int)]
    records=[dict(source=i,target=1-i,points=[(v,t.tolist(),[.2,.3,.5],[0.,1.,0.]) for v,t in zip(ids,triangles)]) for i in (0,1)]
    evaluator=CorrespondenceEvaluator(fitter,records)
    for fn in [fitter.objective_pair,evaluator.contact,evaluator.clearance]:
        _,jac=fn(x)
        for col in range(138):
            d=np.zeros(138);d[col]=1e-7
            numeric=(fn(x+d)[0]-fn(x-d)[0])/2e-7
            np.testing.assert_allclose(jac[:,col],numeric,atol=3e-5,rtol=3e-4)
