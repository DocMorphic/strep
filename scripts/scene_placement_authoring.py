"""Immutable authored placement snapshots and necessary native anchor reach checks.

Placement changes define a new request. Source animations and old evidence stay
preserved. Reach checks cannot certify feasible poses or acceptable geometry.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import uuid
import numpy as np
from strep import ROOT, read, save, sha256, now
from scene_constraints import pose, sample_object, transform_motion, target_track
from skin_point_reach_bound import error_lower_bound

JOBS = ROOT/'reports/scene-placement-jobs'
SKIN = ROOT/'vendor/kimodo/kimodo/assets/skeletons/somaskel77/skin_standard.npz'
METHODS = ['scene_placement_authoring.py','skin_point_reach_bound.py','scene_constraints.py',
           'scene_release_job.py','object_geometry.py','floor_contact.py','palm_contacts.py','inspect_motion.py']


def source(url):
    from scene_release_job import source_metadata
    result = source_metadata(url, allow_native_runs=True, allow_actor_only=True)
    for entry in result['bundle']['scene']['actors'].values():
        if entry.get('source_sha256') != result['files'][(ROOT/entry['motion']).resolve()]:
            raise ValueError('Saved animation hash does not match its clip')
    return result


def revision(data):
    return hashlib.sha256(json.dumps(dict(source=data['revision'],skin=sha256(SKIN),
        methods={name:sha256(ROOT/'scripts'/name) for name in METHODS}),sort_keys=True).encode()).hexdigest()


def metadata(url):
    data = source(url)
    return dict(schema='strep-scene-placement-source-v1',source_url=url,revision=revision(data),
                frames=data['bundle']['scene']['frame_count'],placement=placements(data['bundle']['scene']))


def placements(scene):
    return dict(actors={name:copy.deepcopy(entry['transform']) for name,entry in scene['actors'].items()},
                objects={name:copy.deepcopy(obj['keyframes']) for name,obj in scene['objects'].items()})


def apply_placement(original, draft):
    if not isinstance(draft,dict) or set(draft) != {'actors','objects'}:
        raise ValueError('Actor and object placement maps required')
    if any(not isinstance(draft[k],dict) or set(draft[k]) != set(original[k]) for k in ('actors','objects')):
        raise ValueError('Preserve all original actor and object identities')
    scene = copy.deepcopy(original)
    for name, transform in draft['actors'].items():
        pose(transform)
        if set(transform) != {'translation_m','rotation_xyzw'} or max(abs(x) for x in transform['translation_m']) > 100:
            raise ValueError('Actor placement must remain within 100 metres')
        scene['actors'][name]['transform'] = copy.deepcopy(transform)
    for name, keys in draft['objects'].items():
        if not isinstance(keys,list) or [k.get('frame') for k in keys if isinstance(k,dict)] != [k['frame'] for k in original['objects'][name]['keyframes']]:
            raise ValueError('Preserve every original object keyframe and time')
        scene['objects'][name]['keyframes'] = copy.deepcopy(keys)
        sample_object(scene['objects'][name], scene['frame_count'])
        if any(max(abs(x) for x in k['translation_m']) > 100 for k in keys):
            raise ValueError('Object placement must remain within 100 metres')
    return scene


def validate(payload):
    required = {'source_url','revision','placement','label'}
    if not isinstance(payload,dict) or set(payload) != required:
        raise ValueError('Exact source, revision, placement and name required')
    if not isinstance(payload['label'],str) or not 1 <= len(payload['label'].strip()) <= 100:
        raise ValueError('Name must contain 1–100 characters')
    data = source(payload['source_url'])
    if payload['revision'] != revision(data):
        raise ValueError('Source, skin or check code changed; reload the scene')
    scene = apply_placement(data['bundle']['scene'],payload['placement'])
    return data,scene


def measure(scene, skin, motions):
    frames = scene['frame_count']
    if len({c['id'] for c in scene['contacts']}) != len(scene['contacts']):
        raise ValueError('Preserve distinct contact identities')
    actors = {name:transform_motion(motions[name],entry['transform']) for name,entry in scene['actors'].items()}
    local_actors = {name:dict(positions=motion['posed_joints'],rotations=motion['global_rot_mats']) for name,motion in motions.items()}
    objects = {name:sample_object(obj,frames) for name,obj in scene['objects'].items()}
    inverse = np.linalg.inv(skin['bind_rig_transform'])
    names = list(map(str,skin['rig_joint_names']))
    rows,skipped,tracks,contacts = [],[],{},[]
    from scene_constraints import effector_track
    for contact in scene['contacts']:
        name = contact['actor'];effector = contact['effector'];actor = actors[name]
        actual = effector_track(actor,effector,skin)
        desired = target_track(contact['target'],actors,objects,frames,skin)
        tracks[contact['id']] = dict(actual=effector_track(local_actors[name],effector,skin).tolist())
        if contact['target']['space'] == 'actor':
            tracks[contact['id']]['target'] = effector_track(local_actors[contact['target']['actor']],contact['target'],skin).tolist()
        first,last = contact['start_frame'],contact['end_frame'];tolerance = contact.get('tolerance_m',.03)
        if type(first) is not int or type(last) is not int or not 0 <= first <= last < frames:
            raise ValueError('Contact interval must stay within the original clock')
        if type(tolerance) not in (int,float) or not np.isfinite(tolerance) or tolerance <= 0:
            raise ValueError('Positive finite authored anchor tolerance required')
        errors = np.linalg.norm(actual-desired,axis=1);valid=np.flatnonzero(errors[first:last+1] <= tolerance)+first
        contacts.append(dict(id=contact['id'],actor=name,start_frame=first,end_frame=last,
            max_interval_error_m=float(errors[first:last+1].max()),mean_interval_error_m=float(errors[first:last+1].mean()),
            frames_within_tolerance=len(valid),interval_frames=last-first+1,
            first_valid_frame=int(valid[0]) if len(valid) else None,
            all_requested_frames_within_tolerance=bool(len(valid)==last-first+1)))
        if contact['target']['space'] == 'actor':
            skipped.append(dict(contact=contact['id'],reason='Partner targets may move under coupled edits; no impossibility claim'))
            continue
        if 'surface_vertex' in effector:
            vertex = effector['surface_vertex'];indices=skin['lbs_indices'][vertex];weights=skin['lbs_weights'][vertex]
            local=(inverse[indices]@np.r_[skin['bind_vertices'][vertex],1])[:,:3]
        else:
            indices=np.array([names.index(effector['joint'])]);weights=np.ones(1)
            local=np.asarray(effector['offset_m'])[None]
        clock=slice(first,last+1)
        result=error_lower_bound(actor['positions'][clock][:,indices],actor['rotations'][clock][:,indices],
                                 local,weights,desired[clock],.22)
        lower=result['error_lower_bound_m'];bad=np.flatnonzero(lower > tolerance)+first
        worst=int(lower.argmax())+first
        rows.append(dict(contact=contact['id'],actor=name,start_frame=first,end_frame=last,samples=len(lower),
            position_budget_m=.22,authored_tolerance_m=tolerance,maximum_error_lower_bound_m=float(lower.max()),
            incompatible_frames=bad.tolist(),worst_frame=worst,worst_seconds=worst/30,
            lower_bounds_m=lower.tolist(),arithmetic_slack_m=result['arithmetic_slack_m']))
    report=dict(schema='strep-scene-placement-reach-v1',status='provably_incompatible' if any(r['incompatible_frames'] for r in rows) else 'not_ruled_out',
        rows=rows,skipped=skipped,quality_approved=False,release_approved=False,
        scope='Authored native anchor tolerances against the selected saved native animation and current scene placement, '
              'with every joint edit within 22 cm. Proper rotations are unrestricted. No converse feasibility, region, '
              'anatomy, speed, geometry, physics, export or between-key certificate. This check does not alter fitting options.')
    bundle=dict(scene=scene,evaluation=dict(contacts=contacts,object_collisions=[],geometry_evaluated=False,anchor_only=True),
                native_contact_tracks=tracks,quality_approved=False,release_approved=False)
    return report,bundle


def check(payload):
    data,scene=validate(payload)
    motions={name:dict(np.load(ROOT/entry['motion'],allow_pickle=False)) for name,entry in scene['actors'].items()}
    report,_=measure(scene,dict(np.load(SKIN,allow_pickle=False)),motions)
    if any(sha256(path)!=digest for path,digest in data['files'].items()) or revision(data)!=payload['revision']:
        raise ValueError('Source changed during reach check')
    return dict(**report,source_url=payload['source_url'],revision=payload['revision'],
                placement_sha256=hashlib.sha256(json.dumps(payload['placement'],sort_keys=True).encode()).hexdigest())


def stage(payload, folder=None):
    data,scene=validate(payload)
    folder=Path(folder).resolve() if folder is not None else JOBS/('placement-'+uuid.uuid4().hex)
    if not folder.is_relative_to(JOBS.resolve()) or folder == JOBS.resolve():
        raise ValueError('Placement snapshot must stay inside its collection')
    motions={name:dict(np.load(ROOT/entry['motion'],allow_pickle=False)) for name,entry in scene['actors'].items()}
    report,bundle=measure(scene,dict(np.load(SKIN,allow_pickle=False)),motions)
    folder.mkdir(parents=True,exist_ok=False)
    save(folder/'pipeline.json',dict(status='processing',stage='Saving authored placement'))
    try:
        save(folder/'source-bundle.json',data['bundle']);save(folder/'request.json',payload)
        for name,entry in scene['actors'].items():
            for field,path,filename in [('motion',ROOT/entry['motion'],'motion.npz'),('preview_glb',data['base']/entry['preview_glb'],'actor.glb')]:
                target=folder/'assets'/name/filename;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target)
                if sha256(target)!=data['files'][path.resolve()]:
                    raise ValueError('Source asset changed during snapshot')
                entry[field]=target.relative_to(ROOT if field=='motion' else folder).as_posix()
            entry['source_sha256']=sha256(ROOT/entry['motion'])
        license_path=data['base']/'SOMA-preview-LICENSE.txt'
        if not license_path.is_file():license_path=ROOT/'vendor/kimodo/LICENSE'
        shutil.copyfile(license_path,folder/'SOMA-preview-LICENSE.txt')
        if sha256(folder/'SOMA-preview-LICENSE.txt')!=data['files'][license_path.resolve()]:
            raise ValueError('Source license changed during snapshot')
        scene['id']='placement'
        save(folder/'reach.json',report);save(folder/'scene.json',bundle)
        save(folder/'manifest.json',dict(scenes=[dict(id='placement',label=payload['label'].strip(),variants=dict(palm='scene.json'),
            review_note='Authored placement snapshot; original animation bytes preserved. Anchor reach was screened; geometry and naturalness are unevaluated.',
            downloads=[dict(label='Anchor reach screen',path='reach.json'),dict(label='Original scene and evidence',path='source-bundle.json')])],
            quality_approved=False,release_approved=False))
        if any(sha256(path)!=digest for path,digest in data['files'].items()) or revision(data)!=payload['revision']:
            raise ValueError('Source changed while saving placement')
        (folder/'implementation').mkdir()
        for name in METHODS:shutil.copyfile(ROOT/'scripts'/name,folder/'implementation'/name)
        if revision(data)!=payload['revision']:
            raise ValueError('Check implementation changed during snapshot')
        if any(sha256(folder/'implementation'/name)!=sha256(ROOT/'scripts'/name) for name in METHODS):
            raise ValueError('Check implementation changed during copy')
        save(folder/'provenance.json',dict(at=now(),source_url=payload['source_url'],source_revision=payload['revision'],
            source_files_sha256={str(path):digest for path,digest in data['files'].items()},skin_sha256=sha256(SKIN),
            files_sha256={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file() and p.name!='pipeline.json'},
            quality_approved=False,release_approved=False,animation_generated=False,optimizer_ran=False))
        save(folder/'pipeline.json',dict(status='complete',stage='Authored placement saved; geometry review required'))
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc)))
        raise
    return dict(collection=folder.relative_to(ROOT/'reports').as_posix(),scene_id='placement',reach=report,
                source_url=payload['source_url'],revision=payload['revision'],quality_approved=False,release_approved=False)
