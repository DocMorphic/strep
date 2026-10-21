"""Attribute a failed import comparison without changing its requested clock.

Reported-time comparisons are diagnostic only. The ordinary requested-time
clock/pose/skin gates remain separate and unchanged; no capture is repaired.
"""
import numpy as np
from native_engine_contacts import matrices
from native_scene_imported_skin import ImportedSceneSkin
from native_scene_engine import POSE_TOLERANCE,SKIN_POSITION_TOLERANCE


def diagnose(rig,reader,observed,times):
    times=np.asarray(times,float)
    if (times.ndim!=1 or len(times)<2 or not np.isfinite(times).all() or times[0]!=0
            or np.any(np.diff(times)<=0) or times[-1]>reader.duration):
        raise ValueError('Complete increasing in-range requested clock required')
    if len(observed['frames'])!=len(times):raise ValueError('Complete captured frame population required')
    skin=ImportedSceneSkin(rig,observed);mesh_names={m['node'] for m in observed['meshes']};rows=[]
    duration=observed['duration_s']
    if type(duration) not in (int,float) or not np.isfinite(duration):raise ValueError('Finite captured duration required')
    for index,(time,frame) in enumerate(zip(times,observed['frames'])):
        echo=frame['requested_time_s'];actual=frame['actual_time_s']
        if (type(echo) not in (int,float) or type(actual) not in (int,float)
                or not np.isfinite([echo,actual]).all() or not 0<=actual<=reader.duration):
            raise ValueError('Finite in-range raw capture clocks required')
        # Preserve the same four-ULP request echo and 1ns seek tests as imported_world.
        echo_pass=abs(echo-float(time))<=4*abs(np.spacing(float(time)))
        seek_pass=abs(actual-time)<=1e-9
        world=matrices(frame['bones'])
        if world.shape!=(len(skin.bone_map),4,4):raise ValueError('Complete captured bone population required')
        skeleton=matrices(frame['skeleton_world']);meshes=frame['mesh_world']
        if len(meshes)!=len(mesh_names) or {m['node'] for m in meshes}!=mesh_names:
            raise ValueError('Complete captured mesh transforms required')
        if any(np.max(np.abs(matrices(m['matrix'])-skeleton))>1e-7 for m in meshes):
            raise ValueError('Captured mesh and skeleton spaces differ')
        ordered=np.empty_like(world);ordered[skin.bone_map]=world
        vertices=skin.vertices(ordered)
        requested_pose=reader.sample(float(time));reported_pose=reader.sample(float(actual))
        requested_vertices=rig.vertices(requested_pose);reported_vertices=rig.vertices(reported_pose)
        rows.append(dict(index=index,requested_time_s=float(time),echo_time_s=float(echo),actual_time_s=float(actual),
            request_echo_pass=bool(echo_pass),seek_clock_pass=bool(seek_pass),clock_error_s=float(actual-time),
            requested_pose_element_error=float(np.max(abs(ordered-requested_pose[rig.joints]))),
            reported_time_pose_element_error=float(np.max(abs(ordered-reported_pose[rig.joints]))),
            requested_skin_error_m=float(np.linalg.norm(vertices-requested_vertices,axis=1).max()),
            reported_time_skin_error_m=float(np.linalg.norm(vertices-reported_vertices,axis=1).max()),
            native_shift_from_clock_m=float(np.linalg.norm(reported_vertices-requested_vertices,axis=1).max()),
            captured_floor_depth_m=max(0.,-float(vertices[:,1].min()))))
    peak=lambda key:max(rows,key=lambda r:r[key])
    clock_pass=all(r['request_echo_pass'] and r['seek_clock_pass'] for r in rows)
    header_pass=abs(duration-reader.duration)<=1e-6 and observed['loop_mode']==0
    pose_pass=header_pass and peak('requested_pose_element_error')['requested_pose_element_error']<=POSE_TOLERANCE
    skin_pass=peak('requested_skin_error_m')['requested_skin_error_m']<=SKIN_POSITION_TOLERANCE
    return dict(schema='strep-native-import-clock-diagnostic-v1',samples=len(rows),rows=rows,
        requested_clock_pass=clock_pass,requested_pose_samples_pass=bool(pose_pass),requested_skin_samples_pass=bool(skin_pass),
        requested_import_comparison_pass=bool(clock_pass and pose_pass and skin_pass),
        bad_clock_indices=[r['index'] for r in rows if not r['request_echo_pass'] or not r['seek_clock_pass']],
        maximum_requested_skin_error_m=peak('requested_skin_error_m')['requested_skin_error_m'],
        maximum_reported_time_skin_error_m=peak('reported_time_skin_error_m')['reported_time_skin_error_m'],
        maximum_native_shift_from_clock_m=peak('native_shift_from_clock_m')['native_shift_from_clock_m'],
        worst_requested_skin_frame=peak('requested_skin_error_m')['index'],
        observed_duration_s=duration,source_duration_s=reader.duration,loop_mode=observed['loop_mode'],
        imported_skin={k:v for k,v in skin.report.items() if k not in ('source_mapping','imported_references')},
        tolerances=dict(actual_clock_s=1e-9,pose_element=POSE_TOLERANCE,skin_position_m=SKIN_POSITION_TOLERANCE),
        scope='All recorded frames and complete imported skin. Reported-time metrics attribute failure only; requested clocks/capture remain unchanged. No rates, contacts, GPU, physics or quality acceptance.',
        quality_approved=False,release_approved=False)
