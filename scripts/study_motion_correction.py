"""Apply pinned upstream correction to retained motions; no inference or training."""
import os
import sys
import shutil
import time
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now, offline_environment, source_check


def run(out,pose_only=False):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    os.environ.update(offline_environment())
    package=ROOT/'.cache/motion-correction-package'
    sys.path.insert(0,str(package))
    import torch
    from kimodo.skeleton import SOMASkeleton30, SOMASkeleton77
    from kimodo.postprocess import post_process_motion
    from kimodo.exports.motion_io import save_kimodo_npz
    from generation_constraints import load_guides
    from inspect_motion import validate_motion
    from audit_body_ground import measure
    from build_soma_preview import make_preview, ASSET
    from gltf_tools import write_glb
    from action_worker_lock import worker_lock
    import motion_correction._motion_correction as native
    build=read(package/'build-provenance.json')
    build['loaded_extension_sha256']=sha256(Path(native.__file__))
    skeleton=SOMASkeleton30();full=SOMASkeleton77()
    subset=[full.bone_order_names.index(n) for n in skeleton.bone_order_names]
    skin=dict(np.load(ASSET,allow_pickle=False));rows=[]
    sources=['jump-205','jump-204','dance-203','dance-204']
    modes=['raw','guided','guided_pose_only'] if pose_only else ['raw','contact_only','guided']
    save(out/'design.json',dict(cases=sources,variants=modes,contact_threshold=.5,root_margin=.04,scope='Exact retained baseline outputs; offline CPU postprocessing. guided_pose_only suppresses predicted contact input to the solver only; output contact labels are still original, unconfirmed model predictions. Not an equivalent rerun of multiprompt generation: no per-segment re-encoding. No inference, training, default promotion, or animator approval.',build=build))
    impl=out/'implementation';impl.mkdir();shutil.copyfile(__file__,impl/Path(__file__).name)
    save(out/'pipeline.json',dict(status='running'))
    with worker_lock():
        for case in sources:
            source=ROOT/'reports/boundary-guidance-v1'/(case+'-baseline')
            original=dict(np.load(source/'motion.npz',allow_pickle=False));record=read(source/'record.json')
            assert sha256(source/'motion.npz')==record['raw_sha256']
            compiled=read(source/'constraints.json')
            guide=dict(np.load(source/'guide.npz',allow_pickle=False))
            folder=out/case;folder.mkdir()
            for name in ('guide.npz','constraints.json','request.json','record.json'):
                shutil.copyfile(source/name,folder/('source-'+name))
            n=len(original['root_positions']);anchors=[0,1,n-2,n-1]
            local=torch.tensor(original['local_rot_mats'][:,subset])[None]
            root=torch.tensor(original['root_positions'])[None]
            contacts=torch.tensor(original['foot_contacts'][:,[0,1,3,4]])[None]
            # Explicitly verify duplicated toe-end channels before inversion.
            assert np.array_equal(original['foot_contacts'][:,1],original['foot_contacts'][:,2])
            assert np.array_equal(original['foot_contacts'][:,4],original['foot_contacts'][:,5])
            for mode in modes:
                target=folder/mode;target.mkdir();start=time.perf_counter();repeat_error=None
                if mode=='raw':
                    shutil.copyfile(source/'motion.npz',target/'motion.npz');data=original
                else:
                    constraints=load_guides(compiled,skeleton) if mode.startswith('guided') else []
                    solver_contacts=torch.zeros_like(contacts) if mode=='guided_pose_only' else contacts
                    corrected=post_process_motion(local,root,solver_contacts,skeleton,constraints,contact_threshold=.5,root_margin=.04)
                    repeated=post_process_motion(local,root,solver_contacts,skeleton,constraints,contact_threshold=.5,root_margin=.04)
                    repeat_error=max(float((corrected[k]-repeated[k]).abs().max()) for k in corrected)
                    if repeat_error!=0:raise ValueError('Repeated correction is not deterministic')
                    assert torch.equal(local,torch.tensor(original['local_rot_mats'][:,subset])[None])
                    assert torch.equal(root,torch.tensor(original['root_positions'])[None])
                    assert torch.equal(contacts,torch.tensor(original['foot_contacts'][:,[0,1,3,4]])[None])
                    corrected['foot_contacts']=contacts
                    expanded=skeleton.output_to_SOMASkeleton77(corrected)
                    data={k:v[0].numpy() for k,v in expanded.items()}
                    # Do not keep stale smooth-root/features from the input NPZ.
                    save_kimodo_npz(str(target/'motion.npz'),data)
                seconds=time.perf_counter()-start
                validate_motion(data,30)
                ground=measure(data,skin);save(target/'ground-audit.json',ground)
                doc,binary,_,_=make_preview(skin,data,np.zeros(3),repeat=False)
                write_glb(target/'soma.glb',doc,binary)
                row=dict(case=case,mode=mode,source_sha256=record['raw_sha256'],output_sha256=sha256(target/'motion.npz'),glb_sha256=sha256(target/'soma.glb'),seconds_including_repeat=seconds,repeat_max_error=repeat_error,frames=n,anchors=anchors,source_job=record['source_job'],native_mesh_floor_m=ground['mesh_max_depth_m'],kimodo_commit=source_check(),human_approved=False)
                rows.append(row);save(target/'record.json',row)
                save(out/'comparison.json',dict(cases=rows,quality_approved=False,production_changed=False))
                print(case,mode,'floor_mm',ground['mesh_max_depth_m']*1000,flush=True)
            assert sha256(source/'motion.npz')==record['raw_sha256']
    save(out/'pipeline.json',dict(status='complete',finished_at=now(),outputs=len(rows)))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--pose-only',action='store_true');a=p.parse_args()
    existed=a.output.exists()
    try:run(a.output,a.pose_only)
    except Exception as exc:
        if not existed and a.output.exists():save(a.output/'pipeline.json',dict(status='failed',error=str(exc)))
        raise
