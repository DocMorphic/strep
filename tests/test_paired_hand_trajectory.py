import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from strep import ROOT,read
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from target_rig_contact import baseline
from build_soma_preview import ASSET
from paired_palm_region import RegionActor,region
from paired_hand_trajectory import TrajectoryFitter,TemporalSurface


def make():
    source=ROOT/'reports/paired-hand-prototype-v6';scene=read(source/'input-scene.json')['scene']
    skin=dict(np.load(ASSET,allow_pickle=False));patch=region(skin,'LeftHand');actors=[]
    for name in ['A','B']:
        rig=RigAsset.load(source/'input'/name/'character.glb');_,local=baseline(rig,150)
        actors.append(RegionActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],skin['faces'],scene['actors'][name]['transform'],patch=patch))
    return TrajectoryFitter(actors),skin


def test_constant_controls_match_actual_export_at_integer_and_half_frames():
    fitter,_=make();values=read(ROOT/'reports/paired-palm-region-v5/parameters.json')['values'];x=fitter.expand(values)
    np.testing.assert_allclose(fitter.values(x),fitter.base.envelope[:,None]*values,atol=1e-15)
    assert fitter.step_pair(x)[0].min()>=0
    for i,name in enumerate(['A','B']):
        rig=RigAsset.load(ROOT/f'reports/paired-palm-region-export-v5/candidate/{name}/character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
        for frame in [60.,65.5,74.,74.5,75.,75.5,85.5,90.]:
            expected=sampler.sample(float(np.float32(frame/30)))
            actual=fitter.actors[i].pose(frame,x[i*36:(i+1)*36])
            np.testing.assert_allclose(actual,expected,atol=1e-6,rtol=0)


def test_fractional_surface_and_temporal_limit_derivatives():
    fitter,_=make();x=np.random.default_rng(237).normal(size=72)*.005
    records=[dict(source=i,target=1-i,points=[(14712,[1427,1428,14712],[.2,.3,.5],[0.,1.,0.])]) for i in [0,1]]
    surface=TemporalSurface(fitter,74.5,records)
    for fn in [surface.clearance,fitter.step_pair]:
        _,jac=fn(x)
        for col in range(72):
            d=np.zeros(72);d[col]=1e-5
            numeric=(fn(x+d)[0]-fn(x-d)[0])/2e-5
            np.testing.assert_allclose(jac[:,col],numeric,atol=1e-6,rtol=3e-4)
    np.testing.assert_array_equal(fitter.values(x)[fitter.base.envelope==0],0.)
    # An extreme alternating correction violates the existing adjacent limit.
    bad=np.zeros((2,3,12));bad[:,0,0]=1;bad[:,1,0]=-1
    assert fitter.step_pair(bad.ravel())[0].min()<0


def test_varying_controls_match_new_glb_interpolation(tmp_path):
    from rig_loop import encode
    fitter,_=make();actor=fitter.actors[0]
    controls=np.random.default_rng(920).normal(size=36)*.02
    frames=np.array([actor.pose(f,controls) for f in range(150)])
    rig=actor.rig;animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(actor.nodes)
    root=next(i for i,n in enumerate(rig.document['nodes']) if n.get('name')=='Hips')
    path=tmp_path/'varied.glb';encode(rig,frames,animated,root,path,'Varied trajectory test')
    result=RigAsset.load(path);sampler=AnimationSampler(result.document,result.binary,0)
    for frame in [64.5,74.5,75.5,80.25,89.5]:
        np.testing.assert_allclose(actor.pose(frame,controls),sampler.sample(float(np.float32(frame/30))),atol=1e-6,rtol=0)
