"""All-population decoded scene audit after exact generation/verification owners exit."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now


def await_owner(record,pid_key,created_key,folder,statuses):
    while True:
        try:
            owner=psutil.Process(record[pid_key])
            if owner.create_time()!=record[created_key]:raise RuntimeError('Owner PID reused; inspect before proceeding')
            live=owner.is_running()
        except psutil.NoSuchProcess:live=False
        if not live:
            if read(folder/'pipeline.json')['status'] not in statuses:raise RuntimeError('Owner ended without required evidence: '+str(folder))
            return
        time.sleep(5)


def run(study,hull_check,output):
    from paired_guide_study import validate
    from convex_partner_surface import penetration
    from rig_asset import RigAsset,array
    from rig_clip_import import AnimationSampler
    from verify_palm_region import measure
    from run_godot_scene_import import run as engine
    study,hull_check,output=[Path(p).resolve() for p in [study,hull_check,output]]
    if output.exists():raise ValueError('Preserve prior audit')
    output.mkdir();(output/'implementation').mkdir()
    names=['audit_paired_guides.py','convex_partner_surface.py','verify_palm_region.py','rig_asset.py','rig_clip_import.py','run_godot_scene_import.py','godot_scene_import_audit.gd']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'runner.json',dict(pid=os.getpid(),created=psutil.Process().create_time(),started_at=now()))
    save(output/'request.json',dict(at=now(),study=str(study),study_protocol_sha256=sha256(study/'protocol.json'),hull_check=str(hull_check),
        frames=sorted(set(range(150))|{60+i*.5 for i in range(61)}),methods=['baseline','hand','body'],planned_pairs=15,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Full clip integer samples plus half-frame samples60..90; every baseline and generated pair, fixed placement. Raw generated fingers retained. No corrections, anatomy/self-collision/continuous-time or semantic quality certificate.'))
    def phase(status,**kwargs):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**kwargs));print(status,kwargs,flush=True)
    try:
        phase('waiting_for_generation');await_owner(read(study/'runner.json'),'pid','created',study,{'generated_pending_scene_audit'})
        phase('waiting_for_hull_verification');await_owner(read(hull_check/'request.json'),'pid','created',hull_check,{'complete'})
        verified=read(hull_check/'verification.json')
        if verified['results_sha256']!=sha256(hull_check/'results.json') or verified['directions']!=244:raise ValueError('Hull validation evidence changed/incomplete')
        protocol=validate(study);trials=read(study/'generation/summary.json')['trials'];takes={(t['request_id'],t['seed']):t for t in trials}
        guide_scene=read(study/'guide-scene.json')['scene'];baseline=read(study/'baseline-population.json')['entries']
        patches_path=ROOT/'reports/paired-palm-region-v5/palm-region.json';patches=read(patches_path)
        save(output/'palm-region.json',patches)
        scene_rows=[];manifest=dict(scenes=[],assets={});(output/'assets').mkdir()
        for entry in baseline:
            scene=copy.deepcopy(guide_scene);scene['id']='baseline-seed-'+str(entry['seed'])
            original=read(ROOT/'reports/breadth-partners-v2'/entry['scene'])['scene']
            if sha256(ROOT/'reports/breadth-partners-v2'/entry['scene'])!=entry['scene_sha256']:raise ValueError('Baseline scene changed')
            for actor in ['A','B']:
                source=entry['sources'][actor]
                scene['actors'][actor]=dict(motion=source['original_motion'],preview_glb=source['original_glb'],source_sha256=source['original_motion_sha256'],glb_sha256=source['original_glb_sha256'],transform=original['actors'][actor]['transform'])
            scene_rows.append(dict(id=scene['id'],method='baseline',seed=entry['seed'],scene=scene))
        for pair in protocol['pairs']:
            scene=copy.deepcopy(guide_scene);scene['id']=pair['id']
            for actor in ['A','B']:
                take=takes[(pair['requests'][actor],pair['seed'])];folder=study/'generation/takes'/take['id']
                scene['actors'][actor].update(motion=str(folder/'motion.npz'),preview_glb=str(folder/'soma.glb'),source_sha256=take['hashes']['motion.npz'],glb_sha256=take['hashes']['soma.glb'])
            scene_rows.append(dict(id=pair['id'],method=pair['method'],seed=pair['seed'],scene=scene))
        for row in scene_rows:
            scene=row['scene']
            for actor,entry in scene['actors'].items():
                for key,extension,digestkey in [('motion','npz','source_sha256'),('preview_glb','glb','glb_sha256')]:
                    source=Path(entry[key]);dest=output/'assets'/f'{row["id"]}-{actor}.{extension}'
                    if sha256(source)!=entry[digestkey]:raise ValueError('Scene source changed')
                    shutil.copyfile(source,dest);entry[key]=dest.relative_to(ROOT).as_posix() if key=='motion' else dest.relative_to(output).as_posix()
                    manifest['assets'][dest.relative_to(output).as_posix()]=dict(sha256=sha256(dest))
                entry.pop('glb_sha256')
            save(output/(row['id']+'/scene.json'),dict(scene=scene))
            manifest['scenes'].append(dict(id=row['id'],label=row['id'],variants={'palm':row['id']+'/scene.json'}))
        save(output/'manifest.json',manifest);shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
        frames=read(output/'request.json')['frames'];results=[]
        save(output/'results.json',dict(rows=[dict(id=r['id'],status='pending') for r in scene_rows],quality_approved=False))
        with threadpool_limits(limits=1):
            for row in scene_rows:
                scene=row['scene'];group=[];faces=None;folder=output/row['id']
                for actor in ['A','B']:
                    entry=scene['actors'][actor];rig=RigAsset.load(output/entry['preview_glb']);sampler=AnimationSampler(rig.document,rig.binary,0)
                    indices=array(rig.document,rig.binary,rig.document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3)
                    if faces is not None and not np.array_equal(indices,faces):raise ValueError('Native topology changed')
                    faces=indices;group.append((rig,sampler,Rotation.from_quat(entry['transform']['rotation_xyzw']).as_matrix(),np.asarray(entry['transform']['translation_m'])))
                vertex=scene['contacts'][0]['effector']['surface_vertex'];adjacent=faces[np.any(faces==vertex,axis=1)];samples=[]
                for f in frames:
                    points=[rig.vertices(sampler.sample(float(np.float32(f/30))))@rot.T+shift for rig,sampler,rot,shift in group]
                    normals=[]
                    for p in points:
                        tri=p[adjacent];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0);length=np.linalg.norm(normal)
                        if length<1e-12:raise ValueError('Degenerate palm normal')
                        normals.append(normal/length)
                    collision=[penetration(points[a],points[b],faces) for a,b in [(0,1),(1,0)]]
                    sample=dict(frame=f,gap_m=float(np.linalg.norm(points[0][vertex]-points[1][vertex])),normal_degrees=float(np.degrees(np.arccos(np.clip(-normals[0]@normals[1],-1,1)))),floor_depth_m=[max(0.,-float(p[:,1].min())) for p in points],collision=collision)
                    if f==75:sample['region']=measure(points,[patches['A'],patches['B']],faces,.003)
                    samples.append(sample);save(folder/'samples.json',dict(rows=samples,quality_approved=False))
                    save(output/'pipeline.json',dict(status='scene_geometry',scene=row['id'],samples=len(samples),total=len(frames),quality_approved=False))
                phase('engine',scene=row['id']);engine_source=folder/'engine-source';engine_source.mkdir()
                placed=copy.deepcopy(scene)
                for entry in placed['actors'].values():entry['preview_glb']=str((output/entry['preview_glb']).resolve())
                save(engine_source/'scene.json',dict(scene=placed));save(engine_source/'manifest.json',dict(scenes=[dict(variants={'palm':'scene.json'})],assets={str((output/entry['preview_glb']).resolve()):manifest['assets'][entry['preview_glb']] for entry in scene['actors'].values()}))
                engine(engine_source,folder/'engine-audit')
                engine_checks=read(folder/'engine-audit/verification.json')['checks']
                if len(engine_checks)!=2 or {c['actor'] for c in engine_checks}!={'A','B'} or any(c['frames']!=150 for c in engine_checks):raise ValueError('Incomplete paired engine population')
                event=next(s for s in samples if s['frame']==75);close=[s['frame'] for s in samples if s['gap_m']<=.03]
                result=dict(id=row['id'],method=row['method'],seed=row['seed'],status='complete',event=event,nearest_point_contact_offset_frames=min(abs(f-75) for f in close) if close else None,
                    max_depth_m=max(c['max_depth_m'] for s in samples for c in s['collision']),floor_max_depth_m=max(max(s['floor_depth_m']) for s in samples),
                    samples_sha256=sha256(folder/'samples.json'),engine_sha256=sha256(folder/'engine-audit/verification.json'),engine_actor_frames=sum(c['frames'] for c in engine_checks),quality_approved=False)
                results.append(result);save(output/'results.json',dict(rows=results+[dict(id=r['id'],status='pending') for r in scene_rows[len(results):]],quality_approved=False));print(row['id'],result['max_depth_m'],event['gap_m'],flush=True)
        save(output/'completion.json',dict(at=now(),pairs=len(results),samples_per_pair=len(frames),engine_actor_frames=sum(r['engine_actor_frames'] for r in results),results_sha256=sha256(output/'results.json'),manifest_sha256=sha256(output/'manifest.json'),hull_verification_sha256=sha256(hull_check/'verification.json'),quality_approved=False))
        phase('complete')
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('hull_check',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.hull_check,a.output)
