"""Independent decoded skin and local edit checks for the isolated knee poses."""
import argparse
import hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from strep import now,read,save,sha256


def run(soft,hard,output):
    if output.exists():raise ValueError('Preserve earlier verification')
    protocol=read(soft/'protocol.json');groups={};rows=[];inputs={}
    for folder in [soft,hard]:
        if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Incomplete probe')
        for name in ['protocol.json','results.json','manifest.json','engine/verification.json']:
            inputs[str(folder/name)]=sha256(folder/name)
    hard_protocol=read(hard/'protocol.json')
    if hard_protocol['source_protocol_sha256']!=sha256(soft/'protocol.json') or hard_protocol['source_results_sha256']!=sha256(soft/'results.json'):
        raise ValueError('Hard comparison source changed')
    for folder in [soft,hard]:
        source_rows=read(folder/'results.json')['rows'];proof=read(folder/'engine/verification.json')['checks']
        if [r['id'] for r in source_rows]!=[c['id'] for c in protocol['cases']]:raise ValueError('Changed population')
        if [(r['id'],r['frames'],r['source_sha256']) for r in proof]!=[(r['id'],2,r['candidate_sha256']) for r in source_rows]:
            raise ValueError('Engine proof differs from static pose exports')
        with threadpool_limits(limits=1):
            for case,result in zip(protocol['cases'],source_rows):
                source=soft/case['id'];spec=read(source/'spec.json')
                for path,digest in [(source/'spec.json',case['spec_sha256']),(source/'source-pose.npz',case['source_pose_sha256']),
                    (folder/case['id']/'candidate.glb',result['candidate_sha256']),(folder/case['id']/'fit.npz',result['fit_sha256'])]:
                    if sha256(path)!=digest:raise ValueError('Source/candidate changed')
                    inputs[str(path)]=digest
                with np.load(source/'source-pose.npz',allow_pickle=False) as z:original=dict(z)
                if folder==soft:groups.setdefault(hashlib.sha256(original['world'].tobytes()).hexdigest(),[]).append(case['id'])
                rig=RigAsset.load(folder/case['id']/'candidate.glb')
                sampler=AnimationSampler(rig.document,rig.binary,0)
                world=sampler.sample(0.);np.testing.assert_allclose(world,sampler.sample(1/30),atol=1e-7,rtol=0)
                local=world.copy()
                for node,parent in enumerate(rig.parents):
                    if parent>=0:local[node]=np.linalg.inv(world[parent])@world[node]
                root=spec['root_node'];shift=world[root,:3,3]-original['world'][root,:3,3]
                horizontal=float(np.linalg.norm(shift[[0,2]]));vertical=float(abs(shift[1]))
                rotations={role:float(np.degrees(Rotation.from_matrix(original['local'][e['node'],:3,:3].T@local[e['node'],:3,:3]).magnitude())) for role,e in spec['edit_joints'].items()}
                allowed={e['node'] for e in spec['edit_joints'].values()}
                untouched=[i for i in range(len(local)) if i not in allowed]
                rotation_unchanged=float(np.max(np.abs(local[untouched,:3,:3]-original['local'][untouched,:3,:3])))
                nonroot=[i for i in range(len(local)) if i!=root]
                offsets_unchanged=float(np.max(np.abs(local[nonroot,:3,3]-original['local'][nonroot,:3,3])))
                bounds_ok=bool(horizontal<=spec['limits']['root_horizontal_m']+1e-6 and vertical<=spec['limits']['root_vertical_m']+1e-6
                    and all(v<=spec['edit_joints'][k]['limit_degrees']+1e-4 for k,v in rotations.items())
                    and max(rotation_unchanged,offsets_unchanged)<1e-6)
                points=rig.vertices(world);floor=max(0.,-float(points[:,1].min()))
                patches={c['patch']:dict(error_m=float(np.linalg.norm(points[spec['patches'][c['patch']]['vertices']].mean(0)-c['target_position_m'])),
                    min_y_m=float(points[spec['patches'][c['patch']]['vertices'],1].min())) for c in spec['contacts']}
                maximum=max(p['error_m'] for p in patches.values())
                passed=bool(bounds_ok and floor<=spec['screen']['floor_depth_m'] and maximum<=spec['screen']['contact_error_m'] and result['solver_success'])
                if passed!=result['pose_screen_passed']:raise ValueError('Independent screen disagrees with solver report')
                rows.append(dict(id=case['id'],method='soft' if folder==soft else 'hard',source_frame=case['source_frame'],floor_depth_m=floor,patches=patches,
                    contact_error_max_m=maximum,root_horizontal_edit_m=horizontal,root_vertical_edit_m=vertical,joint_edits_degrees=rotations,
                    unedited_local_rotation_max_error=rotation_unchanged,nonroot_local_offset_max_error_m=offsets_unchanged,
                    pose_bounds_passed=bounds_ok,pose_screen_passed=passed,quality_approved=False))
    summary=dict(at=now(),inputs=inputs,rows=rows,exact_reference_pose_groups=list(groups.values()),
        soft_passed=sum(r['pose_screen_passed'] for r in rows if r['method']=='soft'),hard_passed=sum(r['pose_screen_passed'] for r in rows if r['method']=='hard'),
        bounds_numerical_tolerance=dict(position_m=1e-6,rotation_degrees=1e-4),floor_and_contact_screens_unrelaxed=True,
        engine_actor_frames=32,quality_approved=False,human_review=None,
        scope='Eight source-clip cases but six exactly distinct reference poses. Each export repeats one pose for two frames. No animation continuity, neighboring-frame feasibility, balance or visual quality approval.')
    output.mkdir(parents=True);save(output/'verification.json',summary)
    lines=['# Knee contact pose feasibility','','| Method | Case | Floor depth (mm) | Patch error (mm) | Existing pose screen |','|---|---|---:|---:|---|']
    for r in rows:lines.append(f"| {r['method']} | {r['id']} @ {r['source_frame']} | {r['floor_depth_m']*1000:.3f} | {r['contact_error_max_m']*1000:.3f} | {r['pose_screen_passed']} |")
    lines+=['',summary['scope'],'','All geometry is decoded from exported files. Existing floor and contact screens remain 5 mm and 20 mm; passing permits residual error. Hard inequalities target a 10 micrometre numerical margin inside those screens.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(dict(soft_passed=summary['soft_passed'],hard_passed=summary['hard_passed'],unique_reference_poses=len(groups)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['soft','hard','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.soft.resolve(),a.hard.resolve(),a.output.resolve())
