"""Fresh complete-skin queries against an exactly bound retained source population."""
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
from audit_paired_temporal_rates import validate_engine


def run(study,witnesses,engine,output):
    study,witnesses,engine,output=map(lambda x:Path(x).resolve(),[study,witnesses,engine,output])
    if output.exists():raise ValueError('Preserve earlier geometry review')
    request,result=read(study/'request.json'),read(study/'result.json');wr,wp=read(witnesses/'request.json'),read(witnesses/'result.json')
    if result['status']!='complete' or result['request_sha256']!=sha256(study/'request.json') or result['selected'] is None:raise ValueError('Completed selected proposal required')
    if wp['status']!='complete' or wp['request_sha256']!=sha256(witnesses/'request.json'):raise ValueError('Completed bound source population required')
    inputs={**request['inputs']};exports={v:{} for v in ['input','candidate']};manifest=read(study/'manifest.json')
    if len(manifest['cases'])!=4:raise ValueError('Four exact input/candidate clips required')
    for entry in manifest['cases']:
        variant,actor=entry['id'].split('-')
        if variant not in exports or actor not in ['A','B'] or actor in exports[variant]:raise ValueError('Distinct expected actor clips required')
        path=study/entry['path'];exports[variant][actor]=entry;inputs[str(path)]=entry['sha256']
        if variant=='input':
            source=ROOT/'reports/paired-guarded-temporal-v4'/actor/'candidate.glb'
            if entry['sha256']!=wr['inputs'][str(source)]:raise ValueError('Source geometry is for another clip')
    frames=wr['frames'];baseline={}
    for name,digest in wp['artifacts'].items():
        path=witnesses/name;inputs[str(path)]=digest;row=read(path)
        if row['frame'] in baseline:raise ValueError('Duplicate source time')
        baseline[row['frame']]=row
    if sorted(baseline)!=frames:raise ValueError('Incomplete source time population')
    validate_engine(exports,read(engine/'verification.json')['checks'])
    patch=ROOT/'reports/paired-guide-audit-v1/palm-region.json';patches=read(patch)
    old_request=ROOT/'reports/paired-guarded-geometry-v1/geometry/request.json'
    if sha256(patch)!=read(old_request)['palm_region_sha256']:raise ValueError('Contact patch changed')
    for path in [study/'request.json',study/'result.json',study/'manifest.json',witnesses/'request.json',witnesses/'result.json',engine/'verification.json',patch]:inputs[str(path)]=sha256(path)
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Bound input changed')
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['audit_coupled_pair_geometry.py','convex_partner_surface.py','verify_palm_region.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','audit_paired_temporal_rates.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    protocol=dict(at=now(),inputs=inputs,frames=frames,implementation={n:sha256(snapshot/n) for n in methods},quality_approved=False,
        scope='Fresh complete candidate skin queries in both directions. Source queries reused only with exact actor GLB identities, source placements and frame population. Source near-band query includes every penetrating point; candidate conservative hull filtering excludes only nonpenetrating points. No continuous triangle, self-collision, force or naturalness certification.')
    save(output/'request.json',protocol)
    scene=read(ROOT/'reports/paired-pose-posture-v1/body_fit_posture-seed-1301.json')['scene'];actors=[];faces=None
    for actor in ['A','B']:
        rig=RigAsset.load(study/exports['candidate'][actor]['path']);sampler=AnimationSampler(rig.document,rig.binary,0)
        f=array(rig.document,rig.binary,rig.document['meshes'][0]['primitives'][0]['indices']).reshape(-1,3)
        if faces is not None:np.testing.assert_array_equal(faces,f)
        faces=f;placement=scene['actors'][actor]['transform'];actors.append((rig,sampler,Rotation.from_quat(placement['rotation_xyzw']).as_matrix(),np.asarray(placement['translation_m'])))
    rows=[]
    for index,frame in enumerate(frames):
        points=[rig.vertices(sampler.sample(frame/30))@r.T+shift for rig,sampler,r,shift in actors]
        directions=[penetration(points[a],points[b],faces) for a,b in [(0,1),(1,0)]];original=baseline[frame]
        source_depth=max(d['maximum_depth_m'] for d in original['directions']);candidate_depth=max(d['max_depth_m'] for d in directions)
        row=dict(frame=frame,directions=directions,source_depth_m=source_depth,candidate_depth_m=candidate_depth,change_m=candidate_depth-source_depth,
            cap_excess_m=max(0.,candidate_depth-max(.005,source_depth)),floor_depth_m=[max(0.,-float(v[:,1].min())) for v in points],source_floor_depth_m=original['floor_depth_m'],
            directional_changes_m=[d['max_depth_m']-s['maximum_depth_m'] for d,s in zip(directions,original['directions'])])
        if frame==75:row['region']=measure(points,[patches['A'],patches['B']],faces,.003)
        rows.append(row);save(output/'samples.json',dict(rows=rows,quality_approved=False));save(output/'progress.json',dict(status='running',completed=index+1,total=len(frames)))
        if (index+1)%10==0:print(dict(completed=index+1,total=len(frames)),flush=True)
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input changed during review')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Audit method changed')
    summary=dict(at=now(),request_sha256=sha256(output/'request.json'),samples_sha256=sha256(output/'samples.json'),samples=len(rows),fresh_directional_queries=2*len(rows),
        source_peak_m=max(r['source_depth_m'] for r in rows),candidate_peak_m=max(r['candidate_depth_m'] for r in rows),
        source_screen_failures=sum(r['source_depth_m']>.005 for r in rows),candidate_screen_failures=sum(r['candidate_depth_m']>.005 for r in rows),
        depth_increases_over_1e_6=sum(r['change_m']>1e-6 for r in rows),maximum_depth_increase_m=max(r['change_m'] for r in rows),
        cap_failures_over_1e_6=sum(r['cap_excess_m']>1e-6 for r in rows),maximum_cap_excess_m=max(r['cap_excess_m'] for r in rows),
        maximum_floor_increase_m=max(max(r['floor_depth_m'])-max(r['source_floor_depth_m']) for r in rows),event=next(r for r in rows if r['frame']==75),quality_approved=False)
    save(output/'verification.json',summary);save(output/'progress.json',dict(status='complete'));print({k:v for k,v in summary.items() if k!='event'},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','witnesses','engine','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.witnesses,a.engine,a.output)
