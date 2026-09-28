"""Test a smooth local pose edit on full clips; retain contact/interpolation failures."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits

from inspect_kneel_phases import summarize_trace
from pose_edit_window import blend
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from rig_loop import encode
from strep import ROOT,now,read,save,sha256


def posture(world,mapping):
    p=world[:,:,:3,3];knees=[];angles=[]
    for side in ['Left','Right']:
        hip,knee,ankle=[p[:,mapping[side+part]] for part in ['Leg','Shin','Foot']]
        a,b=hip-knee,ankle-knee
        angle=180-np.degrees(np.arccos(np.clip(np.sum(a*b,axis=1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)),-1,1)))
        knees.append(knee[:,1]);angles.append(angle)
    return summarize_trace(p[:,mapping['Hips'],1],np.stack(knees,axis=1),np.stack(angles,axis=1),30.)


def run(output):
    if output.exists():raise ValueError('Preserve earlier window probes')
    soft=ROOT/'reports/knee-patch-feasibility-v1';hard=ROOT/'reports/knee-patch-constrained-v1'
    verification=ROOT/'reports/knee-patch-comparison-v1/verification.json'
    v=read(verification)
    for path,digest in v['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Verified source changed')
    cases=read(hard/'results.json')['rows'];output.mkdir(parents=True)
    names=['probe_knee_contact_windows.py','pose_edit_window.py','rig_asset.py','rig_clip_import.py','rig_transition.py','rig_loop.py','inspect_kneel_phases.py']
    snapshots=output/'implementation';snapshots.mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,snapshots/name)
    save(output/'protocol.json',dict(at=now(),reference_verification_sha256=sha256(verification),cases=[c['id'] for c in cases],radius_frames=15,
        implementation={f'scripts/{n}':sha256(ROOT/'scripts'/n) for n in names},sampling='All180keys andquarterframes;717surface samples perclip',
        contact_contract='Original static guide is required only at its source frame. Surrounding fixed-patch drift is measured, not claimed constrained or confirmed support.',
        scope='Full180frame body-clearance input; additive local rotation/root edit from solved static pose with quintic envelope and two unchanged outer samples. No clipping to force a pass. Diagnostic bridge before temporal optimization; preserve every failure.',quality_approved=False))
    save(output/'pipeline.json',dict(status='processing',at=now()));rows=[];manifest=[]
    with threadpool_limits(limits=1):
        for case in cases:
            dest=output/case['id'];dest.mkdir()
            body=ROOT/'reports/kneel-body-clearance-v1/takes'/case['id']/'soma.glb'
            if sha256(body)!=case['body_glb_sha256'] or sha256(hard/case['id']/'candidate.glb')!=case['candidate_sha256']:
                raise ValueError('Body or target pose changed')
            spec=read(soft/case['id']/'spec.json');rig=RigAsset.load(body);sampler=AnimationSampler(rig.document,rig.binary,0)
            world=np.array([sampler.sample(f/30) for f in range(180)])
            limb=RigAsset.load(case['source_glb']);ls=AnimationSampler(limb.document,limb.binary,0)
            limb_world=np.array([ls.sample(f/30) for f in range(180)])
            target_rig=RigAsset.load(hard/case['id']/'candidate.glb')
            target=AnimationSampler(target_rig.document,target_rig.binary,0).sample(0.)
            editable=[e['node'] for e in spec['edit_joints'].values()];root=spec['root_node'];frame=case['source_frame']
            after,weights=blend(world,rig.parents,root,editable,frame,target,radius=15)
            np.testing.assert_array_equal(after[weights==0],world[weights==0])
            animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(editable)
            _,roundtrip=encode(rig,after,animated,root,dest/'candidate.glb','Experimental local knee-contact edit')
            encoded=RigAsset.load(dest/'candidate.glb');es=AnimationSampler(encoded.document,encoded.binary,0)
            decoded=np.array([es.sample(f/30) for f in range(180)])
            before_local=localize(limb_world,rig.parents);after_local=localize(decoded,rig.parents)
            shifts=decoded[:,root,:3,3]-limb_world[:,root,:3,3]
            edits={};steps={}
            for role,e in spec['edit_joints'].items():
                n=e['node'];delta=before_local[:,n,:3,:3].transpose(0,2,1)@after_local[:,n,:3,:3]
                edits[role]=float(np.degrees(Rotation.from_matrix(delta).magnitude()).max())
                steps[role]=float(np.degrees(Rotation.from_matrix(delta[:-1].transpose(0,2,1)@delta[1:]).magnitude()).max())
            temporal=dict(root_horizontal_edit_m=float(np.linalg.norm(shifts[:,[0,2]],axis=1).max()),root_vertical_edit_m=float(abs(shifts[:,1]).max()),
                root_edit_step_m=float(np.linalg.norm(np.diff(shifts,axis=0),axis=1).max()),joint_edits_degrees=edits,joint_edit_steps_degrees=steps)
            bounds=bool(temporal['root_horizontal_edit_m']<=spec['limits']['root_horizontal_m']+1e-6 and temporal['root_vertical_edit_m']<=spec['limits']['root_vertical_m']+1e-6
                and all(x<=spec['edit_joints'][n]['limit_degrees']+1e-4 for n,x in edits.items()))
            step_ok=bool(temporal['root_edit_step_m']<=spec['limits']['root_step_m']+1e-6 and max(steps.values())<=spec['limits']['joint_step_degrees']+1e-4)
            floor=[];curves={n:dict(before=[],after=[]) for n in spec['patches']};target_errors={}
            for f in np.arange(0,179.001,.25):
                p=encoded.vertices(es.sample(float(f/30)));b=rig.vertices(sampler.sample(float(f/30)))
                floor.append(dict(frame=float(f),before_m=max(0.,-float(b[:,1].min())),after_m=max(0.,-float(p[:,1].min()))))
                if frame-15<=f<=frame+15:
                    for name,patch in spec['patches'].items():
                        curves[name]['before'].append(b[patch['vertices']].mean(0).tolist());curves[name]['after'].append(p[patch['vertices']].mean(0).tolist())
                if f==frame:
                    target_errors={c['patch']:float(np.linalg.norm(p[spec['patches'][c['patch']]['vertices']].mean(0)-c['target_position_m'])) for c in spec['contacts']}
            stats={}
            for name,curve in curves.items():
                before,changed=np.asarray(curve['before']),np.asarray(curve['after'])
                stats[name]=dict(before_peak_speed_m_s=float(np.linalg.norm(np.diff(before,axis=0),axis=1).max()*120),
                    after_peak_speed_m_s=float(np.linalg.norm(np.diff(changed,axis=0),axis=1).max()*120),
                    added_peak_speed_m_s=float(np.linalg.norm(np.diff(changed-before,axis=0),axis=1).max()*120))
            mapping={rig.document['nodes'][n]['name']:n for n in rig.joints}
            row=dict(id=case['id'],source_frame=frame,body_sha256=sha256(body),target_sha256=case['candidate_sha256'],
                candidate_sha256=sha256(dest/'candidate.glb'),floor_max_m=max(r['after_m'] for r in floor),floor_failed_samples=sum(r['after_m']>spec['screen']['floor_depth_m'] for r in floor),
                center_contact_errors_m=target_errors,center_contact_passed=max(target_errors.values())<=spec['screen']['contact_error_m'],
                pose_bounds_passed=bounds,temporal_edit_bounds_passed=step_ok,temporal=temporal,patch_window_speeds=stats,
                before_posture=posture(world,mapping),after_posture=posture(decoded,mapping),
                unchanged_outer_frames_before_export=True,decoded_outer_matrix_error=float(np.max(abs(decoded[weights==0]-world[weights==0]))),
                roundtrip=roundtrip,quality_approved=False,human_review=None)
            save(dest/'floor.json',dict(samples=floor));save(dest/'patch-tracks.json',dict(start_frame=frame-15,fps=120,curves=curves))
            np.savez_compressed(dest/'poses.npz',body=world,limb=limb_world,after=decoded,weights=weights)
            row['detail_hashes']={n:sha256(dest/n) for n in ['floor.json','patch-tracks.json','poses.npz']}
            rows.append(row);save(dest/'result.json',row);save(output/'results.json',dict(rows=rows))
            manifest.append(dict(id=case['id'],path=str((dest/'candidate.glb').resolve()),sha256=row['candidate_sha256'],fps=30,frames=180,sample_by_time=True))
            save(output/'pipeline.json',dict(status='processing',completed=len(rows),at=now()))
            print(case['id'],dict(floor_mm=row['floor_max_m']*1000,contact=row['center_contact_passed'],steps=step_ok),flush=True)
    save(output/'manifest.json',dict(cases=manifest));save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();run(a.output.resolve())
