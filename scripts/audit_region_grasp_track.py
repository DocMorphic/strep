"""Replay native trajectory edits and measure exported full skin at quarter frames."""
import argparse
import shutil
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from scipy.interpolate import CubicHermiteSpline
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET, make_preview
from gltf_tools import write_glb, read_glb
from rig_clip_import import AnimationSampler
from grasp_pose_witness import PoseProblem
from grasp_contact_binding import apply_region_binding
from audit_sphere_region import triangle_audit
from audit_grasp_restoration import compare_record
from scene_solver_context import context_primitives


def quintic(t):
    t = min(1., max(0., t)); return 6*t**5-15*t**4+10*t**3


def run(study, output, approach_patch=None, floor_patch=None, release_patch=None, spatial_patch=None, coupled_patch=None):
    study, output = Path(study).resolve(), Path(output).resolve(); protocol, result = read(study/'protocol.json'), read(study/'result.json')
    if result['status'] != 'complete' or not result['motion_generated']: raise ValueError('Completed trajectory required')
    for path, digest in [(study/'protocol.json', result['protocol_sha256']), (study/'motion.npz', result['motion_sha256'])]:
        if sha256(path) != digest: raise ValueError('Trajectory artifact changed')
    for name, digest in protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Trajectory input changed')
    for name, digest in protocol['implementation'].items():
        if sha256(study/'implementation'/name) != digest: raise ValueError('Trajectory implementation snapshot changed')
    regions, bindings = protocol['region_protocols'], protocol['contact_bindings']
    fit = ROOT/protocol['study']/'fit'; summary = read(fit/'summary.json'); folder = fit/'assets'/summary['trials'][0]['id']/'A'
    skin = dict(np.load(ASSET, allow_pickle=False)); start, end = protocol['active_interval']; edit_start, edit_end = protocol['edited_interval']
    p0 = PoseProblem(folder, skin, start); candidate = dict(np.load(study/'motion.npz', allow_pickle=False)); source = p0.candidate
    reference = np.array(read(ROOT/protocol['pose_report']/'result.json')['parameters']); active = {r['frame']: r for r in result['rows']}
    if set(active) != set(range(start, end+1)): raise ValueError('Missing or duplicate active frames')
    expected_edited = set(range(edit_start+1, edit_end)); stored = {r['frame']:r for r in result['parameter_track']}
    if set(stored) != expected_edited or len(stored) != len(result['parameter_track']): raise ValueError('Unexpected edited frame set')
    outside = np.array(sorted(set(range(protocol['frame_count']))-expected_edited))
    for name in source: np.testing.assert_array_equal(source[name][outside], candidate[name][outside])
    columns = [3*p0.lookup[p0.names.index(side+name)]+k for side in ['Left','Right'] for name in ['Shoulder','Arm','ForeArm','Hand'] for k in range(3)]
    frozen = np.setdiff1d(np.arange(p0.dim), columns); max_serialized_error = 0.; replay_passes = 0
    for frame, record in stored.items():
        relative = p0.previous['local_rot_mats'][frame].transpose(0,2,1)@source['local_rot_mats'][frame]
        baseline = np.r_[Rotation.from_matrix(relative[p0.editable]).as_rotvec().ravel(), p0.recipe['root_lift_m'][frame]]
        if frame < start: weight = quintic((frame-edit_start)/(start-edit_start)); expected = (1-weight)*baseline+weight*np.array(active[start]['parameters'])
        elif frame > end: weight = 1-quintic((frame-end)/(edit_end-end)); expected = (1-weight)*baseline+weight*np.array(active[end]['parameters'])
        else: weight = 1.; expected = np.array(active[frame]['parameters']); np.testing.assert_array_equal(expected[frozen],reference[frozen])
        values = np.array(record['parameters']); np.testing.assert_allclose(values, expected, atol=1e-12, rtol=0.); np.testing.assert_allclose(record['blend_weight'],weight,atol=1e-12)
        p0.frame = frame; audit, replay = p0.independent(values)
        for name in candidate:
            serialized = replay[name][0].astype(candidate[name].dtype)
            np.testing.assert_array_equal(serialized,candidate[name][frame])
            if name in ['posed_joints','root_positions','global_rot_mats']: max_serialized_error=max(max_serialized_error,float(np.max(np.abs(replay[name][0]-candidate[name][frame]))))
        if not audit['rotation_norm_bounds_passed']: raise ValueError('Original edit budget violated')
        if start <= frame <= end:
            p = PoseProblem(folder,skin,frame)
            for binding,rp in zip(bindings,regions): apply_region_binding(p,binding['hand'],binding['anchor'],rp['patch'])
            actual,_=p.independent(values); compare_record(actual,active[frame]['candidate'])
            replay_passes += actual['pose_witness_passed']
    patch_verification=None
    if approach_patch is not None:
        patch_path=Path(approach_patch).resolve();pp,rr=read(patch_path/'protocol.json'),read(patch_path/'result.json')
        if ROOT/pp['base_study']!=study or rr['status']!='complete':raise ValueError('Completed matching approach patch required')
        if sha256(patch_path/'motion.npz')!=rr['motion_sha256'] or sha256(patch_path/'protocol.json')!=rr['protocol_sha256']:raise ValueError('Approach artifact changed')
        for name,digest in pp['inputs'].items():
            if sha256(ROOT/name)!=digest:raise ValueError('Approach input changed')
        for name,digest in pp['implementation'].items():
            if sha256(patch_path/'implementation'/name)!=digest:raise ValueError('Approach implementation snapshot changed')
        if pp['eligible_frames']!=list(range(edit_start+1,start)) or pp['arm_columns']!=columns:raise ValueError('Approach scope changed')
        if [r['frame'] for r in rr['rows']]!=pp['eligible_frames']:raise ValueError('Missing approach rows')
        changed=[r['frame'] for r in rr['rows'] if r['changed']]
        if changed!=rr['changed_frames']:raise ValueError('Changed frame summary mismatch')
        patched=dict(np.load(patch_path/'motion.npz',allow_pickle=False));unmodified=np.setdiff1d(np.arange(protocol['frame_count']),changed)
        for name in candidate:np.testing.assert_array_equal(patched[name][unmodified],candidate[name][unmodified])
        for binding,rp in zip(bindings,regions):apply_region_binding(p0,binding['hand'],binding['anchor'],rp['patch'])
        for row in rr['rows']:
            frame=row['frame'];base=np.array(stored[frame]['parameters']);p0.frame=frame
            p0.objects=[(g,o['id'],p0.t(o['positions_m'][frame])[None],p0.t(o['rotations'][frame])[None]) for g,o in context_primitives(p0.context)]
            before,base_motion=p0.independent(base)
            vertices=p0.surface.vertices(base_motion['global_rot_mats'][0],base_motion['posed_joints'][0]);sphere,_,center,_=p0.objects[0]
            for guide,binding in zip(row['guides'],bindings):
                hand=binding['hand'];root=p0.names.index(hand);descendants={root}
                for j,parent in enumerate(p0.parents):
                    if parent in descendants:descendants.add(j)
                ids=np.array([i for i in range(len(vertices)) if any(j in descendants and w>0 for j,w in zip(skin['lbs_indices'][i],skin['lbs_weights'][i]))])
                direction=np.array(guide['outward']);np.testing.assert_allclose(np.linalg.norm(direction),1.,atol=1e-12)
                point=vertices[binding['anchor']];expected_direction=point-center.numpy()[0];expected_direction/=np.linalg.norm(expected_direction)
                np.testing.assert_allclose(direction,expected_direction,atol=1e-12)
                np.testing.assert_allclose(guide['point'],point+direction*guide['distance_m'],atol=1e-12)
                clearance=np.linalg.norm(vertices[ids]+direction*guide['distance_m']-center.numpy()[0],axis=1).min()-sphere.dimensions[0]
                if guide['distance_m']<0 or clearance<pp['settings']['guide_clearance_m']-1e-10:raise ValueError('Rigid guidance clearance failed')
                if guide['distance_m']>0 and abs(clearance-pp['settings']['guide_clearance_m'])>1e-8:raise ValueError('Rigid guidance is not on first escape boundary')
            if row['changed']:
                values=np.array(row['parameters']);np.testing.assert_array_equal(values[frozen],base[frozen]);actual,replay=p0.independent(values)
                compare_record(before,row['before']);compare_record(actual,row['candidate'])
                if not actual['rotation_norm_bounds_passed']:raise ValueError('Approach bounds failed')
                for name in candidate:np.testing.assert_array_equal(replay[name][0].astype(patched[name].dtype),patched[name][frame])
        candidate=patched
        patch_verification=dict(report=patch_path.relative_to(ROOT).as_posix(),result_sha256=sha256(patch_path/'result.json'),protocol_sha256=sha256(patch_path/'protocol.json'),
                                changed_frames=changed,unchanged_frames=len(unmodified),non_arm_parameters_exact=True,grasp_and_release_exact=True,rigid_guidance_verified=True)
        # Reset the reference object/contact records used to compile dense authored targets.
        p0=PoseProblem(folder,skin,start)
    floor_verification=None
    if floor_patch is not None:
        if approach_patch is None:raise ValueError('Floor correction requires its verified approach input')
        fp=Path(floor_patch).resolve();fprotocol,fresult=read(fp/'protocol.json'),read(fp/'result.json')
        if ROOT/fprotocol['approach_report']!=Path(approach_patch).resolve() or ROOT/fprotocol['base_study']!=study or fresult['status']!='complete':raise ValueError('Floor input mismatch')
        for path,digest in [(fp/'protocol.json',fresult['protocol_sha256']),(fp/'motion.npz',fresult['motion_sha256'])]:
            if sha256(path)!=digest:raise ValueError('Floor artifact changed')
        for name,digest in fprotocol['inputs'].items():
            if sha256(ROOT/name)!=digest:raise ValueError('Floor source changed')
        for name,digest in fprotocol['implementation'].items():
            if sha256(fp/'implementation'/name)!=digest:raise ValueError('Floor implementation snapshot changed')
        free=fprotocol['settings']['free_frames']
        if free!=list(range(1,edit_start)):raise ValueError('Floor correction changed interaction or initial pose')
        delta=np.array(fresult['root_lift_delta_m']);locked=np.setdiff1d(np.arange(protocol['frame_count']),free)
        if delta.shape!=(protocol['frame_count'],) or not np.isfinite(delta).all() or np.any(delta<0):raise ValueError('Invalid floor lift')
        np.testing.assert_array_equal(delta[locked],0.)
        lifted=dict(np.load(fp/'motion.npz',allow_pickle=False))
        for name in candidate:
            expected=candidate[name].copy()
            if name=='root_positions':expected[:,1]+=delta
            elif name=='posed_joints':expected[:,:,1]+=delta[:,None]
            np.testing.assert_array_equal(expected,lifted[name]);np.testing.assert_array_equal(candidate[name][locked],lifted[name][locked])
        total_lift=lifted['root_positions'][:,1]-p0.base['root_positions'][:,1]
        if total_lift.min()< -1e-6 or total_lift.max()>p0.config['max_root_lift_m']+1e-6:raise ValueError('Original root bound exceeded')
        prior_dense=read(ROOT/fprotocol['dense_audit']/'candidate.json');predicted=[]
        for time,height in zip(prior_dense['frames'],prior_dense['floor_height_m']):
            low,high=int(np.floor(time)),int(np.ceil(time));fraction=0.
            if low!=high:
                a,b,t=[float(np.float32(f/30)) for f in [low,high,time]];fraction=(t-a)/(b-a)
            predicted.append(height+(1-fraction)*delta[low]+fraction*delta[high])
        if min(predicted)<fprotocol['settings']['target_height_m']-1e-10:raise ValueError('Predicted dense floor constraints failed')
        candidate=lifted;outside=np.setdiff1d(outside,free)
        floor_verification=dict(report=fp.relative_to(ROOT).as_posix(),result_sha256=sha256(fp/'result.json'),protocol_sha256=sha256(fp/'protocol.json'),
                                maximum_lift_m=float(delta.max()),locked_frames_exact=len(locked),rotations_exact=True,horizontal_root_exact=True,grasp_and_release_exact=True,
                                minimum_predicted_height_m=min(predicted))
    release_verification=None
    if release_patch is not None:
        if floor_patch is None:raise ValueError('Release patch requires its floor-corrected input')
        path=Path(release_patch).resolve();rp,rr=read(path/'protocol.json'),read(path/'result.json')
        if ROOT/rp['floor_report']!=Path(floor_patch).resolve() or ROOT/rp['base_study']!=study or rr['status']!='complete':raise ValueError('Release patch input mismatch')
        for artifact,digest in [(path/'protocol.json',rr['protocol_sha256']),(path/'motion.npz',rr['motion_sha256'])]:
            if sha256(artifact)!=digest:raise ValueError('Release artifact changed')
        for name,digest in rp['inputs'].items():
            if sha256(ROOT/name)!=digest:raise ValueError('Release source changed')
        for name,digest in rp['implementation'].items():
            if sha256(path/'implementation'/name)!=digest:raise ValueError('Release source snapshot changed')
        blend_end=rp['blend_end']
        if rp['release_frame']!=end or type(blend_end) is not int or not end<blend_end<protocol['frame_count'] or rp['blend_frames']!=blend_end-end:raise ValueError('Release timing changed')
        changed=list(range(end+1,blend_end))
        if [r['frame'] for r in rr['rows']]!=changed:raise ValueError('Release frames missing')
        released=dict(np.load(path/'motion.npz',allow_pickle=False));protected=np.setdiff1d(np.arange(protocol['frame_count']),changed)
        for name in candidate:np.testing.assert_array_equal(released[name][protected],candidate[name][protected])
        endpoint=np.array(active[end]['parameters']);np.testing.assert_array_equal(endpoint,rr['grasp_endpoint_parameters'])
        for row in rr['rows']:
            frame=row['frame'];relative=p0.previous['local_rot_mats'][frame].transpose(0,2,1)@source['local_rot_mats'][frame]
            baseline=np.r_[Rotation.from_matrix(relative[p0.editable]).as_rotvec().ravel(),p0.recipe['root_lift_m'][frame]]
            t=(frame-end)/(blend_end-end);profile=rp.get('profile','quintic')
            if profile=='quintic':weight=1-quintic(t)
            elif profile=='early-return':weight=sum(math.comb(10,j)*t**j*(1-t)**(10-j) for j in range(3))
            else:raise ValueError('Unsupported release curve')
            expected=(1-weight)*baseline+weight*endpoint;values=np.array(row['parameters'])
            np.testing.assert_allclose(row['weight'],weight,atol=1e-12);np.testing.assert_allclose(values,expected,atol=1e-12,rtol=0.)
            p0.frame=frame;actual,replay=p0.independent(values)
            if not actual['rotation_norm_bounds_passed']:raise ValueError('Release edit bounds failed')
            for name in candidate:np.testing.assert_array_equal(released[name][frame],replay[name][0].astype(released[name].dtype))
        candidate=released;outside=np.setdiff1d(outside,changed);edit_end=max(edit_end,blend_end);p0=PoseProblem(folder,skin,start)
        release_verification=dict(report=path.relative_to(ROOT).as_posix(),result_sha256=sha256(path/'result.json'),protocol_sha256=sha256(path/'protocol.json'),
                                  release_frame=end,blend_end=blend_end,protected_frames_exact=len(protected),approach_and_grasp_exact=True,original_edit_bounds_verified=True)
    spatial_verification=None
    if spatial_patch is not None:
        if release_patch is None: raise ValueError('Spatial patch requires its release input')
        path=Path(spatial_patch).resolve(); sp,sr=read(path/'protocol.json'),read(path/'result.json')
        if ROOT/sp['release_report']!=Path(release_patch).resolve() or sp['base_study']!=rp['base_study'] or sr['status']!='complete': raise ValueError('Spatial input mismatch')
        for artifact,digest in [(path/'protocol.json',sr['protocol_sha256']),(path/'motion.npz',sr['motion_sha256']),(path/'uncorrected-motion.npz',sr['uncorrected_motion_sha256'])]:
            if sha256(artifact)!=digest: raise ValueError('Spatial artifact changed')
        for name,digest in sp['inputs'].items():
            if sha256(ROOT/name)!=digest: raise ValueError('Spatial input changed')
        for name,digest in sp['implementation'].items():
            if sha256(path/'implementation'/name)!=digest: raise ValueError('Spatial snapshot changed')
        first,last=sp['release_frame'],sp['blend_end']
        if first!=end or last!=rp['blend_end'] or sp['eligible_frames']!=list(range(first+1,last)) or [r['frame'] for r in sr['rows']]!=sp['eligible_frames']: raise ValueError('Spatial timing changed')
        arms=[p0.names.index(s+n) for s in ['Left','Right'] for n in ['Shoulder','Arm','ForeArm','Hand']]
        if arms!=sp['arm_joints'] or list(columns)!=sp['arm_columns']: raise ValueError('Spatial joint scope changed')
        spatial=dict(np.load(path/'motion.npz',allow_pickle=False)); uncorrected=dict(np.load(path/'uncorrected-motion.npz',allow_pickle=False))
        protected=np.setdiff1d(np.arange(protocol['frame_count']),sp['eligible_frames'])
        for name in candidate:
            np.testing.assert_array_equal(spatial[name][protected],candidate[name][protected])
            np.testing.assert_array_equal(uncorrected[name][protected],candidate[name][protected])
        release_rows={r['frame']:r for r in rr['rows']}
        for row in sr['rows']:
            frame=row['frame']; q=quintic((frame-first)/(last-first))
            # Independent Slerp implementation of each local endpoint path.
            profile=sp.get('path_profile','quintic')
            if profile=='quintic':
                desired=np.array([Slerp([0.,1.],Rotation.from_matrix(candidate['local_rot_mats'][[first,last],j]))(q).as_matrix() for j in arms])
            elif profile=='tangent-cubic':
                desired=[]
                for j in arms:
                    before,a,b,after=Rotation.from_matrix(candidate['local_rot_mats'][[first-1,first,last,last+1],j])
                    delta=(a.inv()*b).as_rotvec(); theta=np.linalg.norm(delta)
                    x,y,z=delta; skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
                    # Invert the forward right Jacobian rather than use the
                    # writer's inverse-Jacobian cross-product expression.
                    aa=(1-np.cos(theta))/theta**2 if theta>1e-4 else .5-theta**2/24
                    bb=(theta-np.sin(theta))/theta**3 if theta>1e-4 else 1/6-theta**2/120
                    jac=np.eye(3)-aa*skew+bb*(skew@skew)
                    incoming=(before.inv()*a).as_rotvec()*(last-first)
                    outgoing=np.linalg.solve(jac,(b.inv()*after).as_rotvec()*(last-first))
                    vector=CubicHermiteSpline([0,1],np.stack([np.zeros(3),delta]),np.stack([incoming,outgoing]))((frame-first)/(last-first))
                    desired.append((a*Rotation.from_rotvec(vector)).as_matrix())
                desired=np.array(desired)
            else: raise ValueError('Unknown spatial profile')
            expected=np.array(release_rows[frame]['parameters']); expected[columns]=Rotation.from_matrix(p0.previous['local_rot_mats'][frame,arms].transpose(0,2,1)@desired).as_rotvec().ravel()
            if 'proposed_parameters' in row: np.testing.assert_allclose(row['proposed_parameters'],expected,atol=1e-12,rtol=0)
            reserve=sp.get('path_bound_reserve_radians')
            if reserve is not None:
                if reserve!=.001: raise ValueError('Unexpected spatial seed reserve')
                for joint,col in zip(arms,np.array(columns).reshape(-1,3)):
                    norm=np.linalg.norm(expected[col]); maximum=p0.limits[p0.lookup[joint]]-reserve
                    if norm>maximum: expected[col]*=maximum/norm
            initial=np.array(row['initial_parameters']); values=np.array(row['parameters'])
            np.testing.assert_allclose(initial,expected,atol=1e-12,rtol=0)
            np.testing.assert_array_equal(values[frozen],initial[frozen])
            p0.frame=frame
            for parameters,motion in [(initial,uncorrected),(values,spatial)]:
                actual,replay=p0.independent(parameters)
                if not actual['rotation_norm_bounds_passed']: raise ValueError('Spatial edit bounds failed')
                for name in candidate: np.testing.assert_array_equal(motion[name][frame],replay[name][0].astype(motion[name].dtype))
            if row['solver'] is None: np.testing.assert_array_equal(values,initial)
        candidate=spatial; p0=PoseProblem(folder,skin,start)
        spatial_verification=dict(report=path.relative_to(ROOT).as_posix(),result_sha256=sha256(path/'result.json'),protocol_sha256=sha256(path/'protocol.json'),protected_frames_exact=len(protected),non_arm_parameters_exact=True,native_path_and_correction_replayed=True)
    coupled_verification=None;coupled_source=None;speed_cap_verification=None;angular_join_verification=None
    if coupled_patch is not None:
        if spatial_patch is None: raise ValueError('Coupled patch requires its spatial input')
        path=Path(coupled_patch).resolve(); cp,cr=read(path/'protocol.json'),read(path/'result.json')
        if ROOT/cp['spatial_report']!=Path(spatial_patch).resolve() or cp['base_study']!=sp['base_study'] or cr['status'] not in ['complete','interrupted_resource_guard']: raise ValueError('Coupled input mismatch')
        for artifact,digest in [(path/'protocol.json',cr['protocol_sha256']),(path/'motion.npz',cr['motion_sha256'])]:
            if sha256(artifact)!=digest: raise ValueError('Coupled artifact changed')
        for name,digest in cp['inputs'].items():
            if sha256(ROOT/name)!=digest: raise ValueError('Coupled input changed')
        for name,digest in cp['implementation'].items():
            if sha256(path/'implementation'/name)!=digest: raise ValueError('Coupled source snapshot changed')
        frames=list(range(end-5,end+4))
        if cp['frames']!=frames or [r['frame'] for r in cr['rows']]!=frames or cp['arm_columns']!=list(columns): raise ValueError('Coupled frame/joint scope changed')
        if len(cp['targets'])!=len(frames) or any(len(t)!=len(bindings) for t in cp['targets']): raise ValueError('Coupled guidance population changed')
        if cp['settings'].get('preserve_angular_joins'):
            support=list(range(frames[0]-2,frames[-1]+3));local=candidate['local_rot_mats'][support][:,arms]
            rates=np.array([(Rotation.from_matrix(local[i]).inv()*Rotation.from_matrix(local[i+1])).as_rotvec()*30 for i in range(len(local)-1)])
            caps=np.linalg.norm(np.diff(rates,axis=0),axis=-1)
            if cp['settings']['angular_join_frames']!=support[1:-1]:raise ValueError('Angular preservation frame set changed')
            np.testing.assert_allclose(cp['settings']['source_angular_join_caps_rad_s'],caps,atol=1e-12,rtol=0)
            np.testing.assert_allclose(cp['settings']['fitting_angular_join_caps_rad_s'],caps*.99,atol=1e-12,rtol=0)
            angular_join_verification=dict(frames=support[1:-1],joints=[p0.names[j] for j in arms],source_native_caps_rad_s=caps.tolist(),fitting_fraction=.99,
                                           scope='Per-joint native caps verified; decoded join preservation requires the boundary-rate audit.')
            coupled_source={k:v.copy() for k,v in candidate.items()}
        reserve=cp['settings'].get('release_speed_reserve_m_s')
        if reserve is not None:
            if not np.isfinite(reserve) or reserve<=0 or cp['settings']['release_frame']!=end: raise ValueError('Invalid coupled speed policy')
            obj=next(o for o in p0.context['primitives'] if o['id']==protocol['object_id']);points=[]
            for frame in range(end-2,end+3):
                vertices=p0.surface.vertices(candidate['global_rot_mats'][frame],candidate['posed_joints'][frame]);rotation=np.array(obj['rotations'][frame]);position=np.array(obj['positions_m'][frame])
                points.append([rotation.T@(vertices[b['anchor']]-position) for b in bindings])
            caps=np.linalg.norm(np.diff(np.array(points),axis=0),axis=2).max(0)*30
            if np.any(caps<=reserve): raise ValueError('Speed reserve exceeds source cap')
            np.testing.assert_allclose(cp['settings']['source_native_release_speed_caps_m_s'],caps,atol=1e-12,rtol=0)
            np.testing.assert_allclose(cp['settings']['fitting_release_speed_caps_m_s'],caps-reserve,atol=1e-12,rtol=0)
            speed_cap_verification=dict(source_native_caps_m_s=caps.tolist(),fitting_caps_m_s=(caps-reserve).tolist(),reserve_m_s=reserve,scope='Native fitting caps verified; export preservation measured separately.')
            coupled_source={k:v.copy() for k,v in candidate.items()}
        fitted=dict(np.load(path/'motion.npz',allow_pickle=False));protected=np.setdiff1d(np.arange(protocol['frame_count']),frames)
        for name in candidate: np.testing.assert_array_equal(fitted[name][protected],candidate[name][protected])
        source_parameters={r['frame']:r['parameters'] for r in result['rows']};source_parameters.update({r['frame']:r['parameters'] for r in sr['rows']})
        for i,row in enumerate(cr['rows']):
            frame=row['frame'];values=np.array(row['parameters']);np.testing.assert_array_equal(values[frozen],np.array(source_parameters[frame])[frozen])
            p0.frame=frame;actual,replay=p0.independent(values)
            if not actual['rotation_norm_bounds_passed']: raise ValueError('Coupled original edit bounds failed')
            for name in candidate: np.testing.assert_array_equal(fitted[name][frame],replay[name][0].astype(fitted[name].dtype))
            vertices=p0.surface.vertices(candidate['global_rot_mats'][frame],candidate['posed_joints'][frame])
            for saved,binding,region in zip(cp['targets'][i],bindings,regions):
                anchor,point,normal,tangent=saved
                if anchor!=binding['anchor']: raise ValueError('Coupled guidance anchor changed')
                tri=vertices[skin['faces'][region['patch']['face_ids']]];n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0);n/=np.linalg.norm(n)
                hand=binding['hand'];knuckles=[p0.names.index(hand+j+'2') for j in ['Index','Middle','Ring','Pinky']]
                direction=candidate['posed_joints'][frame,knuckles].mean(0)-candidate['posed_joints'][frame,p0.names.index(hand)];direction=direction-n*(n@direction);direction/=np.linalg.norm(direction)
                np.testing.assert_allclose(point,vertices[anchor],atol=2e-6,rtol=0);np.testing.assert_allclose(normal,n,atol=2e-5,rtol=0);np.testing.assert_allclose(tangent,direction,atol=2e-5,rtol=0)
        candidate=fitted;p0=PoseProblem(folder,skin,start)
        coupled_verification=dict(report=path.relative_to(ROOT).as_posix(),result_sha256=sha256(path/'result.json'),protocol_sha256=sha256(path/'protocol.json'),
                                  protected_frames_exact=len(protected),non_arm_parameters_exact=True,active_grasp_modified=True,solver_status=cr['solver'],original_edit_bounds_verified=True,speed_cap_policy=speed_cap_verification,angular_join_policy=angular_join_verification)
    output.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(Path(__file__),output/Path(__file__).name)
    metadata = dict(at=now(), study=study.relative_to(ROOT).as_posix(), protocol_sha256=sha256(study/'protocol.json'), result_sha256=sha256(study/'result.json'),
                    native_replay_exact=True, untouched_frames_exact=len(outside), original_edit_budgets_pass=True, serialization_max_error=max_serialized_error,approach_patch=patch_verification,floor_patch=floor_verification,release_patch=release_verification,
                    spatial_patch=spatial_verification,coupled_patch=coupled_verification,substeps=4, scope='Decoded GLB full-skin integer/quarter-frame samples; exact original native edits and untouched frames verified. Discrete samples do not certify continuous collision, anatomy, self-collision, dynamics or human quality.', quality_approved=False)
    save(output/'protocol.json',metadata)
    times=np.arange((protocol['frame_count']-1)*4+1)/4; count=protocol['frame_count']; originals={}; hand_specs=[]
    for geometry,obj in context_primitives(p0.context):
        positions=np.asarray(obj['positions_m']); rotations=np.asarray(obj['rotations'])
        sampled_p=np.stack([np.interp(times,np.arange(count),positions[:,i]) for i in range(3)],1)
        sampled_r=Slerp(np.arange(count),Rotation.from_matrix(rotations))(times).as_matrix()
        originals[obj['id']]=(geometry,sampled_p,sampled_r,positions,rotations)
    geometry,op,orr,object_p,object_r=originals[protocol['object_id']]
    for binding,rp in zip(bindings,regions):
        hand=binding['hand']; contact=next(c for c in p0.contacts if c['region']==hand)
        # p0 contacts retain frame-start authored targets; transport through the same object track.
        authored_local=object_r[start].T@(np.array(contact['target'])-object_p[start])
        n=next(n.numpy() for name,f,n in p0.normals if name==binding['normal_id']); normal_local=object_r[start].T@n
        declared=protocol['targets'][hand]; anchor_local=object_r[start].T@(np.array(declared['points'][start])-object_p[start])
        hand_specs.append(dict(hand=hand,anchor=binding['anchor'],ids=np.array(rp['patch']['vertices']),faces=skin['faces'][rp['patch']['face_ids']],limits=rp['limits'],
                               targets=op+np.einsum('fij,j->fi',orr,authored_local),normals=np.einsum('fij,j->fi',orr,normal_local),anchor_local=anchor_local))
    variants={}; active_mask=(times>=start)&(times<=end); edited_mask=(times>=edit_start)&(times<=edit_end)
    measured_variants=[('baseline',source),('candidate',candidate)]
    if coupled_source is not None:measured_variants.append(('coupled_input',coupled_source))
    for label,motion in measured_variants:
        doc,binary,_,_=make_preview(skin,motion,np.zeros(3),repeat=False); write_glb(output/(label+'.glb'),doc,binary)
        doc,binary=read_glb(output/(label+'.glb')); sampler=AnimationSampler(doc,binary,0); joints=doc['skins'][0]['joints']
        floor=[]; objects={name:[] for name in originals}; poses=[]; hand_rows={s['hand']:[] for s in hand_specs}; key_error=0.; bound_rows=[]
        for index,time in enumerate(times):
            world=sampler.sample(float(np.float32(time/30)))[joints]; rotation=world[:,:3,:3]; positions=world[:,:3,3]; poses.append(positions)
            left=int(np.floor(time));right=int(np.ceil(time));fraction=float(time-left)
            if right!=left:
                ta,tb,tt=[float(np.float32(f/30)) for f in [left,right,time]];fraction=(tt-ta)/(tb-ta)
            previous_a=Rotation.from_matrix(p0.previous['local_rot_mats'][left]);previous_b=Rotation.from_matrix(p0.previous['local_rot_mats'][right])
            previous=(previous_a*Rotation.from_rotvec((previous_a.inv()*previous_b).as_rotvec()*fraction)).as_matrix()
            local=rotation.copy()
            for joint,parent in enumerate(p0.parents):
                if parent>=0:local[joint]=rotation[parent].T@rotation[joint]
            angles=Rotation.from_matrix(previous.transpose(0,2,1)@local).magnitude()
            base_root=(1-fraction)*p0.base['root_positions'][left]+fraction*p0.base['root_positions'][right]
            root_delta=positions[0]-base_root;fixed_joints=np.setdiff1d(np.arange(77),p0.editable)
            bound_pass=bool(np.all(angles[p0.editable]<=p0.limits+1e-6) and angles[fixed_joints].max()<1e-6 and -.000001<=root_delta[1]<=p0.config['max_root_lift_m']+.000001 and abs(root_delta[[0,2]]).max()<1e-6)
            bound_rows.append(dict(frame=float(time),passed=bound_pass,maximum_rotation_edit_degrees=float(np.rad2deg(angles).max()),root_lift_m=float(root_delta[1])))
            if time.is_integer(): key_error=max(key_error,float(abs(rotation-motion['global_rot_mats'][int(time)]).max()),float(abs(positions-motion['posed_joints'][int(time)]).max()))
            vertices=p0.surface.vertices(rotation,positions); floor.append(float(vertices[:,1].min()))
            for name,(g,po,ro,_,_) in originals.items():
                gap=np.linalg.norm(vertices-po[index],axis=1)-g.dimensions[0] if g.shape=='sphere' else (np.abs((vertices-po[index])@ro[index])-np.array(g.dimensions)/2).max(-1)
                objects[name].append(float(gap.min()))
            for spec in hand_specs:
                tri=vertices[spec['faces']]; normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0); normal/=np.linalg.norm(normal)
                anchor=vertices[spec['anchor']]; error=float(np.linalg.norm(anchor-spec['targets'][index])); angle=float(np.rad2deg(np.arccos(np.clip(normal@spec['normals'][index],-1,1))))
                gaps=np.linalg.norm(vertices[spec['ids']]-op[index],axis=1)-geometry.dimensions[0]
                triangle,_=triangle_audit(vertices[spec['ids']],spec['ids'],spec['targets'][index],gaps,spec['limits']) if active_mask[index] else (None,None)
                hand_rows[spec['hand']].append(dict(frame=float(time),anchor=anchor.tolist(),object_local_anchor=((anchor-op[index])@orr[index]).tolist(),point_error_m=error,normal_error_degrees=angle,contact_triangle=triangle))
        if key_error>1e-5: raise ValueError('Export differs from native keys')
        contacts={}
        for spec in hand_specs:
            rows=hand_rows[spec['hand']]; local=np.array([r['object_local_anchor'] for r in rows]); point=np.array([r['anchor'] for r in rows]); speed=np.linalg.norm(np.diff(point,axis=0),axis=1)*120
            slip=np.linalg.norm(np.diff(local,axis=0),axis=1)*120; mask=active_mask[:-1]&active_mask[1:]
            boundary={}
            for name,frame in [('entry',start),('release',end)]:
                near=(times[1:]>=frame-1)&(times[:-1]<=frame+1);boundary[name]=dict(peak_anchor_speed_m_s=float(speed[near].max()),peak_object_relative_speed_m_s=float(slip[near].max()))
            active_rows=[r for r,a in zip(rows,active_mask) if a]
            contacts[spec['hand']]=dict(maximum_point_error_m=max(r['point_error_m'] for r in active_rows),maximum_normal_error_degrees=max(r['normal_error_degrees'] for r in active_rows),
                distributed_contact_passes=sum(r['contact_triangle'] is not None for r in active_rows),active_samples=len(active_rows),maximum_relative_slip_m_s=float(slip[mask].max()),boundary=boundary)
        floor=np.array(floor); positions=np.array(poses); velocity=np.diff(positions,axis=0)*120; acceleration=np.diff(velocity,axis=0)*120
        all_geometry=(floor>=p0.config['clearance_m']-1e-6)
        for v in objects.values(): all_geometry &= np.array(v)>=p0.config['object_clearance_m']-1e-6
        region_pass=all_geometry & np.array([r['passed'] for r in bound_rows])
        for spec in hand_specs:
            rows=hand_rows[spec['hand']]
            region_pass &= np.array([r['point_error_m']<=p0.config['point_tolerance_m']+1e-6 and r['normal_error_degrees']<=p0.config['normal_tolerance_degrees']+1e-4 and r['contact_triangle'] is not None for r in rows])
        variants[label]=dict(key_matrix_error=key_error,minimum_floor_m=float(floor.min()),minimum_active_floor_m=float(floor[active_mask].min()),
            objects={name:dict(minimum_clearance_m=min(v),minimum_active_clearance_m=float(np.array(v)[active_mask].min()),worst_frame=float(times[np.argmin(v)])) for name,v in objects.items()},
            contacts=contacts,active_region_pass_count=int(region_pass[active_mask].sum()),active_samples=int(active_mask.sum()),
            original_edit_bound_fail_count=sum(not r['passed'] for r in bound_rows),maximum_rotation_edit_degrees=max(r['maximum_rotation_edit_degrees'] for r in bound_rows),
            edited_geometry_fail_count=int((~all_geometry[edited_mask]).sum()),full_geometry_fail_count=int((~all_geometry).sum()),maximum_joint_speed_m_s=float(np.linalg.norm(velocity,axis=-1).max()),
            maximum_joint_acceleration_m_s2=float(np.linalg.norm(acceleration,axis=-1).max()),glb_sha256=sha256(output/(label+'.glb')))
        save(output/(label+'.json'),dict(frames=times.tolist(),floor_height_m=floor.tolist(),object_clearance_m=objects,hands=hand_rows,edit_bounds=bound_rows,summary=variants[label]))
        print(dict(variant=label,active_passes=variants[label]['active_region_pass_count'],active_samples=int(active_mask.sum()),minimum_active_sphere_m=variants[label]['objects'][protocol['object_id']]['minimum_active_clearance_m'],edited_geometry_fail_count=variants[label]['edited_geometry_fail_count']),flush=True)
    preservation=None
    if coupled_source is not None:
        preservation={hand:dict(source_m_s=variants['coupled_input']['contacts'][hand]['boundary']['release']['peak_object_relative_speed_m_s'],candidate_m_s=variants['candidate']['contacts'][hand]['boundary']['release']['peak_object_relative_speed_m_s']) for hand in variants['candidate']['contacts']}
        for row in preservation.values():row['passed']=row['candidate_m_s']<=row['source_m_s']+1e-7
    save(output/'verification.json',dict(**metadata,variants=variants,release_speed_preservation=preservation,auditor_sha256=sha256(Path(__file__)),release_approved=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--approach-patch',type=Path);parser.add_argument('--floor-patch',type=Path);parser.add_argument('--release-patch',type=Path);parser.add_argument('--spatial-patch',type=Path);parser.add_argument('--coupled-patch',type=Path);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.output,args.approach_patch,args.floor_patch,args.release_patch,args.spatial_patch,args.coupled_patch)
