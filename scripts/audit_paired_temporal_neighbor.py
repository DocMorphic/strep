"""Decode temporal trials, compare joint rates and query complete partner skin."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset,array
from rig_clip_import import AnimationSampler
from convex_partner_surface import penetration
from verify_palm_region import measure
from audit_scene_joint_rates import compare_rates
from paired_temporal_neighbor import placed_joint_positions


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve();protocol,result=read(study/'protocol.json'),read(study/'result.json')
    if output.exists():raise ValueError('Preserve earlier geometry audit')
    if result['status']!='complete' or result['protocol_sha256']!=sha256(study/'protocol.json'):raise ValueError('Completed unchanged trial required')
    for file,digest in protocol['inputs'].items():
        if sha256(file)!=digest:raise ValueError('Trial input changed')
    for name,digest in protocol['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Trial snapshot changed')
    scene=read(ROOT/protocol['source_scene'])['scene'];patch_path=ROOT/'reports/paired-guide-audit-v1/palm-region.json';patches=read(patch_path)
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['audit_paired_temporal_neighbor.py','convex_partner_surface.py','verify_palm_region.py','audit_scene_joint_rates.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','paired_temporal_neighbor.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    times=np.arange(597)/4;interval=np.arange(protocol['first'],protocol['last']+.001,.25)
    request=dict(at=now(),study=study.relative_to(ROOT).as_posix(),result_sha256=sha256(study/'result.json'),protocol_sha256=sha256(study/'protocol.json'),
        palm_region_sha256=sha256(patch_path),times=interval.tolist(),implementation={n:sha256(snapshot/n) for n in methods},quality_approved=False)
    save(output/'request.json',request);samples={};rates={};preservation={};input_event=None;input_matrices={}
    for variant in protocol['variants']:
        actors=[];positions={};preservation[variant]={}
        for actor in ['A','B']:
            entry=result['exports'][variant][actor];path=study/entry['path']
            if sha256(path)!=entry['sha256']:raise ValueError('Trial export changed')
            rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0);placement=scene['actors'][actor]['transform']
            r=Rotation.from_quat(placement['rotation_xyzw']).as_matrix();shift=np.array(placement['translation_m'])
            matrices=np.array([sampler.sample(t/30) for t in times])
            positions[actor]=placed_joint_positions(matrices,rig.joints,r,shift)
            if variant=='input':input_matrices[actor]=matrices
            else:
                locked=(times<protocol['first'])|(times>protocol['last'])|(times==protocol['event'])
                np.testing.assert_allclose(matrices[locked],input_matrices[actor][locked],atol=1e-12,rtol=0)
                preservation[variant][actor]=dict(locked_sample_count=int(locked.sum()),world_matrix_max_error=float(np.abs(matrices[locked]-input_matrices[actor][locked]).max()),world_matrix_tolerance=1e-12)
            actors.append((rig,sampler,r,shift));names=[rig.document['nodes'][j]['name'] for j in rig.joints]
        if variant=='input':input_positions=positions
        else:
            windows=dict(whole_clip=[0,149],edited_interval=[70,80],event=[73,77],entry_join=[68,72],exit_join=[78,82])
            rates[variant]={actor:compare_rates(input_positions[actor],positions[actor],names,windows) for actor in ['A','B']}
            save(output/(variant+'-rates.json'),rates[variant])
        faces=array(actors[0][0].document,actors[0][0].binary,actors[0][0].document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3)
        partner=actors[1][0]
        np.testing.assert_array_equal(faces,array(partner.document,partner.binary,partner.document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3))
        rows=[]
        for frame in interval:
            points=[rig.vertices(sampler.sample(frame/30))@r.T+shift for rig,sampler,r,shift in actors]
            if frame==protocol['event']:
                if variant=='input':input_event=[v.copy() for v in points]
                else:
                    drift=max(float(np.abs(actual-expected).max()) for actual,expected in zip(points,input_event))
                    for actual,expected in zip(points,input_event):np.testing.assert_allclose(actual,expected,atol=1e-12,rtol=0)
                    preservation[variant]['event_skin_max_error_m']=drift
            collision=[penetration(points[a],points[b],faces) for a,b in [(0,1),(1,0)]]
            row=dict(frame=float(frame),collision=collision,maximum_depth_m=max(c['max_depth_m'] for c in collision),
                floor_depth_m=[max(0.,-float(v[:,1].min())) for v in points],palm_gap_m=float(np.linalg.norm(points[0][14712]-points[1][14712])))
            if frame==protocol['event']:row['region']=measure(points,[patches['A'],patches['B']],faces,.003)
            rows.append(row);save(output/(variant+'-geometry.json'),dict(rows=rows,quality_approved=False))
            save(output/'progress.json',dict(status='running',variant=variant,frame=float(frame),completed=len(rows),total=len(interval)))
            if len(rows)%10==0:print(dict(variant=variant,completed=len(rows),total=len(interval)),flush=True)
        samples[variant]=rows
    comparisons={}
    for variant in protocol['variants'][1:]:
        deltas=[dict(frame=a['frame'],depth_change_m=b['maximum_depth_m']-a['maximum_depth_m'],
                     new_failure=bool(a['maximum_depth_m']<=.005 and b['maximum_depth_m']>.005),
                     floor_change_m=max(b['floor_depth_m'])-max(a['floor_depth_m'])) for a,b in zip(samples['input'],samples[variant])]
        comparisons[variant]=dict(depth_increases_over_1e_6=sum(d['depth_change_m']>1e-6 for d in deltas),new_collision_failures=sum(d['new_failure'] for d in deltas),
            maximum_depth_increase_m=max(d['depth_change_m'] for d in deltas),maximum_floor_increase_m=max(d['floor_change_m'] for d in deltas),rows=deltas)
    for file,digest in protocol['inputs'].items():
        if sha256(file)!=digest:raise ValueError('Input changed during geometry audit')
    for name,digest in request['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Audit method changed')
    summaries={v:dict(maximum_depth_m=max(r['maximum_depth_m'] for r in rows),collision_failures=sum(r['maximum_depth_m']>.005 for r in rows),
        floor_maximum_m=max(max(r['floor_depth_m']) for r in rows),event=next(r for r in rows if r['frame']==75)) for v,rows in samples.items()}
    save(output/'verification.json',dict(at=now(),request_sha256=sha256(output/'request.json'),summaries=summaries,comparisons=comparisons,
        preservation=preservation,artifacts={p.name:sha256(p) for p in output.glob('*-*.json')},quality_approved=False,
        scope=f'Fresh full-skin bilateral vertex queries at all {len(interval)} quarter-frame times in {protocol["first"]}–{protocol["last"]}, all-joint rates on the complete clip, and protected world matrices/event skin within 1e-12 decode tolerance. Exact serialized keys are checked by the generation study. Existing outside collision/floor failures remain. No continuous triangle, self-collision, force, anatomy or human-quality approval.'))
    save(output/'progress.json',dict(status='complete'));print({k:{f:v[f] for f in ['maximum_depth_m','collision_failures','floor_maximum_m']} for k,v in summaries.items()},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.output)
