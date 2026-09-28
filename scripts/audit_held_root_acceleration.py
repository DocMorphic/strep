"""Attribute held-root acceleration failures before a root-aware experiment."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(output):
    if output.exists(): raise ValueError('Preserve existing diagnostic')
    eligibility = ROOT/'reports/release-method-eligibility-v1.json'; report = read(eligibility); rows=[]
    bindings={str(eligibility):sha256(eligibility)}
    for case in report['rows']:
        for path,digest in case['inputs'].items():
            if sha256(ROOT/path)!=digest: raise ValueError('Eligibility source changed')
        held=ROOT/'reports/support-release-hold-v1/takes'/case['case']; prior=ROOT/'reports/whole-support-breadth-v1/takes'/case['case']
        spec=read(held/'spec.json'); tracks={}; stats={}
        for name,path in [('raw',held/'input/character.glb'),('prior',prior/'candidate/character.glb'),('held',held/'candidate/character.glb')]:
            bindings[str(path)]=sha256(path); rig=RigAsset.load(path); sampler=AnimationSampler(rig.document,rig.binary,0)
            track=np.array([sampler.sample(float(np.float32(f/spec['fps'])))[spec['root_node'],:3,3] for f in range(spec['frames'])])
            acceleration=np.diff(track,n=2,axis=0)*spec['fps']**2; magnitude=np.linalg.norm(acceleration,axis=1)
            tracks[name]=dict(position=track,acceleration=acceleration,magnitude=magnitude)
            stats[name]=dict(max_m_s2=float(magnitude.max()),peak_center_frame=int(magnitude.argmax()+1))
        limit=max(stats[v]['max_m_s2'] for v in ['raw','prior'])+1e-5
        bad=np.flatnonzero(tracks['held']['magnitude']>limit);peak=int(tracks['held']['magnitude'].argmax());points=[]
        for index in sorted(set(bad.tolist()+[peak])):
            vectors={v:tracks[v]['acceleration'][index].tolist() for v in tracks}
            correction=tracks['held']['acceleration'][index]-tracks['raw']['acceleration'][index]
            points.append(dict(center_frame=index+1,vectors_m_s2=vectors,held_correction_vector_m_s2=correction.tolist(),
                held_correction_norm_m_s2=float(np.linalg.norm(correction)),held_norm_m_s2=float(tracks['held']['magnitude'][index]),
                original_global_limit_m_s2=limit))
        rows.append(dict(case=case['case'],frames=spec['frames'],fps=spec['fps'],statistics=stats,original_global_limit_m_s2=limit,
            failing_centers=(bad+1).tolist(),failing_center_count=len(bad),samples=points,
            maximum_root_displacement_from_raw_m=float(np.linalg.norm(tracks['held']['position']-tracks['raw']['position'],axis=1).max())))
    for path,digest in bindings.items():
        if sha256(path)!=digest: raise ValueError('Input changed during diagnostic')
    save(output,dict(at=now(),implementation_sha256=sha256(__file__),files=bindings,rows=rows,quality_approved=False,
        scope='Fresh decoded raw/prior/held root acceleration vectors for all four eligible-screen cases. Correction-vector attribution is algebraic, not a physical cause claim. No fitting, acceptance change or contact guarantee.'))
    print([dict(case=r['case'],statistics=r['statistics'],failing_centers=r['failing_centers']) for r in rows])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output.resolve())
