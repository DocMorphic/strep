"""Check the actual exported local corrections at integer and half frames."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from motion_edit_bounds import enforce
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize


def run(study):
    study=Path(study).resolve();output=study/'decoded-bounds-verification.json'
    if output.exists():raise ValueError('Preserve prior verification')
    if read(study/'pipeline.json')['status']!='complete_pending_geometry':raise ValueError('Incomplete export')
    spec=read(study/'request.json');manifest=read(study/'manifest.json');frames=np.arange(0,149.5,.5);times=(frames/30).astype(np.float32);rows=[];files={}
    for seed in spec['seeds']:
        for actor in ['A','B']:
            folder=study/f'seed-{seed}'/actor;source=folder/'raw/character.glb';rig=RigAsset.load(source);sampler=AnimationSampler(rig.document,rig.binary,0)
            original=np.array([sampler.sample(float(t)) for t in times]);local=localize(original,rig.parents);names=[str(n.get('name') or f'node-{i}') for i,n in enumerate(rig.document['nodes'])];hips=names.index('Hips')
            for mode in ['body_fit','body_fit_posture']:
                path=folder/mode/'character.glb';relative=path.relative_to(study).as_posix()
                if sha256(path)!=manifest['assets'][relative]['sha256']:raise ValueError('Changed candidate')
                decoded=RigAsset.load(path)
                if not np.array_equal(decoded.parents,rig.parents) or [n.get('name') for n in decoded.document['nodes']]!=[n.get('name') for n in rig.document['nodes']]:raise ValueError('Changed rig hierarchy')
                other=AnimationSampler(decoded.document,decoded.binary,0);world=np.array([other.sample(float(t)) for t in times]);candidate=localize(world,rig.parents)
                caps={n:spec['edit_limits'].get(n,0.) for n in names}
                if mode=='body_fit_posture':
                    for n in names:
                        if n.startswith('LeftHand') and n[-1:].isdigit():caps[n]=60.
                budgets=dict(joint_rotation_degrees=caps,joint_correction_speed_degrees_s={n:150. for n in names},root_components_m=[0.,0.,0.],root_correction_speed_m_s=0.)
                report=enforce(local[:,:,:3,:3],candidate[:,:,:3,:3],original[:,hips,:3,3],world[:,hips,:3,3],times,names,budgets)
                frozen=(frames<=60)|(frames>=90);error=float(np.abs(candidate[frozen]-local[frozen]).max())
                if error>1e-5:raise ValueError('Export changed motion outside edit interval')
                rows.append(dict(seed=seed,actor=actor,mode=mode,bounds=report,outside_interval_matrix_error=error));files[relative]=sha256(path)
            files[source.relative_to(study).as_posix()]=sha256(source)
    if len(rows)!=20:raise ValueError('Incomplete corrected population')
    save(output,dict(at=now(),request_sha256=sha256(study/'request.json'),manifest_sha256=sha256(study/'manifest.json'),verifier_sha256=sha256(__file__),guard_sha256=sha256(ROOT/'scripts/motion_edit_bounds.py'),
        frames=frames.tolist(),rows=rows,files=files,quality_approved=False,
        scope='Actual exported original/candidate local rotations and hips at all299 integer/half-frame samples, explicit total-edit/correction-speed budgets and preserved outside-window matrices. Not continuous-time, anatomy, contact or animator certification.'))
    print({'candidates':len(rows),'decoded_samples_per_candidate':len(frames),'all_sampled_budgets_passed':True},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);run(p.parse_args().study)
