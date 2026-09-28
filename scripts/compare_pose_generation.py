"""Compare every constrained take with its same-seed unconstrained baseline."""
import argparse
import zipfile
from pathlib import Path
import numpy as np
from strep import read, save, sha256, now
from audit_generation_guides import audit


def compare(folder):
    folder=Path(folder); freeze=read(folder/'freeze.json'); summary=read(folder/'summary.json')
    surface={t['id']:t for t in read(folder/'ground-audit.json')['trials']}
    rows=[]
    for fixture in freeze['fixtures']:
        action=fixture['action']
        seeds=next(r for r in read(folder/'request.json')['requests'] if r['id']==action)['seeds']
        for seed in seeds:
            pair={}
            for variant,suffix in [('baseline',''),('guided','-pose')]:
                take=f'{action}{suffix}-seed-{seed}'; trial=next(t for t in summary['trials'] if t['id']==take)
                path=folder/'takes'/take/'motion.npz'
                if sha256(path)!=trial['source_sha256']:raise ValueError('Source checksum mismatch')
                with np.load(path,allow_pickle=False) as archive: motion=dict(archive)
                step=np.linalg.norm(np.diff(motion['posed_joints'],axis=0),axis=-1)
                guide=audit(motion,fixture['compiled'])
                pair[variant]=dict(id=take,source_sha256=trial['source_sha256'],target_audit=guide,
                    foot_speed_p95_m_s=trial['metrics']['foot_horizontal_speed_predicted_contact_m_s']['p95'],
                    joint_step_max_m=float(step.max()),joint_step_p95_m=float(np.percentile(step,95)),
                    mesh_depth_m=surface[take]['mesh_max_depth_m'],mesh_frames_over_1cm=surface[take]['frames_over_1cm'],
                    existing_flags=trial['flags'],generation_time_s=trial['generation_time_s'])
                with zipfile.ZipFile(folder/'takes'/take/'animation-pack.zip') as archive:
                    for name in archive.namelist():
                        source=folder/'SOMA-preview-LICENSE.txt' if name=='LICENSE.txt' else folder/'takes'/take/name
                        if archive.read(name)!=source.read_bytes():raise ValueError('Package differs from output: '+name)
            rows.append(dict(action=action,seed=seed,**pair))
    report=dict(created_at=now(),pairs=rows,package_byte_checks=8,release_approved=False,
        scope='Matched-seed in-sample engineering pilot. Pose target from a prior generated clip, not external animator annotation. No naturalness/semantic or partner/object validation. Joint steps are diagnostics, not universal gates.',
        method_sha256=sha256(Path(__file__)))
    save(folder/'comparison.json',report)
    for row in rows:
        print(row['action'],row['seed'], {k:dict(target=v['target_audit']['guides'][0]['maximum'],slide=v['foot_speed_p95_m_s'],depth=v['mesh_depth_m']) for k,v in row.items() if k in ['baseline','guided']})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);compare(parser.parse_args().folder)
