"""Author bounded root translations for a contact target, never a motion clip.

Preserves every joint rotation. Searches a declared clearance grid on a fixed
pose; no generated sample is selected or relabeled as successful.
"""
import argparse
import copy
import os
from pathlib import Path
import shutil
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET,make_preview
from floor_contact import Surface
from convex_partner_surface import penetration
from verify_palm_region import measure
from gltf_tools import write_glb
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def translations(points,vertex,normal,separation,root_limits=(.04,.12,.04),tangent_offset=None):
    """Symmetric displacement, then minimum shared lift for 1 mm clearance."""
    relative=points[0][vertex]-points[1][vertex]+normal*separation
    if tangent_offset is not None:relative+=np.asarray(tangent_offset)
    deltas=np.array([-relative/2,relative/2])
    lift=max(0.,*(.001-float(p[:,1].min())-d[1] for p,d in zip(points,deltas)))
    deltas[:,1]+=lift
    if np.any(np.abs(deltas)>np.asarray(root_limits)+1e-10):raise ValueError('Target root displacement exceeds declared limits')
    return deltas


def inspect(points,patches,faces,vertex):
    region=measure(points,patches,faces,.003)
    collision=[penetration(points[a],points[b],faces) for a,b in [(0,1),(1,0)]]
    gap=float(np.linalg.norm(points[0][vertex]-points[1][vertex]));floor=[max(0.,-float(p[:,1].min())) for p in points]
    screens=dict(point=gap<=.03,region=all(d['within_tolerance_count']>=3 and min(d['source_area_witness']['area_m2'],d['target_area_witness']['area_m2'])>=2.5e-5 for d in region['directions']),normal=region['opposing_normal_degrees']<=20,penetration=max(c['max_depth_m'] for c in collision)<=.005,floor=max(floor)<=.005)
    return dict(gap_m=gap,region=region,collision=collision,floor_depth_m=floor,screens=screens,passed=all(screens.values()))


def run(study,output,grid=None,prior_plan=None,tangent_offsets=None):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve previous target plan')
    grid=[0.,.001,.002,.003,.004,.005,.008,.012] if grid is None else list(grid)
    if not grid or not np.isfinite(grid).all() or any(x<0 or x>.03 for x in grid) or any(b<=a for a,b in zip(grid,grid[1:])):
        raise ValueError('Separation grid must be finite, strictly increasing and within 0 to 30 mm')
    tangent_offsets=[0.] if tangent_offsets is None else list(tangent_offsets)
    if not tangent_offsets or not np.isfinite(tangent_offsets).all() or any(abs(x)>.02 for x in tangent_offsets) or len(set(tangent_offsets))!=len(tangent_offsets):
        raise ValueError('Tangent offsets must be distinct finite distances within 20 mm')
    spec=read(study/'protocol.json');scene=read(study/'guide-scene.json')['scene'];skin=dict(np.load(ASSET,allow_pickle=False));surface=Surface(skin)
    if sha256(study/'guide-scene.json')!=spec['guide_scene_sha256']:raise ValueError('Changed guide scene')
    prior=None
    if prior_plan is not None:
        prior_plan=Path(prior_plan).resolve();request=read(prior_plan/'request.json')
        if read(prior_plan/'pipeline.json')['status']!='complete_no_feasible_target':raise ValueError('Prior plan must be a completed unsuccessful search')
        if request['source_protocol_sha256']!=sha256(study/'protocol.json'):raise ValueError('Prior plan uses different targets')
        prior=dict(path=str(prior_plan),request_sha256=sha256(prior_plan/'request.json'),trials_sha256=sha256(prior_plan/'trials.json'))
    patchfile=Path(spec['guide_export'])/'refinement/palm-region.json';patches=read(patchfile);event=spec['event_frame'];vertex=scene['contacts'][0]['effector']['surface_vertex']
    data=[];points=[];rotations=[];placements=[]
    for actor in ['A','B']:
        guide=spec['guides'][actor];path=ROOT/guide['path']
        if sha256(path)!=guide['sha256']:raise ValueError('Guide changed')
        motion=dict(np.load(path,allow_pickle=False));transform=scene['actors'][actor]['transform'];rot=Rotation.from_quat(transform['rotation_xyzw']).as_matrix();shift=np.asarray(transform['translation_m'])
        data.append(motion);rotations.append(rot);placements.append(shift);points.append(surface.vertices(motion['global_rot_mats'][event],motion['posed_joints'][event])@rot.T+shift)
    triangle=points[0][skin['faces'][patches['A']['face_ids']]];normal=np.cross(triangle[:,1]-triangle[:,0],triangle[:,2]-triangle[:,0]).sum(0);normal/=np.linalg.norm(normal)
    names=list(map(str,skin['rig_joint_names']))
    long_axis=(data[0]['posed_joints'][event,names.index('LeftHandMiddle1')]-data[0]['posed_joints'][event,names.index('LeftHand')])@rotations[0].T
    tangent=np.cross(normal,long_axis)
    if np.linalg.norm(tangent)<1e-10:raise ValueError('Degenerate palm tangent')
    tangent/=np.linalg.norm(tangent)
    output.mkdir();(output/'implementation').mkdir()
    names=['plan_paired_contact_target.py','convex_partner_surface.py','verify_palm_region.py','floor_contact.py','rig_asset.py','rig_clip_import.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),source_study=str(study),source_protocol_sha256=sha256(study/'protocol.json'),source_guides=spec['guides'],scene_sha256=sha256(study/'guide-scene.json'),
        patch_sha256=sha256(patchfile),skin_sha256=sha256(ASSET),event_frame=event,guide_frames=[0,event,149],separation_grid_m=grid,root_component_limits_m=[.04,.12,.04],floor_clearance_m=.001,
        tangent_offsets_m=tangent_offsets,tangent_world=tangent.tolist(),tangent_definition='Normalized cross product of actor A patch normal with LeftHand-to-LeftHandMiddle1 vector; across palm width.',
        selection='First grid entry passing all fixed geometric screens; all entries retained. Then independently decode and recheck exported target frame.',prior_plan=prior,
        pid=os.getpid(),created=psutil.Process().create_time(),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Authored key-pose target planning, not correction of generated motion or a playback-ready animation. All joint rotations and unselected frames retained. Root positions may change at only0/event/149. No physical balance, contact support, continuous motion or anatomy approval.'))
    trials=[]
    with threadpool_limits(limits=1):
        for separation in grid:
            for offset in tangent_offsets:
                try:delta=translations(points,vertex,normal,separation,tangent_offset=tangent*offset)
                except ValueError as exc:
                    row=dict(separation_m=separation,tangent_offset_m=offset,passed=False,rejected=str(exc))
                else:row=dict(separation_m=separation,tangent_offset_m=offset,world_root_delta_m=delta.tolist(),**inspect([p+d for p,d in zip(points,delta)],[patches['A'],patches['B']],skin['faces'],vertex))
                trials.append(row);save(output/'trials.json',dict(rows=trials,quality_approved=False));save(output/'pipeline.json',dict(status='planning',completed_trials=len(trials),total=len(grid)*len(tangent_offsets)));print(separation,offset,row.get('screens',row.get('rejected')),flush=True)
        selected=next((i for i,r in enumerate(trials) if r['passed']),None)
        if selected is None:
            save(output/'pipeline.json',dict(status='complete_no_feasible_target',quality_approved=False));return
        delta=np.asarray(trials[selected]['world_root_delta_m']);export_points=[];anchors=[];planned_scene=copy.deepcopy(scene);planned_scene['id']='authored-contact-target'
        for i,actor in enumerate(['A','B']):
            motion=copy.deepcopy(data[i]);deltas={event:delta[i]}
            for frame in [0,149]:
                p=surface.vertices(motion['global_rot_mats'][frame],motion['posed_joints'][frame])@rotations[i].T+placements[i]
                lift=max(0.,.001-float(p[:,1].min()))
                if lift>.12:raise ValueError('Boundary target exceeds vertical root budget')
                deltas[frame]=np.array([0.,lift,0.])
            for frame,d in deltas.items():
                native=d@rotations[i];motion['root_positions'][frame]+=native;motion['posed_joints'][frame]+=native
                if 'smooth_root_pos' in motion:motion['smooth_root_pos'][frame]+=native
            for key in ['local_rot_mats','global_rot_mats','foot_contacts']:
                if not np.array_equal(motion[key],data[i][key]):raise ValueError('Protected target arrays changed')
            folder=output/'guides'/actor;folder.mkdir(parents=True);np.savez_compressed(folder/'motion.npz',**motion)
            doc,binary,_,_=make_preview(skin,motion,np.zeros(3),repeat=False);write_glb(folder/'character.glb',doc,binary)
            rig=RigAsset.load(folder/'character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
            for frame,d in deltas.items():
                p=rig.vertices(sampler.sample(float(np.float32(frame/30))))@rotations[i].T+placements[i]
                depth=max(0.,-float(p[:,1].min()))
                if depth>.005:raise ValueError('Decoded boundary target fails floor screen')
                anchors.append(dict(actor=actor,frame=frame,world_root_delta_m=d.tolist(),decoded_floor_depth_m=depth))
                if frame==event:export_points.append(p)
            planned_scene['actors'][actor].update(motion=(folder/'motion.npz').relative_to(ROOT).as_posix(),source_sha256=sha256(folder/'motion.npz'),preview_glb=f'guides/{actor}/character.glb')
        decoded=inspect(export_points,[patches['A'],patches['B']],skin['faces'],vertex)
        if not decoded['passed']:raise ValueError('Decoded target fails independent geometric check')
        save(output/'scene.json',dict(scene=planned_scene));save(output/'verification.json',dict(at=now(),selected_trial=selected,decoded=decoded,anchors=anchors,request_sha256=sha256(output/'request.json'),trials_sha256=sha256(output/'trials.json'),quality_approved=False))
        save(output/'pipeline.json',dict(status='complete',quality_approved=False,playback_ready=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);p.add_argument('--separations',type=float,nargs='+');p.add_argument('--prior-plan',type=Path);p.add_argument('--tangent-offsets',type=float,nargs='+');a=p.parse_args();run(a.study,a.output,a.separations,a.prior_plan,a.tangent_offsets)
