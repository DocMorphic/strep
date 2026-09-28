"""Verify and summarize completed release-hold cases without hiding pending ones."""
import argparse
from pathlib import Path
from strep import read, save, sha256, now
from study_support_release import compare
from study_whole_support_breadth import check_engine


def run(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    request, results = read(study/'request.json'), read(study/'results.json')
    if [r['id'] for r in results['rows']] != [c['id'] for c in request['cases']]:
        raise ValueError('Release population differs')
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case, row in zip(request['cases'], results['rows']):
        if row['status'] != 'complete':
            rows.append(dict(id=row['id'], status=row['status']))
            continue
        folder = study/'takes'/case['id']; prior = Path(case['prior'])
        for name, digest in row['files'].items():
            if sha256(folder/name) != digest: raise ValueError('Completed artifact changed: '+name)
        for name, digest in case['inputs'].items():
            if sha256(name) != digest: raise ValueError('Prior input changed: '+name)
        dynamics = read(folder/'release-dynamics.json')
        proof, prior_proof = read(folder/'verification.json'), read(prior/'verification.json')
        recomputed = compare(prior_proof, proof, read(prior/'traces.json'), read(folder/'traces.json'), dynamics)
        if recomputed != row['decision'] or recomputed != read(folder/'comparison.json'):
            raise ValueError('Recorded release screen differs')
        group = study/'engine-groups'/case['id']
        if sha256(group/'audit/verification.json') != row['engine_verification_sha256']:
            raise ValueError('Engine evidence changed')
        frames = check_engine(read(group/'audit/verification.json'), read(group/'manifest.json')['cases'])
        if frames != row['engine_actor_frames']: raise ValueError('Engine population differs')
        regressions = []
        for side in ['Left','Right']:
            tracks = [dynamics[v]['feet'][side]['releases'] for v in ['input','prior','candidate']]
            for raw, previous, candidate in zip(*tracks):
                if candidate['acceleration_max_m_s2'] > max(raw['acceleration_max_m_s2'], previous['acceleration_max_m_s2']) + 1e-5:
                    regressions.append(dict(side=side, release_frame=candidate['release_frame'],
                        raw_acceleration_m_s2=raw['acceleration_max_m_s2'], prior_acceleration_m_s2=previous['acceleration_max_m_s2'],
                        candidate_acceleration_m_s2=candidate['acceleration_max_m_s2']))
        rows.append(dict(id=row['id'],status='complete',decision=recomputed,engine_actor_frames=frames,
            root_acceleration_m_s2=dict(raw=proof['metrics']['input']['root_acceleration_max_m_s2'],
                prior=prior_proof['metrics']['candidate']['root_acceleration_max_m_s2'], candidate=proof['metrics']['candidate']['root_acceleration_max_m_s2']),
            release_regressions=regressions,artifact_hashes=row['files'],engine_verification_sha256=row['engine_verification_sha256']))
    complete = [r for r in rows if r['status']=='complete']
    save(output/'summary.json',dict(at=now(),study=str(study),request_sha256=sha256(study/'request.json'),
        total=len(rows),completed=len(complete),pending=len(rows)-len(complete),
        passing=sum(r['decision']['passes_development_screen'] for r in complete),engine_actor_frames=sum(r['engine_actor_frames'] for r in complete),
        rows=rows,quality_approved=False,scope='Read-only matched ablation summary; incomplete cases retained. '
        'Recomputed frozen numerical screens and verified completed artifacts/engine evidence. No animator or quality approval.'))
    print(dict(total=len(rows),completed=len(complete),passing=sum(r['decision']['passes_development_screen'] for r in complete)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.study,a.output)
