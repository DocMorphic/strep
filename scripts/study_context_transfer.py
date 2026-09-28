"""Matched raw/fitted motion transfer with and without source transform context."""
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize,compose,blend
from rig_prompt_edit import weights
from retarget_rig import transfer,resolve_profile
from rig_loop import encode
from kimodo.skeleton import SOMASkeleton77


def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    cases=['jump-205','jump-204','dance-203','dance-204'];manifest=[];rows=[]
    save(out/'design.json',dict(cases=cases,inputs=['raw','pose_fitted'],versions=['reference','context'],scope='All four retained cases and both native inputs. No inference, training or mesh cleanup. Context retains original source translations and unmapped local transforms.'))
    implementation=out/'implementation';implementation.mkdir()
    for name in ['study_context_transfer.py','retarget_rig.py','rig_prompt_edit.py','rig_transition.py','rig_loop.py']:
        shutil.copyfile(ROOT/'scripts'/name,implementation/name)
    for case in cases:
        record=read(ROOT/'reports/motion-correction-v2'/case/'guided_pose_only/record.json');job=ROOT/'reports/rig-jobs'/record['source_job']
        original=RigAsset.load(job/'input/character.glb');reference=RigAsset.load(job/'source/character.glb');profile=read(job/'source/rig-profile.json');mapping,offset=resolve_profile(reference,profile)
        sampler=AnimationSampler(original.document,original.binary,0);report=read(job/'input/report.json');edit=read(job/'prompt-edit.json');a,b,k=(edit[t] for t in ('start_frame','last_frame','blend_frames'))
        before=np.array([sampler.sample(float(np.float32(f/30))) for f in range(report['frames'])]);context=localize(before[a:b+1],original.parents);n=b-a+1
        for mode in ['raw','pose_fitted']:
            native_path=job/'generation/aligned-generated.npz' if mode=='raw' else ROOT/'reports/corrected-rig-transfer-v1'/case/'aligned-native.npz'
            motion=dict(np.load(native_path,allow_pickle=False));folder=out/(case+'-'+mode);folder.mkdir();shutil.copyfile(native_path,folder/'motion.npz')
            for version in ['reference','context']:
                target=folder/version;target.mkdir()
                world,_,_,_,diagnostic=transfer(reference,motion,SOMASkeleton77(),mapping,offset,profile.get('axis_alignment_xyzw'),context_local=context if version=='context' else None)
                animated={c[0] for c in sampler.channels}|set(mapping.values())
                encode(original,world,animated,report['root_node'],target/'unblended.glb',case+' '+mode+' '+version+' unblended')
                local=localize(before,original.parents);local[a:b+1]=blend(local[a:b+1],localize(world,original.parents),weights(n,k));spliced=compose(local,original.parents)
                encode(original,spliced,animated,report['root_node'],target/'character.glb',case+' '+mode+' '+version)
                for file,frames in [('unblended.glb',n),('character.glb',len(before))]:
                    path=target/file;manifest.append(dict(id=case+'-'+mode+'-'+version+'-'+file[:-4],path=path.relative_to(out).as_posix(),sha256=sha256(path),frames=frames,fps=30))
            row=dict(case=case,mode=mode,source_job=record['source_job'],motion_sha256=sha256(native_path),source_glb_sha256=sha256(job/'input/character.glb'),edit=edit,frames=len(before),mapping=mapping,root_node=report['root_node'],human_approved=False)
            save(folder/'record.json',row);rows.append(row)
            print(case,mode,'exported',flush=True)
    save(out/'manifest.json',dict(cases=manifest));save(out/'comparison.json',dict(cases=rows,quality_approved=False));save(out/'pipeline.json',dict(status='complete',finished_at=now()))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);run(p.parse_args().output)
