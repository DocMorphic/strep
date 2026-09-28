"""Read-only root dynamics and convergence evidence for completed support fits."""
import argparse
from pathlib import Path
import numpy as np
from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(study, output):
    study, output = study.resolve(), output.resolve()
    if output.exists(): raise ValueError('Preserve previous diagnostic')
    rows, inputs = [], {}
    for row in read(study/'results.json')['rows']:
        if row['status'] != 'complete': continue
        folder=study/'takes'/row['id']; spec=read(folder/'spec.json')
        if sha256(folder/'verification.json') != row['verification_sha256']:
            raise ValueError('Verification changed')
        verification=read(folder/'verification.json'); fit=read(folder/'fit-summary.json')
        tracks={}
        for variant, digest_key in [('input','source_sha256'),('candidate','candidate_sha256')]:
            path=folder/variant/'character.glb'
            if sha256(path) != verification[digest_key]: raise ValueError('GLB changed')
            rig=RigAsset.load(path); sampler=AnimationSampler(rig.document,rig.binary,0)
            tracks[variant]=np.array([sampler.sample(float(np.float32(f/spec['fps'])))[spec['root_node'],:3,3]
                                      for f in range(spec['frames'])])
        acceleration={key:np.diff(track,n=2,axis=0)*spec['fps']**2 for key,track in tracks.items()}
        peaks={key:int(np.argmax(np.linalg.norm(value,axis=1)))+1 for key,value in acceleration.items()}
        for key, peak in peaks.items():
            if abs(np.linalg.norm(acceleration[key][peak-1])-verification['metrics'][key]['root_acceleration_max_m_s2'])>1e-7:
                raise ValueError('Decoded acceleration differs')
        edit=tracks['candidate']-tracks['input']; edit_acc=np.diff(edit,n=2,axis=0)*spec['fps']**2
        centers=sorted({1,len(edit)-2,*peaks.values()})
        rows.append(dict(case=row['id'],frames=len(edit),fps=spec['fps'],peak_frames=peaks,
            root_acceleration_max_m_s2={k:float(np.linalg.norm(v,axis=1).max()) for k,v in acceleration.items()},
            sampled_centers=[dict(frame=f,raw_acceleration_m_s2=acceleration['input'][f-1].tolist(),
                candidate_acceleration_m_s2=acceleration['candidate'][f-1].tolist(),
                correction_acceleration_m_s2=edit_acc[f-1].tolist(),
                root_edit_neighborhood_m=edit[f-1:f+2].tolist()) for f in centers],
            convergence=fit['convergence'],root_tracks_m={k:v.tolist() for k,v in tracks.items()}))
        for name in ['spec.json','fit-summary.json','verification.json','input/character.glb','candidate/character.glb']:
            inputs[str(folder/name)]=sha256(folder/name)
    save(output,dict(at=now(),implementation_sha256=sha256(__file__),inputs=inputs,rows=rows,
        quality_approved=False,scope='Decoded root acceleration decomposition and reported convergence only. Large remaining updates do not prove the cause of a dynamics defect. No new optimization.'))
    print([dict(case=r['case'],peaks=r['peak_frames'],last_parameter_change=r['convergence']['changes'][-1]) for r in rows])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
