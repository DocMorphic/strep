"""Create a separate, reproducible floor-cleanup study from finite raw exports."""
import argparse
import shutil
import zipfile
import time
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from kimodo.skeleton import SOMASkeleton77
from kimodo.exports.bvh import save_motion_bvh,bvh_to_kimodo_motion
from strep import ROOT,read,save,sha256,now
from floor_contact import correct,CONFIG
from evaluate_floor_contact import compare
from build_soma_preview import ASSET,make_preview
from gltf_tools import write_glb,read_glb,sample_animation,accessor
from inspect_motion import validate_motion,metrics,contact_events
from export_actions import sequence_diagnostics


def run(folders, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    skin=dict(np.load(ASSET,allow_pickle=False));skeleton=SOMASkeleton77()
    summary=dict(id=output.name,created_at=now(),trials=[],config=CONFIG,
        implementation_hashes={n:sha256(ROOT/'scripts'/n) for n in ['floor_contact.py','evaluate_floor_contact.py','run_floor_contact.py']},
        mesh_sha256=sha256(ASSET),scope='Experimental, bounded hands/feet collision cleanup. Residual torso/knee penetration and contact drift are retained failures.')
    license=ROOT/'vendor/kimodo/LICENSE';shutil.copyfile(license,output/'SOMA-preview-LICENSE.txt')
    for folder in [Path(p).resolve() for p in folders]:
        for raw in read(folder/'summary.json')['trials']:
            id=raw['id']
            if any(t['id']==id for t in summary['trials']):id=folder.name+'-'+id
            origin=folder/'takes'/raw['id'];source=origin/'motion.npz';digest=sha256(source)
            if digest!=raw['source_sha256']:raise ValueError('Raw hash mismatch')
            motion=dict(np.load(source,allow_pickle=False));started=time.perf_counter()
            corrected,recipe=correct(motion,skin);elapsed=time.perf_counter()-started
            repeated,_=correct(motion,skin)
            if any(not np.array_equal(corrected[k],repeated[k]) for k in corrected):raise ValueError('Non-deterministic correction')
            names,parents,feet=validate_motion(corrected,30);evaluation=compare(motion,corrected,skin)
            path=output/'takes'/id;path.mkdir(parents=True)
            np.savez(path/'motion.npz',**corrected)
            save_motion_bvh(path/'motion.bvh',torch.from_numpy(corrected['local_rot_mats']),torch.from_numpy(corrected['root_positions']),skeleton=skeleton,fps=30,standard_tpose=True)
            restored,fps=bvh_to_kimodo_motion(path/'motion.bvh',skeleton=skeleton,standard_tpose=True)
            bvh_error=float(np.linalg.norm(restored['posed_joints'].numpy()-corrected['posed_joints'],axis=-1).max())
            if fps!=30 or bvh_error>1e-4:raise ValueError('BVH roundtrip mismatch')
            doc,binary,positions,rotations=make_preview(skin,corrected,np.zeros(3),repeat=False)
            write_glb(path/'soma.glb',doc,binary);decoded,payload=read_glb(path/'soma.glb')
            error=0.;rotation_error=0.;surface_error=0.
            from floor_contact import Surface
            surface=Surface(skin)
            for f in range(len(positions)):
                world=sample_animation(decoded,payload,0,f)[1:78]
                error=max(error,float(np.linalg.norm(world[:,:3,3]-positions[f],axis=-1).max()))
                rotation_error=max(rotation_error,float(np.abs(world[:,:3,:3]-rotations[f]).max()))
                # Independent exported transform hierarchy, all surface vertices.
                minimum=float(surface.vertices(world[:,:3,:3],world[:,:3,3])[:,1].min())
                depth=max(0,-minimum)
                surface_error=max(surface_error,abs(depth-evaluation['after']['per_frame_max_depth_m'][f]))
            if max(error,rotation_error,surface_error)>1e-5:raise ValueError('GLB roundtrip mismatch')
            times=np.arange(len(positions))/30
            save(path/'root-motion.json',dict(space='SOMA Hips world transform, meters, Y up. Unchanged from raw; not engine root extraction.',times_s=times.tolist(),positions_m=corrected['root_positions'].tolist(),rotations_xyzw=Rotation.from_matrix(corrected['global_rot_mats'][:,0]).as_quat().tolist()))
            save(path/'contacts.json',dict(provenance='Unchanged model foot contact predictions; no inferred hand supports or certified gameplay events.',intervals=contact_events(corrected['foot_contacts'],feet,30)))
            for file in ['request.json','timeline.json','generation-record.json']:shutil.copyfile(origin/file,path/file)
            raw_copy=path/'raw';raw_copy.mkdir()
            for file in ['motion.npz','soma.glb','motion.bvh','evidence.json','root-motion.json','contacts.json']:shutil.copyfile(origin/file,raw_copy/file)
            raw_trial={**raw,'id':id};save(raw_copy/'trial.json',raw_trial)
            record={**raw,'id':id,'label':raw['label'],'source_sha256':digest,'metrics':metrics(corrected,names,feet,30),
                'processing':'Experimental floor cleanup; compare with raw and inspect remaining flags',
                'raw_trial':raw_trial,'floor_correction':evaluation,'raw_flags':raw['flags'],'flags':evaluation['flags'],
                'sequence':sequence_diagnostics(corrected,read(origin/'timeline.json')['segments']),
                'correction_time_s':elapsed,'source_collection':folder.relative_to(ROOT/'reports').as_posix(),
                'validation':dict(reproduces_exactly=True,glb_joint_error_m=error,glb_rotation_error=rotation_error,
                    glb_surface_depth_error_m=surface_error,bvh_joint_error_m=bvh_error,raw_unchanged=sha256(source)==digest),
                'human_approved':False,'engine_import':None}
            save(path/'recipe.json',dict(**recipe,source_sha256=digest,implementation_hashes=summary['implementation_hashes']))
            save(path/'comparison.json',evaluation);save(path/'evidence.json',record)
            files=['soma.glb','motion.npz','motion.bvh','root-motion.json','contacts.json','timeline.json','generation-record.json','evidence.json','request.json','recipe.json','comparison.json']
            with zipfile.ZipFile(path/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as z:
                for file in files:z.write(path/file,file)
                z.write(license,'LICENSE.txt')
            record['hashes']={file:sha256(path/file) for file in files+['animation-pack.zip']}
            summary['trials'].append(record);save(output/'summary.json',summary)
            print(f"{id}: {evaluation['before']['mesh_max_depth_m']*100:.2f} -> {evaluation['after']['mesh_max_depth_m']*100:.2f} cm; {evaluation['flags']}",flush=True)
    summary['finished_at']=now();save(output/'summary.json',summary)
    save(output/'pipeline.json',dict(status='complete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folders',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.folders,a.output)
