"""Immutable Studio region-edit requests, supervised fitting and audit results."""
import argparse
import copy
import hashlib
import json
import os
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from scene_release_job import source_metadata
from scene_region_contact import SCHEMA,mesh_fingerprint,compile_region
from hand_patch_authoring import hand_mesh,custom_patch

JOBS=ROOT/'reports/scene-region-jobs'
METHODS=['audit_scene_edit_window.py','plan_scene_edit_window.py','localized_spline.py','shared_pose_diagnostic.py','box_root_optimizer.py','bounded_root_coordinates.py','linear_skin_operator.py','export_motion_sampling.py','export_rate_objective.py','scene_region_job.py','scene_fit_initialization.py','hand_patch_authoring.py','fit_scene_regions.py','audit_scene_region_fit.py','region_contact_objective.py',
         'compile_scene_regions.py','scene_region_contact.py','support_contact_v8.py','scene_constraints.py',
         'scene_solver_context.py','paired_palm_region.py','palm_contacts.py','floor_contact.py','object_geometry.py',
         'scene_release_job.py','compile_scene_contacts.py','contact_spec.py','support_contact.py','support_contact_v5.py',
         'inspect_motion.py','build_soma_preview.py','gltf_tools.py','rig_clip_import.py']
DEFAULT_LIMITS=dict(clearance_m=.002,contact_gap_m=.003,spacing_m=.006,area_m2=.000025,
                    centroid_error_m=.005,local_radius_m=.020,normal_degrees=10.)


def revision(source):
    return hashlib.sha256(json.dumps(dict(scene=source['revision'],mesh=sha256(ASSET),
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}),sort_keys=True).encode()).hexdigest()


def region_source(url):
    source=source_metadata(url,allow_native_runs=True)
    for entry in source['bundle']['scene']['actors'].values():
        if entry.get('source_sha256') and entry['source_sha256']!=source['files'][(ROOT/entry['motion']).resolve()]:
            raise ValueError('Saved actor hash no longer matches its motion')
    return source


def suggested_patch(skin,contact,radius=.045,angle=60.):
    from paired_palm_region import region
    hand=contact['effector']['joint'];patch=region(skin,hand,radius,angle)
    names=list(map(str,skin['rig_joint_names']));allowed=np.array([n.startswith(hand) for n in names])
    supported=np.all(allowed[skin['lbs_indices']]|(skin['lbs_weights']==0),axis=1)
    faces=[i for i in patch['face_ids'] if supported[skin['faces'][i]].all()]
    if not faces:raise ValueError('Suggested patch has no supported hand triangles')
    ids=np.unique(skin['faces'][faces]);old=contact['effector']['surface_vertex']
    anchor=int(ids[np.linalg.norm(skin['bind_vertices'][ids]-skin['bind_vertices'][old],axis=1).argmin()])
    return dict(schema=SCHEMA,mesh_sha256=mesh_fingerprint(skin),hand=hand,face_ids=faces,limits=DEFAULT_LIMITS.copy()),anchor


def metadata(url):
    source=region_source(url);scene=source['bundle']['scene'];skin=dict(np.load(ASSET,allow_pickle=False));contacts=[]
    for c in scene['contacts']:
        if c['effector'].get('joint') not in ['LeftHand','RightHand'] or c['target'].get('space')!='object':continue
        try:
            trial=copy.deepcopy(c)
            if 'region_contact' in c:binding=copy.deepcopy(c['region_contact']);anchor=c['effector']['surface_vertex'];mode='saved'
            else:binding,anchor=suggested_patch(skin,c);mode='suggested'
            trial['effector']['surface_vertex']=anchor;trial['region_contact']=binding;compile_region(trial,scene,skin)
            contacts.append(dict(id=c['id'],actor=c['actor'],hand=c['effector']['joint'],supported=True,
                edit=dict(id=c['id'],start_frame=c['start_frame'],end_frame=c['end_frame'],point_m=c['target']['point_m'],
                    anchor_tolerance_m=c.get('tolerance_m',.005),patch_mode=mode,patch_radius_m=.045,patch_normal_degrees=60.,limits=binding['limits']),
                target_object=c['target']['object'],anchor_vertex=anchor,patch_vertices=len(np.unique(skin['faces'][binding['face_ids']])),
                patch_face_ids=binding['face_ids'],hand_mesh=hand_mesh(skin,c['effector']['joint'])))
        except (ValueError,KeyError,IndexError) as exc:
            contacts.append(dict(id=c['id'],actor=c['actor'],supported=False,reason=str(exc)))
    return dict(source_url=url,revision=revision(source),frames=scene['frame_count'],actors=list(scene['actors']),contacts=contacts,
        note='Suggested palm patches are geometric proposals. Changes create a new authored condition; fitting and completion are not quality approval.')


def validate_window(window,frames,contacts):
    if window is None:return None
    from localized_spline import localized_controls
    from support_contact_v5 import correction_basis
    from support_contact_v8 import CONFIG
    basis,_=correction_basis(frames,CONFIG['knot_spacing_frames'])
    localized_controls(basis,window)
    if any(c['start_frame']<window[0] or c['end_frame']>window[1] for c in contacts):
        raise ValueError('Edit range must include every selected contact interval')
    return list(window)


def validate(payload):
    required={'source_url','revision','actor','label','contacts'}
    if not isinstance(payload,dict) or not required<=set(payload) or set(payload)-required-{'edit_window'}:
        raise ValueError('Scene, revision, actor, name and contact edits required')
    source=region_source(payload['source_url'])
    if payload['revision']!=revision(source):raise ValueError('Scene, mesh or fitting code changed; reload the saved scene')
    if not isinstance(payload['label'],str) or not 1<=len(payload['label'].strip())<=100:raise ValueError('Name must contain 1–100 characters')
    scene=copy.deepcopy(source['bundle']['scene']);actor=payload['actor']
    if actor not in scene['actors']:raise ValueError('Select a source actor')
    edits=payload['contacts']
    if not isinstance(edits,list) or not 1<=len(edits)<=8:raise ValueError('Select one to eight contacts')
    ids=[e.get('id') for e in edits if isinstance(e,dict)]
    if len(ids)!=len(edits) or len(set(ids))!=len(ids):raise ValueError('Distinct contact edits required')
    skin=dict(np.load(ASSET,allow_pickle=False))
    for edit in edits:
        keys={'id','start_frame','end_frame','point_m','anchor_tolerance_m','patch_mode','patch_radius_m','patch_normal_degrees','limits'}
        if edit.get('patch_mode')=='custom':keys|={'patch_mesh_sha256','patch_face_ids'}
        if set(edit)!=keys:raise ValueError('Invalid region contact fields')
        matches=[c for c in scene['contacts'] if c['id']==edit['id'] and c['actor']==actor]
        if len(matches)!=1:raise ValueError('Contact must belong to the selected actor')
        c=matches[0]
        if edit['patch_mode']=='saved':
            if 'region_contact' not in c:raise ValueError('No saved region exists for this contact')
            binding=copy.deepcopy(c['region_contact']);anchor=c['effector']['surface_vertex']
        elif edit['patch_mode']=='suggested':
            radius,angle=edit['patch_radius_m'],edit['patch_normal_degrees']
            if type(radius) not in [int,float] or not .01<=radius<=.06 or type(angle) not in [int,float] or not 5<=angle<=85:
                raise ValueError('Patch radius must be 1–6 cm and selection angle 5–85 degrees')
            binding,anchor=suggested_patch(skin,c,radius,angle)
        elif edit['patch_mode']=='custom':
            binding,anchor=custom_patch(skin,c,edit)
        else:raise ValueError('Choose a saved, suggested or painted hand region')
        binding['limits']=copy.deepcopy(edit['limits']);c['region_contact']=binding
        c['effector']=dict(joint=binding['hand'],surface_vertex=anchor)
        c['start_frame']=edit['start_frame'];c['end_frame']=edit['end_frame'];c['target']['point_m']=edit['point_m'];c['tolerance_m']=edit['anchor_tolerance_m']
        compile_region(c,scene,skin)
    from compile_scene_regions import compile_regions
    compile_regions(scene,actor,ids,skin)
    validate_window(payload.get('edit_window'),scene['frame_count'],edits)
    return source,scene,ids


def prepare(payload,folder):
    source,scene,ids=validate(payload);folder=Path(folder).resolve()
    if not folder.is_relative_to(JOBS.resolve()):raise ValueError('Region job must stay within its job collection')
    folder.mkdir(parents=True,exist_ok=False);(folder/'source').mkdir()
    for name,entry in scene['actors'].items():
        for field,original,filename in [('motion',ROOT/entry['motion'],'motion.npz'),('preview_glb',source['base']/entry['preview_glb'],'actor.glb')]:
            target=folder/'source/actors'/name/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,target)
            if sha256(target)!=source['files'][original.resolve()]:raise ValueError('Source changed during snapshot')
            entry[field]=target.relative_to(ROOT if field=='motion' else folder).as_posix()
        entry['source_sha256']=sha256(ROOT/entry['motion'])
    save(folder/'source/authored-scene.json',scene);save(folder/'source/original-bundle.json',source['bundle'])
    (folder/'source/implementation').mkdir()
    for name in METHODS:shutil.copyfile(ROOT/'scripts'/name,folder/'source/implementation'/name)
    license_path=source['base']/'SOMA-preview-LICENSE.txt'
    if not license_path.exists():license_path=ROOT/'vendor/kimodo/LICENSE'
    shutil.copyfile(license_path,folder/'SOMA-preview-LICENSE.txt')
    if sha256(folder/'SOMA-preview-LICENSE.txt')!=source['files'][license_path.resolve()]:raise ValueError('License changed during snapshot')
    if revision(source)!=payload['revision']:raise ValueError('Implementation or mesh changed during snapshot')
    save(folder/'request.json',dict(at=now(),authored=payload,contact_ids=ids,mesh_sha256=sha256(ASSET),
        files={p.relative_to(folder).as_posix():sha256(p) for p in (folder/'source').rglob('*') if p.is_file()}))
    save(folder/'pipeline.json',dict(status='starting',stage='Prepared source and authored regions'))


def audit_summary(audit):
    candidate,source=audit['variants']['candidate'],audit['variants']['source']
    regressions=[key for key in ['peak_joint_speed_m_s','peak_joint_acceleration_m_s2'] if candidate[key]>source[key]+1e-7]
    passed=bool(audit['hard_edit_bounds_passed'] and candidate['contact_failures']==0 and candidate['geometry_failures']==0)
    return dict(contact_geometry_passed=passed,contact_failures=candidate['contact_failures'],contact_samples=candidate['contact_samples'],
        geometry_failures=candidate['geometry_failures'],geometry_samples=len(candidate['rows']),hard_edit_bounds_passed=audit['hard_edit_bounds_passed'],
        motion_regressions=regressions,quality_approved=False,review_status='not_reviewed')


def bundle(scene,assessment,skin):
    from scene_constraints import effector_track
    actors={name:dict(np.load(ROOT/e['motion'],allow_pickle=False)) for name,e in scene['actors'].items()};tracks={}
    def track(name,effector):
        m=actors[name];return effector_track(dict(positions=m['posed_joints'],rotations=m['global_rot_mats']),effector,skin).tolist()
    for c in scene['contacts']:
        row=dict(actual=track(c['actor'],c['effector']))
        if c['target']['space']=='actor':row['target']=track(c['target']['actor'],c['target'])
        tracks[c['id']]=row
    return dict(scene=scene,evaluation=assessment,native_contact_tracks=tracks)


def include_window_audit(study,geometry_path,output,summary,window):
    from audit_scene_edit_window import run as audit_window
    from plan_scene_edit_window import plan,boundary_policy
    study,output=Path(study),Path(output)
    protocol=read(study/'protocol.json');geometry=read(geometry_path)
    if protocol.get('edit_window')!=window or geometry['result_sha256']!=sha256(study/'result.json'):
        raise ValueError('Window review differs from requested fit or geometry audit')
    preservation=audit_window(study,output/'window-audit')
    summary['window_preservation']=preservation['groups']
    for group,flag in [('locked_segments','edit_window_outside_change'),('boundary_segments','edit_window_boundary_change')]:
        if preservation['groups'][group]['within_numerical_tolerance'] is False:summary['motion_regressions'].append(flag)
    rows=geometry['variants']['candidate']['rows']
    summary['window_geometry']=plan(rows,window,preservation['frames'],protocol['config']['clearance_m'],protocol['config']['object_clearance_m'],preserve_boundary_keys=boundary_policy(study))
    save(output/'window-geometry.json',summary['window_geometry'])


def run(folder):
    import psutil
    folder=Path(folder).resolve()
    if not folder.is_relative_to(JOBS.resolve()):raise ValueError('Invalid job folder')
    try:
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        request=read(folder/'request.json')
        for filename,digest in request['files'].items():
            if sha256(folder/filename)!=digest:raise ValueError('Saved input changed')
        if sha256(ASSET)!=request['mesh_sha256']:raise ValueError('Character mesh changed')
        for name in METHODS:
            if sha256(ROOT/'scripts'/name)!=sha256(folder/'source/implementation'/name):raise ValueError('Fitting code changed after preparation')
        payload=request['authored'];actor=payload['actor']
        save(folder/'pipeline.json',dict(status='processing',stage='Fitting authored hand regions'))
        from fit_scene_regions import run as fit
        window=payload.get('edit_window')
        authored=read(folder/'source/authored-scene.json')
        validate_window(window,authored['frame_count'],[c for c in authored['contacts'] if c['id'] in request['contact_ids']])
        options={} if window is None else dict(edit_window=window)
        fit(folder/'source/authored-scene.json',actor,request['contact_ids'],folder/'fit',stages=3,iterations=40,seconds=300,region_loss='balanced',**options)
        save(folder/'pipeline.json',dict(status='processing',stage='Checking exported contact, clearance and edit bounds'))
        from audit_scene_region_fit import run as audit
        audit(folder/'fit',folder/'audit');summary=audit_summary(read(folder/'audit/verification.json'))
        if window is not None:
            include_window_audit(folder/'fit',folder/'audit/verification.json',folder,summary,window)
        save(folder/'assessment.json',summary)
        skin=dict(np.load(ASSET,allow_pickle=False));input_scene=read(folder/'source/authored-scene.json');candidate=read(folder/'fit/candidate-scene.json')
        input_scene['actors'][actor]['preview_glb']='fit/source.glb';candidate['actors'][actor]['preview_glb']='fit/candidate.glb'
        input_bundle=bundle(input_scene,read(folder/'fit/source-evaluation.json'),skin)
        candidate_bundle=bundle(candidate,read(folder/'fit/candidate-evaluation.json'),skin);candidate_bundle['region_fit']=summary
        save(folder/'input.json',input_bundle);save(folder/'candidate.json',candidate_bundle)
        label=payload['label'].strip();note=('Contact and clearance samples pass.' if summary['contact_geometry_passed'] else 'Needs correction: contact or clearance checks failed.')+' Human review pending.'
        downloads=[dict(label='Candidate GLB',path='fit/candidate.glb'),dict(label='Independent audit',path='audit/verification.json'),dict(label='Authored scene',path='candidate.json')]
        if window is not None:
            downloads.extend([dict(label='Edit-window preservation',path='window-audit/verification.json'),dict(label='Remaining geometry by edit range',path='window-geometry.json')])
        save(folder/'manifest.json',dict(scenes=[dict(id='input',label=label+' · Input',variants=dict(palm='input.json'),review_note='Preserved source with the newly authored contact condition.'),
            dict(id='candidate',label=label+' · Candidate',variants=dict(palm='candidate.json'),review_note=note,downloads=downloads)]))
        save(folder/'pipeline.json',dict(status='complete',stage=note,finished_at=now(),assessment=summary))
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);run(parser.parse_args().folder)
