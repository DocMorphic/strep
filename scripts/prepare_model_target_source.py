"""Prepare model-representable guide poses for geometry planning; no inference."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
import torch
from kimodo.skeleton import SOMASkeleton30,SOMASkeleton77
from strep import ROOT,read,save,sha256,now


def run(source,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT):raise ValueError('Use a new project folder')
    original=read(source/'protocol.json')
    if sha256(source/'protocol.json')!=read(source/'freeze.json')['protocol_sha256']:raise ValueError('Changed source protocol')
    if sha256(source/'guide-scene.json')!=original['guide_scene_sha256']:raise ValueError('Changed source scene')
    scene=read(source/'guide-scene.json');protocol=copy.deepcopy(original);guides={}
    small,full=SOMASkeleton30(),SOMASkeleton77();output.mkdir();(output/'guides').mkdir()
    for name,entry in original['guides'].items():
        path=ROOT/entry['path']
        if sha256(path)!=entry['sha256']:raise ValueError('Changed source guide')
        motion=dict(np.load(path,allow_pickle=False));local=torch.tensor(motion['local_rot_mats'],dtype=torch.float32)
        reduced=small.from_SOMASkeleton77(local);expanded=small.to_SOMASkeleton77(reduced)
        r,p,_=full.fk(expanded,torch.tensor(motion['root_positions'],dtype=torch.float32))
        motion.update(local_rot_mats=expanded.numpy(),global_rot_mats=r.numpy(),posed_joints=p.numpy())
        # Conversion is idempotent on all local matrices, including fingers.
        if not torch.equal(expanded,small.to_SOMASkeleton77(small.from_SOMASkeleton77(expanded))):raise ValueError('Model conversion is not stable')
        dest=output/'guides'/(name+'.npz');np.savez_compressed(dest,**motion)
        guides[name]=dict(path=dest.relative_to(ROOT).as_posix(),sha256=sha256(dest))
        scene['scene']['actors'][name].update(motion=guides[name]['path'],source_sha256=guides[name]['sha256'])
        scene['scene']['actors'][name].pop('preview_glb',None)
    save(output/'guide-scene.json',scene)
    # Retain only fields consumed by the planner; this is not a generation protocol.
    protocol=dict(at=now(),guides=guides,guide_scene_sha256=sha256(output/'guide-scene.json'),guide_export=original['guide_export'],event_frame=original['event_frame'],
        source_protocol=str(source/'protocol.json'),source_protocol_sha256=sha256(source/'protocol.json'),source_guides=original['guides'],
        preparer_sha256=sha256(__file__),scope='Planning-only canonical SOMA30-expanded pose source. Every finger follows the model representation. No inference, generation request or motion approval.',quality_approved=False)
    save(output/'protocol.json',protocol);save(output/'freeze.json',dict(protocol_sha256=sha256(output/'protocol.json')))
    shutil.copyfile(__file__,output/'prepare_model_target_source.py');print(str(output),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.source,a.output)
