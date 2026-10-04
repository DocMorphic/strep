"""Review exposed points of explicitly selected native contact regions.

No anatomical inference, intent replacement, fitting, collision certification or
training labels. Every original contact clock and declared region is retained.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from native_scene_contacts import SceneContacts, fields, scalar
from native_scene_geometry import faces_for
from native_surface_contact import normals, METHODS as SURFACE_METHODS

METHODS=tuple(dict.fromkeys(SURFACE_METHODS+('native_contact_region_review.py',)))


def region_ids(refs, skin):
    table={tuple(ref):i for i,ref in enumerate(skin.vertex_references.tolist())}
    if not isinstance(refs,list) or not 1<=len(refs)<=len(table):
        raise ValueError('A complete nonempty explicitly selected vertex region is required')
    result=[]
    for ref in refs:
        if not isinstance(ref,list) or len(ref)!=3 or any(type(v) is not int for v in ref) or tuple(ref) not in table:
            raise ValueError('Existing integer region vertex references required')
        result.append(table[tuple(ref)])
    if len(set(result))!=len(result):raise ValueError('Distinct region vertex references required')
    return np.asarray(result,dtype=np.int64)


def policy_for(policy,scene,digest):
    fields(policy,('schema','contacts_sha256','limits','maximum_surface_pose_queries','maximum_candidate_curve_values','contacts'),'region review policy')
    if policy['schema']!='strep-native-contact-region-review-v1' or policy['contacts_sha256']!=digest:
        raise ValueError('Region policy must bind the exact original contacts')
    limits=policy['limits']
    fields(limits,('support_band_m','maximum_candidate_normal_angle_degrees','minimum_normal_area_m2','minimum_normal_coherence'),'region review limits')
    scalar(limits['support_band_m'],0,.02,'support band')
    scalar(limits['maximum_candidate_normal_angle_degrees'],0,90,'candidate normal cone')
    scalar(limits['minimum_normal_area_m2'],1e-16,1e-4,'normal area')
    scalar(limits['minimum_normal_coherence'],.000001,1,'normal coherence')
    budget=policy['maximum_surface_pose_queries']
    if type(budget) is not int or not 1<=budget<=20000:raise ValueError('Explicit full-surface pose query budget required')
    curve_budget=policy['maximum_candidate_curve_values']
    if type(curve_budget) is not int or not 1<=curve_budget<=20000000:raise ValueError('Explicit complete candidate curve budget required')
    if not isinstance(policy['contacts'],dict) or set(policy['contacts'])!={r['authored']['id'] for r in scene.rows}:
        raise ValueError('Every original contact must have a declared region')
    regions={}
    for entry in scene.rows:
        row=entry['authored'];item=policy['contacts'][row['id']];partner=row['target']['space']=='actor'
        fields(item,('source_vertices','partner_vertices') if partner else ('source_vertices',),'contact regions')
        source=region_ids(item['source_vertices'],scene.actors[row['actor']]['skin'])
        if not np.isin(entry['ids'],source).all():raise ValueError('Source region must include every original effector vertex')
        target=None
        if partner:
            target=region_ids(item['partner_vertices'],scene.actors[row['target']['actor']]['skin'])
            if not np.isin(entry['target_ids'],target).all():raise ValueError('Partner region must include every original target vertex')
        regions[row['id']]=(source,target)
    return limits,budget,regions


def vertex_normals(vertices,faces,minimum_area,minimum_coherence):
    """Every incident face once per vertex, including repeated degenerate indices."""
    vertices=np.asarray(vertices,float);faces=np.asarray(faces)
    # The shared scalar oracle validates the full mesh and reliability thresholds.
    normals(vertices,faces,[[0]],minimum_area=minimum_area,minimum_coherence=minimum_coherence)
    triangles=vertices[faces];cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    area=np.linalg.norm(cross,axis=1);summed=np.zeros_like(vertices);total=np.zeros(len(vertices));bad=np.zeros(len(vertices),int)
    for slot in range(3):
        unique=np.ones(len(faces),bool)
        for previous in range(slot):unique&=faces[:,slot]!=faces[:,previous]
        ids=faces[unique,slot]
        np.add.at(summed,ids,cross[unique]);np.add.at(total,ids,area[unique]);np.add.at(bad,ids,(area[unique]<=minimum_area).astype(int))
    length=np.linalg.norm(summed,axis=1)
    coherence=np.divide(length,total,out=np.zeros_like(length),where=total>0)
    available=(bad==0)&(total>0)&(length>minimum_area)&(coherence>=minimum_coherence)
    unit=np.divide(summed,length[:,None],out=np.zeros_like(summed),where=available[:,None])
    return unit,available


def envelope(vertices,region,point,axis,unit,available,limits):
    projection=(vertices[region]-point)@axis
    front=float(projection.max());back=float(projection.min());witness=int(region[int(np.argmax(projection))])
    aligned=(unit[region]@axis)>=np.cos(np.deg2rad(limits['maximum_candidate_normal_angle_degrees']))
    eligible=region[(front-projection<=limits['support_band_m'])&available[region]&aligned]
    return dict(front_extent_m=front,back_extent_m=back,front_witness=witness,
                original_point_exposed=front<=limits['support_band_m'],eligible_vertices=eligible.tolist())


def evaluate(scene,policy,digest,*,actor_vertices=None):
    limits,budget,regions=policy_for(policy,scene,digest)
    point_result,point_arrays=scene.evaluate()
    needed=0;curve_values=0
    for index,entry in enumerate(scene.rows):
        row=entry['authored']
        count=len(point_arrays[f'contact_{index}_times_s']);needed+=count
        curve_values+=count*len(regions[row['id']][0])*(1 if row['reduction']=='centroid' else len(entry['ids']))
        if row['target']['space']=='actor':
            needed+=count;target=row['target']
            curve_values+=count*len(regions[row['id']][1])*(1 if target['reduction']=='centroid' else len(entry['target_ids']))
    if needed>budget:raise ValueError('Whole contact-clock surface population exceeds budget; no subset returned')
    if curve_values>policy['maximum_candidate_curve_values']:raise ValueError('Whole candidate curve population exceeds budget; no subset returned')
    faces={name:faces_for(actor['rig'])[0] for name,actor in scene.actors.items()}
    cache=[None,None];results=[];arrays={};queries=0
    def surface(name,time):
        nonlocal queries
        key=(name,float(time))
        if key!=cache[0]:
            if queries>=budget:raise ValueError('Complete surface query budget exceeded')
            actor=scene.actors[name];p,r=actor['placement']
            vertices=actor['rig'].vertices(actor['sampler'].sample(float(time)))@r.T+p if actor_vertices is None else np.asarray(actor_vertices(name,float(time)),float)
            if vertices.shape!=(len(actor['skin'].nodes),3) or not np.isfinite(vertices).all():raise ValueError('Complete finite source skin required')
            unit,available=vertex_normals(vertices,faces[name],limits['minimum_normal_area_m2'],limits['minimum_normal_coherence'])
            cache[:]=[key,(vertices,unit,available)];queries+=1
        return cache[1]
    for index,entry in enumerate(scene.rows):
        row=entry['authored'];clock=point_arrays[f'contact_{index}_times_s'];sides=[]
        participants=[('source',row['actor'],entry['ids'],row['reduction'],regions[row['id']][0],point_arrays[f'contact_{index}_effector_world_m'])]
        if row['target']['space']=='actor':
            target=row['target'];participants.append(('partner',target['actor'],entry['target_ids'],target['reduction'],regions[row['id']][1],point_arrays[f'contact_{index}_target_world_m']))
        for label,name,ids,reduction,region,original in participants:
            groups=[ids] if reduction=='centroid' else [[int(i)] for i in ids]
            stable=[set(map(int,region)) for _ in groups];history=[[] for _ in groups]
            records=[];front=[];back=[];reliable=[];witnesses=[]
            for stamp,time in enumerate(clock):
                vertices,unit,available=surface(name,time)
                checked=vertices[ids].mean(0,keepdims=True) if reduction=='centroid' else vertices[ids]
                if not np.allclose(checked,original[stamp],atol=2e-12,rtol=0):raise ValueError('Original contact point and complete region poses differ')
                axes=normals(vertices,faces[name],groups,minimum_area=limits['minimum_normal_area_m2'],minimum_coherence=limits['minimum_normal_coherence'])
                samples=[];fs=[];bs=[];valid=[];ws=[]
                for k,normal in enumerate(axes):
                    result=None
                    if normal['available']:
                        result=envelope(vertices,region,original[stamp,k],np.asarray(normal['normal_world']),unit,available,limits)
                        stable[k].intersection_update(result['eligible_vertices'])
                    else:stable[k].clear()
                    persistent=np.asarray(sorted(stable[k]),dtype=np.int64)
                    history[k].append((persistent,np.linalg.norm(vertices[persistent]-original[stamp,k],axis=1)))
                    samples.append(dict(normal_available=normal['available'],normal_world=normal['normal_world'],envelope=result))
                    fs.append(result['front_extent_m'] if result else np.nan);bs.append(result['back_extent_m'] if result else np.nan)
                    valid.append(normal['available']);ws.append(result['front_witness'] if result else -1)
                records.append(dict(time_s=float(time),points=samples));front.append(fs);back.append(bs);reliable.append(valid);witnesses.append(ws)
            candidates=[]
            for k,selected in enumerate(stable):
                ordered=sorted(selected);candidate_ids=np.asarray(ordered,dtype=int)
                values=np.asarray([shift[np.searchsorted(ids,candidate_ids)] for ids,shift in history[k]],dtype='<f8')
                refs=scene.actors[name]['skin'].vertex_references[candidate_ids].tolist()
                candidates.append(dict(point=k,vertices=refs,count=len(ordered),
                    maximum_reference_shift_m=values.max(axis=0).tolist() if ordered else [],
                    eligible_at_every_original_contact_time=True,
                    directly_encodable_as_one_contact=len(ordered)<=256 and bool(ordered),
                    requires_author_selection=True))
                arrays[f'contact_{index}_{label}_point_{k}_candidate_ids']=candidate_ids
                arrays[f'contact_{index}_{label}_point_{k}_reference_shift_m']=values
            finite=np.asarray(front);valid=np.asarray(reliable,bool)
            passed=bool(valid.all() and (finite<=limits['support_band_m']).all())
            sides.append(dict(side=label,actor=name,declared_region_vertices=len(region),samples=records,
                original_point_exposed_at_every_time=passed,candidates=candidates,
                maximum_front_extent_m=float(finite[valid].max()) if valid.any() else None))
            arrays[f'contact_{index}_{label}_front_extent_m']=np.asarray(front,dtype='<f8')
            arrays[f'contact_{index}_{label}_back_extent_m']=np.asarray(back,dtype='<f8')
            arrays[f'contact_{index}_{label}_normal_available']=valid
            arrays[f'contact_{index}_{label}_front_witness_ids']=np.asarray(witnesses,dtype=np.int64)
        results.append(dict(id=row['id'],sides=sides,original_contact= row,
            original_points_exposed=all(s['original_point_exposed_at_every_time'] for s in sides)))
        arrays[f'contact_{index}_times_s']=clock
    scene.check_inputs()
    return dict(schema='strep-native-contact-region-review-result-v1',status='complete',contacts=results,limits=limits,
        surface_pose_queries=queries,candidate_curve_value_upper_bound=curve_values,
        point_contacts_pass=point_result['passed'],original_contact_limits_unchanged=True,
        original_selected=True,original_intent_changed=False,anatomical_review_pending=True,
        collision_verified=False,quality_approved=False,training_admitted=False,release_approved=False,
        scope='Exposed-plane review relative to original winding-derived normals over explicitly declared regions and all original contact clocks. '
              'Candidates are persistent material vertex references for explicit author selection, not automatic palms, replacement intent or collision/quality proof.'),arrays


def run(contacts,policy_path,output):
    contacts,policy_path,output=map(lambda p:Path(p).resolve(),(contacts,policy_path,output))
    if output.exists():raise ValueError('Fresh contact-region review output required')
    with worker_lock(),threadpool_limits(limits=1):
        bindings={str(p):sha256(p) for p in (contacts,policy_path)}
        scene=SceneContacts(read(contacts),contacts.parent);policy=read(policy_path);policy_for(policy,scene,bindings[str(contacts)])
        bindings.update(scene.inputs);methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();snapshots={}
        save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
            for index,(path,digest) in enumerate(bindings.items()):
                target=output/'input'/f'{index}{Path(path).suffix}';target.parent.mkdir(exist_ok=True);shutil.copyfile(path,target)
                snapshots[path]=dict(path=target.relative_to(output).as_posix(),sha256=digest)
            save(output/'request.json',dict(at=now(),inputs_sha256=bindings,implementation_sha256=methods,source_snapshots=snapshots))
            result,arrays=evaluate(scene,policy,bindings[str(contacts)])
            np.savez_compressed(output/'observations.npz',**arrays)
            with np.load(output/'observations.npz',allow_pickle=False) as stored:
                if set(stored.files)!=set(arrays) or any(stored[n].dtype!=v.dtype or stored[n].shape!=v.shape or stored[n].tobytes()!=v.tobytes() for n,v in arrays.items()):raise ValueError('Full contact-region array readback changed')
            if any(sha256(p)!=h or sha256(output/snapshots[p]['path'])!=h for p,h in bindings.items()):raise ValueError('Contact-region source changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):raise ValueError('Contact-region methods changed')
            result.update(at=now(),inputs_sha256=bindings,implementation_sha256=methods,source_snapshots=snapshots,
                          observations_sha256=sha256(output/'observations.npz'),arrays_roundtrip_exact=True)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as error:
            save(output/'pipeline.json',dict(status='failed',error=str(error),original_selected=True));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('contacts','policy','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();run(args.contacts,args.policy,args.output)
