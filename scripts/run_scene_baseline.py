"""Measure preserved box-lift/high-five outputs in explicitly authored scenes."""
import numpy as np
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from scene_constraints import evaluate


def actor(case,seed,name,position,rotation):
    folder=ROOT/'runs'/case/f'seed-{seed}'/'unprocessed'/f'actor-{name}'/'attempt-001'
    source=folder/'source/motion.npz';record=read(folder/'record.json')
    if sha256(source)!=record['source_motion_file_and_hash']['sha256']:raise ValueError('Raw motion provenance mismatch')
    return dict(motion=source.relative_to(ROOT).as_posix(),transform=dict(translation_m=position,rotation_xyzw=rotation))


def scenes(seed):
    lift=dict(schema_version=1,id=f'lift-box-seed-{seed}',fps=30,frame_count=180,
        actors=dict(A=actor('lift_box',seed,'A',[0,0,0],[0,0,0,1])),
        objects=dict(box=dict(shape='box',size_m=[.4,.4,.4],keyframes=[dict(frame=0,translation_m=[0,.2,.55],rotation_xyzw=[0,0,0,1])],
            trajectory_provenance='Provisional static evaluation fixture from v0; no generated object trajectory or attachment.')),
        contacts=[dict(id=side.lower()+'-grip',actor='A',effector=dict(joint=side+'Hand',offset_m=[0,0,0],label='uncalibrated wrist proxy'),
            target=dict(space='object',object='box',point_m=[x,.1,0]),start_frame=60,end_frame=179,tolerance_m=.03) for side,x in [('Left',-.2),('Right',.2)]])
    pair=dict(schema_version=1,id=f'high-five-seed-{seed}',fps=30,frame_count=120,
        actors=dict(A=actor('high_five',seed,'A',[0,0,-.55],[0,0,0,1]),B=actor('high_five',seed,'B',[0,0,.55],[0,1,0,0])),objects={},
        contacts=[dict(id=name+'-meeting',actor=name,effector=dict(joint='RightHand',offset_m=[0,0,0],label='uncalibrated wrist proxy'),
            target=dict(space='world',point_m=[0,1.5,0]),start_frame=60,end_frame=60,tolerance_m=.03) for name in ['A','B']])
    pair['contacts'].append(dict(id='hand-to-hand',actor='A',effector=dict(joint='RightHand',offset_m=[0,0,0],label='uncalibrated wrist proxy'),
        target=dict(space='actor',actor='B',joint='RightHand',offset_m=[0,0,0]),start_frame=60,end_frame=60,tolerance_m=.03))
    return [lift,pair]


def run():
    out=ROOT/'reports/scene-baseline-v1';out.mkdir(exist_ok=False)
    skin=dict(np.load(ASSET));summary=dict(created_at=now(),implementation_sha256=sha256(ROOT/'scripts/scene_constraints.py'),
        fixture_builder_sha256=sha256(__file__),source_benchmark_sha256=sha256(ROOT/'benchmarks/v0.json'),trials=[],
        scope='Re-evaluation of existing raw outputs, not fresh inference or held-out evaluation. Original provisional placements and uncalibrated wrist proxies; not release acceptance.')
    for seed in [11,22,33,44,55]:
        for scene in scenes(seed):
            path=out/scene['id'];path.mkdir();save(path/'scene.json',scene)
            result=evaluate(scene,skin);save(path/'evaluation.json',result)
            for record in result['sources'].values():assert sha256(ROOT/record['path'])==record['sha256']
            summary['trials'].append(dict(id=scene['id'],scene_sha256=sha256(path/'scene.json'),evaluation_sha256=sha256(path/'evaluation.json'),
                contacts=result['contacts'],max_object_vertex_depth_m=max((x['max_skin_vertex_depth_m'] for x in result['object_collisions']),default=None),
                required_interaction_features_missing=['object attachment'] if scene['objects'] else ['partner collision','joint reaction coordination']))
            save(out/'summary.json',summary)
            print(scene['id'],[(c['id'],round(c['max_interval_error_m'],3)) for c in result['contacts']],flush=True)
    save(out/'pipeline.json',dict(status='complete'))


if __name__=='__main__':run()
