"""Explicit-profile captured ASF/AMC transfer to a supplied rig; no cleanup.

Source roles distinguish joint origin from orientation segment. Every original
sample is retained, with glTF float32 time quantization recorded explicitly.
Existing target animations and payload bytes survive in the derived character.
"""
import argparse
import copy
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
from acclaim_motion import read_motion,forward_kinematics
from retarget_rig import ROLE_PARENTS,resolve_profile,transfer
from rig_asset import RigAsset
from gltf_tools import local_matrix,append_accessor,write_glb,sample_animation
from native_rig_transfer import preserves_target
from strep import read,save,sha256,now

METHODS=('acclaim_rig_transfer.py','acclaim_motion.py','retarget_rig.py','rig_asset.py','gltf_tools.py','strep.py',
         'native_rig_transfer.py','rig_clip_import.py','native_support_clock.py','action_worker_lock.py')


def resolve_source(skeleton,profile,asf_sha256):
    required={'schema','asf_sha256','reference_pose','mapping'}
    if not isinstance(profile,dict) or not required<=set(profile) or set(profile)-required-{'notes'}:
        raise ValueError('Explicit bounded source profile required')
    if (profile['schema']!='strep-acclaim-humanoid-profile-v1' or profile['asf_sha256']!=asf_sha256
            or profile['reference_pose']!='zero_amc_rotations'):
        raise ValueError('Matching ASF checksum and explicit zero-channel reference required')
    mapping=profile['mapping'];names=skeleton['names'];parents=skeleton['parents']
    if not isinstance(mapping,dict) or set(mapping)!=set(ROLE_PARENTS):raise ValueError('All 19 explicit anatomical source roles required')
    origins={};orientations={}
    for role,item in mapping.items():
        if not isinstance(item,dict) or set(item)!={'position_bone','rotation_bone'}:raise ValueError('Each role requires explicit origin and orientation segments')
        p,r=item['position_bone'],item['rotation_bone']
        if type(p) is not str or type(r) is not str or p not in names or r not in names:raise ValueError('Mapped source segment missing')
        origins[role]=p;orientations[role]=r
    if len(set(origins.values()))!=len(origins) or len(set(orientations.values()))!=len(orientations):
        raise ValueError('Source roles must use distinct origins and orientations')
    if origins['Hips']!='root' or orientations['Hips']!='root':raise ValueError('Source pelvis must use the declared root')
    inverse={v:k for k,v in origins.items()}
    for role,p in origins.items():
        expected=ROLE_PARENTS[role]
        if expected is not None:
            ancestor=parents[p]
            while ancestor not in inverse:ancestor=parents[ancestor]
            if inverse[ancestor]!=expected:raise ValueError('Source anatomical hierarchy is incompatible')
        r=orientations[role]
        while r!=p:
            if r=='root' or r in inverse:raise ValueError('Orientation must remain in its origin segment chain')
            r=parents[r]
    return origins,orientations


def mapped_motion(skeleton,motion,source_profile,asf_sha256):
    origins,orientations=resolve_source(skeleton,source_profile,asf_sha256)
    names=list(ROLE_PARENTS);lookup={n:i for i,n in enumerate(skeleton['names'])}
    origin_indices=[lookup[origins[r]] for r in names];rotation_indices=[lookup[orientations[r]] for r in names]
    zero={'root':np.zeros(6),**{n:np.zeros(len(b['dof'])) for n,b in skeleton['bones'].items()}}
    neutral=forward_kinematics(skeleton,[zero])['positions_m'][0,origin_indices]
    reference=SimpleNamespace(bone_order_names=names,neutral_joints=neutral)
    result=dict(root_positions=motion['positions_m'][:,lookup['root']],
        global_rot_mats=motion['rotations'][:,rotation_indices],posed_joints=motion['positions_m'][:,origin_indices])
    return reference,result,dict(position_segments=origins,rotation_segments=orientations,
        reference_policy='ASF geometry reconstructed with all AMC rotations and root translation zero; not an observed support pose')


def _export(asf,amc,source_profile_path,character,target_profile_path,output,*,fps,length_convention=None,metres_per_unit=None):
    paths=[Path(p).resolve() for p in (asf,amc,source_profile_path,character,target_profile_path)]
    asf,amc,source_profile_path,character,target_profile_path=paths;output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh captured-transfer output required')
    for profile_path in (source_profile_path,target_profile_path):
        if profile_path.stat().st_size>65536:raise ValueError('Rig profile exceeds its bounded metadata capacity')
    bindings={str(p):sha256(p) for p in paths};methods={n:sha256(Path(__file__).with_name(n)) for n in METHODS}
    source_profile=read(source_profile_path);target_profile=read(target_profile_path)
    if target_profile.get('character_sha256')!=bindings[str(character)]:raise ValueError('Target profile character checksum mismatch')
    skeleton,motion,source_bindings=read_motion(asf,amc,fps=fps,length_convention=length_convention,metres_per_unit=metres_per_unit)
    if any(bindings[p]!=h for p,h in source_bindings.items()):raise ValueError('Captured input changed before transfer')
    reference,mapped,source_mapping=mapped_motion(skeleton,motion,source_profile,bindings[str(asf)])
    rig=RigAsset.load(character);mapping,offset=resolve_profile(rig,target_profile)
    if len(rig.document['nodes'])>512:raise ValueError('Bounded target rig required')
    matrices,translations,rotations,scale,diagnostics=transfer(rig,mapped,reference,mapping,offset,target_profile.get('axis_alignment_xyzw'))
    diagnostics['axis_alignment_space']='Target reference world axes to explicit ASF zero-channel world axes; premultiplied onto target reference joint rotation'
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    times=motion['times_s'];encoded=times.astype('<f4')
    if np.any(np.diff(encoded)<=0):raise ValueError('glTF time encoding collapses captured keys')
    animation=dict(name='Strep captured reference',channels=[],samplers=[],extras=dict(
        strep_acclaim_transfer=dict(source_asf_sha256=bindings[str(asf)],source_amc_sha256=bindings[str(amc)],
            source_profile_sha256=bindings[str(source_profile_path)],fps=float(fps),contact_verified=False,quality_approved=False)))
    accessor=append_accessor(document,binary,encoded,'SCALAR')
    for node in translations:
        entry=document['nodes'][node]
        if 'matrix' in entry:
            local=local_matrix(entry);entry.pop('matrix');entry.update(translation=local[:3,3].tolist(),
                rotation=Rotation.from_matrix(local[:3,:3]).as_quat().tolist(),scale=[1,1,1])
        for path,values,kind in (('translation',translations[node],'VEC3'),('rotation',rotations[node],'VEC4')):
            a=append_accessor(document,binary,values,kind)
            animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=path)))
            animation['samplers'].append(dict(input=accessor,output=a,interpolation='LINEAR'))
    output_index=len(document.get('animations',[]));document.setdefault('animations',[]).append(animation)
    output.mkdir(parents=True);save(output/'pipeline.json',dict(status='processing',original_selected=True))
    write_glb(output/'character.glb',document,binary);decoded=RigAsset.load(output/'character.glb')
    preserved=preserves_target(rig,decoded,mapping)
    if not preserved:raise ValueError('Original target payload or animation metadata changed')
    matrix_error=0.;vertex_error=0.;minima=[];joint_errors={r:[] for r in mapping}
    for i,expected in enumerate(matrices):
        actual=sample_animation(decoded.document,decoded.binary,output_index,i)
        vertices=decoded.vertices(actual)
        matrix_error=max(matrix_error,float(np.max(abs(actual-expected))))
        vertex_error=max(vertex_error,float(np.max(np.linalg.norm(vertices-rig.vertices(expected),axis=1))))
        minima.append(float(vertices[:,1].min()))
        for role,node in mapping.items():
            goal=mapped['posed_joints'][i,reference.bone_order_names.index(role)]*scale+offset
            joint_errors[role].append(float(np.linalg.norm(actual[node,:3,3]-goal)))
    floor_depth=np.maximum(0.,-np.array(minima));clock_error=float(np.max(abs(encoded.astype(float)-times)))
    np.savez_compressed(output/'target-transforms.npz',global_matrices=matrices,times_s=times,encoded_times_s=encoded,
        source_frame_ids=motion['source_frame_ids'],minimum_vertex_y_m=np.array(minima),
        role_names=np.array(list(mapping)),role_position_error_m=np.array(list(joint_errors.values())).T)
    save(output/'root-motion.json',dict(space='Target mapped pelvis world transform, Y-up metres; extraction not applied',node=mapping['Hips'],
        original_times_s=times.tolist(),encoded_times_s=encoded.tolist(),positions_m=matrices[:,mapping['Hips'],:3,3].tolist(),
        rotations_xyzw=Rotation.from_matrix(matrices[:,mapping['Hips'],:3,:3]).as_quat().tolist()))
    save(output/'contacts.json',dict(provenance='No captured contact annotations supplied; unknown, not confirmed no-contact',intervals=[],contact_verified=False))
    report=dict(schema='strep-acclaim-rig-transfer-v1',status='complete' if max(matrix_error,vertex_error)<=1e-5 else 'failed',created_at=now(),
        input_sha256=bindings,implementation_sha256=methods,source_mapping=source_mapping,target_mapping=mapping,
        frames=len(times),fps=float(fps),last_source_time_s=float(times[-1]),last_encoded_time_s=float(encoded[-1]),
        clock_quantization_max_s=clock_error,all_source_frames_retained=True,downsampled=False,filtered=False,
        output_animation_index=output_index,original_target_payload_preserved=preserved,original_selected=True,
        scale_from_mean_leg_lengths=scale,calibration=diagnostics,world_offset_m=offset.tolist(),automatic_floor_lift_m=0.,
        roundtrip_max_matrix_error=matrix_error,roundtrip_max_vertex_error_m=vertex_error,
        mapped_position_errors={r:dict(max_m=max(v),rms_m=float(np.sqrt(np.mean(np.square(v))))) for r,v in joint_errors.items()},
        native_key_floor_tolerance_m=.005,native_key_failed_floor_samples=int(np.sum(floor_depth>.005)),
        native_key_max_floor_depth_m=float(floor_depth.max()),vertices_per_key=len(vertices),
        glb_sha256=sha256(output/'character.glb'),transforms_sha256=sha256(output/'target-transforms.npz'),
        contact_verified=False,between_key_geometry_verified=False,training_admitted=False,quality_approved=False,engine_import_verified=False,release_approved=False,
        limitations=['Explicit anatomical origin/orientation mappings and zero-channel reference require review; twist remains underdetermined.',
            'Existing target rotation calibration and fixed local bone translations; no positional IK, proportional adaptation, floor lift or contact correction.',
            'Native-key mesh screening only; no between-key/continuous geometry, captured support, source surfaces, semantics, force or human approval.',
            'Unmapped helper/finger locals retain target defaults. ASF source availability does not establish captured finger/thumb validity.'])
    if any(sha256(p)!=h for p,h in bindings.items()) or any(sha256(Path(__file__).with_name(n))!=h for n,h in methods.items()):raise ValueError('Bound input or method changed during transfer')
    save(output/'report.json',report);save(output/'pipeline.json',dict(status=report['status'],original_selected=True))
    if report['status']!='complete':raise ValueError('Captured transfer roundtrip failed; retained derived output and report')
    return report


def export(asf,amc,source_profile_path,character,target_profile_path,output,*,fps,length_convention=None,metres_per_unit=None):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh captured-transfer output required')
    try:
        return _export(asf,amc,source_profile_path,character,target_profile_path,output,
            fps=fps,length_convention=length_convention,metres_per_unit=metres_per_unit)
    except Exception as exc:
        if output.exists():save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('asf','amc','source-profile','character','target-profile','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--fps',type=float,required=True)
    u=p.add_mutually_exclusive_group(required=True);u.add_argument('--length-convention',choices=['cmu-inches']);u.add_argument('--metres-per-unit',type=float)
    a=p.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=1):
        r=export(a.asf,a.amc,a.source_profile,a.character,a.target_profile,a.output,fps=a.fps,
            length_convention=a.length_convention,metres_per_unit=a.metres_per_unit)
    print({k:r[k] for k in ('status','frames','native_key_failed_floor_samples','native_key_max_floor_depth_m')} )
