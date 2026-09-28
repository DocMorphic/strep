"""Independent desired-world/splice oracle and source-channel preservation checks."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from gltf_tools import local_matrix
from verify_prompt_edits import localize
from retarget_rig import resolve_profile,calibration
from verify_motion_correction import angle
from kimodo.skeleton import SOMASkeleton77


def samples(rig,n):
    sampler=AnimationSampler(rig.document,rig.binary,0)
    return np.array([sampler.sample(float(np.float32(f/30))) for f in range(n)]),sampler


def verify(out):
    out=Path(out);checks=[]
    for item in read(out/'comparison.json')['cases']:
        folder=out/(item['case']+'-'+item['mode']);job=ROOT/'reports/rig-jobs'/item['source_job'];motion=dict(np.load(folder/'motion.npz'))
        assert sha256(folder/'motion.npz')==item['motion_sha256'] and sha256(job/'input/character.glb')==item['source_glb_sha256']
        source=RigAsset.load(job/'input/character.glb');reference=RigAsset.load(job/'source/character.glb');profile=read(job/'source/rig-profile.json');sk=SOMASkeleton77()
        mapping,offset=resolve_profile(reference,profile);corrections,scale,_=calibration(reference,mapping,sk,profile.get('axis_alignment_xyzw'));inverse={node:sk.bone_order_names.index(role) for role,node in mapping.items()}
        before,_=samples(source,item['frames']);a,b,k=(item['edit'][s] for s in ('start_frame','last_frame','blend_frames'));n=b-a+1;before_local=localize(before,source.parents);context=before_local[a:b+1];anchors=np.array([0,1,n-2,n-1]);mapped=list(mapping.values());unmapped=[i for i in range(len(source.parents)) if i not in mapped];nonroot=[i for i in range(len(source.parents)) if i!=mapping['Hips']]
        def depth(node):return 0 if source.parents[node]<0 else 1+depth(source.parents[node])
        for version in ['reference','context']:
            base=context.copy() if version=='context' else np.repeat(np.array([local_matrix(node) for node in reference.document['nodes']])[None],n,axis=0)
            world=np.empty_like(base)
            for node in sorted(range(len(source.parents)),key=depth):
                parent=source.parents[node];pw=np.repeat(np.eye(4)[None],n,axis=0) if parent<0 else world[:,parent];local=base[:,node].copy()
                if node in inverse:
                    desired=motion['global_rot_mats'][:,inverse[node]]@corrections[node]
                    local[:,:3,:3]=Rotation.from_matrix(np.linalg.inv(pw[:,:3,:3])@desired).as_matrix()
                    if node==mapping['Hips']:local[:,:3,3]=(np.linalg.inv(pw)@np.c_[motion['root_positions']*scale+offset,np.ones(n)][:,:,None])[:,:3,0]
                world[:,node]=pw@local
            expected=before_local.copy();w=np.zeros(len(before))
            unblended_local=localize(world,source.parents)
            for i in range(n):
                u=np.clip((min(i,n-1-i)-1)/(k-2),0,1);weight=u*u*(3-2*u);f=a+i;w[f]=weight
                expected[f,:,:3,3]=(1-weight)*before_local[f,:,:3,3]+weight*unblended_local[i,:,:3,3]
                for node in range(len(source.parents)):
                    expected[f,node,:3,:3]=Slerp([0,1],Rotation.from_matrix([before_local[f,node,:3,:3],unblended_local[i,node,:3,:3]]))([weight]).as_matrix()[0]
            rig=RigAsset.load(folder/version/'character.glb');actual,sampler=samples(rig,len(before));decoded_local=localize(actual,source.parents)
            unblended=RigAsset.load(folder/version/'unblended.glb');decoded,_=samples(unblended,n)
            oracle=max(float(np.abs(decoded-world).max()),float(np.abs(decoded_local-expected).max()));assert oracle<1e-5
            fixed=float(np.abs(actual[w==0]-before[w==0]).max());assert fixed<1e-5
            translation=float(np.abs(decoded_local[:,nonroot,:3,3]-before_local[:,nonroot,:3,3]).max())
            helper=float(np.abs(decoded_local[:,unmapped]-before_local[:,unmapped]).max()) if unmapped else 0.
            if version=='context':assert max(translation,helper)<1e-6
            anchor_position=float(np.linalg.norm(decoded[anchors][:,mapped,:3,3]-before[a+anchors][:,mapped,:3,3],axis=-1).max())
            anchor_rotation=float(angle(decoded[anchors][:,mapped,:3,:3],before[a+anchors][:,mapped,:3,:3]).max())
            if version=='context' and item['mode']=='pose_fitted':assert anchor_position<1e-5 and anchor_rotation<.001
            floor=np.array([max(0.,-float(rig.vertices(m)[:,1].min())) for m in actual]);half=max(max(0.,-float(rig.vertices(sampler.sample((f+.5)/30))[:,1].min())) for f in range(len(before)-1))
            step=angle(decoded_local[:-1,:,:3,:3],decoded_local[1:,:,:3,:3])
            row=dict(case=item['case'],mode=item['mode'],version=version,oracle_error=oracle,preserved_world_error=fixed,nonroot_translation_error_m=translation,unmapped_local_transform_error=helper,unblended_anchor_position_error_m=anchor_position,unblended_anchor_rotation_error_degrees=anchor_rotation,whole_floor_m=float(floor.max()),editable_floor_m=float(floor[w>0].max()),half_floor_m=half,joint_step_max_degrees=float(step.max()),quality_approved=False)
            checks.append(row);print(row,flush=True)
    save(out/'verification.json',dict(cases=checks,scope='Shared profile calibration, independent hierarchy and SciPy Slerp oracle; decoded GLB source local-channel preservation and all integer/half-frame surface floors. No contact or semantic acceptance.'))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);verify(p.parse_args().output)
