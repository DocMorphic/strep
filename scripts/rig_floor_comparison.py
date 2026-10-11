"""Compare two rigged clips against an explicitly declared horizontal plane.

Checks every vertex at the supplied clock. It does not modify clips, establish
causality, identify intentional supports, or certify continuous-time motion.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import sha256,save


def worst_vertex(rig,flat_index):
    start=0
    for primitive in rig.primitives:
        if flat_index<start+len(primitive['positions']):
            number=flat_index-start;influences=[]
            if primitive['joints'] is not None:
                for joint,weight in zip(primitive['joints'][number],primitive['weights'][number]):
                    if weight>0:
                        node=int(rig.joints[int(joint)])
                        influences.append(dict(node=node,name=rig.document['nodes'][node].get('name'),weight=float(weight)))
            return dict(flat_vertex=flat_index,node=primitive['node'],primitive=primitive['primitive'],
                primitive_vertex=number,skin_influences=influences)
        start+=len(primitive['positions'])
    raise ValueError('Vertex not found in evaluated rig')


def compare(source,target,times_s,*,source_animation=0,target_animation=0,floor_y_m=0.,tolerance_m=.005):
    if type(floor_y_m) not in (int,float) or not np.isfinite(floor_y_m):raise ValueError('Finite declared floor height required')
    if type(tolerance_m) not in (int,float) or not np.isfinite(tolerance_m) or tolerance_m<=0:raise ValueError('Positive declared floor tolerance required')
    if type(source_animation) is not int or type(target_animation) is not int:raise ValueError('Explicit integer animation selections required')
    raw=np.asarray(times_s)
    if (raw.ndim!=1 or not 1<=len(raw)<=20000 or raw.dtype.kind not in 'fiu'
            or any(isinstance(x,(bool,np.bool_)) for x in np.asarray(times_s,dtype=object).flat)
            or not np.isfinite(raw).all() or raw[0]<0 or np.any(raw[1:]<=raw[:-1])):
        raise ValueError('Bounded increasing nonnegative finite sampling clock required')
    times=raw.astype('<f8');paths={'source':Path(source),'target':Path(target)}
    methods={str(Path(__file__).with_name(name)):sha256(Path(__file__).with_name(name)) for name in
        ('rig_floor_comparison.py','rig_asset.py','gltf_tools.py','rig_clip_import.py','native_support_clock.py')}
    inputs={str(path):sha256(path) for path in paths.values()};results={};traces={}
    for name,path in paths.items():
        rig=RigAsset.load(path);selection=source_animation if name=='source' else target_animation
        sampler=NativeSupportSampler(rig.document,rig.binary,selection)
        if times[-1]>sampler.duration:raise ValueError('Sampling clock extends beyond selected animation')
        minima=[];witnesses=[]
        for time in times:
            positions=rig.vertices(sampler.sample(float(time)))
            if not np.isfinite(positions).all():raise ValueError('Non-finite sampled mesh')
            vertex=int(np.argmin(positions[:,1]));minima.append(float(positions[vertex,1]));witnesses.append((vertex,positions[vertex].tolist()))
        minima=np.asarray(minima);depth=np.maximum(0.,floor_y_m-minima);traces[name]=depth
        peak=int(np.argmax(depth));vertex,point=witnesses[peak]
        results[name]=dict(sha256=inputs[str(path)],animation_index=selection,vertices=sum(len(p['positions']) for p in rig.primitives),
            minimum_y_m=minima.tolist(),depth_m=depth.tolist(),maximum_depth_m=float(depth.max()),
            failed_samples=int(np.sum(depth>tolerance_m)),sampled_floor_pass=bool(np.all(depth<=tolerance_m)),
            peak_sample=peak,peak_time_s=float(times[peak]),peak_point_m=point,peak_vertex=worst_vertex(rig,vertex))
    source_failed=traces['source']>tolerance_m;target_failed=traces['target']>tolerance_m
    assert all(sha256(p)==h for p,h in {**inputs,**methods}.items()),'Comparison input or method changed'
    return dict(schema='strep-rig-floor-comparison-v1',status='complete',samples=len(times),times_s=times.tolist(),
        clock_sha256=hashlib.sha256(times.tobytes()).hexdigest(),floor_y_m=floor_y_m,tolerance_m=tolerance_m,
        source=results['source'],target=results['target'],source_bindings_sha256=inputs,implementation_sha256=methods,
        paired_samples=dict(both_fail=int(np.sum(source_failed&target_failed)),source_only_fail=int(np.sum(source_failed&~target_failed)),
            target_only_fail=int(np.sum(~source_failed&target_failed)),neither_fail=int(np.sum(~source_failed&~target_failed))),
        cause_established=False,contact_or_support_verified=False,continuous_time_verified=False,
        human_approved=False,quality_approved=False,release_approved=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('target',type=Path)
    parser.add_argument('--clock',type=Path,required=True,help='JSON array of explicit sample times in seconds')
    parser.add_argument('--floor-y',type=float,required=True);parser.add_argument('--tolerance',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=1):
        result=compare(args.source,args.target,json.loads(args.clock.read_text(encoding='utf-8')),floor_y_m=args.floor_y,tolerance_m=args.tolerance)
        save(args.output,result)
    print(json.dumps(dict(status=result['status'],samples=result['samples'],paired_samples=result['paired_samples'])))
