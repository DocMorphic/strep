"""Source-bound moving mesh grips and complete sampled scene geometry.

This opt-in layer retains the primitive scene and its original actor assets.
It uses the imported prop triangles, never a bounding-box collision proxy.
It measures authored motion; it does not fit motion or infer grasp/physics.
"""
import argparse
import copy
import hashlib
from itertools import combinations
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from scipy.spatial.transform import Rotation, Slerp
import trimesh

from static_prop_asset import StaticPropAsset
from native_scene_contacts import SceneContacts, fields, scalar, vector, pose, references
from native_scene_contacts import METHODS as CONTACT_METHODS
from native_scene_geometry import faces_for, policy_for, volume_state, evaluate as base_geometry
from triangle_crossing import audit as crossings
from native_containment_crosscheck import penetration, crosscheck, METHOD as CONTAINMENT_METHOD
from native_self_surface import audit as self_surface, METHOD as SELF_METHOD
from triangle_primitive_depth import query as primitive_depth
from engine_contact_sampling import frame_populations, contract_sha256
from native_observation_archive import ObservationArchive, verify
from strep import read, save, sha256

MAX_JSON_BYTES=1024**2
MAX_PROP_BYTES=64*1024**2
MAX_SAMPLES=10000
MAX_ARRAY_BYTES=64*1024**2
METHODS=tuple(sorted(set(CONTACT_METHODS)|{'native_mesh_prop_scene.py','static_prop_asset.py',
    'native_scene_geometry.py','triangle_crossing.py','convex_partner_surface.py','native_containment_crosscheck.py','native_self_surface.py',
    'triangle_primitive_depth.py','native_observation_archive.py'}))


def _json(path,maximum=MAX_JSON_BYTES):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate mesh scene JSON field')
            result[key]=value
        return result
    def constant(_):raise ValueError('Finite mesh scene JSON required')
    with Path(path).open('rb') as stream:raw=stream.read(maximum+1)
    if not raw or len(raw)>maximum:raise ValueError('Bounded nonempty mesh scene JSON required')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=constant),hashlib.sha256(raw).hexdigest()


def _digest(value):
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Explicit lowercase SHA256 required')
    return value


def _path(base,value):
    if not isinstance(value,str) or not value or len(value)>4096:raise ValueError('Explicit source path required')
    return (base/value).resolve()


def guarded_output(output):
    """The resource auditor requires fresh evidence inside this checkout."""
    output=Path(output).resolve();reports=Path(__file__).resolve().parents[1]/'reports'
    if output==reports or not output.is_relative_to(reports) or output.exists():
        raise ValueError('Fresh guarded mesh scene output inside reports required')
    return output


class MeshPropScene:
    def __init__(self,manifest_path):
        path=Path(manifest_path).resolve();spec,digest=_json(path);base=path.parent
        fields(spec,('schema','actor_scene','actor_scene_sha256','props','mesh_contacts'),'mesh prop scene')
        if spec['schema']!='strep-native-mesh-prop-scene-v1':raise ValueError('Explicit mesh prop scene schema required')
        actor_path=_path(base,spec['actor_scene']);actor_spec,actor_digest=_json(actor_path)
        if actor_digest!=_digest(spec['actor_scene_sha256']):raise ValueError('Actor scene binding changed')
        self._scene=SceneContacts(actor_spec,actor_path.parent);self.duration=self._scene.duration
        self._actor_scene_sha256=actor_digest
        self._manifest_sha256=digest;self._manifest_path=path
        self._inputs={str(path):digest,str(actor_path):actor_digest,**self._scene.inputs}
        props=spec['props']
        if not isinstance(props,dict) or not 1<=len(props)<=32:raise ValueError('Declare 1-32 mesh props')
        self._props={};bytes_owned=0
        for name,item in props.items():
            SceneContacts.name(name);fields(item,('glb','sha256','geometry_sha256','keyframes'),'mesh prop')
            if name in self._scene.actors or name in self._scene.objects:raise ValueError('Distinct scene entity names required')
            prop_path=_path(base,item['glb']);prop=StaticPropAsset.load(prop_path)
            if prop.source_sha256!=_digest(item['sha256']) or prop.geometry_sha256!=_digest(item['geometry_sha256']):
                raise ValueError('Mesh prop source or geometry binding changed')
            bytes_owned+=prop.vertices_m.nbytes+prop.faces.nbytes+len(prop.binary)
            if bytes_owned>MAX_PROP_BYTES:raise ValueError('Complete mesh prop geometry exceeds storage budget; no triangles dropped')
            keys=item['keyframes']
            if not isinstance(keys,list) or not 1<=len(keys)<=3601:raise ValueError('Explicit rigid mesh pose keys required')
            times=[];positions=[];rotations=[]
            for key in keys:
                fields(key,('time_s','translation_m','rotation_xyzw'),'mesh prop pose key')
                times.append(scalar(key['time_s'],0,self.duration,'mesh prop time'))
                p,r=pose({k:key[k] for k in ('translation_m','rotation_xyzw')});positions.append(p);rotations.append(r)
            times=np.asarray(times)
            if times[0]!=0 or np.any(np.diff(times)<=0) or len(times)>1 and times[-1]!=self.duration:
                raise ValueError('Mesh pose keys must be static at zero or span the shared duration')
            self._props[name]=dict(asset=prop,times=times,positions=np.asarray(positions),rotations=np.asarray(rotations))
            self._inputs[str(prop_path)]=prop.source_sha256
        contacts=spec['mesh_contacts'];seen={row['authored']['id'] for row in self._scene.rows};self._rows=[]
        if not isinstance(contacts,list) or len(contacts)>64:raise ValueError('Declare 0-64 mesh grip contacts')
        for row in contacts:
            fields(row,('id','actor','vertices','reduction','prop','grip','grip_sha256','mode','interval_s','limits'),'mesh contact')
            SceneContacts.name(row['id'])
            if row['id'] in seen:raise ValueError('Distinct contact IDs required')
            seen.add(row['id'])
            if not isinstance(row['actor'],str) or row['actor'] not in self._scene.actors:raise ValueError('Existing effector actor required')
            if not isinstance(row['prop'],str) or row['prop'] not in self._props:raise ValueError('Existing mesh prop required')
            ids=references(row['vertices'],self._scene.actors[row['actor']]['skin']);SceneContacts.reduction(row['reduction'])
            if row['reduction']=='individual' and len(ids)!=1:raise ValueError('One grip per contact; use an explicit centroid or separate contacts')
            a,b=vector(row['interval_s'],2,'mesh contact interval')
            if not 0<=a<=b<=self.duration or row['mode'] not in ('touch','hold') or (row['mode']=='touch')!=(a==b):
                raise ValueError('Touch needs one time; hold needs a positive in-clip interval')
            fields(row['limits'],('position_m',) if row['mode']=='touch' else ('position_m','relative_speed_m_s'),'mesh contact limits')
            for value in row['limits'].values():scalar(value,0,1e6,'mesh contact limit')
            grip_path=_path(base,row['grip']);grip,grip_digest=_json(grip_path,16384)
            if grip_digest!=_digest(row['grip_sha256']):raise ValueError('Grip file binding changed')
            fields(grip,('schema','label','face','barycentric','position_m','winding_normal','source_sha256','geometry_sha256','space','outward_normal_verified','contact_verified'),'saved mesh grip')
            if type(grip['outward_normal_verified']) is not bool or type(grip['contact_verified']) is not bool:
                raise ValueError('Explicit saved grip approval flags required')
            if not isinstance(grip['label'],str) or not grip['label'].strip() or len(grip['label'])>120:raise ValueError('Saved grip label required')
            prop=self._props[row['prop']]['asset'];point=prop.surface_point(grip['face'],grip['barycentric'])
            if grip!={'schema':'strep-prop-grip-selection-v1','label':grip['label'],**point}:
                raise ValueError('Grip does not reproduce the exact imported prop triangle')
            self._inputs[str(grip_path)]=grip_digest
            self._rows.append(dict(authored=copy.deepcopy(row),ids=ids,point=np.asarray(point['position_m']),normal=np.asarray(point['winding_normal'])))
        self.check_inputs()

    @property
    def inputs(self):return self._inputs.copy()

    def check_inputs(self):
        self._scene.check_inputs()
        if any(sha256(path)!=digest for path,digest in self._inputs.items()):raise ValueError('Mesh scene source changed')

    def prop_poses(self,name,times):
        if not isinstance(name,str) or name not in self._props:raise ValueError('Existing mesh prop required')
        if isinstance(times,(list,tuple)) and any(isinstance(value,(bool,np.bool_)) for value in times):
            raise ValueError('Numeric mesh query times cannot contain booleans')
        raw=np.asarray(times)
        if raw.dtype.kind not in 'fiu' or raw.ndim!=1 or not 1<=len(raw)<=MAX_SAMPLES or not np.isfinite(raw).all() or np.any(np.diff(raw.astype(float))<=0) or np.any(raw<0) or np.any(raw>self.duration):
            raise ValueError('Complete sorted unique in-clip mesh query clock required')
        item=self._props[name];times=raw.astype(float)
        if len(item['times'])==1:return np.repeat(item['positions'],len(times),axis=0),np.repeat(item['rotations'],len(times),axis=0)
        p=np.stack([np.interp(times,item['times'],item['positions'][:,axis]) for axis in range(3)],axis=1)
        return p,Slerp(item['times'],Rotation.from_matrix(item['rotations']))(times).as_matrix()

    def contact_audit(self):
        self.check_inputs()
        native=[channel[2] for actor in self._scene.actors.values() for channel in actor['sampler'].channels]
        native += [item['times'] for item in self._scene.objects.values()]+[item['times'] for item in self._props.values()]
        legacy_bytes=0
        for entry in self._scene.rows:
            row=entry['authored'];a,b=row['interval_s'];populations=frame_populations([a,b]) if row['mode']=='hold' else []
            times=np.unique(np.concatenate([np.array([a,b])]+native+[p['times_s'] for p in populations]));times=times[(times>=a)&(times<=b)]
            count=1 if row['reduction']=='centroid' else len(entry['ids']);legacy_bytes+=len(times)*(1+9*count)*8
            largest=len(entry['ids'])
            if row['target']['space']=='actor':largest=max(largest,len(entry['target_ids']))
            if len(times)>MAX_SAMPLES or len(times)*largest*3*8>MAX_ARRAY_BYTES or legacy_bytes>MAX_ARRAY_BYTES:
                raise ValueError('Complete legacy contact observations exceed mesh-layer budget')
        base,observations=self._scene.evaluate();arrays={'base_'+key:value for key,value in observations.items()};rows=[]
        for ordinal,entry in enumerate(self._rows):
            row=entry['authored'];a,b=row['interval_s'];populations=frame_populations([a,b]) if row['mode']=='hold' else []
            times=np.unique(np.concatenate([np.array([a,b])]+native+[p['times_s'] for p in populations]));times=times[(times>=a)&(times<=b)]
            if len(times)>MAX_SAMPLES:raise ValueError('Complete mesh contact clock exceeds budget; no samples dropped')
            values=[]
            for start in range(0,len(times),32):
                point=self._scene.actor_points(row['actor'],entry['ids'],times[start:start+32])
                values.append(point.mean(axis=1,keepdims=True) if row['reduction']=='centroid' else point)
            effector=np.concatenate(values);p,r=self.prop_poses(row['prop'],times)
            target=np.einsum('fij,j->fi',r,entry['point'])+p;normal=np.einsum('fij,j->fi',r,entry['normal']);world_error=effector-target[:,None];error=np.einsum('fvi,fij->fvj',world_error,r)
            distance=np.linalg.norm(error,axis=2);peak=np.unravel_index(distance.argmax(),distance.shape);speeds=[]
            for population in populations:
                clock=population['times_s'];indices=np.searchsorted(times,clock)
                if not np.array_equal(times[indices],clock):raise ValueError('Complete mesh contact frame population required')
                available=len(clock)>=2;maximum=None
                if available:maximum=float((np.linalg.norm(np.diff(error[indices],axis=0),axis=2)*population['rate_hz']).max())
                speeds.append(dict(id=population['id'],times_s=clock.tolist(),rate_hz=population['rate_hz'],phase_offset_frames=population['phase_offset_frames'],available=available,maximum_relative_speed_m_s=maximum,passed=bool(available and maximum<=row['limits']['relative_speed_m_s'])))
            arrays.update({f'mesh_contact_{ordinal}_times_s':times,f'mesh_contact_{ordinal}_effector_world_m':effector,f'mesh_contact_{ordinal}_target_world_m':target[:,None],f'mesh_contact_{ordinal}_target_winding_normal_world':normal[:,None],f'mesh_contact_{ordinal}_error_object_m':error})
            if sum(array.nbytes for array in arrays.values())>MAX_ARRAY_BYTES:raise ValueError('Complete mesh contact observations exceed budget; no rows dropped')
            maximum=float(distance.max());rows.append(dict(id=row['id'],actor=row['actor'],prop=row['prop'],mode=row['mode'],samples=len(times),vertices=len(entry['ids']),interval_s=row['interval_s'],limits=row['limits'],maximum_position_error_m=maximum,peak_time_s=float(times[peak[0]]),relative_speed_frame='prop local',relative_speed_populations=speeds,orientation_evaluated=False,outward_normal_verified=False,passed=bool(maximum<=row['limits']['position_m'] and all(item['passed'] for item in speeds))))
        self.check_inputs()
        return dict(schema='strep-native-mesh-prop-contact-audit-v1',base_contacts=base,mesh_contacts=rows,inputs_sha256=self.inputs,frame_sampling_contract_sha256=contract_sha256(),all_declared_point_contacts_pass=bool(base['passed'] and all(row['passed'] for row in rows)),point_contact_intent_evaluated=bool(rows or base['point_contact_intent_evaluated']),collision_verified=False,motion_fitted=False,physics_verified=False,quality_approved=False,release_approved=False),arrays

    def _clock(self,policy):
        fields(policy,('schema','mesh_scene_sha256','clock','limits','planes'),'mesh geometry policy')
        if policy['schema']!='strep-native-mesh-prop-geometry-v1' or policy['mesh_scene_sha256']!=self._manifest_sha256:raise ValueError('Geometry policy must bind the mesh scene')
        base=dict(schema='strep-native-scene-geometry-v1',contacts_sha256=self._actor_scene_sha256,clock=copy.deepcopy(policy['clock']),limits=copy.deepcopy(policy['limits']),planes=copy.deepcopy(policy['planes']))
        times,populations,_=policy_for(base,self._scene,base['contacts_sha256'])
        if policy['clock']['mode']=='native-and-frame-populations':
            times=np.unique(np.concatenate([times]+[p['times'] for p in self._props.values()]+[np.array(row['authored']['interval_s']) for row in self._rows]))
        if len(times)>MAX_SAMPLES:raise ValueError('Complete geometry clock exceeds budget; no samples dropped')
        base['clock']=dict(mode='explicit',times_s=times.tolist())
        return times,base,populations

    def geometry(self,policy,*,sample_indices=None,observation_sink=None,query_batch_size=4):
        self.check_inputs();policy=copy.deepcopy(policy);times,base_policy,populations=self._clock(policy)
        if type(query_batch_size) is not int or not 1<=query_batch_size<=32:raise ValueError('Explicit signed-distance batch size1-32 required')
        if isinstance(sample_indices,(list,tuple)) and any(isinstance(value,(bool,np.bool_)) for value in sample_indices):
            raise ValueError('Geometry indices cannot contain booleans')
        selected=np.arange(len(times)) if sample_indices is None else np.asarray(sample_indices)
        if selected.dtype.kind not in 'iu' or selected.ndim!=1 or not len(selected) or np.any(selected<0) or np.any(selected>=len(times)) or np.any(np.diff(selected.astype(np.int64))<=0):raise ValueError('Sorted unique existing geometry indices required')
        actor_faces={name:faces_for(actor['rig'])[0] for name,actor in self._scene.actors.items()}
        vertices_count=sum(sum(len(part['positions']) for part in actor['rig'].primitives) for actor in self._scene.actors.values())+sum(len(prop['asset'].vertices_m) for prop in self._props.values())
        estimated=len(selected)*(vertices_count*3*8+sum(len(f) for f in actor_faces.values())*len(self._scene.objects)*5*8+sum(len(p['asset'].faces) for p in self._props.values())*len(self._scene.objects)*2*8)+len(selected)*8
        if observation_sink is None and estimated>MAX_ARRAY_BYTES:raise ValueError('Use a streaming observation archive for the complete geometry population')
        arrays={} if observation_sink is None else observation_sink
        original,_=base_geometry(self._scene,base_policy,base_policy['contacts_sha256'],sample_indices=selected,observation_sink=arrays,partner_query_batch_size=query_batch_size)
        prop_poses={name:self.prop_poses(name,times[selected]) for name in self._props};primitive_poses={name:self._scene.object_poses(name,times[selected]) for name in self._scene.objects}
        limit=policy['limits']['penetration_m'];tolerance=policy['limits']['surface_tolerance_m'];rows=[]
        for ordinal,index in enumerate(selected):
            index=int(index);stamp=float(times[index]);actor_vertices={};prop_vertices={};faces={};states={};degenerate={};self_surfaces={}
            for name,actor in self._scene.actors.items():
                p,r=actor['placement'];actor_vertices[name]=actor['rig'].vertices(actor['sampler'].sample(stamp))@r.T+p
                faces[('actor',name)]=actor_faces[name]
            for name,prop in self._props.items():
                p,r=prop_poses[name];prop_vertices[name]=prop['asset'].vertices_m@r[ordinal].T+p[ordinal];faces[('prop',name)]=prop['asset'].faces
            meshes={('actor',name):v for name,v in actor_vertices.items()}|{('prop',name):v for name,v in prop_vertices.items()}
            for key,v in meshes.items():
                _,states[key]=volume_state(v,faces[key]);tri=v[faces[key]];degenerate[key]=np.flatnonzero(np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)<=tolerance**2).tolist()
                own=(original['samples'][ordinal]['self_surfaces'][key[1]] if key[0]=='actor'
                    else self_surface(v,faces[key],tolerance_m=tolerance))
                self_surfaces[key]=own;eligible=not own['records'] and not own['degenerate_faces']
                states[key].update(self_intersection_checked=True,self_surface_method=SELF_METHOD,
                    containment_blocked_by_self_geometry=not eligible,
                    containment_available=bool(states[key]['containment_available'] and eligible),
                    containment_scope='Topology and sampled self-surface eligibility only; point consensus remains required. No solid certificate.')
                arrays[f'mesh_frame_{index}_{key[0]}_{key[1]}_world_m']=v
            def pair(left,right):
                surface=crossings(meshes[left],faces[left],meshes[right],faces[right],tolerance_m=tolerance);depths=[]
                for a,b in [(left,right),(right,left)]:
                    if states[b]['containment_available'] and not degenerate[b]:
                        measure=penetration(meshes[a],meshes[b],faces[b],tolerance_m=max(limit,1e-12),query_batch_size=query_batch_size,surface_tolerance_m=tolerance)
                        depths.append(dict(source=list(a),target=list(b),**measure))
                    else:depths.append(dict(source=list(a),target=list(b),available=False))
                passed=bool(not surface['records'] and not any(surface['degenerate_faces']) and all(item['available'] and item['max_depth_m']<=limit for item in depths))
                return dict(left=list(left),right=list(right),surface=surface,vertex_containment=depths,passed=passed)
            pairs=[pair(('actor',actor),('prop',prop)) for actor in actor_vertices for prop in prop_vertices]
            pairs += [pair(('prop',a),('prop',b)) for a,b in combinations(prop_vertices,2)]
            primitive_pairs=[];planes=[]
            for name,vertices in prop_vertices.items():
                key=('prop',name);mesh,_=volume_state(vertices,faces[key])
                for other,obj in self._scene.objects.items():
                    p,r=primitive_poses[other];depth=primitive_depth(vertices[faces[key]],obj['geometry'],p[ordinal],r[ordinal],resolution_m=policy['limits']['depth_resolution_m'])
                    containment='unavailable'
                    if states[key]['containment_available'] and not degenerate[key]:
                        check=crosscheck(vertices,faces[key],p[ordinal][None],surface_tolerance_m=tolerance)
                        containment=check['states'][0]
                    hi=float(depth['upper_m'].max());passed=bool(hi<=limit and not degenerate[key] and not len(depth['degenerate_faces']) and containment=='outside')
                    primitive_pairs.append(dict(prop=name,object=other,maximum_depth_lower_m=float(depth['lower_m'].max()),maximum_depth_upper_m=hi,containment=containment,total_faces=len(faces[key]),passed=passed))
                    prefix=f'mesh_frame_{index}_prop{len(name)}_{name}_object{len(other)}_{other}'
                    arrays[prefix+'_depth_lower_m']=depth['lower_m'];arrays[prefix+'_depth_upper_m']=depth['upper_m']
                for plane_name,plane in policy['planes'].items():
                    used=np.unique(faces[key]);distances=vertices@np.array(plane['normal_world'])-plane['offset_m'];peak=int(used[distances[used].argmin()]);depth=max(0.,-float(distances[peak]))
                    planes.append(dict(prop=name,plane=plane_name,maximum_depth_m=depth,peak_vertex=peak,passed=bool(depth<=limit and not degenerate[key])))
            previous=original['samples'][ordinal];conditions=previous['actor_objects']+previous['actor_pairs']+previous['world_planes']+pairs+primitive_pairs+planes
            passed=bool(previous['passed'] or not previous['conditions_available']) and bool(conditions and all(item['passed'] for item in conditions) and not any(degenerate.values())
                and all(not s['records'] and not s['degenerate_faces'] for s in self_surfaces.values()))
            rows.append(dict(index=index,time_s=stamp,base_scene=previous,mesh_pairs=pairs,mesh_primitive_pairs=primitive_pairs,mesh_world_planes=planes,
                self_surfaces=[dict(kind=key[0],name=key[1],audit=value) for key,value in self_surfaces.items()],
                volumes=[dict(kind=key[0],name=key[1],**value) for key,value in states.items()],passed=passed))
        self.check_inputs()
        report=dict(schema='strep-native-mesh-prop-geometry-result-v1',samples=rows,inputs_sha256=self.inputs,limits=policy['limits'],clock_mode=policy['clock']['mode'],complete_clock_s=times.tolist(),sample_indices=selected.tolist(),times_s=times[selected].tolist(),frame_populations=[dict(id=p['id'],times_s=p['times_s'].tolist()) for p in populations],all_policy_samples_evaluated=len(selected)==len(times),sampled_conditions_pass=all(row['passed'] for row in rows),actor_faces={name:len(value) for name,value in actor_faces.items()},prop_faces={name:len(prop['asset'].faces) for name,prop in self._props.items()},query_batch_size=query_batch_size,topology_modified=False,collision_verified=False,continuous_collision_certified=False,self_collision_verified=False,motion_fitted=False,physics_verified=False,quality_approved=False,release_approved=False,scope='Complete imported actor/prop triangles at declared selected times. Includes legacy actor/primitive/plane/partner checks, all actor/mesh-prop pairs, mesh-prop/mesh-prop pairs, mesh-prop/legacy-primitive pairs and prop/world planes. Crossing/boundary/near outcomes and unavailable outward-volume containment fail sampled conditions. Original primitive/primitive, continuous-time, dynamics, engine and semantic checks remain separate. No geometry proxy, topology repair, fit or release approval.')
        report['containment_method']=CONTAINMENT_METHOD
        report['self_surface_method']=SELF_METHOD
        report['scope']+=' Every actor/prop receives a complete sampled self-surface screen; crossings, ambiguous records and degeneracy block containment and sampled acceptance. Containment also requires signed/ray/winding consensus. No valid-solid or continuous self-collision certificate.'
        return report,arrays


def run(manifest_path,policy_path,output,*,start=0,count=None):
    manifest_path=Path(manifest_path).resolve();policy_path=Path(policy_path).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh mesh scene evaluation output required')
    scene=MeshPropScene(manifest_path);policy,policy_digest=_json(policy_path);times,_,_=scene._clock(policy)
    count=len(times)-start if count is None else count
    if type(start) is not int or type(count) is not int or not 0<=start<len(times) or not 1<=count<=len(times)-start:raise ValueError('Explicit complete existing geometry slice required')
    bindings={**scene.inputs,str(policy_path):policy_digest};methods={name:sha256(Path(__file__).parent/name) for name in METHODS}
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
    for name in METHODS:shutil.copyfile(Path(__file__).parent/name,archive/name)
    save(output/'input.json',dict(inputs_sha256=bindings,implementation_sha256=methods,start=start,count=count,complete_clock_s=times.tolist(),quality_approved=False))
    contact,arrays=scene.contact_audit();save(output/'contacts.json',contact);np.savez_compressed(output/'contact-observations.npz',**arrays)
    with ObservationArchive(output/'geometry-observations.npz',maximum_array_bytes=MAX_ARRAY_BYTES) as sink:
        geometry,_=scene.geometry(policy,sample_indices=np.arange(start,start+count),observation_sink=sink)
    verify(output/'geometry-observations.npz');save(output/'geometry.json',geometry)
    if any(sha256(path)!=digest for path,digest in bindings.items()) or any(sha256(Path(__file__).parent/name)!=digest or sha256(archive/name)!=digest for name,digest in methods.items()):raise ValueError('Mesh scene source or implementation changed')
    result=dict(status='complete',schema='strep-native-mesh-prop-evaluation-v1',point_contacts_pass=contact['all_declared_point_contacts_pass'],sampled_geometry_pass=geometry['sampled_conditions_pass'],mesh_contacts=len(contact['mesh_contacts']),geometry_samples=count,complete_geometry_samples=len(times),all_geometry_samples_evaluated=count==len(times),original_selected=True,motion_fitted=False,quality_approved=False,release_approved=False)
    save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','policy','output']:parser.add_argument(name,type=Path)
    parser.add_argument('--start',type=int,default=0);parser.add_argument('--count',type=int);parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(),threadpool_limits(limits=1):print(run(args.manifest,args.policy,args.output,start=args.start,count=args.count))
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run as guarded
        from audit_guarded_job import audit
        args.output=guarded_output(args.output)
        arguments=[str(args.manifest.resolve()),str(args.policy.resolve()),str(args.output.resolve()/'evaluation'),'--worker','--start',str(args.start)]
        if args.count is not None:arguments+=['--count',str(args.count)]
        result=guarded(Path(__file__),args.output/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,stable_seconds=15,admission_seconds=600,max_seconds=900),worker_args=arguments)
        save(args.output/'resource-replay.json',audit(args.output/'guard'));print(result)
        raise SystemExit({'complete':0,'failed':1,'deferred':2}[result['status']])
