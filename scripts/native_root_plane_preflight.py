"""Read-only vertical-root/floor/point-contact intersection for native scenes."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now
from native_scene_contacts import SceneContacts
from native_scene_geometry import policy_for,faces_for,METHODS as GEOMETRY_METHODS
from root_plane_contact_bounds import translation_coefficients,interval

METHODS=tuple(dict.fromkeys(GEOMETRY_METHODS+('native_root_plane_preflight.py','root_plane_contact_bounds.py','action_worker_lock.py')))


def run(contacts,geometry_policy,actor,root,plane,maximum_shift_m,output):
    contacts,geometry_policy,output=map(lambda p:Path(p).resolve(),(contacts,geometry_policy,output))
    if output.exists():raise FileExistsError(output)
    if type(maximum_shift_m) not in (int,float) or not np.isfinite(maximum_shift_m) or not 0<=maximum_shift_m<=.22:
        raise ValueError('Explicit original root displacement bound up to 22 cm required')
    with worker_lock(),threadpool_limits(limits=1):
        scene=SceneContacts(read(contacts),contacts.parent);policy=read(geometry_policy)
        times,_,_=policy_for(policy,scene,sha256(contacts))
        if actor not in scene.actors or plane not in policy['planes']:raise ValueError('Existing explicit actor and floor plane required')
        floor=policy['planes'][plane]
        if floor['normal_world']!=[0,1,0]:raise ValueError('Preflight requires an explicitly upward horizontal plane')
        bindings={str(p):sha256(p) for p in (contacts,geometry_policy)};bindings.update(scene.inputs)
        if any(Path(p).is_relative_to(output) for p in bindings):raise ValueError('Original inputs must stay outside output')
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        selected=scene.actors[actor];coefficients,descendants=translation_coefficients(selected['rig'],root)
        faces,_=faces_for(selected['rig']);used=np.unique(faces)
        _,observations=scene.evaluate();active={};populations={}
        for i,entry in enumerate(scene.rows):
            row=entry['authored'];target=row['target'];sign=0;ids=None;reduction=None
            if row['actor']==actor:sign=1;ids=entry['ids'];reduction=row['reduction']
            elif target['space']=='actor' and target['actor']==actor:sign=-1;ids=entry['target_ids'];reduction=target['reduction']
            if not sign:continue
            clock=observations[f'contact_{i}_times_s'];error=observations[f'contact_{i}_effector_world_m']-observations[f'contact_{i}_target_world_m']
            response=coefficients[ids]*sign
            if reduction=='centroid':response=np.array([response.mean()])
            populations[row['id']]=len(clock)*len(response)
            for t,errors in zip(clock,error):
                for point,(difference,coefficient) in enumerate(zip(errors,response)):
                    active.setdefault(float(t),[]).append(dict(id=row['id']+':'+str(point),error_m=difference.tolist(),coefficient=float(coefficient),position_limit_m=row['limits']['position_m']))
        times=np.unique(np.r_[times,np.asarray(list(active),float)]);results=[];minimum_heights=[]
        rotation=selected['placement'][1];position=selected['placement'][0]
        threshold=floor['offset_m']-policy['limits']['penetration_m']
        for t in times:
            vertices=selected['rig'].vertices(selected['sampler'].sample(float(t)))@rotation.T+position
            result=interval(vertices[used,1],coefficients[used],floor_height_m=threshold,
                lower_m=-float(maximum_shift_m),upper_m=float(maximum_shift_m),contacts=active.get(float(t),[]))
            result['time_s']=float(t);results.append(result);minimum_heights.append(float(vertices[used,1].min()))
        scene.check_inputs()
        if any(sha256(p)!=h for p,h in bindings.items()) or any(sha256(ROOT/'scripts'/n)!=h for n,h in methods.items()):raise ValueError('Original input or preflight method changed')
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        np.savez_compressed(output/'observations.npz',times_s=times,minimum_heights_m=minimum_heights,coefficients=coefficients,
            triangle_referenced_vertices=used,descendant_nodes=descendants,lower_m=[r['lower_m'] for r in results],upper_m=[r['upper_m'] for r in results])
        result=dict(schema='strep-native-root-plane-preflight-v1',status='complete',at=now(),actor=actor,root_node=root,plane=plane,
            maximum_shift_m=float(maximum_shift_m),samples=len(times),vertices=len(used),contact_rows_by_id=populations,
            poses_with_empty_intersections=sum(not r['per_pose_interval_nonempty'] for r in results),per_pose_intersections=results,
            source_bindings_sha256=bindings,implementation_sha256=methods,observations_sha256=sha256(output/'observations.npz'),
            root_coefficient_minimum=float(coefficients.min()),root_coefficient_maximum=float(coefficients.max()),
            original_selected=True,clip_feasibility_established=False,quality_approved=False,training_admitted=False,release_approved=False,
            scope='Necessary independent-pose vertical world-root intervals for every referenced triangle vertex and every declared affected incoming/outgoing point contact. Original 22-cm ceiling and plane/contact tolerances unchanged. Ordinary Float64, not interval proof. No key interpolation, motion-rate, contact-slip, other-plane/object/partner collision, balance, anatomy, export, engine or human approval.')
        save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('contacts','geometry_policy','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--actor',required=True);parser.add_argument('--root',type=int,required=True);parser.add_argument('--plane',required=True);parser.add_argument('--maximum-shift',type=float,required=True)
    args=parser.parse_args();run(args.contacts,args.geometry_policy,args.actor,args.root,args.plane,args.maximum_shift,args.output)
