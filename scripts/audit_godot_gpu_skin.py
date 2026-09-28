"""Render imported skin and independently posed reference triangles on the GPU."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from probe_godot_render import engine_command, run_engine, project_file


def masks(gpu, reference):
    a, b = [np.all(np.array(Image.open(p).convert('RGB')) > 127, axis=2) for p in (gpu, reference)]
    union = a | b
    intersection = a & b
    delta = a ^ b
    boundary = max(float(distance_transform_edt(~a)[b].max()) if b.any() else float('inf'),
                   float(distance_transform_edt(~b)[a].max()) if a.any() else float('inf'))
    box = np.argwhere(union)
    border = bool(len(box) and (box.min() < 2 or np.any(box.max(axis=0) > np.array(a.shape)-3)))
    return dict(gpu_pixels=int(a.sum()), reference_pixels=int(b.sum()),
        intersection_over_union=float(intersection.sum()/max(1, union.sum())), differing_pixels=int(delta.sum()),
        maximum_silhouette_distance_pixels=boundary, clipped_at_border=border)


def run(output, omit_root_control=False):
    output.mkdir(parents=True, exist_ok=False)
    project = output/'project';project.mkdir();project_file(project/'project.godot')
    sources = ('godot_gpu_skin_audit.gd','godot_cycle_adapter.gd')
    for name in sources: shutil.copyfile(ROOT/'scripts'/name, project/name)
    previous = ROOT/'reports/runtime-reverse-v2/request.json'
    cases = []
    placement = np.eye(4);placement[:3,:3]=Rotation.from_euler('y',.4).as_matrix();placement[:3,3]=[2,.3,-1]
    for item in read(previous)['cases']:
        if omit_root_control and item['id']!='20260926-212541-f05dcc66': continue
        folder=output/item['id'];folder.mkdir()
        for source,key,name in [('path','glb_sha256','character.glb'),('metadata','metadata_sha256','runtime-cycle.json'),('repeated','repeated_sha256','reference.glb')]:
            if sha256(item[source]) != item[key]: raise ValueError('Frozen runtime fixture changed')
            shutil.copyfile(item[source],folder/name)
        metadata=read(folder/'runtime-cycle.json');period=metadata['period_frames']
        rig=RigAsset.load(folder/'reference.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
        indices=[];offset=0
        for primitive in rig.primitives:
            source=rig.document['meshes'][rig.document['nodes'][primitive['node']]['mesh']]['primitives'][primitive['primitive']]
            ids=array(rig.document,rig.binary,source['indices']).astype(int) if 'indices' in source else np.arange(len(primitive['positions']))
            if len(ids)%3: raise ValueError('Reference triangle topology invalid')
            indices.extend((ids+offset).tolist());offset+=len(primitive['positions'])
        frames=[0.,period/2-.5,period-.5,float(period),period+7.5,period*2+3.5]
        samples=[]
        for index,frame in enumerate(frames):
            points=rig.vertices(sampler.sample(frame/30))
            points=points@placement[:3,:3].T+placement[:3,3]
            lo,hi=points.min(axis=0),points.max(axis=0)
            samples.append(dict(index=index,frame=frame,vertices=points.tolist(),center=((lo+hi)/2).tolist(),
                camera_size=float(np.linalg.norm(hi-lo)*1.2)))
        save(folder/'reference-vertices.json',dict(samples=samples,indices=indices))
        cases.append(dict(id=item['id'],path=str(folder/'character.glb'),metadata=str(folder/'runtime-cycle.json'),
            reference=str(folder/'reference-vertices.json'),source_glb_sha256=item['glb_sha256'],
            repeated_sha256=item['repeated_sha256'],metadata_sha256=item['metadata_sha256'],reference_sha256=sha256(folder/'reference-vertices.json')))
    limits=dict(minimum_pixels=500,minimum_iou=.995,maximum_boundary_distance_pixels=1.5)
    save(output/'request.json',dict(at=now(),cases=cases,views=[[0,.15,1],[1,.15,0],[1,.25,1]],limits=limits,omit_root_control=omit_root_control,
        source_request_sha256=sha256(previous),implementation={n:sha256(ROOT/'scripts'/n) for n in (*sources,'audit_godot_gpu_skin.py','probe_godot_render.py')},
        scope='Four existing runtime fixtures, six fixed poses, three views, two root modes. Solid double-sided silhouette renders; not material, physics, contact or animator validation.'))
    save(output/'pipeline.json',dict(at=now(),status='rendering'))
    run_engine(engine_command('godot_gpu_skin_audit.gd',project,output/'request.json',output),output/'engine.log',timeout=240)
    observed=read(output/'engine-output.json')
    if not observed['adapter'] or observed['driver']!='opengl3': raise ValueError('Unexpected graphics backend')
    checks=[]
    for expected,actual in zip(cases,observed['cases']):
        if expected['id']!=actual['id'] or len(actual['records'])!=36: raise ValueError('Incomplete rendered population')
        for record in actual['records']:
            prefix=record['prefix']; metrics=masks(output/(prefix+'-gpu.png'),output/(prefix+'-reference.png'))
            passed=bool(min(metrics['gpu_pixels'],metrics['reference_pixels'])>=limits['minimum_pixels'] and
                metrics['intersection_over_union']>=limits['minimum_iou'] and
                metrics['maximum_silhouette_distance_pixels']<=limits['maximum_boundary_distance_pixels'] and not metrics['clipped_at_border'])
            checks.append(dict(**record,**metrics,passed=passed))
    if omit_root_control:
        positives=[c for c in checks if not c['extracted']]
        # Final pose lies after two turns of the existing authored cycle.
        last=max(c['frame'] for c in checks)
        negatives=[c for c in checks if c['extracted'] and c['frame']==last]
        passed=bool(len(checks)==36 and len(positives)==18 and all(c['passed'] for c in positives)
            and len(negatives)==3 and all(not c['passed'] for c in negatives))
    else: passed=bool(len(checks)==144 and all(c['passed'] for c in checks))
    save(output/'verification.json',dict(at=now(),passed=passed,checks=checks,renderer=observed,
        request_sha256=sha256(output/'request.json'),engine_output_sha256=sha256(output/'engine-output.json'),
        images={p.name:sha256(p) for p in output.glob('*.png')},deliberately_broken_root=omit_root_control,
        interpretation='Positive skeleton renders must pass; omitted-root final renders must fail in all three views.' if omit_root_control else 'All correctly integrated renders must pass.',quality_approved=False))
    save(output/'pipeline.json',dict(at=now(),status='complete' if passed else 'failed_comparison',comparisons=len(checks),passed=passed))
    print(dict(passed=passed,comparisons=len(checks),min_iou=min(c['intersection_over_union'] for c in checks),
        max_boundary_pixels=max(c['maximum_silhouette_distance_pixels'] for c in checks)))
    if not passed: raise ValueError('GPU render comparison failed; retained renders and metrics')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    parser.add_argument('--omit-root-control',action='store_true')
    args=parser.parse_args();run(args.output.resolve(),args.omit_root_control)
