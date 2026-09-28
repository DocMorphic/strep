"""Compare hull-screened decoded samples against a complete retained audit."""
import argparse
import os
from pathlib import Path
import time
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset,array
from rig_clip_import import AnimationSampler
from convex_partner_surface import penetration


def run(baseline,output):
    baseline,output=Path(baseline).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier verification')
    recipe=read(baseline/'request.json');summary=read(baseline/'summary.json');samples=read(baseline/'samples.json')['rows']
    if read(baseline/'pipeline.json')['status']!='complete' or summary['request_sha256']!=sha256(baseline/'request.json') or summary['samples_sha256']!=sha256(baseline/'samples.json'):raise ValueError('Incomplete or changed reference')
    if [r['frame'] for r in samples]!=recipe['frames']:raise ValueError('Incomplete reference population')
    export=Path(recipe['export']);actors={}
    for variant in ['input','candidate']:
        scene=read(export/(variant+'-scene.json'))['scene'];actors[variant]=[]
        for name in ['A','B']:
            entry=scene['actors'][name];path=export/entry['preview_glb']
            if sha256(path)!=recipe['glb_sha256'][variant+'/'+name]:raise ValueError('Changed GLB')
            rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
            indices=array(rig.document,rig.binary,rig.document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3)
            actors[variant].append((rig,sampler,Rotation.from_quat(entry['transform']['rotation_xyzw']).as_matrix(),np.asarray(entry['transform']['translation_m']),indices))
    output.mkdir();save(output/'request.json',dict(at=now(),reference=str(baseline),reference_summary_sha256=sha256(baseline/'summary.json'),frames=recipe['frames'],pid=os.getpid(),created=psutil.Process().create_time(),implementation={n:sha256(ROOT/'scripts'/n) for n in ['convex_partner_surface.py','verify_convex_partner_surface.py']}))
    results=[];start=time.perf_counter()
    with threadpool_limits(limits=1):
        for row in samples:
            for variant,group in actors.items():
                points=[rig.vertices(sampler.sample(float(np.float32(row['frame']/30))))@rotation.T+translation for rig,sampler,rotation,translation,faces in group]
                for direction,(a,b) in enumerate([(0,1),(1,0)]):
                    actual=penetration(points[a],points[b],group[b][-1]);expected=row['variants'][variant]['collision'][direction]
                    error=abs(actual['max_depth_m']-expected['max_depth_m'])
                    if error>1e-10 or any(actual[k]!=expected[k] for k in ['vertices_checked','vertices_over_tolerance','deepest_vertex','broadphase_candidates']):
                        save(output/'mismatch.json',dict(frame=row['frame'],variant=variant,direction=direction,actual=actual,expected=expected));raise ValueError('Hull-screened depth query disagrees')
                    results.append(dict(frame=row['frame'],variant=variant,direction=direction,actual=actual,depth_error_m=error))
            save(output/'pipeline.json',dict(status='checking',directions_checked=len(results),directions_total=len(samples)*4))
            print(row['frame'],len(results),flush=True)
    save(output/'results.json',dict(rows=results))
    before=sum(r['actual']['convex_broadphase']['aabb_candidates'] for r in results);after=sum(r['actual']['convex_broadphase']['hull_candidates'] for r in results)
    save(output/'verification.json',dict(at=now(),directions=len(results),sample_frames=len(samples),aabb_queries=before,hull_queries=after,query_reduction_fraction=1-after/max(before,1),seconds=time.perf_counter()-start,results_sha256=sha256(output/'results.json'),request_sha256=sha256(output/'request.json'),quality_approved=False,scope='Same retained depth/count/deepest vertex on every listed decoded sample. Query reduction is not an isolated runtime benchmark or continuous collision certificate.'))
    save(output/'pipeline.json',dict(status='complete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('baseline',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.baseline,a.output)
