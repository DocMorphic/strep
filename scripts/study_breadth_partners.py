"""Scene-context evaluation of independent breadth-study partner actors."""
import argparse
import os
import shutil
from pathlib import Path
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET

SOURCES=['study_breadth_partners.py','scene_constraints.py','palm_contacts.py','floor_contact.py',
         'audit_partner_surface.py','run_godot_scene_import.py','godot_scene_import_audit.gd','inspect_motion.py']
CASES={'partner_interaction-handshake':dict(hand='RightHand',start=60,end=119),
       'partner_interaction-left-high-five':dict(hand='LeftHand',start=75,end=75)}


def placement(root, actor):
    yaw=0 if actor=='A' else 180
    rot=Rotation.from_euler('y',yaw,degrees=True)
    anchor=np.array([0.,0.,-.55 if actor=='A' else .55])
    # Preserve source Y and all motion; only initial root XZ is positioned.
    initial=np.array(root,float).copy();initial[1]=0
    return dict(translation_m=(anchor-rot.apply(initial)).tolist(),rotation_xyzw=rot.as_quat().tolist())


def prepare(breadth,output):
    from breadth_study import validate_freeze,verify_complete
    from palm_contacts import calibrate
    breadth,output=Path(breadth).resolve(),Path(output).resolve()
    frozen=validate_freeze(breadth);protocol=read(breadth/'protocol.json')
    cases=[c for c in protocol['cases'] if c['id'] in CASES]
    requested={c['id']+'-'+a['id'].lower() for c in cases for a in c['actors']}
    found={}
    for batch in frozen['batches']:
        requests=read(ROOT/batch['request'])['requests']
        if not any(r['id'] in requested for r in requests):continue
        for take in verify_complete(batch):
            if take['request_id'] in requested:
                found[(take['request_id'],take['seed'])]=(ROOT/batch['output']/'takes'/take['id'],take)
    expected={(c['id']+'-'+a['id'].lower(),s) for c in cases for a in c['actors'] for s in c['seeds']}
    if len(cases)!=2 or set(found)!=expected:raise ValueError('Require every actor and seed from both complete source populations')
    if output.exists():raise ValueError('Preserve earlier study')
    output.mkdir(parents=True);(output/'assets').mkdir();(output/'implementation').mkdir()
    for name in SOURCES:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    palms=calibrate(dict(np.load(ASSET,allow_pickle=False)))
    save(output/'palm-calibration.json',dict(mesh_sha256=sha256(ASSET),candidates=palms,anatomical_review=None))
    manifest=dict(created_at=now(),scenes=[],assets={},scope='Independently generated partner actors in fixed authored scenes. Unchanged source motion, no interaction fitting, physics or successful-action claim.')
    entries=[]
    for case in cases:
        setup=CASES[case['id']]
        for seed in case['seeds']:
            identifier=case['id']+'-seed-'+str(seed);actors={};hashes={}
            for actor in case['actors']:
                label=actor['id'];source,take=found[(case['id']+'-'+label.lower(),seed)]
                native=source/'motion.npz';glb=source/'soma.glb'
                if sha256(native)!=take['source_sha256'] or sha256(glb)!=take['hashes']['soma.glb']:raise ValueError('Source changed')
                stem=identifier+'-'+label;dest=output/'assets'/(stem+'.npz');shutil.copyfile(native,dest)
                preview='assets/'+stem+'.glb';shutil.copyfile(glb,output/preview)
                motion=dict(np.load(dest,allow_pickle=False))
                actors[label]=dict(motion=dest.relative_to(ROOT).as_posix(),source_sha256=sha256(dest),preview_glb=preview,
                    transform=placement(motion['root_positions'][0],label))
                hashes[label]=dict(original_motion=str(native),original_motion_sha256=sha256(native),original_glb=str(glb),original_glb_sha256=sha256(glb),prompt=actor['prompt'])
                manifest['assets'][preview]=dict(sha256=sha256(output/preview))
            if hashes['A']['original_motion_sha256']==hashes['B']['original_motion_sha256']:
                raise ValueError('Actors must have independent motion payloads')
            hand=palms[setup['hand']]
            scene=dict(schema_version=1,id=identifier,fps=30,frame_count=case['duration_s']*30,actors=actors,objects={},contacts=[
                dict(id='palm-to-palm',actor='A',effector=hand,target=dict(space='actor',actor='B',**hand),
                     start_frame=setup['start'],end_frame=setup['end'],tolerance_m=.03)])
            folder=output/identifier;folder.mkdir();save(folder/'scene.json',dict(scene=scene))
            manifest['scenes'].append(dict(id=identifier,label=identifier,variants={'palm':identifier+'/scene.json'}))
            entries.append(dict(id=identifier,case=case['id'],seed=seed,sources=hashes,scene=identifier+'/scene.json',scene_sha256=sha256(folder/'scene.json')))
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
    save(output/'manifest.json',manifest)
    spec=dict(created_at=now(),source_protocol_sha256=frozen['protocol_sha256'],scenes=entries,planned_pairs=10,planned_actors=20,
        point_tolerance_m=.03,normal_diagnostic_degrees=15,penetration_diagnostic_m=.005,timing_tolerance_frames=2,
        skin_sha256=sha256(ASSET),implementation={n:sha256(ROOT/'scripts'/n) for n in SOURCES},
        authored_context='Initial root XZ at (0,-0.55)/(0,+0.55), yaw0/180, original rootY. Flat floorY0. Handshake contact frames60..119; high-five frame75. No per-seed placement/timing optimization.',
        scope='Development test of independently prompted actors in additional explicit context; source generation had no such scene constraints. Failure may reflect missing conditioning, choreography or model error. No post-hoc source baseline relabeling or release approval.')
    save(output/'protocol.json',spec);save(output/'freeze.json',dict(protocol_sha256=sha256(output/'protocol.json'),manifest_sha256=sha256(output/'manifest.json')))
    save(output/'results.json',dict(rows=[dict(id=e['id'],status='pending') for e in entries],quality_approved=False))
    save(output/'pipeline.json',dict(status='prepared'))
    return spec


def point_metrics(a,b,normal_a,normal_b,start,end,tolerance=.03):
    distance=np.linalg.norm(a-b,axis=1)
    normal=np.degrees(np.arccos(np.clip(-np.sum(normal_a*normal_b,axis=1),-1,1)))
    close=np.flatnonzero(distance<=tolerance)
    offsets=np.maximum(start-close,0)+np.maximum(close-end,0)
    return dict(palm_gap_m=distance.tolist(),opposing_normal_error_degrees=normal.tolist(),
        requested_gap_max_m=float(distance[start:end+1].max()),requested_gap_mean_m=float(distance[start:end+1].mean()),
        requested_frames_within_point_tolerance=int(np.sum(distance[start:end+1]<=tolerance)),
        requested_frame_count=end-start+1,requested_normal_error_max_degrees=float(normal[start:end+1].max()),
        closest_frame=int(distance.argmin()),closest_gap_m=float(distance.min()),
        nearest_within_tolerance_timing_error_frames=int(offsets.min()) if len(close) else None,
        interpretation='Timing is null if palms never meet point tolerance; a closest miss is not a contact. Opposing normals do not verify grip, fingers or hand tangents.')


def validate(output):
    spec=read(output/'protocol.json');freeze=read(output/'freeze.json')
    if sha256(output/'protocol.json')!=freeze['protocol_sha256'] or sha256(output/'manifest.json')!=freeze['manifest_sha256']:raise ValueError('Frozen protocol/manifest changed')
    if sha256(ASSET)!=spec['skin_sha256']:raise ValueError('Skin changed')
    for name,digest in spec['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed: '+name)
    for entry in spec['scenes']:
        if sha256(output/entry['scene'])!=entry['scene_sha256']:raise ValueError('Scene changed')
    return spec


def run(output):
    from scene_constraints import transform_motion,effector_track
    from palm_contacts import surface_normal_track
    from floor_contact import Surface
    from audit_partner_surface import audit
    from run_godot_scene_import import run as engine
    from threadpoolctl import threadpool_limits
    output=Path(output).resolve();spec=validate(output)
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Already started; preserve attempts and inspect actual process')
    owner=psutil.Process();save(output/'runner.json',dict(pid=owner.pid,created_at=owner.create_time(),status='running',started_at=now()))
    skin=dict(np.load(ASSET,allow_pickle=False));surface=Surface(skin);data=read(output/'results.json');manifest=read(output/'manifest.json')
    try:
        with threadpool_limits(limits=1):
            for entry in spec['scenes']:
                validate(output);row=next(r for r in data['rows'] if r['id']==entry['id']);row.update(status='running')
                save(output/'results.json',data);save(output/'pipeline.json',dict(status='auditing',scene=entry['id']))
                folder=output/entry['id'];scene=read(output/entry['scene'])['scene'];actors={}
                try:
                    for name,actor in scene['actors'].items():
                        if sha256(ROOT/actor['motion'])!=actor['source_sha256'] or sha256(output/actor['preview_glb'])!=manifest['assets'][actor['preview_glb']]['sha256']:raise ValueError('Actor artifact changed')
                        actors[name]=transform_motion(dict(np.load(ROOT/actor['motion'],allow_pickle=False)),actor['transform'])
                    contact=scene['contacts'][0];effector=contact['effector'];vertex=effector['surface_vertex']
                    positions=[effector_track(actors[n],effector,skin) for n in ['A','B']]
                    normals=[surface_normal_track(actors[n],skin,vertex) for n in ['A','B']]
                    points=point_metrics(*positions,*normals,contact['start_frame'],contact['end_frame'],spec['point_tolerance_m'])
                    save(folder/'point-audit.json',points)
                    floor={n:max(max(0.,-float(surface.vertices(r,p)[:,1].min())) for r,p in zip(a['rotations'],a['positions'])) for n,a in actors.items()}
                    save(folder/'floor-audit.json',dict(max_depth_m=floor,plane_y_m=0,scope='Full skin at integer frames, not continuous or self-collision proof.'))
                    collision=audit(scene,skin,tolerance_m=spec['penetration_diagnostic_m'],progress=lambda p:save(folder/'pipeline.json',dict(status='partner_surface',**p)))
                    save(folder/'partner-surface-audit.json',collision)
                    group=output/'engine-groups'/entry['id'];group.mkdir(parents=True)
                    # The engine importer resolves previews relative to its source.
                    placed=read(output/entry['scene'])
                    for a in placed['scene']['actors'].values():a['preview_glb']=str((output/a['preview_glb']).resolve())
                    save(group/'scene.json',placed)
                    save(group/'manifest.json',dict(scenes=[dict(variants={'palm':'scene.json'})],assets={str((output/a['preview_glb']).resolve()):manifest['assets'][a['preview_glb']] for a in scene['actors'].values()}))
                    engine(group,group/'audit')
                    row.update(status='complete',point_metrics=points,floor_depth_m=floor,
                        partner_depth_max_m=collision['pairs'][0]['max_depth_m'],partner_frames_over_tolerance=collision['pairs'][0]['frames_over_tolerance'],
                        engine=read(group/'audit/verification.json'),human_review=None,quality_approved=False)
                except Exception as exc:row.update(status='failed',error=str(exc),traceback=traceback.format_exc())
                save(output/'results.json',data);print(entry['id']+' '+row['status'],flush=True)
        save(output/'pipeline.json',dict(status='complete' if all(r['status']=='complete' for r in data['rows']) else 'complete_with_failures',finished_at=now(),quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()));raise
    finally:save(output/'runner.json',dict(pid=owner.pid,created_at=owner.create_time(),status='stopped',finished_at=now()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--breadth',type=Path,default=ROOT/'reports/breadth-baseline-v2');a=p.parse_args()
    if a.command=='prepare':print(prepare(a.breadth,a.output)['planned_pairs'])
    else:run(a.output)
