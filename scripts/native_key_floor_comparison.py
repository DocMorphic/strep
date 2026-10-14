"""Separate source-generation and rig-transfer floor diagnostics at native keys.

All triangle-referenced skin vertices are retained. Different meshes and body
proportions prevent causal isolation from this comparison alone.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,save,sha256,now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_scene_geometry import faces_for,METHODS as GEOMETRY_METHODS

METHODS=tuple(dict.fromkeys(GEOMETRY_METHODS+('native_key_floor_comparison.py','action_worker_lock.py')))
FLOOR_TOLERANCE_M=.005


def sampler(rig,index):
    if type(index) is not int or not 0<=index<len(rig.document.get('animations',[])):
        raise ValueError('Explicit existing animation index required')
    return NativeSupportSampler(rig.document,rig.binary,index)


def native_clock(reader):
    times=np.unique(np.concatenate([np.asarray(c[2],float) for c in reader.channels]))
    if not 2<=len(times)<=10000 or not np.isfinite(times).all() or times[0]!=0 or times[-1]!=reader.duration:
        raise ValueError('Complete finite native-key clock with both clip endpoints required')
    return times


def measure(rig,reader,times):
    faces,_=faces_for(rig);used=np.unique(faces);minima=[];witnesses=[];nodes=[];weights=[]
    for time in times:
        vertices=rig.vertices(reader.sample(float(time)))
        if not np.isfinite(vertices).all():raise ValueError('Complete finite skin population required')
        winner=int(used[np.argmin(vertices[used,1])]);minima.append(float(vertices[winner,1]));witnesses.append(winner)
        offset=0
        for primitive in rig.primitives:
            count=len(primitive['positions'])
            if offset<=winner<offset+count:
                if primitive['weights'] is None:node=primitive['node'];weight=0.
                else:
                    local=winner-offset;slot=int(np.argmax(primitive['weights'][local]));node=rig.joints[int(primitive['joints'][local,slot])];weight=float(primitive['weights'][local,slot])
                nodes.append(node);weights.append(weight);break
            offset+=count
    minima=np.asarray(minima);depth=np.maximum(-minima,0);peak=int(depth.argmax());node=nodes[peak]
    report=dict(samples=len(times),duration_s=reader.duration,vertices=len(used),faces=len(faces),peak_depth_m=float(depth.max()),
        floor_failed_keys=int((depth>FLOOR_TOLERANCE_M).sum()),peak_time_s=float(times[peak]),peak_vertex=int(witnesses[peak]),
        peak_dominant_joint=dict(node=node,name=rig.document['nodes'][node].get('name',''),weight=weights[peak]),rig_profile_reviewed=False)
    return report,dict(times=times,min_y_m=minima,witness_vertices=np.asarray(witnesses),dominant_joint_nodes=np.asarray(nodes))


def compare(source,target,source_index,target_index,scale):
    if type(scale) not in (int,float) or not np.isfinite(scale) or not 0<scale<=100:
        raise ValueError('Explicit finite positive source-to-target scale required')
    before=sampler(source,source_index);after=sampler(target,target_index);times=native_clock(before)
    if not np.array_equal(times,native_clock(after)):raise ValueError('Exact shared original native-key clock required; retime explicitly first')
    original,a=measure(source,before,times);transferred,b=measure(target,after,times)
    scaled=np.maximum(-a['min_y_m']*scale,0);target_depth=np.maximum(-b['min_y_m'],0)
    report=dict(source=original,target=transferred,source_to_target_scale=float(scale),floor_tolerance_m=FLOOR_TOLERANCE_M,
        maximum_scaled_source_depth_m=float(scaled.max()),maximum_target_minus_scaled_source_depth_m=float((target_depth-scaled).max()),
        source_and_target_clocks_equal=True,quality_approved=False,release_approved=False)
    arrays={kind+'_'+name:values for kind,data in [('source',a),('target',b)] for name,values in data.items()}
    return report,arrays


def run(source_path,target_path,output,*,source_index,target_index,scale):
    source_path,target_path,output=map(lambda p:Path(p).resolve(),(source_path,target_path,output))
    if output.exists():raise FileExistsError(output)
    if source_path.is_relative_to(output) or target_path.is_relative_to(output):raise ValueError('Original inputs must stay outside output')
    with worker_lock(),threadpool_limits(limits=1):
        bindings={str(p):sha256(p) for p in (source_path,target_path)};methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        report,arrays=compare(RigAsset.load(source_path),RigAsset.load(target_path),source_index,target_index,scale)
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        np.savez_compressed(output/'observations.npz',**arrays)
        if any(sha256(p)!=h for p,h in bindings.items()) or any(not (sha256(ROOT/'scripts'/n)==sha256(archive/n)==h) for n,h in methods.items()):
            raise ValueError('Original input or comparison method changed')
        result=dict(schema='strep-native-key-floor-comparison-v1',at=now(),status='complete',**report,
            source_animation_index=source_index,target_animation_index=target_index,source_bindings_sha256=bindings,implementation_sha256=methods,
            observations_sha256=sha256(output/'observations.npz'),original_selected=True,training_admitted=False,
            scope='Complete source/target triangle-referenced skin at shared native keys, ground Y=0, explicit leg/unit scale and unchanged 5-mm diagnostic. Different meshes/proportions prevent causal isolation. No continuous/engine/semantic/human approval.')
        save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','target','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--source-index',type=int,required=True);parser.add_argument('--target-index',type=int,required=True);parser.add_argument('--scale',type=float,required=True)
    args=parser.parse_args();run(args.source,args.target,args.output,source_index=args.source_index,target_index=args.target_index,scale=args.scale)
