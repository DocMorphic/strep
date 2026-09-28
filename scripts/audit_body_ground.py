"""Measure the actual eight-weight SOMA surface against the preview's Y=0 floor.

Read-only diagnostic, not a collision solver or contact/realism certification.
"""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET


def measure(motion,skin):
    weights=skin['lbs_weights'];joints=skin['lbs_indices']
    points=np.c_[skin['bind_vertices'],np.ones(len(weights))]
    inverse=np.linalg.inv(skin['bind_rig_transform'])
    names=[str(n) for n in skin['rig_joint_names']]
    dominant=joints[np.arange(len(joints)),weights.argmax(axis=1)]
    depths=[];fractions=[];regions={};worst=None
    for frame,(rotation,position) in enumerate(zip(motion['global_rot_mats'],motion['posed_joints'])):
        transform=np.broadcast_to(np.eye(4),(77,4,4)).copy()
        transform[:,:3,:3]=rotation;transform[:,:3,3]=position;transform=transform@inverse
        # Only Y is needed; this is the same eight-influence LBS used by the preview.
        y=np.sum(np.einsum('vwi,vi->vw',transform[joints,1,:],points)*weights,axis=1)
        vertex=int(y.argmin());depth=max(0,float(-y[vertex]));depths.append(depth)
        fractions.append(float(np.mean(y<-.01)))
        for bone in np.unique(dominant[y<-.01]):
            region=names[bone];regions[region]=regions.get(region,0)+1
        if worst is None or depth>worst['depth_m']:
            worst={'frame':frame,'time_s':frame/30,'depth_m':depth,'vertex':vertex,'dominant_bone':names[dominant[vertex]]}
    return {'mesh_max_depth_m':max(depths),'mesh_frame_max_depth_p95_m':float(np.percentile(depths,95)),
        'frames_over_1cm':int(np.sum(np.array(depths)>.01)),'frame_count':len(depths),
        'max_fraction_of_vertices_below_1cm':max(fractions),'worst':worst,
        'region_frames_over_1cm':regions,'per_frame_max_depth_m':depths,
        'scope':'All 18,056 SOMA vertices, all eight weights, static Y=0 floor. Dominant bone labels locate affected skin approximately. No object/self collisions, contact classification, correction or physical realism score.'}


def main(folder):
    folder=Path(folder);summary=read(folder/'summary.json');skin=dict(np.load(ASSET,allow_pickle=False));trials=[]
    for trial in summary['trials']:
        path=folder/'takes'/trial['id']/'motion.npz';before=sha256(path)
        if before!=trial['source_sha256']:raise ValueError('Raw source provenance mismatch')
        result=measure(dict(np.load(path,allow_pickle=False)),skin)
        assert sha256(path)==before
        trials.append({'id':trial['id'],'source_sha256':before,**result})
        print(trial['id']+f": {result['mesh_max_depth_m']*100:.1f} cm / "+result['worst']['dominant_bone'],flush=True)
    save(folder/'ground-audit.json',{'created_at':now(),'method_sha256':sha256(Path(__file__)),'mesh_sha256':sha256(ASSET),'trials':trials,
        'scope':'Diagnostic only; raw motion unchanged. Floor origin matches studio preview. All frames measured, no subsampling.'})
    summary['surface_audit']='ground-audit.json';save(folder/'summary.json',summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path,nargs='?',default=ROOT/'reports/action-coverage-v1');main(p.parse_args().folder)
