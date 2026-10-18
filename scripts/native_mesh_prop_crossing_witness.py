"""Source-bound exact witnesses for every selected-prop surface record.

Exactness concerns represented binary-float triangles, not earlier skinning,
whole-scene clearance, continuous time, or animation quality.
"""
import argparse
import copy
from fractions import Fraction
from itertools import combinations
from pathlib import Path
import shutil
import numpy as np
from exact_triangle_crossing_witness import witness,verify as verify_exact
from triangle_crossing import classify
from native_mesh_prop_pose import GripPoseEdit,metrics,_bytes,METHODS as POSE_METHODS
from native_mesh_prop_scene import MeshPropScene,_json,guarded_output
from native_scene_geometry import faces_for
from native_observation_archive import verify as verify_archive
from strep import save,sha256

METHODS=tuple(sorted(set(POSE_METHODS)|{'native_mesh_prop_crossing_witness.py','exact_triangle_crossing_witness.py'}))


def certify_record(left_vertices,left_faces,right_vertices,right_faces,record,tolerance):
    if not isinstance(record,dict) or set(record)!={'left_triangle','right_triangle','kind','overlap_length_m'}:raise ValueError('Complete original crossing record required')
    if record['kind'] not in ('proper_crossing','boundary_or_near_contact','coplanar_or_near_parallel_overlap','degenerate'):raise ValueError('Recorded non-disjoint surface outcome required')
    ids=[record['left_triangle'],record['right_triangle']]
    for index,faces in zip(ids,[left_faces,right_faces]):
        if type(index) is not int or not 0<=index<len(faces):raise ValueError('Original triangle identity outside complete topology')
    a=np.asarray(left_vertices)[left_faces[ids[0]]];b=np.asarray(right_vertices)[right_faces[ids[1]]]
    expected=classify(a,b,tolerance)
    if expected!=dict(kind=record['kind'],overlap_length_m=record['overlap_length_m']):raise ValueError('Crossing classification does not reproduce from bound world triangles')
    proof=witness(a,b);verify_exact(proof)
    proven=record['kind']=='proper_crossing' and proof['strict_interior_crossing_proved']
    result=dict(source_record=copy.deepcopy(record),status='proved' if proven else 'unresolved',exact_proof=proof,whole_scene_certified=False,quality_approved=False)
    if proven:
        bary=np.array([[float(Fraction(v)) for v in row] for row in proof['barycentric_rational']]);point=np.array(proof['witness_world_approx_m'])
        reconstructed=np.stack([bary[0]@a,bary[1]@b]);result.update(barycentric_approx=bary.tolist(),world_points_approx_m=reconstructed.tolist(),maximum_float_reconstruction_error_m=float(np.linalg.norm(reconstructed-point,axis=1).max()))
    return result


def complete_populations(scene,report,policy):
    actors=list(scene._scene.actors);props=list(scene._props);objects=list(scene._scene.objects);planes=list(policy['planes'])
    expected={(('actor',a),('prop',p)) for a in actors for p in props}|{(('prop',a),('prop',b)) for a,b in combinations(props,2)}
    def same(items,identities):
        if len(items)!=len(set(items)) or set(items)!=identities:raise ValueError('Complete unique original geometry condition population required')
    for row in report['samples']:
        same([(tuple(r['left']),tuple(r['right'])) for r in row['mesh_pairs']],expected)
        base=row['base_scene'];same([(r['actor'],r['object']) for r in base['actor_objects']],{(a,o) for a in actors for o in objects})
        same([tuple(r['actors']) for r in base['actor_pairs']],set(combinations(actors,2)))
        same([(r['actor'],r['plane']) for r in base['world_planes']],{(a,p) for a in actors for p in planes})
        same([(r['prop'],r['object']) for r in row['mesh_primitive_pairs']],{(p,o) for p in props for o in objects})
        same([(r['prop'],r['plane']) for r in row['mesh_world_planes']],{(p,q) for p in props for q in planes})


def collect(permissions_path,probe,output,*,maximum_records=4096):
    if type(maximum_records) is not int or not 1<=maximum_records<=4096:raise ValueError('Explicit witness budget1-4096 required')
    edit=GripPoseEdit(permissions_path);probe=Path(probe).resolve();output=Path(output).resolve()
    decision,decision_sha=_json(probe/'decision.json');parent,parent_sha=_json(probe.parent/'result.json',16*1024**2)
    parent_input,parent_input_sha=_json(probe.parent/'input.json',16*1024**2)
    if any(parent_input['inputs_sha256'].get(p)!=d for p,d in edit.inputs.items()) or any(sha256(p)!=d for p,d in parent_input['inputs_sha256'].items()):raise ValueError('Original producer input/permission epoch binding changed')
    if any(sha256(probe.parent/'implementation'/n)!=d for n,d in parent_input['implementation_sha256'].items()):raise ValueError('Producer implementation snapshot changed')
    if parent['status']!='complete':raise ValueError('Completed producer required; raw interrupted studies stay separate')
    matches=[r for r in parent['history'] if r['probe']==decision['probe']]
    if len(matches)!=1 or decision!=dict(matches[0],original_selected=True,quality_approved=False,release_approved=False):raise ValueError('Probe decision must match completed producer history')
    if not decision['native_pose_permissions_pass'] or not decision['sampled_pose_permissions_pass']:raise ValueError('Original native and sampled pose permissions required')
    expected,_=edit.manifest(decision['controls']);spec,manifest_sha=_json(probe/'mesh-scene.json')
    if _bytes(spec)!=_bytes(expected):raise ValueError('Probe must reproduce original-relative controls and unchanged frozen/source content')
    scene=MeshPropScene(probe/'mesh-scene.json');policy,policy_sha=_json(probe/'policy.json');times,_,_=scene._clock(policy)
    geometry,geometry_sha=_json(probe/'geometry.json',16*1024**2)
    if geometry['inputs_sha256']!=scene.inputs or geometry['complete_clock_s']!=times.tolist() or geometry['sample_indices']!=list(range(len(times))) or geometry['times_s']!=times.tolist() or not geometry['all_policy_samples_evaluated']:raise ValueError('Complete bound producer geometry clock required')
    if len(geometry['samples'])!=len(times) or any(row['index']!=i or row['time_s']!=float(times[i]) or row['base_scene']['time_s']!=float(times[i]) for i,row in enumerate(geometry['samples'])):raise ValueError('Every ordered producer sample identity required')
    if metrics(geometry)!=decision['metrics'] or geometry['sampled_conditions_pass']!=decision['sampled_geometry_pass']:raise ValueError('Producer geometry metrics or decisions changed')
    complete_populations(scene,geometry,policy)
    faces={('actor',n):faces_for(a['rig'])[0] for n,a in scene._scene.actors.items()};faces.update({('prop',n):p['asset'].faces for n,p in scene._props.items()})
    if geometry['actor_faces']!={n:len(faces['actor',n]) for n in scene._scene.actors} or geometry['prop_faces']!={n:len(p['asset'].faces) for n,p in scene._props.items()}:raise ValueError('Complete source faces required')
    selected=('prop',edit._name);count=sum(len(pair['surface']['records']) for row in geometry['samples'] for pair in row['mesh_pairs'] if selected in [tuple(pair['left']),tuple(pair['right'])])
    if count>maximum_records:raise ValueError('All crossing records exceed witness budget; no record truncation')
    archive_path=probe/'geometry-observations.npz';verify_archive(archive_path)
    bindings={**parent_input['inputs_sha256'],**edit.inputs,**scene.inputs,str(probe/'decision.json'):decision_sha,str(probe.parent/'result.json'):parent_sha,str(probe.parent/'input.json'):parent_input_sha,str(probe/'mesh-scene.json'):manifest_sha,str(probe/'policy.json'):policy_sha,str(probe/'geometry.json'):geometry_sha,str(archive_path):sha256(archive_path),str(Path(str(archive_path)+'.receipt.json')):sha256(Path(str(archive_path)+'.receipt.json'))}
    bindings.update({str(probe.parent/'implementation'/n):d for n,d in parent_input['implementation_sha256'].items()})
    if output.exists():raise ValueError('Fresh crossing-witness output required')
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();methods={n:sha256(Path(__file__).parent/n) for n in METHODS}
    for n in METHODS:shutil.copyfile(Path(__file__).parent/n,archive/n)
    save(output/'input.json',dict(inputs_sha256=bindings,implementation_sha256=methods,original_cumulative_controls=decision['controls'],selected_prop=edit._name,geometry_times_s=times.tolist(),selected_prop_surface_records=count,maximum_records=maximum_records,source_rebased=False,quality_approved=False))
    records=[];arrays=dict(record_indices=[],left_barycentric=[],right_barycentric=[],left_world_m=[],right_world_m=[],left_vertices=[],right_vertices=[])
    with np.load(archive_path,allow_pickle=False) as z:
        if not np.array_equal(z['times_s'],times):raise ValueError('Observation clock changed')
        for frame,stamp in enumerate(times):
            worlds={}
            for name,actor in scene._scene.actors.items():
                p,r=actor['placement'];worlds['actor',name]=actor['rig'].vertices(actor['sampler'].sample(float(stamp)))@r.T+p
            for name,prop in scene._props.items():
                p,r=scene.prop_poses(name,np.array([stamp]));worlds['prop',name]=prop['asset'].vertices_m@r[0].T+p[0]
            for (kind,name),vertices in worlds.items():
                if z[f'mesh_frame_{frame}_{kind}_{name}_world_m'].tobytes()!=vertices.tobytes():raise ValueError('Complete world vertices do not reproduce bound source')
            for pair in geometry['samples'][frame]['mesh_pairs']:
                left,right=tuple(pair['left']),tuple(pair['right'])
                if selected not in [left,right]:continue
                for item in pair['surface']['records']:
                    proof=certify_record(worlds[left],faces[left],worlds[right],faces[right],item,policy['limits']['surface_tolerance_m']);index=len(records)
                    record=dict(index=index,sample_index=frame,time_s=float(stamp),left=list(left),right=list(right),**proof);records.append(record)
                    if proof['status']=='proved':
                        arrays['record_indices'].append(index)
                        for side,key in enumerate([left,right]):
                            label='left' if side==0 else 'right';arrays[label+'_barycentric'].append(proof['barycentric_approx'][side]);arrays[label+'_world_m'].append(proof['world_points_approx_m'][side]);arrays[label+'_vertices'].append(faces[key][item[label+'_triangle']].tolist())
    if len(records)!=count:raise ValueError('Every selected-prop surface record must be retained')
    converted={k:np.asarray(v,dtype=np.int64 if k=='record_indices' or k.endswith('_vertices') else np.float64).reshape((-1,) if k=='record_indices' else (-1,3)) for k,v in arrays.items()}
    save(output/'records.json',records);np.savez_compressed(output/'witness-observations.npz',**converted)
    edit.check_inputs();scene.check_inputs()
    if any(sha256(p)!=d for p,d in bindings.items()) or any(sha256(Path(__file__).parent/n)!=sha256(archive/n) or sha256(archive/n)!=d for n,d in methods.items()):raise ValueError('Bound source or implementation changed')
    proven=sum(r['status']=='proved' for r in records)
    result=dict(status='complete',geometry_times=len(times),selected_prop_surface_records=count,exact_interior_crossings_proved=proven,unresolved_records=count-proven,all_records_retained=True,all_complete_world_vertex_arrays_byte_identical=True,source_author_permissions_and_frozen_content_verified=True,source_rebased=False,character_motion_edited=False,correction_applied=False,whole_scene_certified=False,continuous_collision_certified=False,quality_approved=False,release_approved=False,scope='Source-bound exact rational witnesses for every recorded selected-prop surface pair in a complete producer policy. Exactness concerns represented world triangles after skinning/transform rounding. Nonproper/unsupported exact outcomes remain unresolved, never clearance. No whole-scene completeness proof beyond bound producer data, correction, full-timeline/continuous/dynamic/engine/semantic/human approval.')
    save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['permissions','probe','output']:parser.add_argument(n,type=Path)
    parser.add_argument('--maximum-records',type=int,default=4096);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(),threadpool_limits(limits=1):print(collect(args.permissions,args.probe,args.output,maximum_records=args.maximum_records))
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        args.output=guarded_output(args.output);arguments=[str(args.permissions.resolve()),str(args.probe.resolve()),str(args.output/'collection'),'--worker','--maximum-records',str(args.maximum_records)]
        result=run(Path(__file__),args.output/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,stable_seconds=15,admission_seconds=600,max_seconds=300),worker_args=arguments)
        save(args.output/'resource-replay.json',audit(args.output/'guard'));print(result);raise SystemExit({'complete':0,'failed':1,'deferred':2}[result['status']])
