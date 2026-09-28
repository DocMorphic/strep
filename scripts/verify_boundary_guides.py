"""Independent NumPy feature decoding, FK, guide and native-export checks."""
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256
from kimodo.skeleton import SOMASkeleton30,SOMASkeleton77
from gltf_tools import read_glb,sample_animation,accessor


def positions(local,root,skeleton):
    neutral=np.asarray(skeleton.neutral_joints);parents=np.asarray(skeleton.joint_parents)
    global_r=np.empty_like(local);p=np.empty(local.shape[:2]+(3,))
    for j,parent in enumerate(parents):
        if parent<0:global_r[:,j]=local[:,j];p[:,j]=root
        else:
            global_r[:,j]=global_r[:,parent]@local[:,j]
            p[:,j]=p[:,parent]+np.einsum('fij,j->fi',global_r[:,parent],neutral[j]-neutral[parent])
    return p,global_r


def decode_positions(features,mean,std):
    x=features[0].astype(float)*np.sqrt(std.astype(float)**2+1e-5)+mean
    p=x[:,5:95].reshape(-1,30,3).copy();p[:,:,[0,2]]+=x[:,None,[0,2]]
    return p,x


def verify(out):
    out=Path(out);s30=SOMASkeleton30();s77=SOMASkeleton77();subset=[s77.bone_order_names.index(n) for n in s30.bone_order_names]
    stats=ROOT/'models/checkpoints/Kimodo-SOMA-RP-v1.1/stats/motion'
    mean=np.concatenate([np.load(stats/p/'mean.npy') for p in ('global_root','body')]);std=np.concatenate([np.load(stats/p/'std.npy') for p in ('global_root','body')])
    cases=[];manifest=[]
    for item in read(out/'comparison.json')['cases']:
        label=item['case']+'-'+item['mode'];folder=out/label;record=read(folder/'record.json');cap=dict(np.load(folder/'feature-capture.npz'));motion=dict(np.load(folder/'motion.npz'));guide=dict(np.load(folder/'guide.npz'))
        assert record['raw_sha256']==sha256(folder/'motion.npz') and record['raw_feature_sha256']==sha256(folder/'feature-capture.npz')
        frames=record['anchors'];n=len(motion['root_positions']);expected,_=positions(guide['local_rot_mats'][:,subset].astype(float),guide['root_positions'],s30)
        p,x=decode_positions(cap['features'],mean,std);observed,_=decode_positions(cap['observed'],mean,std)
        condition_error=float(np.abs(observed[frames]-expected[frames]).max());assert condition_error<1e-5
        np.testing.assert_allclose(p,cap['position_head'],atol=1e-5,rtol=0)
        fk,_=positions(motion['local_rot_mats'][:,subset].astype(float),motion['root_positions'],s30)
        np.testing.assert_allclose(fk,cap['rotation_fk'],atol=1e-5,rtol=0)
        common=[0,1,n-2,n-1]
        error=float(np.linalg.norm(fk[common]-expected[common],axis=-1).max())
        assert abs(error-record['common_anchors_rotation_fk']['max_joint_error_m'])<1e-5
        assert not cap['mask'][0,:,95:275].any()
        if record['mode']=='baseline':
            source=ROOT/'reports/rig-jobs'/record['source_job']/'generation/takes'/f'replacement-seed-{record["seed"]}'/'motion.npz'
            assert sha256(source)==sha256(folder/'motion.npz')
        doc,binary=read_glb(folder/'soma.glb');pose_error=0.;rotation_error=0.
        for f in range(n):
            world=sample_animation(doc,binary,0,f)[1:78]
            pose_error=max(pose_error,float(np.abs(world[:,:3,3]-motion['posed_joints'][f]).max()))
            rotation_error=max(rotation_error,float(np.abs(world[:,:3,:3]-motion['global_rot_mats'][f]).max()))
        assert max(pose_error,rotation_error)<1e-5
        from build_soma_preview import ASSET
        skin=dict(np.load(ASSET));attrs=doc['meshes'][0]['primitives'][0]['attributes']
        weights=np.concatenate([accessor(doc,binary,attrs[f'WEIGHTS_{i}']) for i in (0,1)],axis=1)
        assert np.array_equal(weights,skin['lbs_weights'])
        # Adjacent local-rotation change is diagnostic, not a speed limit.
        from scipy.spatial.transform import Rotation
        r=motion['local_rot_mats'].astype(float);step=np.degrees(Rotation.from_matrix((r[:-1].transpose(0,1,3,2)@r[1:]).reshape(-1,3,3)).magnitude()).reshape(n-1,77)
        case=dict(id=label,guide_roundtrip_error=condition_error,common_anchor_error_m=error,preview_position_error_m=pose_error,preview_rotation_error=rotation_error,all_eight_skin_weights_preserved=True,local_rotation_step_max_degrees=float(step.max()),boundary_eight_frame_step_max_degrees=float(np.r_[step[:8].ravel(),step[-8:].ravel()].max()),source_sha256=record['raw_sha256'])
        cases.append(case);manifest.append(dict(id=label,path=label+'/soma.glb',sha256=sha256(folder/'soma.glb'),frames=n,fps=30))
    save(out/'verification.json',dict(cases=cases,scope='NumPy stats decode and local FK independent of model inverse/constraint loader; frozen baseline NPZ identity, observed position channels and every native GLB frame/eight skin weights. No semantic or animator acceptance.'))
    save(out/'manifest.json',dict(cases=manifest));print(dict(verified=len(cases),max_condition_error=max(c['guide_roundtrip_error'] for c in cases),max_preview_error=max(c['preview_position_error_m'] for c in cases)))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);verify(p.parse_args().folder)
