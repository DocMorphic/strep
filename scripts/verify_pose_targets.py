"""Independent decoded-pose checks for authored targets and rejected candidates."""
import argparse
import os
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from gltf_tools import sample_animation
from inspect_motion import skeleton_metadata


def verify(folders,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);names,parents,_=skeleton_metadata(77)
    rows=[];manifest=[]
    for folder in map(Path,folders):
        audit=read(folder/'audit.json');request=read(folder/'request.json');source=ROOT/request['motion']
        assert sha256(source)==request['sha256']==audit['source_sha256']
        assert sha256(folder/'candidate.npz')==audit['candidate_sha256']
        worlds={};local={};floor={};errors={}
        for mode in ['original','candidate']:
            path=folder/(mode+'.glb');rig=RigAsset.load(path);motion=dict(np.load(folder/(mode+'.npz'),allow_pickle=False))
            poses=np.array([sample_animation(rig.document,rig.binary,0,f)[1:78] for f in range(2)])
            errors[mode]=float(np.max(np.abs(poses[:,:,:3,3]-motion['posed_joints'])))
            assert errors[mode]<1e-5 and np.max(np.abs(poses[:,:,:3,:3]-motion['global_rot_mats']))<1e-5
            worlds[mode]=poses[0];local[mode]=poses[0,:,:3,:3].copy()
            for i,p in enumerate(parents):
                if p>=0:local[mode][i]=np.linalg.solve(poses[0,p,:3,:3],poses[0,i,:3,:3])
            actual=sample_animation(rig.document,rig.binary,0,0)
            floor[mode]=max(0.,-float(rig.vertices(actual)[:,1].min()))
            assert abs(floor[mode]-audit[mode+'_floor_depth_m'])<1e-5
            manifest.append(dict(id=folder.name+'-'+mode,path=Path(os.path.relpath(path.resolve(),output.resolve())).as_posix(),sha256=sha256(path),frames=2,fps=30))
        tip=names.index(request['effector']);desired=worlds['original'][tip,:3,3]+request['offset_m']
        error=float(np.linalg.norm(worlds['candidate'][tip,:3,3]-desired))
        delta=np.linalg.solve(local['original'],local['candidate']);max_edit=float(np.degrees(Rotation.from_matrix(delta).magnitude()).max())
        assert max_edit<=request['max_edit_degrees']+1e-4
        orientation=float(np.degrees(Rotation.from_matrix(np.linalg.solve(worlds['original'][tip,:3,:3],worlds['candidate'][tip,:3,:3])).magnitude()))
        assert orientation<.001
        edited={names.index(n) for n in audit['changed_local_joints']};moving=set(edited)
        for i,p in enumerate(parents):
            if p in moving:moving.add(i)
        fixed=[i for i in range(77) if i not in moving]
        fixed_error=float(np.max(np.abs(worlds['candidate'][fixed]-worlds['original'][fixed])))
        assert fixed_error<1e-5
        with np.load(source,allow_pickle=False) as raw:
            assert np.max(np.abs(worlds['original'][:,:3,3]-raw['posed_joints'][request['source_frame']]))<1e-5
        assert abs(error-audit['actual_native_fk_target_error_m'])<1e-5
        if audit['reached']:assert error<=.005+1e-6 and audit['guide']['sha256']==audit['candidate_sha256']
        else:assert audit['guide'] is None
        rows.append(dict(id=folder.name,reached=audit['reached'],effector=request['effector'],target_error_m=error,
            max_local_edit_degrees=max_edit,unchanged_world_matrix_error=fixed_error,effector_orientation_error_degrees=orientation,
            floor_depth_m=floor,roundtrip_position_error_m=errors))
    save(output/'verification.json',dict(created_at=now(),checks_passed=True,cases=rows,quality_approved=False))
    save(output/'manifest.json',dict(cases=manifest));print(rows)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folders',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();verify(a.folders,a.output)
