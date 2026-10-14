"""Contact/floor initialization at existing native keys; complete clip audit required.

This explicitly different temporal representation is a proposal, not permission
to replace an earlier bounded fit or to reset its original motion-rate reference.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import time
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from bounded_pose_ik import hierarchy_order
from gltf_tools import append_accessor,write_glb
from native_scene_contacts import SceneContacts,fields
from native_scene_geometry import faces_for,policy_for,evaluate_to_archive
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from sampled_motion_caps import features,measures,SampledMotionCaps
from strep import ROOT,read,save,sha256,now
from native_key_boundaries import boundary_policy,key_frozen
from native_affine_key_pose import AffineKeyPose,rotation_fractions
from native_motion_orientation import extract as orientation_features,MODES as ORIENTATION_MODES

SCHEMA='strep-native-key-contact-initializer-v1'


def right_jacobian(vector):
    x,y,z=vector;hat=np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
    angle=np.linalg.norm(vector)
    if angle<1e-6:return np.eye(3)-.5*hat+hat@hat/6
    return np.eye(3)-(1-np.cos(angle))/angle**2*hat+(angle-np.sin(angle))/angle**3*hat@hat


class KeyPose:
    """Exact complete skin derivatives, point targets and plane inequalities."""
    def __init__(self,scene,actor,time_s,nodes,degrees,displacement,planes,penetration,reserve,*,pose_representation='rigid'):
        if pose_representation not in ('rigid','native-trs-v1'):raise ValueError('Explicit supported pose representation required')
        self.scene=scene;self.actor=actor;self.time=float(time_s);self.nodes=list(nodes)
        a=scene.actors[actor];self.rig=a['rig'];self.skin=a['skin'];self.placement=a['placement']
        self.source=a['sampler'].sample(self.time);self.order=hierarchy_order(self.rig.parents)
        self.local=self.source.copy()
        for n,p in enumerate(self.rig.parents):
            if p>=0:self.local[n]=np.linalg.solve(self.source[p],self.source[n])
        if pose_representation=='rigid' and (np.max(abs(self.local[:,:3,:3].swapaxes(-1,-2)@self.local[:,:3,:3]-np.eye(3)))>1e-8
                or np.max(abs(np.linalg.det(self.local[:,:3,:3])-1))>1e-8):
            raise ValueError('Proper rigid source locals required')
        self.affine=AffineKeyPose(a,self.time,nodes,degrees) if pose_representation=='native-trs-v1' else None
        self.caps=np.radians(degrees);self.displacement=float(displacement)
        self.planes=copy.deepcopy(planes);self.penetration=penetration;self.reserve=reserve
        self.used=np.unique(faces_for(self.rig)[0]);self.desc=[]
        for edited in self.nodes:
            affected=[]
            for n in range(len(self.rig.parents)):
                while n>=0 and n!=edited:n=self.rig.parents[n]
                affected.append(n==edited)
            self.desc.append(np.asarray(affected,bool))
        self.affected=np.any(self.desc,axis=0);self.cache=None;self.calls=0
        self.contacts=[]
        for entry in scene.rows:
            row=entry['authored'];target=row['target'];a,b=row['interval_s']
            if not a<=self.time<=b:continue
            if row['actor']==actor:sign=1;ids=entry['ids'];reduction=row['reduction']
            elif target['space']=='actor' and target['actor']==actor:sign=-1;ids=entry['target_ids'];reduction=target['reduction']
            else:continue
            if sign<0:
                fixed=scene.actor_points(row['actor'],entry['ids'],np.array([self.time]))[0]
                if row['reduction']=='centroid':fixed=fixed.mean(0,keepdims=True)
            elif target['space']=='actor':
                fixed=scene.actor_points(target['actor'],entry['target_ids'],np.array([self.time]))[0]
                if target['reduction']=='centroid':fixed=fixed.mean(0,keepdims=True)
            elif target['space']=='object':
                p,r=scene.object_poses(target['object'],np.array([self.time]));fixed=entry['target_ids']@r[0].T+p[0]
            else:fixed=entry['target_ids']
            self.contacts.append((ids,reduction,fixed,row['limits']['position_m']))

    def evaluate(self,value):
        value=np.asarray(value,float)
        if value.shape!=(3*len(self.nodes),) or not np.isfinite(value).all():raise ValueError('Complete finite pose controls required')
        if self.cache is not None and np.array_equal(value,self.cache[0]):return self.cache[1]
        self.calls+=1
        if self.affine is not None:
            world,vertices,jac,jj=self.affine.evaluate(value)
            joints=np.asarray(self.rig.joints);positions=world[joints,:3,3]
        else:
            world=self.source.copy();local=self.local.copy();vectors=value.reshape(-1,3)*self.caps[:,None]
            local[self.nodes,:3,:3]=self.local[self.nodes,:3,:3]@Rotation.from_rotvec(vectors).as_matrix()
            for n in self.order:
                if self.affected[n]:world[n]=world[self.rig.parents[n]]@local[n] if self.rig.parents[n]>=0 else local[n]
            skin=self.skin;components=np.einsum('vkij,vkj->vki',world[skin.nodes,:3,:],skin.points)
            vertices=np.einsum('vki,vk->vi',components,skin.weights)
            jac=np.zeros((len(vertices),3,len(value)));jj=np.zeros((len(self.rig.joints),3,len(value)))
            joints=np.asarray(self.rig.joints);positions=world[joints,:3,3]
            for k,(node,vector,cap,desc) in enumerate(zip(self.nodes,vectors,self.caps,self.desc)):
                axes=world[node,:3,:3]@right_jacobian(vector)*cap
                # Retain the actual inverse-bind homogeneous coordinate, including
                # non-unit terms; a pivot translation acts on that coordinate.
                delta=np.einsum('vki,vk->vi',components-world[node,:3,3]*skin.points[:,:,3,None],skin.weights*desc[skin.nodes])
                joint_delta=(positions-world[node,:3,3])*desc[joints,None]
                for component in range(3):
                    jac[:,:,3*k+component]=np.cross(axes[:,component],delta)
                    jj[:,:,3*k+component]=np.cross(axes[:,component],joint_delta)
        p,r=self.placement;vertices=vertices@r.T+p;jac=np.einsum('ij,vjk->vik',r,jac)
        rows=[1-np.sum(value.reshape(-1,3)**2,axis=1)];derivatives=[]
        balls=np.zeros((len(self.nodes),len(value)))
        for k in range(len(self.nodes)):balls[k,3*k:3*k+3]=-2*value[3*k:3*k+3]
        derivatives.append(balls)
        delta=positions-self.source[joints,:3,3];radius=self.displacement
        rows.append(1-np.sum(delta*delta,axis=1)/radius**2)
        derivatives.append(-2*np.einsum('ji,jik->jk',delta,jj)/radius**2)
        for plane in self.planes.values():
            normal=np.asarray(plane['normal_world']);scale=max(self.penetration,.001)
            rows.append((vertices[self.used]@normal-plane['offset_m']+self.penetration-self.reserve)/scale)
            derivatives.append(np.einsum('i,vik->vk',normal,jac[self.used])/scale)
        for ids,reduction,fixed,limit in self.contacts:
            point=vertices[ids];derivative=jac[ids]
            if reduction=='centroid':point=point.mean(0,keepdims=True);derivative=derivative.mean(0,keepdims=True)
            error=point-fixed;scale=max(limit,.0001)**2
            rows.append((limit**2-np.sum(error*error,axis=1))/scale)
            derivatives.append(-2*np.einsum('vi,vik->vk',error,derivative)/scale)
        result=(np.concatenate(rows),np.vstack(derivatives),world,vertices)
        if not all(np.isfinite(a).all() for a in result):raise ValueError('Nonfinite complete pose observations')
        self.cache=(value.copy(),result);return result

    def solve(self,iterations,deadline):
        zero=np.zeros(3*len(self.nodes));before=self.evaluate(zero)[0]
        if np.all(before>=0):return zero,dict(solved=False,calls=self.calls,pose_conditions_pass=True)
        def observed(x):
            if time.monotonic()>deadline:raise TimeoutError('Explicit complete-key initialization time budget exhausted')
            return self.evaluate(x)
        result=minimize(lambda x:float(x@x),zero,jac=lambda x:2*x,method='SLSQP',bounds=[(-1,1)]*len(zero),
            constraints=dict(type='ineq',fun=lambda x:observed(x)[0],jac=lambda x:observed(x)[1]),
            options=dict(maxiter=iterations,ftol=1e-12))
        finite=np.isfinite(result.x).all();passed=bool(finite and np.all(observed(result.x)[0]>=-1e-7))
        selected=result.x.copy() if passed else zero
        return selected,dict(solved=True,solver_success=bool(result.success),message=str(result.message),iterations=int(result.nit),
            calls=self.calls,pose_conditions_pass=passed,candidate_controls=result.x.tolist() if finite else None,
            minimum_candidate_inequality=float(observed(result.x)[0].min()) if finite else None,
            failed_pose_retains_original=not passed)


def prepare(scene,request,digest,policy):
    if not isinstance(request,dict):raise ValueError('Explicit key initializer object required')
    optional={'pose_representation','orientation_mode','boundary_keys','acknowledge_changed_boundary_compatibility'}
    fields({k:v for k,v in request.items() if k not in optional},('schema','contacts_sha256','actor','root_node','rotations','window_s','frozen_times_s',
        'maximum_joint_displacement_m','maximum_keys','iterations_per_key','maximum_seconds','floor_reserve_m'),'key initializer')
    if request.get('pose_representation','rigid') not in ('rigid','native-trs-v1') or request.get('orientation_mode','strict') not in ORIENTATION_MODES:raise ValueError('Explicit supported pose/orientation modes required')
    if request['schema']!=SCHEMA or request['contacts_sha256']!=digest:raise ValueError('Original-bound explicit key initializer required')
    name=request['actor']
    if name not in scene.actors:raise ValueError('Existing selected actor required')
    actor=scene.actors[name];rig=actor['rig'];root=request['root_node'];rows=request['rotations']
    if type(root) is not int or root not in rig.joints or not isinstance(rows,list) or not 1<=len(rows)<=16:raise ValueError('Existing fixed root and 1-16 explicit rotation tracks required')
    nodes=[];caps=[];channels=[]
    for row in rows:
        fields(row,('node','maximum_degrees'),'key rotation permission');n=row['node'];cap=row['maximum_degrees']
        if type(n) is not int or n not in rig.joints or n in nodes or n==root:raise ValueError('Distinct existing non-root skin joints required')
        parent=n
        while parent>=0 and parent!=root:parent=rig.parents[parent]
        if parent!=root:raise ValueError('Edited rotations must descend from the fixed root')
        if type(cap) not in (int,float) or not np.isfinite(cap) or not 0<cap<=30:raise ValueError('Explicit rotation caps up to 30 degrees required')
        found=[c for c in actor['sampler'].channels if c[:2]==(n,'rotation')]
        if len(found)!=1 or found[0][4]!='LINEAR':raise ValueError('One existing LINEAR rotation channel per edited joint required')
        nodes.append(n);caps.append(cap);channels.append(found[0])
    clock=channels[0][2]
    if any(not np.array_equal(c[2],clock) for c in channels):raise ValueError('Identical existing selected native clocks required; no keys inserted')
    maximum=request['maximum_keys'];iterations=request['iterations_per_key'];seconds=request['maximum_seconds']
    displacement=request['maximum_joint_displacement_m'];reserve=request['floor_reserve_m']
    for key in ('window_s','frozen_times_s'):
        if not isinstance(request[key],list) or any(type(v) not in (int,float) for v in request[key]):raise ValueError('Explicit numeric window and frozen-key times required')
    window=np.asarray(request['window_s'],float);frozen=np.asarray(request['frozen_times_s'],float)
    if type(maximum) is not int or not 2<=maximum<=4096 or len(clock)>maximum:raise ValueError('Complete native clock must fit explicit 2-4096 key budget')
    if type(iterations) is not int or not 1<=iterations<=150:raise ValueError('Choose 1-150 iterations per key')
    if type(seconds) not in (int,float) or not np.isfinite(seconds) or not 1<=seconds<=600:raise ValueError('Choose a finite 1-600 second complete-key budget')
    if type(displacement) not in (int,float) or not np.isfinite(displacement) or not 0<displacement<=.22:raise ValueError('Explicit positive joint displacement bound up to 22 cm required')
    if type(reserve) not in (int,float) or not np.isfinite(reserve) or not 0<=reserve<policy['limits']['penetration_m']:raise ValueError('Floor reserve must fit the unchanged authored tolerance')
    if window.shape!=(2,) or not np.isfinite(window).all() or not 0<=window[0]<window[1]<=scene.duration or not np.isin(window,clock).all():raise ValueError('Finite editable source window must use existing selected native keys')
    if frozen.ndim!=1 or not np.isfinite(frozen).all() or len(np.unique(frozen))!=len(frozen) or not np.isin(frozen,clock).all():raise ValueError('Every explicit frozen time must be an original selected native key')
    boundaries=boundary_policy(request,clock)
    if ((boundaries['start']=='edit' and float(clock[0])!=0.)
            or (boundaries['end']=='edit' and float(clock[-1])!=scene.duration)):
        raise ValueError('Endpoint edits require the actual clip boundary, not an interior channel endpoint')
    if len(scene.actors[name]['skin'].nodes)>32768 or not policy['planes']:raise ValueError('Complete skin up to 32768 vertices and at least one explicit plane required')
    point_rows=0
    for entry in scene.rows:
        row=entry['authored'];target=row['target']
        if row['actor']==name:point_rows+=1 if row['reduction']=='centroid' else len(entry['ids'])
        elif target['space']=='actor' and target['actor']==name:point_rows+=1 if target['reduction']=='centroid' else len(entry['target_ids'])
    count=len(nodes)+len(rig.joints)+len(np.unique(faces_for(rig)[0]))*len(policy['planes'])+point_rows
    if count>100000:raise ValueError('Complete pose population exceeds 100000 scalar conditions; no subset selected')
    return name,nodes,caps,clock.copy(),channels


def encode(rig,index,nodes,channels,controls,caps,path):
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=copy.deepcopy(document['animations'][index])
    animation['name']='Strep_native_key_contact_initializer'
    for node,channel,delta,cap in zip(nodes,channels,controls.transpose(1,0,2),caps):
        values=channel[3].copy();active=np.any(delta!=0,axis=1)
        if np.any(active):
            result=(Rotation.from_quat(values[active])*Rotation.from_rotvec(delta[active]*np.radians(cap))).as_quat()
            result[np.sum(result*values[active],axis=1)<0]*=-1;values[active]=result
        chosen=next(c for c in animation['channels'] if c['target'].get('node')==node and c['target'].get('path')=='rotation')
        sampler=copy.deepcopy(animation['samplers'][chosen['sampler']]);sampler['output']=append_accessor(document,binary,values,'VEC4')
        chosen['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
    output_index=len(document['animations']);document['animations'].append(animation);write_glb(path,document,binary)
    return output_index


def run(contacts,geometry,request_path,output):
    contacts,geometry,request_path,output=map(lambda p:Path(p).resolve(),(contacts,geometry,request_path,output))
    if output.exists():raise FileExistsError(output)
    with worker_lock(),threadpool_limits(limits=1):
        spec=read(contacts);scene=SceneContacts(spec,contacts.parent);policy=read(geometry);digest=sha256(contacts)
        geometry_times,_,_=policy_for(policy,scene,digest);request=read(request_path)
        name,nodes,caps,clock,channels=prepare(scene,request,digest,policy);actor=scene.actors[name]
        uniform=np.arange(int(np.floor(scene.duration*120))+1)/120
        source_uniform=np.array([actor['sampler'].sample(float(t)) for t in uniform])
        orientation_mode=request.get('orientation_mode','strict')
        original_payload,_,original_affine=orientation_features(source_uniform,actor['rig'].joints,orientation_mode)
        rates=SampledMotionCaps(original_payload,uniform,np.linspace(0,scene.duration,5),tolerance=1e-5)
        pins={str(p):sha256(p) for p in (contacts,geometry,request_path)};pins.update(scene.inputs)
        methods={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}
        if any(Path(p).is_relative_to(output) for p in pins):raise ValueError('Original inputs must remain outside fresh output')
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        save(output/'request.json',dict(request=request,source_bindings_sha256=pins,implementation_sha256=methods,
            source_animation_index=actor['animation_index'],temporal_representation='Independent existing native-key rotations, not the previous bounded-knot fit',quality_approved=False))
        values=np.zeros((len(clock),len(nodes),3));records=[];deadline=time.monotonic()+request['maximum_seconds']
        for index,stamp in enumerate(clock):
            pose=KeyPose(scene,name,float(stamp),nodes,caps,request['maximum_joint_displacement_m'],policy['planes'],policy['limits']['penetration_m'],request['floor_reserve_m'],pose_representation=request.get('pose_representation','rigid'))
            frozen=key_frozen(request,clock,stamp)
            if frozen:record=dict(solved=False,frozen=True,pose_conditions_pass=bool(np.all(pose.evaluate(values[index].ravel())[0]>=0)))
            else:
                try:
                    selected,record=pose.solve(request['iterations_per_key'],deadline);values[index]=selected.reshape(len(nodes),3)
                except (TimeoutError,ValueError,FloatingPointError) as error:
                    save(output/'failed-key.json',dict(time_s=float(stamp),completed_keys=len(records),error=type(error).__name__+': '+str(error),original_selected=True,quality_approved=False))
                    if pose.cache is not None:
                        cached=pose.cache[1]
                        np.savez_compressed(output/'failed-key-observations.npz',controls=pose.cache[0],constraints=cached[0],jacobian=cached[1],world=cached[2],vertices=cached[3])
                    raise
            records.append(dict(time_s=float(stamp),**record))
            with (output/'key-results.jsonl').open('a',encoding='utf-8') as journal:journal.write(json.dumps(records[-1],allow_nan=False)+'\n')
            np.savez_compressed(output/'key-checkpoint.npz',times_s=clock,controls=values,completed_keys=len(records))
            save(output/'key-progress.json',dict(completed_keys=len(records),planned_keys=len(clock),original_selected=True))
        save(output/'key-results.json',records);np.savez_compressed(output/'key-controls.npz',times_s=clock,controls=values)
        candidate=output/'character.glb';new_index=encode(actor['rig'],actor['animation_index'],nodes,channels,values,caps,candidate)
        derived=copy.deepcopy(spec)
        for n in derived['actors']:derived['actors'][n]['glb']=str((contacts.parent/derived['actors'][n]['glb']).resolve())
        derived['actors'][name].update(glb=str(candidate),sha256=sha256(candidate),animation_index=new_index)
        save(output/'contacts.json',derived);new_digest=sha256(output/'contacts.json');decoded=SceneContacts(derived,output)
        contact_report,contact_arrays=decoded.evaluate();save(output/'contact-result.json',contact_report);np.savez_compressed(output/'contact-observations.npz',**contact_arrays)
        geo=copy.deepcopy(policy);geo['contacts_sha256']=new_digest;save(output/'geometry.json',geo)
        surface,arrays=evaluate_to_archive(decoded,geo,new_digest,output/'geometry-observations.npz');surface.update(**arrays);save(output/'geometry-result.json',surface)
        uniform=np.arange(int(np.floor(scene.duration*120))+1)/120
        times=np.unique(np.concatenate([geometry_times,uniform,clock]+[a for k,a in contact_arrays.items() if k.endswith('_times_s')]))
        before=np.asarray([actor['sampler'].sample(float(t)) for t in times]);after=np.asarray([decoded.actors[name]['sampler'].sample(float(t)) for t in times]);ids=np.searchsorted(times,uniform);joints=actor['rig'].joints
        if not np.array_equal(before[ids],source_uniform):raise ValueError('Original rate epoch changed during initialization')
        candidate_payload,_,candidate_affine=orientation_features(after[ids],joints,orientation_mode)
        residual=np.concatenate([((v-c-rates.tolerance)/np.maximum(c,.001)).ravel() for v,c in zip(measures(candidate_payload,rates.dt),rates.caps)])
        np.savez_compressed(output/'motion-observations.npz',times_s=times,source_world=before,candidate_world=after,uniform_times_s=uniform,rate_residual=residual,
            **{f'metric_{i}':c for i,c in enumerate(rates.caps)},**{'source_'+k:v for k,v in original_affine.items()},**{'candidate_'+k:v for k,v in candidate_affine.items()})
        displacement=float(np.linalg.norm(after[:,joints,:3,3]-before[:,joints,:3,3],axis=-1).max())
        if request.get('pose_representation','rigid')=='native-trs-v1':
            angles=rotation_fractions(actor,decoded.actors[name],times,nodes,caps)
        else:
            angles=[]
            for node,cap in zip(nodes,caps):
                parent=actor['rig'].parents[node];a=np.linalg.solve(before[:,parent],before[:,node]);b=np.linalg.solve(after[:,parent],after[:,node])
                angles.append(float(np.rad2deg(np.linalg.norm(Rotation.from_matrix(a[:,:3,:3].swapaxes(-1,-2)@b[:,:3,:3]).as_rotvec(),axis=1)).max())/cap)
        root_error=float(abs(after[:,request['root_node']]-before[:,request['root_node']]).max())
        edit_pass=bool(max(angles)<=1 and displacement<=request['maximum_joint_displacement_m'] and root_error==0)
        result=dict(schema=SCHEMA,status='complete',at=now(),keys=len(clock),pose_failures=sum(not r['pose_conditions_pass'] for r in records),
            glb_sha256=sha256(candidate),output_animation_index=new_index,maximum_joint_displacement_m=displacement,maximum_rotation_fraction=max(angles),root_world_element_error=root_error,
            decoded_edit_samples_pass=edit_pass,contact_samples_pass=contact_report['passed'],geometry_samples_pass=surface['sampled_conditions_pass'],
            original_rate_rows=len(residual),failed_original_rate_rows=int((residual>0).sum()),original_motion_caps_pass=bool(np.all(residual<=0)),
            sampled_conditions_pass=bool(edit_pass and contact_report['passed'] and surface['sampled_conditions_pass'] and np.all(residual<=0)),
            **(dict(pose_representation=request.get('pose_representation','rigid'),orientation_mode=orientation_mode) if any(k in request for k in ('pose_representation','orientation_mode')) else {}),
            **(dict(boundary_contract_changed=any(v=='edit' for v in boundary_policy(request,clock).values())) if 'boundary_keys' in request else {}),
            original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,
            scope='Independent existing-key pose initializer with original per-pose bounds and point/floor intent, followed by complete decoded geometry/contact/edit and original 120-Hz four-bin rate audits. Different temporal representation; no prior fit-contract, continuous collision, balance, anatomy, engine or human approval.')
        scene.check_inputs()
        if any(sha256(p)!=h for p,h in pins.items()) or any(sha256(ROOT/'scripts'/n)!=h for n,h in methods.items()):raise ValueError('Original inputs or methods changed')
        save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('contacts','geometry','request','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();run(args.contacts,args.geometry,args.request,args.output)
