"""Frozen isolated-pose knee/foot support feasibility on all eight retained clips."""
import argparse
import shutil
import time
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from analytic_patch_contact import AnalyticPatchFitter
from build_soma_preview import ASSET
from floor_contact import Surface
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_contact_authoring import empty_spec
from rig_loop import encode
from strep import ROOT,now,read,save,sha256


def prepare(output):
    if output.exists():raise ValueError('Preserve earlier probe')
    study=ROOT/'reports/kneel-body-clearance-v1'
    audit=ROOT/'reports/kneel-body-clearance-audit-v1'
    completion=read(audit/'completion.json')
    if read(audit/'pipeline.json')['status']!='complete':raise ValueError('Need complete source audit')
    for p,d in completion['inputs'].items():
        if sha256(p)!=d:raise ValueError('Audited source changed')
    if sha256(audit/'results.json')!=completion['results_sha256']:raise ValueError('Audit results changed')
    output.mkdir(parents=True)
    with np.load(ASSET,allow_pickle=False) as z:skin=dict(z)
    surface=Surface(skin)
    dominant=surface.indices[np.arange(len(surface.indices)),surface.weights.argmax(1)]
    regions=dict(surface.regions)
    for side in ['Left','Right']:
        joint=surface.names.index(side+'Shin')
        near=np.linalg.norm(skin['bind_vertices']-skin['bind_rig_transform'][joint,:3,3],axis=1)<.13
        regions[side+'Knee']=np.flatnonzero((dominant==joint)&near)
    regions={n:v for n,v in regions.items() if 'Hand' not in n}
    cases=[]
    with threadpool_limits(limits=1):
        for trial in read(study/'summary.json')['trials']:
            source=study/'takes'/trial['id']
            with np.load(source/'limb/motion.npz',allow_pickle=False) as z:base=dict(z)
            with np.load(source/'motion.npz',allow_pickle=False) as z:body=dict(z)
            original={n:np.array([surface.vertices(r,p,ids) for r,p in zip(base['global_rot_mats'],base['posed_joints'])]) for n,ids in regions.items()}
            corrected={n:np.array([surface.vertices(r,p,ids) for r,p in zip(body['global_rot_mats'],body['posed_joints'])]) for n,ids in regions.items() if 'Knee' in n}
            active={}
            for name,points in original.items():
                h=points[:,:,1].min(1);speed=np.linalg.norm(np.diff(points.mean(1)[:,[0,2]],axis=0),axis=1)*30
                active[name]=(h[:-1]<.025)&(h[1:]<.025)&(speed<.2)
            choices=[]
            for name in corrected:
                for frame in np.flatnonzero(active[name]):
                    y=original[name][frame,:,1];mask=y<y.min()+.01
                    before=max(0,float(y[mask].min()));after=max(0,float(corrected[name][frame,mask,1].min()))
                    choices.append((after-before,int(frame),name))
            if not choices:raise ValueError('No knee support candidate; report separately before changing the population')
            increase,frame,worst_region=max(choices,key=lambda c:(c[0],-c[1],c[2]))
            folder=output/trial['id'];folder.mkdir()
            glb=source/'limb/soma.glb';rig=RigAsset.load(glb)
            world=AnimationSampler(rig.document,rig.binary,0).sample(frame/30)
            points=rig.vertices(world)
            for name,ids in regions.items():np.testing.assert_allclose(points[ids],original[name][frame],atol=2e-6,rtol=0)
            local=world.copy()
            for node,parent in enumerate(rig.parents):
                if parent>=0:local[node]=np.linalg.inv(world[parent])@world[node]
            mapping={rig.document['nodes'][n]['name']:n for n in rig.joints}
            spec=empty_spec(dict(glb_sha256=sha256(glb),fps=30,frames=2,root_node=mapping['Hips'],mapping=mapping))
            spec['provenance']='Development isolated-pose feasibility. Low/slow knee/foot patches are geometric drafts, not confirmed support. Two repeated frames represent one static pose; no temporal claim.'
            for name,ids in regions.items():
                if not active[name][frame]:continue
                y=original[name][frame,:,1];selected=ids[y<y.min()+.01]
                target=points[selected].mean(0);target[1]=.0015
                spec['patches'][name]=dict(vertices=selected.tolist())
                spec['contacts'].append(dict(patch=name,start_frame=0,end_frame_exclusive=2,target_position_m=target.tolist()))
            save(folder/'spec.json',spec)
            body_rig=RigAsset.load(source/'soma.glb')
            body_world=AnimationSampler(body_rig.document,body_rig.binary,0).sample(frame/30)
            np.savez_compressed(folder/'source-pose.npz',world=world,local=local,body_world=body_world)
            cases.append(dict(id=trial['id'],source_frame=frame,selection_gap_increase_m=increase,selection_region=worst_region,
                source_glb=str(glb),source_glb_sha256=sha256(glb),body_glb_sha256=sha256(source/'soma.glb'),
                source_pose_sha256=sha256(folder/'source-pose.npz'),spec_sha256=sha256(folder/'spec.json')))
    implementation={f'scripts/{n}':sha256(ROOT/'scripts'/n) for n in ['probe_knee_patch_support.py','analytic_patch_contact.py','target_rig_contact.py','rig_clearance_fit.py','rig_asset.py','rig_clip_import.py','rig_contact_authoring.py','rig_loop.py']}
    snapshots=output/'implementation';snapshots.mkdir()
    for p in implementation:shutil.copyfile(ROOT/p,snapshots/Path(p).name)
    save(output/'protocol.json',dict(at=now(),cases=cases,implementation=implementation,source_audit_sha256=sha256(audit/'completion.json'),
        skin_sha256=sha256(ASSET),quality_approved=False,
        selection='One maximum knee-gap increase pose per clip among existing low/slow support candidates; all eight cases retained, including the one without a regression flag. Ties prefer earlier frame.',
        hypothesis='Explicit knee and foot patch targets can reduce lost support while satisfying the existing floor and contact screens and pose edit budgets.',
        scope='Pose feasibility only. Same existing weighted objective and hard pose bounds, analytic derivative verified against legacy residual. No adjacent-frame/dynamics, independent contact, balance or action-quality claim.'))
    save(output/'pipeline.json',dict(status='prepared',at=now()))
    print([(c['id'],c['source_frame']) for c in cases])


def measurements(rig,spec,world):
    points=rig.vertices(world)
    patches={}
    for contact in spec['contacts']:
        ids=spec['patches'][contact['patch']]['vertices'];p=points[ids]
        patches[contact['patch']]=dict(centroid_error_m=float(np.linalg.norm(p.mean(0)-contact['target_position_m'])),
            minimum_y_m=float(p[:,1].min()),centroid_m=p.mean(0).tolist())
    return dict(floor_depth_m=max(0.,-float(points[:,1].min())),patches=patches,
                contact_error_max_m=max(p['centroid_error_m'] for p in patches.values()))


def run(output):
    protocol=read(output/'protocol.json')
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Do not overwrite a started probe')
    for p,d in protocol['implementation'].items():
        if sha256(ROOT/p)!=d:raise ValueError('Prepared implementation changed')
    rows=[];manifest=[]
    save(output/'pipeline.json',dict(status='fitting',at=now()))
    with threadpool_limits(limits=1):
        for case in protocol['cases']:
            folder=output/case['id'];spec=read(folder/'spec.json')
            for path,digest in [(folder/'spec.json',case['spec_sha256']),(folder/'source-pose.npz',case['source_pose_sha256']),(case['source_glb'],case['source_glb_sha256'])]:
                if sha256(path)!=digest:raise ValueError('Frozen input changed')
            rig=RigAsset.load(case['source_glb'])
            with np.load(folder/'source-pose.npz',allow_pickle=False) as z:pose=dict(z)
            fit=AnalyticPatchFitter(rig,spec,np.repeat(pose['local'][None],2,axis=0))
            start=time.perf_counter();result=fit.fit_frame(0,np.zeros(len(fit.bounds)))
            world,_=fit.pose(0,result.x)
            before=measurements(rig,spec,pose['world']);after=measurements(rig,spec,world);body=measurements(rig,spec,pose['body_world'])
            passed=bool(result.success and after['floor_depth_m']<=spec['screen']['floor_depth_m'] and after['contact_error_max_m']<=spec['screen']['contact_error_m'] and np.all(np.abs(result.x)<=fit.bounds+1e-10))
            animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fit.nodes)
            _,roundtrip=encode(rig,np.repeat(world[None],2,axis=0),animated,spec['root_node'],folder/'candidate.glb','Isolated support feasibility pose; not an animation')
            np.savez_compressed(folder/'fit.npz',parameters=result.x,world=world,bounds=fit.bounds)
            row=dict(**case,before=before,body_reference=body,after=after,solver_success=bool(result.success),nfev=result.nfev,seconds=time.perf_counter()-start,
                objective_before=float(np.sum(fit.residual_pair(0,np.zeros(len(fit.bounds)),np.zeros(len(fit.bounds)))[0]**2)),objective_after=float(result.fun@result.fun),
                pose_screen_passed=passed,roundtrip=roundtrip,candidate_sha256=sha256(folder/'candidate.glb'),fit_sha256=sha256(folder/'fit.npz'),quality_approved=False)
            save(folder/'result.json',row);rows.append(row)
            manifest.append(dict(id=case['id'],path=str((folder/'candidate.glb').resolve()),sha256=row['candidate_sha256'],fps=30,frames=2,sample_by_time=True))
            save(output/'results.json',dict(rows=rows));save(output/'pipeline.json',dict(status='fitting',completed=len(rows),at=now()))
            print(case['id'],dict(passed=passed,floor_mm=after['floor_depth_m']*1000,contact_mm=after['contact_error_max_m']*1000),flush=True)
    save(output/'manifest.json',dict(cases=manifest))
    save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run']);p.add_argument('output',type=Path);a=p.parse_args()
    (prepare if a.mode=='prepare' else run)(a.output.resolve())
