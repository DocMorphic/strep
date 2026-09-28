"""Export raw / limb-only / body candidates with independent pose validation."""
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
from floor_contact import correct as limb_correct,Surface
from body_contact import refine,CONFIG
from evaluate_floor_contact import compare
from evaluate_body_contact import evaluate
from build_soma_preview import ASSET,make_preview
from gltf_tools import write_glb,read_glb,sample_animation,accessor
from inspect_motion import validate_motion,metrics,contact_events
from export_actions import sequence_diagnostics


def export_motion(path,motion,skin,skeleton,depths):
    path.mkdir(parents=True,exist_ok=True);np.savez(path/'motion.npz',**motion)
    save_motion_bvh(path/'motion.bvh',torch.from_numpy(motion['local_rot_mats']),torch.from_numpy(motion['root_positions']),skeleton=skeleton,fps=30,standard_tpose=True)
    restored,fps=bvh_to_kimodo_motion(path/'motion.bvh',skeleton=skeleton,standard_tpose=True)
    bvh_error=float(np.linalg.norm(restored['posed_joints'].numpy()-motion['posed_joints'],axis=-1).max())
    assert fps==30 and bvh_error<1e-4
    doc,binary,positions,rotations=make_preview(skin,motion,np.zeros(3),repeat=False)
    write_glb(path/'soma.glb',doc,binary);doc,binary=read_glb(path/'soma.glb')
    errors=np.zeros(3);surface=Surface(skin)
    for f in range(len(positions)):
        w=sample_animation(doc,binary,0,f)[1:78]
        depth=max(0,-float(surface.vertices(w[:,:3,:3],w[:,:3,3])[:,1].min()))
        errors=np.maximum(errors,[np.linalg.norm(w[:,:3,3]-positions[f],axis=-1).max(),
                                  np.abs(w[:,:3,:3]-rotations[f]).max(),abs(depth-depths[f])])
    assert errors.max()<1e-5
    attrs=doc['meshes'][0]['primitives'][0]['attributes']
    for attribute,key in [('WEIGHTS','lbs_weights'),('JOINTS','lbs_indices')]:
        actual=np.concatenate([accessor(doc,binary,attrs[f'{attribute}_{i}']) for i in range(2)],axis=1)
        assert np.array_equal(actual,skin[key])
    _,_,feet=validate_motion(motion,30);times=np.arange(len(positions))/30
    q=Rotation.from_matrix(motion['global_rot_mats'][:,0]).as_quat()
    for f in range(1,len(q)):
        if np.dot(q[f-1],q[f])<0:q[f]*=-1
    save(path/'root-motion.json',dict(space='Actual exported SOMA Hips world transform, meters, Y up; not engine-specific root extraction.',times_s=times.tolist(),positions_m=motion['root_positions'].tolist(),rotations_xyzw=q.tolist()))
    save(path/'contacts.json',dict(provenance='Unchanged model foot-contact predictions, not certified support/gameplay events.',intervals=contact_events(motion['foot_contacts'],feet,30)))
    return dict(glb_joint_error_m=float(errors[0]),glb_rotation_error=float(errors[1]),glb_surface_depth_error_m=float(errors[2]),bvh_joint_error_m=bvh_error,all_eight_weights_verified=True)


def run(folders,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);save(output/'pipeline.json',dict(status='processing'))
    skin=dict(np.load(ASSET));skeleton=SOMASkeleton77()
    scripts=['body_contact.py','evaluate_body_contact.py','floor_contact.py','evaluate_floor_contact.py','run_body_contact.py']
    summary=dict(id=output.name,created_at=now(),trials=[],config=CONFIG,implementation_hashes={n:sha256(ROOT/'scripts'/n) for n in scripts},mesh_sha256=sha256(ASSET))
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
    for folder in [Path(p).resolve() for p in folders]:
        for raw in read(folder/'summary.json')['trials']:
            original_id=raw['id'];id=original_id
            if any(t['id']==id for t in summary['trials']):id=folder.name+'-'+id
            origin=folder/'takes'/original_id;source=origin/'motion.npz'
            assert sha256(source)==raw['source_sha256']
            motion=dict(np.load(source));started=time.perf_counter()
            base,limb_recipe=limb_correct(motion,skin);candidate,recipe=refine(base,skin)
            repeated,_=refine(base,skin)
            assert all(np.array_equal(candidate[k],repeated[k]) for k in candidate)
            evaluation,body=evaluate(motion,base,candidate,skin,recipe);limb_evaluation=compare(motion,base,skin)
            elapsed=time.perf_counter()-started;path=output/'takes'/id
            validation=export_motion(path,candidate,skin,skeleton,evaluation['after']['per_frame_max_depth_m'])
            limb_validation=export_motion(path/'limb',base,skin,skeleton,limb_evaluation['after']['per_frame_max_depth_m'])
            raw_path=path/'raw';raw_path.mkdir()
            for file in ['motion.npz','motion.bvh','soma.glb','root-motion.json','contacts.json','evidence.json']:shutil.copyfile(origin/file,raw_path/file)
            for version in [path,path/'limb',raw_path]:
                for file in ['request.json','timeline.json','generation-record.json']:shutil.copyfile(origin/file,version/file)
            names,_,feet=validate_motion(candidate,30)
            limb_trial={**{k:v for k,v in raw.items() if k!='hashes'},'id':id,'processing':'Hands/feet baseline v1; original root retained','metrics':metrics(base,names,feet,30),'flags':limb_evaluation['flags'],'floor_correction':limb_evaluation}
            save(path/'limb/evidence.json',limb_trial)
            record={**{k:v for k,v in raw.items() if k!='hashes'},'id':id,'source_original_id':original_id,'source_collection':folder.relative_to(ROOT/'reports').as_posix(),
                'raw_trial':{**raw,'id':id},'limb_trial':limb_trial,'raw_flags':raw['flags'],
                'metrics':metrics(candidate,names,feet,30),'flags':evaluation['flags'],'floor_correction':evaluation,'body_correction':body,
                'processing':('Experimental whole-body clearance; vertical root and torso edited; compare all three versions' if recipe['applied'] else 'Body stage unchanged; hands/feet correction only'),
                'sequence':sequence_diagnostics(candidate,read(origin/'timeline.json')['segments']),
                'correction_and_evaluation_time_s':elapsed,'validation':dict(candidate=validation,limb=limb_validation,reproduces_exactly=True),
                'human_approved':False,'engine_import':None}
            save(path/'comparison.json',dict(raw_to_body=evaluation,body=body,raw_to_limb=limb_evaluation))
            save(path/'recipe.json',dict(limb=limb_recipe,body=recipe,source_sha256=sha256(source),implementation_hashes=summary['implementation_hashes']))
            save(path/'evidence.json',record)
            files=['soma.glb','motion.bvh','motion.npz','root-motion.json','contacts.json','request.json','timeline.json','generation-record.json','comparison.json','recipe.json','evidence.json']
            with zipfile.ZipFile(path/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as z:
                for file in files:z.write(path/file,file)
                z.write(ROOT/'vendor/kimodo/LICENSE','LICENSE.txt')
            record['hashes']={str(p.relative_to(path)).replace('\\','/'):sha256(p) for p in path.rglob('*') if p.is_file()}
            summary['trials'].append(record);save(output/'summary.json',summary)
            print(f"{id}: limb {limb_evaluation['after']['mesh_max_depth_m']*100:.2f} -> body {evaluation['after']['mesh_max_depth_m']*100:.2f} cm; {evaluation['flags']}",flush=True)
    summary['finished_at']=now();save(output/'summary.json',summary);save(output/'pipeline.json',dict(status='complete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folders',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.folders,a.output)
