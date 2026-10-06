"""Source-bound triangle crossing diagnostics with conservative edit influence.

Potential influence is not reachable separation. Frozen records cannot be
removed by these tracks; no permission, contact or geometry limit is changed.
"""
import argparse,shutil,traceback
from collections import Counter
from itertools import combinations
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from native_scene_boundary_edit import BoundarySceneEdits
from native_rotation_storage_repair import StorageAdjustedEdits
from native_stored_pair_job import Job,METHODS as JOB_METHODS
from native_scene_geometry import faces_for
from native_surface_model import surface_points
from triangle_crossing import audit
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

METHODS=tuple(sorted(set(JOB_METHODS)|{'native_edit_crossing_diagnostics.py'}))


def sampling_keys(clock,time):
    """Conservative key support of the actual scalar native LINEAR sampler."""
    clock=np.asarray(clock)
    if (clock.ndim!=1 or len(clock)<2 or clock.dtype.kind not in 'fiu' or not np.isfinite(clock).all() or np.any(np.diff(clock)<=0)
            or isinstance(time,(bool,np.bool_)) or not isinstance(time,(int,float,np.integer,np.floating)) or not np.isfinite(time)):
        raise ValueError('Increasing finite native clock and finite scalar time required')
    key=int(np.searchsorted(clock,time,side='left'))
    if key<len(clock) and float(clock[key])==float(time):return [key]
    # Match native scalar endpoint comparisons, including Float32 clock casts.
    if time<=clock[0]:return [0]
    if time>=clock[-1]:return [len(clock)-1]
    left=int(np.searchsorted(clock,time,side='right')-1)
    if not 0<=left<len(clock)-1:raise ValueError('Native interpolation support unavailable')
    return [left,left+1]


def descendants(parents,node):
    if type(node) is not int or not 0<=node<len(parents):raise ValueError('Existing node required')
    if any(isinstance(p,(bool,np.bool_)) or not isinstance(p,(int,np.integer)) or not -1<=p<len(parents) for p in parents):raise ValueError('Existing integer parents required')
    result=[]
    for joint in range(len(parents)):
        current=joint;seen=set();found=False
        while current>=0:
            if current>=len(parents) or current in seen:raise ValueError('Valid acyclic parent hierarchy required')
            if current==node:found=True
            seen.add(current);current=parents[current]
        if found:result.append(joint)
    return result


def vertex_influence(nodes,weights,affected_nodes):
    nodes,weights,affected_nodes=np.asarray(nodes),np.asarray(weights),np.asarray(affected_nodes)
    if (nodes.shape!=weights.shape or nodes.ndim!=2 or nodes.dtype.kind not in 'iu'
            or weights.dtype.kind not in 'fiu' or not np.isfinite(weights).all() or np.any(weights<0) or np.any(nodes<0)
            or affected_nodes.ndim!=1 or len(affected_nodes) and affected_nodes.dtype.kind not in 'iu'):
        raise ValueError('Complete finite nonnegative skin influences required')
    # Retain every positive slot, including small nondominant eighth influences.
    return np.any((weights>0)&np.isin(nodes,affected_nodes),axis=1)


class EditInfluence:
    def __init__(self,editor):
        storage=isinstance(editor,StorageAdjustedEdits);base=editor.base if storage else editor
        if not isinstance(base,BoundarySceneEdits):raise ValueError('Explicit source-bound boundary editor required')
        self.scene=base.scene;self.entries={};self.metadata={}
        for name,actor in self.scene.actors.items():
            entries=[];metadata=[]
            for index,e in enumerate(base.actors.get(name,{}).get('tracks',[])):
                children=descendants(actor['rig'].parents,e['node'])
                mask=vertex_influence(actor['skin'].nodes,actor['skin'].weights,children)
                continuous=np.zeros(len(e['clock']),bool);continuous[e['ids']]=np.any(e['weights']!=0,axis=1)
                potential=continuous.copy()
                if storage and e['path']=='rotation':potential[e['ids']]=True
                entries.append(dict(clock=e['clock'].copy(),potential=potential,vertices=mask))
                metadata.append(dict(index=index,node=e['node'],path=e['path'],descendants=children,
                    potential_vertices=int(mask.sum()),continuous_keys=int(continuous.sum()),
                    potential_keys_including_storage=int(potential.sum()),source_keys=len(e['clock']),
                    control_columns=e['controls'].ravel().tolist()))
            self.entries[name]=entries;self.metadata[name]=metadata

    def tracks(self,name,time):
        if name not in self.scene.actors:raise ValueError('Existing actor required')
        if isinstance(time,(bool,np.bool_)) or not isinstance(time,(int,float,np.integer,np.floating)) or not np.isfinite(time) or not 0<=time<=self.scene.duration:
            raise ValueError('Finite in-clip sample time required')
        return [(i,e['vertices']) for i,e in enumerate(self.entries[name]) if e['potential'][sampling_keys(e['clock'],time)].any()]

    def vertices(self,name,time):
        tracks=self.tracks(name,time)
        result=np.zeros(len(self.scene.actors[name]['skin'].nodes),bool)
        for _,mask in tracks:result|=mask
        return result


def diagnose(job,*,maximum_records=400000,progress=None):
    if type(maximum_records) is not int or not 1<=maximum_records<=1000000:raise ValueError('Explicit complete record budget required')
    influence=EditInfluence(job.edits);native,worlds=job.problem.decoded(job.files,job.value)
    vertices=surface_points(job.problem,worlds);faces={n:faces_for(a['rig'])[0] for n,a in job.scene.actors.items()}
    samples=[];counts=Counter();unique=Counter();kinds=Counter();all_records=0
    for frame,time in enumerate(job.geometry_times):
        time=float(time);points={n:vertices(n,time) for n in job.scene.actors};active={n:influence.tracks(n,time) for n in job.scene.actors};pairs=[]
        for left,right in combinations(job.scene.actors,2):
            crossing=audit(points[left],faces[left],points[right],faces[right],tolerance_m=job.policy['limits']['surface_tolerance_m'])
            records=[]
            for r in crossing['records']:
                if all_records>=maximum_records:raise ValueError('Complete crossing diagnostics exceed resource budget; no subset returned')
                a,b=r['left_triangle'],r['right_triangle']
                left_tracks=[i for i,mask in active[left] if mask[faces[left][a]].any()]
                right_tracks=[i for i,mask in active[right] if mask[faces[right][b]].any()]
                category='both_potentially_editable' if left_tracks and right_tracks else 'one_potentially_editable' if left_tracks or right_tracks else 'both_structurally_fixed'
                counts[category]+=1;kinds[r['kind']]+=1;unique[left,right,a,b,r['kind']]+=1;all_records+=1
                records.append(dict(r,edit_class=category,left_track_indices=left_tracks,right_track_indices=right_tracks))
            pairs.append(dict(actors=[left,right],surface_counts=crossing['counts'],degenerate_faces=crossing['degenerate_faces'],records=records))
        samples.append(dict(time_s=time,pairs=pairs))
        if progress:progress(frame+1,len(job.geometry_times))
    job.check()
    return dict(schema='strep-native-edit-crossing-diagnostics-v1',status='complete',at=now(),
        times_s=job.geometry_times.tolist(),samples=samples,track_influence=influence.metadata,
        complete_actor_triangle_counts={n:len(f) for n,f in faces.items()},complete_crossing_records=all_records,
        edit_classes={k:counts[k] for k in ('both_potentially_editable','one_potentially_editable','both_structurally_fixed')},
        crossing_kinds=dict(kinds),unique_triangle_records=len(unique),triangle_recurrence=[dict(actors=[a,b],triangles=[i,j],kind=k,samples=v) for (a,b,i,j,k),v in sorted(unique.items(),key=lambda item:(-item[1],item[0]))],
        original_native_failures=int((native>0).sum()),original_selected=True,quality_approved=False,release_approved=False,
        scope='Complete actual-anchor actor-pair triangle crossing queries and conservative permitted key/ancestor/positive-skin influence. Potential influence does not prove reachable separation under motion/contact budgets. No correction, permission revision, containment/object/plane/self-collision/continuous-time/physics/engine or quality certification.')


def run(request,output,*,maximum_records=400000):
    output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        if output.exists():raise ValueError('Fresh immutable diagnostics output required')
        job=Job(request);hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True);(output/'implementation').mkdir();(output/'inputs').mkdir()
        try:
            snapshots={}
            for role,path in {**job.roles,'job_request':job.path}.items():
                dest=output/'inputs'/(role+path.suffix);shutil.copyfile(path,dest);snapshots[role]=dict(path=str(dest.relative_to(output)),sha256=sha256(dest))
            for n in hashes:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
            def progress(done,total):
                if done==1 or done%100==0 or done==total:
                    save(output/'pipeline.json',dict(status='processing',completed_samples=done,total_samples=total,at=now()))
                    print('Crossing sample',done,'/',total,flush=True)
            result=diagnose(job,maximum_records=maximum_records,progress=progress)
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(output/'implementation'/n)!=h for n,h in hashes.items()):raise ValueError('Diagnostics implementation changed')
            result.update(job_request_sha256=sha256(job.path),inputs_sha256=job.inputs,methods_sha256=hashes,input_snapshots=snapshots,maximum_records=maximum_records)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except BaseException as exc:
            save(output/'failure.json',dict(error=str(exc),traceback=traceback.format_exc(),at=now()));save(output/'pipeline.json',dict(status='failed',at=now()));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--maximum-records',default=400000,type=int)
    a=p.parse_args();r=run(a.request,a.output,maximum_records=a.maximum_records);print('Complete:',r['complete_crossing_records'],'records;',r['edit_classes'])

if __name__=='__main__':main()
