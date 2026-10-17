"""Bounded, source-relative prop pose edits about an authored mesh grip.

Characters, geometry, grip selections, times and all undeclared keys remain
unchanged. A finite orientation search is a proposal method, never a global
feasibility test or full-motion/physics/engine/human approval.
"""
import argparse
import copy
import hashlib
from itertools import product
import json
from pathlib import Path
import shutil

import numpy as np
from scipy.spatial.transform import Rotation

from native_mesh_prop_scene import MeshPropScene,_json,_path,_digest,guarded_output,METHODS as SCENE_METHODS
from native_scene_contacts import fields,scalar,vector
from native_observation_archive import ObservationArchive,verify
from strep import save,sha256

METHODS=tuple(sorted(set(SCENE_METHODS)|{'native_mesh_prop_pose.py'}))


def _bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


class GripPoseEdit:
    def __init__(self,permissions_path):
        path=Path(permissions_path).resolve();spec,digest=_json(path)
        fields(spec,('schema','mesh_scene','mesh_scene_sha256','prop','key_index','contact_id','frozen_keys','maximum_rotation_degrees','maximum_translation_m','maximum_clearance_m','clearance_direction_local'),'mesh prop pose permissions')
        if spec['schema']!='strep-native-mesh-prop-pose-edit-v1':raise ValueError('Explicit mesh pose edit schema required')
        scene_path=_path(path.parent,spec['mesh_scene']);self.scene=MeshPropScene(scene_path)
        if self.scene._manifest_sha256!=_digest(spec['mesh_scene_sha256']):raise ValueError('Original mesh scene binding changed')
        if not isinstance(spec['prop'],str) or spec['prop'] not in self.scene._props:raise ValueError('Existing editable prop required')
        self._source,source_digest=_json(scene_path)
        if source_digest!=self.scene._manifest_sha256:raise ValueError('Original mesh scene snapshot changed')
        self._spec=copy.deepcopy(spec);self._path=path;self._base=scene_path.parent
        self._inputs={**self.scene.inputs,str(path):digest};self._name=spec['prop'];self._key=spec['key_index'];self._item=self._source['props'][self._name];keys=self._item['keyframes']
        if type(self._key) is not int or not 0<=self._key<len(keys):raise ValueError('Explicit existing editable prop key required')
        frozen=spec['frozen_keys']
        if not isinstance(frozen,list) or any(type(key) is not int or not 0<=key<len(keys) for key in frozen) or len(set(frozen))!=len(frozen) or self._key in frozen:
            raise ValueError('Distinct explicit frozen keys must exclude the edited key')
        matches=[entry for entry in self.scene._rows if entry['authored']['id']==spec['contact_id'] and entry['authored']['prop']==self._name]
        if len(matches)!=1:raise ValueError('One existing authored grip contact for this prop required')
        entry=matches[0];self._point=entry['point'].copy();self._angle=scalar(spec['maximum_rotation_degrees'],0,180,'rotation edit cap')
        self._translation=scalar(spec['maximum_translation_m'],0,10,'translation edit cap');self._clearance=scalar(spec['maximum_clearance_m'],0,.1,'clearance edit cap')
        self._direction=vector(spec['clearance_direction_local'],3,'authored local clearance direction')
        if abs(np.linalg.norm(self._direction)-1)>1e-8:raise ValueError('Unit authored local clearance direction required')
        self._position,self._rotation=self.scene._props[self._name]['positions'][self._key].copy(),self.scene._props[self._name]['rotations'][self._key].copy()
        self._pivot=self._position+self._rotation@self._point;self.check_inputs()

    @property
    def inputs(self):return self._inputs.copy()

    def check_inputs(self):
        self.scene.check_inputs()
        if any(sha256(path)!=digest for path,digest in self._inputs.items()):raise ValueError('Prop pose edit source changed')

    def _value(self,value):
        if isinstance(value,(list,tuple)) and any(isinstance(v,(bool,np.bool_)) for v in value):raise ValueError('Numeric controls cannot contain booleans')
        raw=np.asarray(value)
        if raw.dtype.kind not in 'fiu' or raw.dtype.itemsize>8 or raw.shape!=(4,) or not np.isfinite(raw).all() or np.any(np.abs(raw[:3])>1) or not 0<=raw[3]<=1:
            raise ValueError('Four finite complete controls: rotation xyz in[-1,1], clearance in[0,1] required')
        value=raw.astype(float,copy=True)
        if self._angle==0 and np.any(value[:3]) or self._clearance==0 and value[3]!=0:raise ValueError('A locked pose component cannot be changed')
        return value

    def evaluate(self,value):
        value=self._value(value);key=self._item['keyframes'][self._key]
        if not np.any(value):
            position=self._position.copy();quaternion=np.asarray(key['rotation_xyzw'],float);rotation=self._rotation.copy()
        else:
            source=Rotation.from_quat(key['rotation_xyzw']);changed=source*Rotation.from_rotvec(np.radians(self._angle)*value[:3]);rotation=changed.as_matrix()
            position=self._pivot+rotation@(self._direction*(self._clearance*value[3])-self._point)
            quaternion=np.asarray(key['rotation_xyzw'],float) if not np.any(value[:3]) else changed.as_quat()
        degrees=float(np.degrees((Rotation.from_matrix(self._rotation).inv()*Rotation.from_matrix(rotation)).magnitude())) if np.any(value[:3]) else 0.
        distance=float(np.linalg.norm(position-self._position));norm_margin=1-float(value[:3]@value[:3]);offset=float(np.linalg.norm(position+rotation@self._point-self._pivot))
        passed=bool(norm_margin>=0 and degrees<=self._angle and distance<=self._translation)
        return dict(position_m=position,rotation_xyzw=quaternion,rotation_matrix=rotation,report=dict(
            schema='strep-native-mesh-prop-pose-proposal-v1',controls=value.tolist(),prop=self._name,key_index=self._key,time_s=key['time_s'],
            native_rotation_ball_margin=norm_margin,rotation_change_degrees=degrees,rotation_cap_degrees=self._angle,
            translation_change_m=distance,translation_cap_m=self._translation,authored_clearance_m=self._clearance*float(value[3]),
            actual_pivot_offset_m=offset,native_pose_permissions_pass=passed,source_relative=True,
            only_declared_key_editable=True,boundary_key_edited=self._key in (0,len(self._item['keyframes'])-1),all_contact_times_verified=False,continuous_rotation_bounds_verified=False,
            transition_compatibility_verified=False,quality_approved=False,release_approved=False))

    def manifest(self,value):
        response=self.evaluate(value)
        if not response['report']['native_pose_permissions_pass']:raise ValueError('Original prop pose permissions failed; proposal is not clipped')
        result=copy.deepcopy(self._source)
        result['actor_scene']=str(_path(self._base,result['actor_scene']))
        for entry in result['props'].values():entry['glb']=str(_path(self._base,entry['glb']))
        for entry in result['mesh_contacts']:entry['grip']=str(_path(self._base,entry['grip']))
        selected=result['props'][self._name]['keyframes'][self._key]
        if np.any(self._value(value)):
            selected['translation_m']=response['position_m'].tolist()
            if np.any(np.asarray(value)[:3]):selected['rotation_xyzw']=response['rotation_xyzw'].tolist()
        original=self._item['keyframes']
        for index,key in enumerate(result['props'][self._name]['keyframes']):
            if index!=self._key:assert _bytes(key)==_bytes(original[index])
        restored=copy.deepcopy(result);restored['props'][self._name]['keyframes'][self._key]=copy.deepcopy(original[self._key])
        source=copy.deepcopy(self._source);source['actor_scene']=str(_path(self._base,source['actor_scene']))
        for entry in source['props'].values():entry['glb']=str(_path(self._base,entry['glb']))
        for entry in source['mesh_contacts']:entry['grip']=str(_path(self._base,entry['grip']))
        assert _bytes(restored)==_bytes(source)
        self.check_inputs();return result,response['report']

    def write(self,value,output):
        self.check_inputs();output=Path(output).resolve()
        if output.exists():raise ValueError('Fresh prop pose proposal directory required')
        manifest,report=self.manifest(value);output.mkdir(parents=True)
        save(output/'mesh-scene.json',manifest);save(output/'proposal.json',dict(report,inputs_sha256=self.inputs,
            frozen_keys=self._spec['frozen_keys'],source_assets_unchanged=True,other_content_unchanged_except_path_relocation=True,
            original_selected=True,motion_fitted=False,quality_approved=False,release_approved=False))
        self.check_inputs();return output/'mesh-scene.json'

    def sampled_permissions(self,candidate,policy):
        source_policy=copy.deepcopy(policy);source_policy['clock']['mode']='native-and-frame-populations'
        times,_,_=self.scene._clock(source_policy);p,r=self.scene.prop_poses(self._name,times);q,s=candidate.prop_poses(self._name,times)
        distances=np.linalg.norm(q-p,axis=1);degrees=np.degrees((Rotation.from_matrix(r).inv()*Rotation.from_matrix(s)).magnitude())
        # Exact identical matrices have exact zero relative rotation. This is
        # an identity check, never a tolerance for small nonzero changes.
        degrees[np.all(r==s,axis=(1,2))]=0.
        report=dict(samples=len(times),maximum_translation_m=float(distances.max()),translation_cap_m=self._translation,
            maximum_rotation_degrees=float(degrees.max()),rotation_cap_degrees=self._angle,
            all_sampled_pose_permissions_pass=bool(np.all(distances<=self._translation) and np.all(degrees<=self._angle)),
            complete_native_and_frame_clock=True,continuous_rotation_bounds_verified=False,quality_approved=False,release_approved=False)
        return report,dict(times_s=times,translation_m=distances,rotation_degrees=degrees)


def candidate_controls(edit):
    """A declared finite full-xyz search; interior candidates are not clipping."""
    result=[np.zeros(4)]
    if edit._clearance:result.append(np.array([0.,0,0,1.]))
    if edit._angle:
        for radius in [.25,.5,1.]:
            for xyz in product([-1.,0,1.],repeat=3):
                direction=np.asarray(xyz)
                if not np.any(direction):continue
                direction=direction/np.linalg.norm(direction)*radius*(1-1e-12)
                result.append(np.r_[direction,1. if edit._clearance else 0.])
    return result


def conditions(report):
    result={}
    for row in report['samples']:
        stamp=row['time_s'];base=row['base_scene'];items=[]
        items += [(('base-object',item['actor'],item['object']),item) for item in base['actor_objects']]
        items += [(('base-partner',*item['actors']),item) for item in base['actor_pairs']]
        items += [(('base-plane',item['actor'],item['plane']),item) for item in base['world_planes']]
        items += [(('mesh-pair',*item['left'],*item['right']),item) for item in row['mesh_pairs']]
        items += [(('mesh-primitive',item['prop'],item['object']),item) for item in row['mesh_primitive_pairs']]
        items += [(('mesh-plane',item['prop'],item['plane']),item) for item in row['mesh_world_planes']]
        items.append((('whole-sample',),row))
        for key,item in items:
            key=(stamp,*key)
            if key in result:raise ValueError('Duplicate geometry condition identity')
            if type(item['passed']) is not bool:raise ValueError('Explicit geometry decision required')
            result[key]=item['passed']
    return result


def metrics(report):
    depths=[];records=0
    for row in report['samples']:
        for item in row['mesh_pairs']+row['base_scene']['actor_pairs']:
            records+=len(item['surface']['records']);depths += [p['max_depth_m'] for p in item['vertex_containment'] if p['available']]
        depths += [item['maximum_depth_m'] for item in row['mesh_world_planes']+row['base_scene']['world_planes']]
        depths += [item['maximum_depth_upper_m'] for item in row['mesh_primitive_pairs']+row['base_scene']['actor_objects']]
    return dict(failed_conditions=sum(not value for value in conditions(report).values()),
        failed_samples=sum(not row['passed'] for row in report['samples']),surface_records=records,maximum_depth_m=max(depths,default=0.))


def pareto_improvement(measure,previous):
    """No collision metric may worsen to buy an improvement in another."""
    expected={'failed_conditions','failed_samples','surface_records','maximum_depth_m'}
    for item in [measure]+([] if previous is None else [previous]):
        if not isinstance(item,dict) or set(item)!=expected:raise ValueError('Complete collision metrics required')
        for key,value in item.items():
            if key=='maximum_depth_m':
                if type(value) not in (int,float) or not np.isfinite(value) or value<0:raise ValueError('Finite nonnegative depth required')
            elif type(value) is not int or value<0:raise ValueError('Complete nonnegative collision counts required')
    return previous is None or all(measure[key]<=previous[key] for key in expected) and any(measure[key]<previous[key] for key in expected)


def search(permissions_path,policy_path,output,*,maximum_candidates=80):
    if type(maximum_candidates) is not int or not 1<=maximum_candidates<=80:raise ValueError('Explicit candidate budget1-80 required')
    edit=GripPoseEdit(permissions_path);policy_path=Path(policy_path).resolve();policy,policy_digest=_json(policy_path)
    times,_,_=edit.scene._clock(policy);output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh bounded prop pose search output required')
    bindings={**edit.inputs,str(policy_path):policy_digest};methods={name:sha256(Path(__file__).parent/name) for name in METHODS}
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
    for name in METHODS:shutil.copyfile(Path(__file__).parent/name,archive/name)
    controls=candidate_controls(edit);save(output/'input.json',dict(inputs_sha256=bindings,implementation_sha256=methods,
        candidate_table=[value.tolist() for value in controls],maximum_candidates=maximum_candidates,all_rotation_axes_included=True,
        geometry_clock_s=times.tolist(),search_interior_fraction=1-1e-12,source_bounds_unchanged=True,rotation_locked=edit._angle==0,clearance_locked=edit._clearance==0,quality_approved=False))
    history=[];baseline=None;baseline_measure=None;best=None;feasible=None;best_measure=None
    for index,value in enumerate(controls[:maximum_candidates]):
        response=edit.evaluate(value);row=dict(probe=index,controls=value.tolist(),native_pose_permissions_pass=response['report']['native_pose_permissions_pass'])
        if not row['native_pose_permissions_pass']:
            row.update(accepted=False,reason='native_pose_permissions');history.append(row);save(output/'history.json',history);continue
        folder=output/f'probe-{index:03d}';manifest=edit.write(value,folder);candidate=MeshPropScene(manifest)
        bound,bound_arrays=edit.sampled_permissions(candidate,policy);save(folder/'sampled-permissions.json',bound);np.savez_compressed(folder/'sampled-permissions.npz',**bound_arrays)
        contact,arrays=candidate.contact_audit();save(folder/'contacts.json',contact);np.savez_compressed(folder/'contact-observations.npz',**arrays)
        derived=copy.deepcopy(policy);derived['mesh_scene_sha256']=sha256(manifest);save(folder/'policy.json',derived)
        with ObservationArchive(folder/'geometry-observations.npz') as sink:geometry,_=candidate.geometry(derived,observation_sink=sink)
        verify(folder/'geometry-observations.npz');save(folder/'geometry.json',geometry);current=conditions(geometry);measure=metrics(geometry)
        if baseline is None:
            assert index==0;baseline=current;baseline_measure=measure.copy();save(output/'baseline.json',dict(metrics=measure,conditions=[dict(id=list(key),passed=value) for key,value in baseline.items()]))
        if current.keys()!=baseline.keys():raise ValueError('Original complete geometry condition population changed')
        new_failures=sum(baseline[key] and not current[key] for key in baseline)
        no_worse=all(measure[key]<=baseline_measure[key] for key in baseline_measure)
        allowed=bool(bound['all_sampled_pose_permissions_pass'] and contact['all_declared_point_contacts_pass'] and new_failures==0 and no_worse)
        improved=bool(allowed and pareto_improvement(measure,best_measure));clean=bool(allowed and geometry['sampled_conditions_pass'])
        if improved:best=index;best_measure=measure.copy()
        if clean:feasible=index
        row.update(sampled_pose_permissions_pass=bound['all_sampled_pose_permissions_pass'],all_declared_point_contacts_pass=contact['all_declared_point_contacts_pass'],new_failed_geometry_conditions=new_failures,metrics=measure,collision_metrics_no_worse_than_source=no_worse,admissible_for_comparison=allowed,improves_best=improved,sampled_geometry_pass=geometry['sampled_conditions_pass'],sampled_candidate_pass=clean)
        save(folder/'decision.json',dict(row,original_selected=True,quality_approved=False,release_approved=False));history.append(row);save(output/'history.json',history);print(row,flush=True)
        if feasible is not None:break
    edit.check_inputs()
    if any(sha256(path)!=digest for path,digest in bindings.items()) or any(sha256(Path(__file__).parent/name)!=digest or sha256(archive/name)!=digest for name,digest in methods.items()):raise ValueError('Prop fit input or implementation changed')
    result=dict(schema='strep-native-mesh-prop-pose-search-v1',status='complete',source_candidate_probe=0,best_admissible_probe=best,sampled_feasible_probe=feasible,
        candidates_recorded=len(history),candidate_table_size=len(controls),candidate_limit=maximum_candidates,complete_table_evaluated=len(history)==len(controls),
        stopped_on_sampled_candidate=feasible is not None,improving_candidate_found=best not in (None,0),history=history,geometry_times=len(times),no_original_geometry_conditions_omitted=True,
        source_assets_and_author_permissions_unchanged=True,character_motion_edited=False,original_selected=True,physics_verified=False,engine_import_verified=False,
        continuous_collision_certified=False,quality_approved=False,release_approved=False,
        scope='Finite authored-key prop orientation/clearance proposals with original native angle/translation limits, full native/frame sampled pose bounds, EVERY declared point contact and EVERY geometry policy time/condition. All original passing conditions protected. Retain every proposal and failure. Frozen keys and character/mesh/grip bytes unchanged. A sampled feasible prop pose is not complete-clock geometry beyond the declared policy, global feasibility, smoothness, dynamics, grasp, game-engine, semantic or human approval.')
    save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['permissions','policy','output']:parser.add_argument(name,type=Path)
    parser.add_argument('--maximum-candidates',type=int,default=80);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(),threadpool_limits(limits=1):
            result=search(args.permissions,args.policy,args.output,maximum_candidates=args.maximum_candidates)
            print(dict(status=result['status'],best_admissible_probe=result['best_admissible_probe'],sampled_feasible_probe=result['sampled_feasible_probe']),flush=True)
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        args.output=guarded_output(args.output);arguments=[str(args.permissions.resolve()),str(args.policy.resolve()),str(args.output/'search'),'--worker','--maximum-candidates',str(args.maximum_candidates)]
        result=run(Path(__file__),args.output/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,stable_seconds=15,admission_seconds=600,max_seconds=900),worker_args=arguments)
        save(args.output/'resource-replay.json',audit(args.output/'guard'));print(result)
        raise SystemExit({'complete':0,'failed':1,'deferred':2}[result['status']])
