"""Screen authored scene references after the actual SOMA30 model projection.

This evaluates supplied reference poses, not all poses satisfying sparse model
constraints. Failure is not a proof that the interaction is impossible. Passing
does not establish generation accuracy, temporal feasibility or motion quality.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now, source_check
from action_requests import request_digest
from inspect_motion import validate_motion
from scene_constraints import evaluate, transform_motion, sample_object
from audit_scene_orientation import audit as audit_orientation
from floor_contact import Surface
from convex_partner_surface import penetration
from build_soma_preview import ASSET
from object_geometry import scene_geometry

SCHEMA='strep-scene-target-representation-v1'
LIMITS=dict(floor_depth_m=.005,object_depth_m=.005,partner_depth_m=.005,normal_degrees=15.)
METHODS=['scene_target_preflight.py','scene_constraints.py','audit_scene_orientation.py',
         'inspect_motion.py','floor_contact.py','palm_contacts.py','object_geometry.py',
         'scene_region_contact.py','convex_partner_surface.py','strep.py']
VENDOR_FILES=['kimodo/skeleton/definitions.py','kimodo/skeleton/base.py',
              'kimodo/skeleton/kinematics.py','kimodo/skeleton/transforms.py',
              'kimodo/assets/skeletons/somaskel30/joints.p',
              'kimodo/assets/skeletons/somaskel77/joints.p',
              'kimodo/assets/skeletons/somaskel77/relaxed_hands_rest_pose.npy']


def orientation(scene,skin,*,motions=None,project_root=ROOT):
    # Region contacts carry their own normals and limits in evaluate_region.
    subset=copy.deepcopy(scene)
    subset['contacts']=[c for c in scene['contacts'] if 'region_contact' not in c]
    for c in subset['contacts']:
        target=c['target']
        if c.get('tangent_target') and not (c.get('normal_target') or target.get('space')=='object' or (target.get('space')=='actor' and 'surface_vertex' in target)):
            raise ValueError('Authored tangent needs an explicit or geometry-derived normal target')
    result=audit_orientation(subset,skin,LIMITS['normal_degrees'],motions=motions,project_root=project_root)
    result['region_normals_in_contact_evaluation']=[c['id'] for c in scene['contacts'] if 'region_contact' in c]
    return result


def project_motion(motion):
    """Exact pinned CPU conversion, including the export's relaxed hand layer."""
    import torch
    from kimodo.skeleton import SOMASkeleton30,SOMASkeleton77
    names,_,_=validate_motion(motion,30)
    small,full=SOMASkeleton30(),SOMASkeleton77()
    if names!=full.bone_order_names:raise ValueError('Scene preflight requires SOMA77 source poses')
    local=torch.tensor(motion['local_rot_mats'],dtype=torch.float32,device='cpu')
    root=torch.tensor(motion['root_positions'],dtype=torch.float32,device='cpu')
    with torch.inference_mode():
        r,p,_=full.fk(local,root)
        if not np.allclose(r.numpy(),motion['global_rot_mats'],atol=1e-4,rtol=0) or not np.allclose(p.numpy(),motion['posed_joints'],atol=1e-4,rtol=0):
            raise ValueError('Source poses disagree with the pinned native skeleton FK')
        expanded=small.to_SOMASkeleton77(small.from_SOMASkeleton77(local))
        if not torch.equal(expanded,small.to_SOMASkeleton77(small.from_SOMASkeleton77(expanded))):
            raise ValueError('Model representation projection is not idempotent')
        r,p,_=full.fk(expanded,root)
    result={k:v.copy() for k,v in motion.items()}
    result.update(local_rot_mats=expanded.numpy().copy(),global_rot_mats=r.numpy().copy(),posed_joints=p.numpy().copy())
    validate_motion(result,30)
    return result


def flags(record):
    for rows,key in [(record['floor'],'depth_m'),(record['objects'],'depth_m'),(record['partners'],'max_depth_m')]:
        if any(type(r[key]) not in [int,float] or not np.isfinite(r[key]) or r[key]<0 for r in rows):
            raise ValueError('Invalid reference depth observations')
    failures=[]
    if any(not c['all_requested_frames_within_tolerance'] for c in record['contacts']['contacts']):failures.append('contact_reference_missed')
    if any(c['frames_over_tolerance'] or c.get('tangent_frames_over_tolerance',0) for c in record['orientation']['contacts']):failures.append('orientation_reference_missed')
    if any(r['depth_m']>LIMITS['floor_depth_m'] for r in record['floor']):failures.append('floor_reference_penetration')
    if any(r['depth_m']>LIMITS['object_depth_m'] for r in record['objects']):failures.append('object_reference_penetration')
    if any(r['max_depth_m']>LIMITS['partner_depth_m'] for r in record['partners']):failures.append('partner_reference_penetration')
    return failures


def population(scene,record):
    frames=sorted({f for c in scene['contacts'] for f in range(c['start_frame'],c['end_frame']+1)})
    expected_floor=[(f,a) for f in frames for a in scene['actors']]
    expected_objects=[(f,a,o) for f in frames for a in scene['actors'] for o in scene.get('objects',{})]
    expected_partners=[(f,a,b) for f in frames for a in scene['actors'] for b in scene['actors'] if a!=b]
    if (record['frames']!=frames or [(r['frame'],r['actor']) for r in record['floor']]!=expected_floor
        or [(r['frame'],r['actor'],r['object']) for r in record['objects']]!=expected_objects
        or [(r['frame'],r['actor'],r['target_actor']) for r in record['partners']]!=expected_partners):
        raise ValueError('Incomplete target-reference geometry population')
    if [c['id'] for c in record['contacts']['contacts']]!=[c['id'] for c in scene['contacts']]:
        raise ValueError('Incomplete target-reference contact population')
    if set(record['contacts']['contact_tracks'])!={c['id'] for c in scene['contacts']}:
        raise ValueError('Incomplete target-reference contact tracks')
    for c in scene['contacts']:
        track=record['contacts']['contact_tracks'][c['id']]
        for name,shape in [('actual_world_m',(scene['frame_count'],3)),('target_world_m',(scene['frame_count'],3)),('errors_m',(scene['frame_count'],))]:
            values=np.asarray(track[name])
            if values.shape!=shape or not np.isfinite(values).all():raise ValueError('Incomplete or nonfinite target-reference track')
    expected=[c['id'] for c in scene['contacts'] if 'region_contact' in c]
    if record['orientation']['region_normals_in_contact_evaluation']!=expected:
        raise ValueError('Dropped target-reference region normals')
    expected=[c['id'] for c in scene['contacts'] if 'region_contact' not in c and 'surface_vertex' in c['effector']
        and (c.get('normal_target') or c['target'].get('space')=='object' or (c['target'].get('space')=='actor' and 'surface_vertex' in c['target']))]
    if [c['id'] for c in record['orientation']['contacts']]!=expected or record['orientation']['tolerance_degrees']!=LIMITS['normal_degrees']:
        raise ValueError('Incomplete target-reference orientation population')
    by_id={c['id']:c for c in scene['contacts']}
    for c in record['orientation']['contacts']:
        contact=by_id[c['id']];a,b=contact['start_frame'],contact['end_frame']
        for field,count in [('per_frame_error_degrees','frames_over_tolerance'),('per_frame_tangent_error_degrees','tangent_frames_over_tolerance')]:
            if field=='per_frame_tangent_error_degrees' and not contact.get('tangent_target'):continue
            values=np.asarray(c[field])
            if values.shape!=(scene['frame_count'],) or not np.isfinite(values).all() or np.any(values<0) or np.any(values>180):
                raise ValueError('Incomplete or invalid target-reference orientation track')
            if c[count]!=int(np.sum(values[a:b+1]>LIMITS['normal_degrees'])):
                raise ValueError('Rebound target-reference orientation decision')


def measure(scene,skin,motions,*,project_root=ROOT):
    """Every contact frame, actor, object and ordered partner pair; no thinning."""
    frames=sorted({f for c in scene['contacts'] for f in range(c['start_frame'],c['end_frame']+1)})
    if not frames:raise ValueError('Scene target preflight requires contact frames')
    contacts=evaluate(scene,skin,project_root,motions=motions)
    rotations=orientation(scene,skin,motions=motions,project_root=project_root)
    actors={name:transform_motion(motions[name],entry['transform']) for name,entry in scene['actors'].items()}
    surface=Surface(skin);floor=[];objects=[];partners=[]
    if list(map(str,skin['rig_joint_names']))!=validate_motion(next(iter(motions.values())),30)[0]:
        raise ValueError('Source skeleton and skin names differ')
    tracks={name:sample_object(obj,scene['frame_count']) for name,obj in scene.get('objects',{}).items()}
    for f in frames:
        vertices={name:surface.vertices(a['rotations'][f],a['positions'][f]) for name,a in actors.items()}
        for name,v in vertices.items():
            floor.append(dict(actor=name,frame=f,vertices_checked=len(v),depth_m=max(0.,-float(v[:,1].min()))))
            for obj,(p,r) in tracks.items():
                depths=scene_geometry(scene['objects'][obj]).penetration_depth(v,p[f],r[f])
                objects.append(dict(actor=name,object=obj,frame=f,vertices_checked=len(v),depth_m=float(depths.max())))
            for other,target in vertices.items():
                if other!=name:partners.append(dict(actor=name,target_actor=other,frame=f,**penetration(v,target,skin['faces'],LIMITS['partner_depth_m'])))
    result=dict(frames=frames,contacts=contacts,orientation=rotations,floor=floor,objects=objects,partners=partners)
    population(scene,result)
    result['flags']=flags(result);result['reference_screens_passed']=not result['flags']
    return result


def write(scene,output,*,scene_file):
    """Create an immutable CPU audit, retaining both representations and failures."""
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    output=Path(output).resolve();scene_file=Path(scene_file).resolve()
    if output.exists():raise ValueError('Preserve previous target preflight')
    document=read(scene_file)
    if document.get('scene',document)!=scene:raise ValueError('Audit scene file does not match supplied scene')
    source_commit=source_check();skin=dict(np.load(ASSET,allow_pickle=False))
    scene_hash=sha256(scene_file);skin_hash=sha256(ASSET)
    methods={name:sha256(ROOT/'scripts'/name) for name in METHODS}
    vendor_hashes={name:sha256(ROOT/'vendor/kimodo'/name) for name in VENDOR_FILES}
    originals={};derived={};actor_records={}
    output.mkdir(parents=True);(output/'model-reference').mkdir();(output/'methods').mkdir()
    for name in METHODS:shutil.copyfile(ROOT/'scripts'/name,output/'methods'/name)
    save(output/'protocol.json',dict(schema=SCHEMA,scene_file=str(scene_file),scene_sha256=scene_hash,
        skin_sha256=skin_hash,kimodo_commit=source_commit,methods_sha256=methods,vendor_sha256=vendor_hashes,limits=LIMITS))
    save(output/'state.json',dict(status='running',at=now()))
    try:
        with worker_lock(),threadpool_limits(limits=1):
            import torch
            previous_threads=torch.get_num_threads();torch.set_num_threads(1)
            try:
                for i,(name,entry) in enumerate(scene['actors'].items()):
                    path=(ROOT/entry['motion']).resolve()
                    if not path.is_relative_to(ROOT.resolve()) or sha256(path)!=entry.get('source_sha256'):
                        raise ValueError('Target source hash/path mismatch')
                    originals[name]=dict(np.load(path,allow_pickle=False));derived[name]=project_motion(originals[name])
                    destination=output/'model-reference'/f'actor-{i}.npz'
                    np.savez_compressed(destination,**derived[name])
                    changed={'local_rot_mats','global_rot_mats','posed_joints'}
                    if set(originals[name])!=set(derived[name]) or any(not np.array_equal(v,derived[name][k]) for k,v in originals[name].items() if k not in changed):
                        raise ValueError('Projection changed protected root/contact/auxiliary arrays')
                    difference=Rotation.from_matrix((derived[name]['local_rot_mats']@originals[name]['local_rot_mats'].swapaxes(-1,-2)).reshape(-1,3,3)).magnitude()
                    names,_,_=validate_motion(originals[name],30)
                    actor_records[name]=dict(source_path=entry['motion'],source_sha256=sha256(path),
                        projected_file=destination.relative_to(output).as_posix(),projected_sha256=sha256(destination),
                        protected_arrays_passed=True,max_local_change_degrees_by_joint=dict(zip(names,np.rad2deg(difference.reshape(-1,77).max(0)).tolist())))
                native=measure(scene,skin,originals);model=measure(scene,skin,derived)
            finally:torch.set_num_threads(previous_threads)
        if sha256(scene_file)!=scene_hash or sha256(ASSET)!=skin_hash:raise ValueError('Changed audit scene/skin during execution')
        if any(sha256(ROOT/'scripts'/n)!=d or sha256(output/'methods'/n)!=d for n,d in methods.items()) or any(sha256(ROOT/'vendor/kimodo'/n)!=d for n,d in vendor_hashes.items()):
            raise ValueError('Changed preflight implementation during execution')
        if any(sha256(ROOT/a['source_path'])!=a['source_sha256'] for a in actor_records.values()):raise ValueError('Changed audit sources during execution')
        result=dict(schema=SCHEMA,status='complete',at=now(),scene_file=str(scene_file),scene_sha256=scene_hash,
            skin_sha256=skin_hash,kimodo_commit=source_commit,vendor_sha256=vendor_hashes,
            methods_sha256=methods,actors=actor_records,limits=LIMITS.copy(),native=native,model=model,
            reference_screens_passed=native['reference_screens_passed'] and model['reference_screens_passed'],
            quality_approved=False,release_approved=False,
            scope='Exact SOMA77 to SOMA30 to relaxed SOMA77 CPU reference conversion, full skin at every authored contact frame. Both directions of partner vertex tests and analytic object depth. Region contacts retain their authored limits. Not exhaustive sparse-constraint feasibility, anatomy, self collision, continuous collision, dynamics, generated motion or human review.')
        save(output/'audit.json',result);save(output/'state.json',dict(status='complete',audit_sha256=sha256(output/'audit.json'),at=now()))
        return result
    except Exception as exc:
        save(output/'state.json',dict(status='failed',error=str(exc),at=now()));raise


def validate_preflight(folder,batch):
    """Reject stale/rejected references before encoding or scene assembly."""
    folder=Path(folder).resolve();freeze_path=folder/'freeze.json';audit_path=folder/'target-preflight/audit.json'
    freeze=read(freeze_path) if freeze_path.exists() else {}
    expected=freeze.get('target_preflight_sha256')
    if expected is None:
        if (folder/'target-preflight').exists() or (folder/'source-snapshot/scene_target_preflight.py').exists():
            raise ValueError('Scene target preflight binding was dropped')
        return None  # Historical ordinary batches have no preflight contract.
    mode=freeze.get('target_preflight_mode')
    if mode not in ['strict','diagnostic'] or sha256(audit_path)!=expected:raise ValueError('Changed scene target preflight')
    if request_digest(batch)!=freeze['request_sha256'] or sha256(folder/'authored-scene.json')!=freeze['scene_sha256']:
        raise ValueError('Changed preflight scene/request')
    result=read(audit_path);scene=read(folder/'authored-scene.json');root=audit_path.parent
    try:commit=source_check()
    except RuntimeError as exc:raise ValueError('Changed upstream projection checkout') from exc
    if commit!=result['kimodo_commit']:raise ValueError('Changed upstream projection revision')
    if result['schema']!=SCHEMA or result['status']!='complete' or result['limits']!=LIMITS or result['scene_sha256']!=freeze['scene_sha256']:
        raise ValueError('Invalid scene target preflight contract')
    if set(result['actors'])!=set(scene['actors']) or result['skin_sha256']!=sha256(ASSET):raise ValueError('Changed preflight actor/skin population')
    if set(result['methods_sha256'])!=set(METHODS) or set(result['vendor_sha256'])!=set(VENDOR_FILES):raise ValueError('Incomplete preflight method population')
    for name,digest in result['methods_sha256'].items():
        if sha256(root/'methods'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Changed preflight methods')
    for name,digest in result['vendor_sha256'].items():
        if sha256(ROOT/'vendor/kimodo'/name)!=digest:raise ValueError('Changed projection implementation/assets')
    for i,(name,entry) in enumerate(scene['actors'].items()):
        actor=result['actors'][name];path=(ROOT/entry['motion']).resolve()
        if not path.is_relative_to(ROOT.resolve()) or actor['source_path']!=entry['motion'] or sha256(path)!=actor['source_sha256'] or actor['source_sha256']!=entry['source_sha256']:
            raise ValueError('Changed preflight source')
        if actor['projected_file']!=f'model-reference/actor-{i}.npz' or sha256(root/actor['projected_file'])!=actor['projected_sha256']:
            raise ValueError('Changed model reference arrays')
    for record in [result['native'],result['model']]:
        population(scene,record)
        if record['flags']!=flags(record) or record['reference_screens_passed']!=(not flags(record)):raise ValueError('Rebound preflight decision')
    passed=result['native']['reference_screens_passed'] and result['model']['reference_screens_passed']
    if result['reference_screens_passed']!=passed or result['quality_approved'] or result['release_approved']:
        raise ValueError('Invalid preflight approval')
    if mode=='strict' and not passed:raise ValueError('Scene target references fail model-representation preflight; inspect retained audit or prepare an explicitly diagnostic batch')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    value=read(a.scene);report=write(value.get('scene',value),a.output,scene_file=a.scene)
    print(dict(reference_screens_passed=report['reference_screens_passed'],native_flags=report['native']['flags'],model_flags=report['model']['flags']),flush=True)
