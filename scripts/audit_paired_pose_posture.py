"""Full-population decoded geometry audit, with exact-hash reuse of raw evidence."""
import argparse
import os
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from audit_paired_guides import await_owner
from convex_partner_surface import penetration
from verify_palm_region import measure
from rig_asset import RigAsset,array
from rig_clip_import import AnimationSampler


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier audit')
    source_request=read(study/'request.json');source_hash=sha256(study/'request.json');output.mkdir();(output/'implementation').mkdir()
    names=['audit_paired_pose_posture.py','convex_partner_surface.py','verify_palm_region.py','rig_asset.py','rig_clip_import.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    frames=sorted(set(range(150))|{60+i*.5 for i in range(61)})
    save(output/'request.json',dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),source=str(study),source_request_sha256=source_hash,
        frames=frames,expected_scenes=15,implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='All five seeds and three variants, actual decoded skin geometry. Reuse raw geometry only after exact asset, transform, frame-population and proof-hash checks. Body corrections may change arbitrary frames; no continuous collision, self-collision, anatomy, semantic or animator certification.'))
    try:
        save(output/'pipeline.json',dict(status='waiting_for_exact_owner',quality_approved=False));await_owner(source_request,'pid','created',study,{'complete_pending_geometry'})
        if sha256(study/'request.json')!=source_hash:raise ValueError('Source request changed')
        for name,digest in source_request['implementation'].items():
            if sha256(study/'implementation'/name)!=digest:raise ValueError('Source implementation changed')
        manifest=read(study/'manifest.json');engine=read(study/'engine-audit/verification.json')['checks']
        expected={f'{mode}-seed-{seed}' for mode in ['raw','body_fit','body_fit_posture'] for seed in source_request['seeds']}
        if len(manifest['scenes'])!=15 or {s['id'] for s in manifest['scenes']}!=expected:raise ValueError('Incomplete scene population')
        if len(engine)!=30 or {(e['scene_id'],e['actor']) for e in engine}!={(s,a) for s in expected for a in ['A','B']} or any(e['frames']!=150 for e in engine):raise ValueError('Incomplete engine population')
        for relative,entry in manifest['assets'].items():
            if sha256(study/relative)!=entry['sha256']:raise ValueError('Changed source asset')
        prior=ROOT/'reports/paired-guide-audit-v1';priorproof=read(prior/'completion.json')
        if sha256(prior/'results.json')!=priorproof['results_sha256'] or sha256(prior/'manifest.json')!=priorproof['manifest_sha256']:raise ValueError('Changed prior audit')
        priorrows={r['id']:r for r in read(prior/'results.json')['rows']};priormanifest=read(prior/'manifest.json')
        patches=read(prior/'palm-region.json');save(output/'palm-region.json',patches);rows=[]
        with threadpool_limits(limits=1):
            for item in manifest['scenes']:
                scene=read(study/item['variants']['palm'])['scene'];folder=output/item['id'];folder.mkdir();actors=[];source_files={}
                for actor in ['A','B']:
                    entry=scene['actors'][actor];path=study/entry['preview_glb'];motion=ROOT/entry['motion']
                    if sha256(motion)!=entry['source_sha256']:raise ValueError('Changed source motion')
                    check=next(e for e in engine if e['scene_id']==scene['id'] and e['actor']==actor)
                    if check['source_sha256']!=sha256(motion) or check['glb_sha256']!=sha256(path):raise ValueError('Engine sources differ')
                    rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0);r=Rotation.from_quat(entry['transform']['rotation_xyzw']).as_matrix();shift=np.asarray(entry['transform']['translation_m'])
                    actors.append((rig,sampler,r,shift));source_files[actor]=dict(motion_sha256=sha256(motion),glb_sha256=sha256(path))
                primitive=actors[0][0].document['meshes'][0]['primitives'][0];faces=array(actors[0][0].document,actors[0][0].binary,primitive['indices']).reshape(-1,3)
                vertex=scene['contacts'][0]['effector']['surface_vertex'];reused=None
                if item['id'].startswith('raw-'):
                    identifier=item['id'].replace('raw-','body-');oldscene=read(prior/identifier/'scene.json')['scene'];oldrow=priorrows[identifier]
                    for actor in ['A','B']:
                        old=oldscene['actors'][actor]
                        if old['transform']!=scene['actors'][actor]['transform'] or priormanifest['assets'][old['preview_glb']]['sha256']!=source_files[actor]['glb_sha256']:raise ValueError('Raw geometry reuse mismatch')
                    samplepath=prior/identifier/'samples.json'
                    if sha256(samplepath)!=oldrow['samples_sha256']:raise ValueError('Changed raw samples')
                    samples=read(samplepath)['rows'];reused=dict(source=str(samplepath),sha256=sha256(samplepath))
                    if [s['frame'] for s in samples]!=frames:raise ValueError('Incomplete raw frame population')
                else:
                    samples=[]
                    # Event preflight is retained early; final rows are chronological.
                    for f in [75]+[f for f in frames if f!=75]:
                        points=[rig.vertices(sampler.sample(float(np.float32(f/30))))@r.T+shift for rig,sampler,r,shift in actors]
                        collision=[penetration(points[a],points[b],faces) for a,b in [(0,1),(1,0)]]
                        row=dict(frame=f,gap_m=float(np.linalg.norm(points[0][vertex]-points[1][vertex])),floor_depth_m=[max(0.,-float(p[:,1].min())) for p in points],collision=collision)
                        if f==75:
                            row['region']=measure(points,[patches['A'],patches['B']],faces,.003);save(folder/'event-preflight.json',dict(event=row,quality_approved=False))
                        samples.append(row);samples.sort(key=lambda s:s['frame']);save(folder/'samples.json',dict(rows=samples,quality_approved=False))
                        save(output/'pipeline.json',dict(status='auditing',scene=item['id'],completed_samples=len(samples),total_samples=len(frames),quality_approved=False))
                save(folder/'samples.json',dict(rows=samples,quality_approved=False));event=next(s for s in samples if s['frame']==75)
                region=all(d['within_tolerance_count']>=3 and min(d['source_area_witness']['area_m2'],d['target_area_witness']['area_m2'])>=2.5e-5 for d in event['region']['directions'])
                summary=dict(id=item['id'],source_files=source_files,reused=reused,event=event,region_pass=region,max_depth_m=max(c['max_depth_m'] for s in samples for c in s['collision']),
                    floor_max_depth_m=max(max(s['floor_depth_m']) for s in samples),samples_sha256=sha256(folder/'samples.json'),quality_approved=False)
                rows.append(summary);save(output/'results.json',dict(rows=rows,quality_approved=False));print(item['id'],summary['max_depth_m'],event['gap_m'],region,flush=True)
        save(output/'completion.json',dict(at=now(),scenes=len(rows),samples_per_scene=len(frames),engine_actor_frames=4500,results_sha256=sha256(output/'results.json'),
            source_manifest_sha256=sha256(study/'manifest.json'),source_engine_sha256=sha256(study/'engine-audit/verification.json'),quality_approved=False))
        save(output/'pipeline.json',dict(status='complete',quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
