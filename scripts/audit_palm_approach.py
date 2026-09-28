"""Independent decoded contact/penetration samples around a partner event.

Reports every requested sample, including failures. Half-frame samples improve
coverage but do not certify continuous collision avoidance or physical contact.
"""
import argparse
import os
from pathlib import Path
import shutil
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset,array
from rig_clip_import import AnimationSampler
from bounded_partner_surface import penetration
from verify_palm_region import measure


def sample_frames(count,event,radius,substeps):
    if any(type(v)is not int for v in [count,event,radius,substeps]):raise ValueError('Integer sample settings required')
    if count<1 or not 0<=event<count or radius<1 or substeps not in (1,2,4):raise ValueError('Invalid sample settings')
    start=max(0,event-radius);end=min(count-1,event+radius)
    return np.arange(start*substeps,end*substeps+1,dtype=float)/substeps


def run(export,study,output,radius=15,substeps=2):
    export,study,output=[Path(p).resolve() for p in [export,study,output]]
    if output.exists():raise ValueError('Preserve earlier approach audit')
    if read(export/'pipeline.json')['status']!='complete' or read(study/'pipeline.json')['status']!='complete':raise ValueError('Require completed exported experiment')
    recipe=read(study/'request.json');patches=read(study/'palm-region.json');manifest=read(export/'manifest.json')
    event=read(export/'request.json')['event_frame'];actors={};scenes={};fingerprints={};faces=None
    for variant in ['input','candidate']:
        scene=read(export/(variant+'-scene.json'))['scene'];scenes[variant]=scene;actors[variant]=[]
        for name in ['A','B']:
            entry=scene['actors'][name];path=export/entry['preview_glb'];digest=sha256(path)
            if digest!=manifest['assets'][entry['preview_glb']]['sha256']:raise ValueError('Export changed')
            fingerprints[variant+'/'+name]=digest
            rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
            primitive=rig.document['meshes'][0]['primitives'][0]
            indices=array(rig.document,rig.binary,primitive['indices']).reshape(-1,3)
            if faces is not None and not np.array_equal(faces,indices):raise ValueError('Native paired skin topology differs')
            faces=indices
            actors[variant].append((rig,sampler,Rotation.from_quat(entry['transform']['rotation_xyzw']).as_matrix(),np.array(entry['transform']['translation_m'])))
    if scenes['input']['frame_count']!=scenes['candidate']['frame_count']:raise ValueError('Scene clocks differ')
    frames=sample_frames(scenes['input']['frame_count'],event,radius,substeps)
    output.mkdir();(output/'implementation').mkdir()
    names=['audit_palm_approach.py','verify_palm_region.py','bounded_partner_surface.py','rig_asset.py','rig_clip_import.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),export=str(export),study=str(study),export_manifest_sha256=sha256(export/'manifest.json'),
        study_request_sha256=sha256(study/'request.json'),patch_sha256=sha256(study/'palm-region.json'),glb_sha256=fingerprints,
        event_frame=event,frames=frames.tolist(),radius=radius,substeps=substeps,screen=recipe['screen'],
        implementation={n:sha256(output/'implementation'/n) for n in names},pid=os.getpid(),created=psutil.Process().create_time(),quality_approved=False)
    save(output/'request.json',request);rows=[];screen=recipe['screen']
    with threadpool_limits(limits=1):
        for f in frames:
            row=dict(frame=float(f),time_s=float(f/30),variants={})
            for variant in ['input','candidate']:
                points=[rig.vertices(sampler.sample(float(np.float32(f/30))))@r.T+t for rig,sampler,r,t in actors[variant]]
                region=measure(points,[patches['A'],patches['B']],faces,screen['max_contact_distance_m'])
                collision=[penetration(points[a],points[b],faces,screen['max_event_penetration_m']) for a,b in [(0,1),(1,0)]]
                row['variants'][variant]=dict(region=region,collision=collision,max_depth_m=max(c['max_depth_m'] for c in collision),
                    proximity_screen_passed=all(d['within_tolerance_count']>=3 and min(d['source_area_witness']['area_m2'],d['target_area_witness']['area_m2'])>=screen['min_triangle_area_m2'] for d in region['directions']),
                    orientation_screen_passed=region['opposing_normal_degrees']<=screen['opposing_normal_max_degrees'])
            rows.append(row)
            save(output/'samples.json',dict(rows=rows,quality_approved=False))
            save(output/'pipeline.json',dict(status='auditing',completed_samples=len(rows),total_samples=len(frames)))
            print('Frame',f,'input/candidate depth',[row['variants'][v]['max_depth_m'] for v in ['input','candidate']],flush=True)
    result={}
    for variant in ['input','candidate']:
        depths=[r['variants'][variant]['max_depth_m'] for r in rows]
        result[variant]=dict(max_depth_m=max(depths),worst_sample_frame=rows[int(np.argmax(depths))]['frame'],
            samples_over_tolerance=[r['frame'] for r,d in zip(rows,depths) if d>screen['max_event_penetration_m']],
            proximity_and_orientation_frames=[r['frame'] for r in rows if all(r['variants'][variant][k] for k in ['proximity_screen_passed','orientation_screen_passed'])])
    save(output/'summary.json',dict(at=now(),variants=result,request_sha256=sha256(output/'request.json'),samples_sha256=sha256(output/'samples.json'),
        scope='Decoded GLB samples in the declared window only. Vertex penetration in both directions, not edge-only triangle intersections, self-collision, anatomy or continuous collision certification. Proximity is not impact force or pressure. No human or action-quality approval.',quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',finished_at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('export',type=Path);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--radius',type=int,default=15);p.add_argument('--substeps',type=int,choices=[1,2,4],default=2)
    a=p.parse_args();run(a.export,a.study,a.output,a.radius,a.substeps)
