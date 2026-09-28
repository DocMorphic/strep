"""Locate residual foot speed against the solver's actual support weights.

Read-only diagnostic of completed candidates. Original predicted contacts and
height-gated/faded optimization intervals are deliberately distinguished.
"""
import argparse
from pathlib import Path
import hashlib
import json
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from study_breadth_contact import validate


def stats(values):
    return dict(count=len(values), speed_p95_m_s=float(np.percentile(values,95)) if len(values) else None,
                speed_max_m_s=float(max(values)) if len(values) else None, over_005_m_s=int(np.sum(values>.05)))


def run(study, output):
    study, output=Path(study).resolve(), Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier diagnostic')
    protocol=validate(study)
    raw=(study/'results.json').read_bytes();results=json.loads(raw)
    rows=[];files={}
    with threadpool_limits(limits=1):
        for case in protocol['cases']:
            result=next(r for r in results['rows'] if r['case']==case['id'] and r['method']=='support')
            if result['status']!='complete':continue
            folder=study/'takes'/result['id'];proof=read(folder/'verification.json')
            if result['verification']!=proof or not proof['bounds_and_preservation_passed']:raise ValueError('Changed candidate proof')
            request,spec=read(folder/'request.json'),read(folder/'spec.json')
            annotations=read(folder/'input/contacts.json');rig=RigAsset.load(folder/'candidate/character.glb')
            for relative,digest in [('input/character.glb',proof['source_sha256']),('candidate/character.glb',proof['candidate_sha256'])]:
                if sha256(folder/relative)!=digest:raise ValueError('Changed candidate or source')
            if (folder/'input/contacts.json').read_bytes()!=(folder/'candidate/contacts.json').read_bytes():raise ValueError('Changed predicted contacts')
            sampler=AnimationSampler(rig.document,rig.binary,0);centroids={side:[] for side in spec['patches']}
            for frame in range(spec['frames']):
                vertices=rig.vertices(sampler.sample(float(np.float32(frame/spec['fps']))))
                for side,patch in spec['patches'].items():
                    centroids[side].append(vertices[patch['vertices']][:,[0,2]].mean(axis=0))
            feet={}
            for side,points in centroids.items():
                speed=np.linalg.norm(np.diff(points,axis=0),axis=1)*spec['fps']
                active=np.zeros(spec['frames'],dtype=bool)
                for interval in annotations['intervals']:
                    if interval['joint'] in [side+'Foot',side+'ToeBase']:
                        active[interval['start_frame']:interval['end_frame_exclusive']]=True
                predicted=active[:-1]&active[1:]
                weights=np.asarray(request['support']['guides'][side]['weights'])
                edge_weight=np.minimum(weights[:-1],weights[1:])
                groups=dict(all_predicted=predicted, full_weight=predicted&(edge_weight>=1-1e-12),
                            faded=predicted&(edge_weight>0)&(edge_weight<1-1e-12), excluded=predicted&(edge_weight==0))
                measured={k:stats(speed[mask]) for k,mask in groups.items()}
                recorded=proof['metrics']['candidate']['feet'][side]['predicted_support_speed_p95_m_s']
                actual=measured['all_predicted']['speed_p95_m_s']
                if (recorded is None)!=(actual is None) or (actual is not None and abs(actual-recorded)>1e-10):raise ValueError('Decoded speed differs from prior proof')
                if sum(measured[k]['count'] for k in ['full_weight','faded','excluded'])!=measured['all_predicted']['count']:raise ValueError('Incomplete support partition')
                feet[side]=dict(groups=measured, high_speed_steps=[dict(start_frame=int(i),end_frame=int(i+1),speed_m_s=float(speed[i]),
                    minimum_solver_weight=float(edge_weight[i])) for i in np.flatnonzero(predicted&(speed>.05))])
            fractions={role:value['max_degrees']/spec['edit_joints'][role]['limit_degrees'] for role,value in proof['joints'].items()}
            rows.append(dict(case=case['id'],rig=case['rig'],feet=feet,joint_budget_used_fraction=fractions,
                root_horizontal_budget_used_fraction=proof['changes']['root_horizontal_max_m']/spec['limits']['root_horizontal_m'],
                root_vertical_budget_used_fraction=proof['changes']['root_vertical_max_m']/spec['limits']['root_vertical_m'],
                root_step_budget_used_fraction=proof['changes']['root_step_max_m']/spec['limits']['root_step_m']))
            for path in [folder/'verification.json',folder/'request.json',folder/'spec.json',folder/'input/contacts.json',folder/'candidate/character.glb']:
                files[str(path)]=sha256(path)
    output.mkdir()
    (output/'results-snapshot.json').write_bytes(raw)
    save(output/'summary.json',dict(at=now(),study=str(study),protocol_sha256=sha256(study/'protocol.json'),
        source_results_sha256=hashlib.sha256(raw).hexdigest(),verifier_sha256=sha256(__file__),files=files,rows=rows,
        complete_support_candidates=len(rows),planned_candidates=len(protocol['cases']),quality_approved=False,
        scope='Captured completed-candidate population; all original predicted-support speeds independently reproduced. Full/faded/excluded refer to actual optimization weights, not confirmed ground truth. Global budget maxima do not prove per-frame feasibility. No new corrected assets or engine claims.'))
    lines=['# Support-weight coverage diagnostic','',f"{len(rows)} of {len(protocol['cases'])} support candidates complete in this snapshot.",'',
           '| Candidate | Foot | Full-weight failures / steps | Faded failures / steps | Excluded failures / steps |',
           '|---|---|---:|---:|---:|']
    for row in rows:
        for side,foot in row['feet'].items():
            values=[f"{foot['groups'][k]['over_005_m_s']} / {foot['groups'][k]['count']}" for k in ['full_weight','faded','excluded']]
            lines.append('| '+ ' | '.join([row['case'],side,*values])+' |')
    lines+=['','A solver penalty on a drafted subset is not a guarantee on every predicted-support interval. Speed remains a proxy: heel/toe rolls, turns, and incorrect source predictions require review. See summary.json for every failing step and edit-budget usage.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(dict(complete_candidates=len(rows),planned_candidates=len(protocol['cases'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
