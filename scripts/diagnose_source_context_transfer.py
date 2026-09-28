"""Four-anchor probe: retain source animated translations during mapped pose transfer."""
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_prompt_edits import localize
from retarget_rig import calibration,resolve_profile
from kimodo.skeleton import SOMASkeleton77


def run(out):
    results=[]
    for case in read(out/'design.json')['cases']:
        folder=out/case;record=read(folder/'transfer-record.json');original=ROOT/'reports/rig-jobs'/record['job']
        ref=RigAsset.load(original/'source/character.glb');source=RigAsset.load(original/'input/character.glb')
        profile=read(original/'source/rig-profile.json');skeleton=SOMASkeleton77();mapping,offset=resolve_profile(ref,profile)
        correction,scale,_=calibration(ref,mapping,skeleton,profile.get('axis_alignment_xyzw'))
        motion=dict(np.load(folder/'aligned-native.npz'));n=len(motion['root_positions']);a=record['edit']['start_frame'];indices=[0,1,n-2,n-1]
        sampler=AnimationSampler(source.document,source.binary,0)
        desired=np.array([sampler.sample(float(np.float32((a+i)/30))) for i in indices])
        local=localize(desired,source.parents);world=np.empty_like(desired)
        inverse={node:skeleton.bone_order_names.index(role) for role,node in mapping.items()}
        def depth(node):return 0 if source.parents[node]<0 else depth(source.parents[node])+1
        for node in sorted(range(len(source.parents)),key=depth):
            parent=source.parents[node];pw=np.repeat(np.eye(4)[None],4,axis=0) if parent<0 else world[:,parent]
            loc=local[:,node].copy()
            if node in inverse:
                target=motion['global_rot_mats'][indices,inverse[node]]@correction[node]
                loc[:,:3,:3]=Rotation.from_matrix(np.linalg.inv(pw[:,:3,:3])@target).as_matrix()
                if node==mapping['Hips']:
                    loc[:,:3,3]=(np.linalg.inv(pw)@np.c_[motion['root_positions'][indices]*scale+offset,np.ones(4)][:,:,None])[:,:3,0]
            world[:,node]=pw@loc
        nodes=list(mapping.values());error=float(np.linalg.norm(world[:,nodes,:3,3]-desired[:,nodes,:3,3],axis=-1).max())
        results.append(dict(case=case,mapped_anchor_position_error_with_source_context_m=error,scope='Four-anchor diagnostic only. Reuses source non-root local translations and unmapped local transforms while applying corrected mapped rotations and hips. Not applied to any exported candidate.'))
    save(out/'source-context-diagnostic.json',dict(cases=results));print(results)


if __name__=='__main__':run(ROOT/'reports/corrected-rig-transfer-v1')
