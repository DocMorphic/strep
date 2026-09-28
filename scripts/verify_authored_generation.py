"""Verify a real Studio job using an authored pose, without claiming motion quality."""
import argparse,os,zipfile,hashlib,urllib.request
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from strep import model_directory
from action_requests import validate_batch,request_digest,conditioning_texts
from generation_constraints import compile_guides
from audit_generation_guides import audit
from inspect_motion import skeleton_metadata
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler

def run(folder,output):
    folder=Path(folder);output=Path(output);batch=validate_batch(read(folder/'request.json'));state=read(folder/'pipeline.json')
    assert state['status']=='complete' and state['request_sha256']==request_digest(batch)
    summary=read(folder/'summary.json');cache=read(folder/'conditioning/manifest.json')
    assert sorted(cache['entries'])==conditioning_texts(batch) and cache['request_sha256']==request_digest(batch)
    for item in cache['entries'].values():assert sha256(folder/'conditioning'/item['file'])==item['sha256']
    checkpoint=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
    checkpoint_hash=sha256(model_directory(checkpoint)/'model.safetensors')
    assert checkpoint_hash==checkpoint['files_sha256']['model.safetensors']
    names,_,_=skeleton_metadata(77);rows=[];http=[];manifest=read(output/'manifest.json')
    for trial in summary['trials']:
        dest=folder/'takes'/trial['id'];request=trial['request'];record=read(dest/'generation-record.json')
        assert request==next(r for r in batch['requests'] if r['id']==request['id'])==record['request']
        assert record['seed'] in request['seeds'] and record['request_sha256']==request_digest(batch)
        assert record['checkpoint_sha256']==checkpoint_hash and record['checkpoint_revision']==checkpoint['revision']
        assert record['postprocessing'] is False and record['diffusion_steps']==100
        compiled,provenance=compile_guides(request)
        assert record['constraints']==compiled and record['constraint_sources']==provenance
        for name,digest in trial['hashes'].items():assert sha256(dest/name)==digest
        with zipfile.ZipFile(dest/'animation-pack.zip') as package:
            assert package.testzip() is None
            for name in package.namelist():
                expected=(ROOT/'vendor/kimodo/LICENSE').read_bytes() if name=='LICENSE.txt' else (dest/name).read_bytes()
                assert package.read(name)==expected
            entries=len(package.namelist())
        motion=dict(np.load(dest/'motion.npz',allow_pickle=False));assert audit(motion,compiled)==read(dest/'constraint-audit.json')
        direct=[]
        for guide in request['generation_constraints']:
            with np.load(ROOT/guide['motion'],allow_pickle=False) as target:
                for f,s in zip(guide['frame_indices'],guide['source_frames']):
                    for joint in guide['joint_names']:
                        j=names.index(joint)
                        delta=np.linalg.solve(target['global_rot_mats'][s,j],motion['global_rot_mats'][f,j])
                        direct.append(dict(joint=joint,frame=f,native_world_position_error_m=float(np.linalg.norm(motion['posed_joints'][f,j]-target['posed_joints'][s,j])),native_world_orientation_error_degrees=float(np.degrees(Rotation.from_matrix(delta).magnitude()))))
        rig=RigAsset.load(dest/'soma.glb');sampler=AnimationSampler(rig.document,rig.binary,0);error=0.;floor=[];half=[]
        for f in range(trial['frames']):
            world=sampler.sample(float(np.float32(f/30)));error=max(error,float(np.max(np.abs(world[1:78,:3,3]-motion['posed_joints'][f]))))
            floor.append(max(0.,-float(rig.vertices(world)[:,1].min())))
            if f<trial['frames']-1:half.append(max(0.,-float(rig.vertices(sampler.sample((f+.5)/30))[:,1].min())))
        assert error<1e-5
        rows.append(dict(id=trial['id'],frames=trial['frames'],direct_native_effector_errors=direct,glb_position_error_m=error,full_mesh_floor_depth_m=max(floor),half_frame_floor_depth_m=max(half),package_entries=entries))
        item=dict(id=trial['id'],path=Path(os.path.relpath((dest/'soma.glb').resolve(),output.resolve())).as_posix(),sha256=sha256(dest/'soma.glb'),frames=trial['frames'],fps=30)
        manifest['cases']=[c for c in manifest['cases'] if c['id']!=item['id']]+[item]
        paths=[dest/'soma.glb',dest/'animation-pack.zip']
        for guide in request['generation_constraints']:
            base=(ROOT/guide['motion']).parent;paths.extend(base/n for n in ['candidate.npz','candidate.glb','audit.json'])
        for path in paths:
            url='http://127.0.0.1:8768/files/'+path.resolve().relative_to(ROOT/'reports').as_posix()
            with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
            digest=hashlib.sha256(data).hexdigest();assert digest==sha256(path)
            http.append(dict(url=url,sha256=digest,bytes=len(data)))
    save(output/'manifest.json',manifest);save(output/'generation-verification.json',dict(created_at=now(),checks_passed=True,cases=rows,model_unchanged=True,quality_approved=False))
    save(output/'http-verification.json',dict(checks_passed=True,files=http));print(rows)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.folder,a.output)
