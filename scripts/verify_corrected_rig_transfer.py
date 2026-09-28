"""Independent calibrated transfer/splice oracle and target surface diagnostics."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_prompt_edits import localize
from retarget_rig import calibration,resolve_profile
from gltf_tools import local_matrix
from verify_motion_correction import anchor_errors,angle
from verify_rig_clearance import verify as verify_clearance


def poses(rig,n):
    s=AnimationSampler(rig.document,rig.binary,0)
    return np.array([s.sample(float(np.float32(f/30))) for f in range(n)]),s


def verify_case(folder):
    from kimodo.skeleton import SOMASkeleton77
    record=read(folder/'transfer-record.json');original=ROOT/'reports/rig-jobs'/record['job']
    assert sha256(original/'input/character.glb')==record['original_source_sha256']
    assert sha256(original/'transfer/character.glb')==record['raw_splice_sha256']
    assert sha256(folder/'corrected-native.npz')==record['corrected_source_sha256']
    native=dict(np.load(folder/'corrected-native.npz'));aligned=dict(np.load(folder/'aligned-native.npz'))
    np.testing.assert_allclose(aligned['root_positions'],native['root_positions']+record['origin_m'],atol=1e-7,rtol=0)
    for key in ('local_rot_mats','global_rot_mats','foot_contacts'):np.testing.assert_array_equal(aligned[key],native[key])
    np.testing.assert_allclose(aligned['posed_joints'],native['posed_joints']+record['origin_m'],atol=1e-7,rtol=0)
    guide=dict(np.load(original/'source/guide-motion.npz'));n=len(native['root_positions']);anchors=[0,1,n-2,n-1]
    anchor_position,anchor_rotation=anchor_errors(native['local_rot_mats'],native['root_positions'],guide,anchors)
    assert anchor_position<1e-5 and anchor_rotation<.001
    report=read(original/'input/report.json');frames=report['frames'];reference=RigAsset.load(original/'source/character.glb');source=RigAsset.load(original/'input/character.glb')
    profile=read(original/'source/rig-profile.json');skeleton=SOMASkeleton77();mapping,offset=resolve_profile(reference,profile);corrections,scale,_=calibration(reference,mapping,skeleton,profile.get('axis_alignment_xyzw'))
    inverse={node:skeleton.bone_order_names.index(role) for role,node in mapping.items()}
    def depth(node):return 0 if reference.parents[node]<0 else 1+depth(reference.parents[node])
    world=np.empty((n,len(reference.parents),4,4))
    for node in sorted(range(len(reference.parents)),key=depth):
        parent=reference.parents[node];pw=np.broadcast_to(np.eye(4),(n,4,4)) if parent<0 else world[:,parent]
        loc=np.repeat(local_matrix(reference.document['nodes'][node])[None],n,axis=0)
        if node in inverse:
            desired=aligned['global_rot_mats'][:,inverse[node]]@corrections[node]
            loc[:,:3,:3]=Rotation.from_matrix(np.linalg.inv(pw[:,:3,:3])@desired).as_matrix()
            if node==mapping['Hips']:loc[:,:3,3]=(np.linalg.inv(pw)@np.c_[aligned['root_positions']*scale+offset,np.ones(n)][:,:,None])[:,:3,0]
        world[:,node]=pw@loc
    unblended=RigAsset.load(folder/'unblended/character.glb');unblended_world,_=poses(unblended,n)
    unblended_error=float(np.abs(unblended_world-world).max());assert unblended_error<1e-5
    before,before_sampler=poses(source,frames);a,b,k=(record['edit'][x] for x in ('start_frame','last_frame','blend_frames'))
    before_local=localize(before,source.parents);new_local=localize(world,source.parents);expected=before_local.copy();envelope=np.zeros(frames)
    for i in range(n):
        u=min(1.,max(0.,(min(i,n-1-i)-1)/(k-2)));w=u*u*(3-2*u);f=a+i;envelope[f]=w
        expected[f,:,:3,3]=(1-w)*before_local[f,:,:3,3]+w*new_local[i,:,:3,3]
        for node in range(len(source.parents)):
            expected[f,node,:3,:3]=Slerp([0,1],Rotation.from_matrix(np.array([before_local[f,node,:3,:3],new_local[i,node,:3,:3]])))([w]).as_matrix()[0]
    spliced=RigAsset.load(folder/'input/character.glb');spliced_world,_=poses(spliced,frames)
    splice_error=float(np.abs(localize(spliced_world,source.parents)-expected).max());assert splice_error<1e-5
    fixed=np.flatnonzero(envelope==0);preservation=float(np.abs(spliced_world[fixed]-before[fixed]).max());assert preservation<1e-5
    # Measure the unblended transferred target anchors before restoration by the splice.
    ids=list(mapping.values());anchor_rot=float(angle(unblended_world[anchors][:,ids,:3,:3],before[np.array(anchors)+a][:,ids,:3,:3]).max())
    anchor_root=float(np.linalg.norm(unblended_world[anchors,mapping['Hips'],:3,3]-before[np.array(anchors)+a,mapping['Hips'],:3,3],axis=-1).max())
    anchor_positions=float(np.linalg.norm(unblended_world[anchors][:,ids,:3,3]-before[np.array(anchors)+a][:,ids,:3,3],axis=-1).max())
    stages={}
    spec=read(folder/'spec.json');annotations=read(folder/'input/contacts.json')
    for label,path in [('source',original/'input/character.glb'),('raw_splice',folder/'raw-splice/character.glb'),('pose_splice',folder/'input/character.glb'),('candidate',folder/'candidate/character.glb')]:
        rig=RigAsset.load(path);w,sampler=poses(rig,frames);vertices=np.array([rig.vertices(m) for m in w]);floor=np.maximum(0,-vertices[:,:,1].min(axis=1));half=np.array([max(0.,-float(rig.vertices(sampler.sample((f+.5)/30))[:,1].min())) for f in range(frames-1)])
        rot=localize(w,rig.parents)[:,:,:3,:3];steps=angle(rot[:-1],rot[1:]);root=w[:,report['root_node'],:3,3];speed=np.linalg.norm(np.diff(root,axis=0),axis=-1)*30
        stages[label]=dict(floor_depth_max_m=float(floor.max()),editable_floor_depth_max_m=float(floor[envelope>0].max()),half_frame_floor_depth_max_m=float(half.max()),local_rotation_step_max_degrees=float(steps.max()),edit_edge_max_degrees=float(steps[max(0,a-1):a+k].max()),return_edge_max_degrees=float(steps[b-k:min(frames-1,b+1)].max()),max_root_speed_m_s=float(speed.max()),max_root_acceleration_m_s2=float(np.linalg.norm(np.diff(root,n=2,axis=0),axis=-1).max()*900),preserved_world_error=float(np.abs(w[fixed]-before[fixed]).max()))
        feet={}
        for side,patch in spec['patches'].items():
            active=np.zeros(frames,bool)
            for interval in annotations['intervals']:
                if interval['joint'] in (side+'Foot',side+'ToeBase'):active[interval['start_frame']:interval['end_frame_exclusive']]=True
            velocity=np.linalg.norm(np.diff(vertices[:,patch['vertices']].mean(axis=1)[:,[0,2]],axis=0),axis=-1)*30
            support=velocity[active[:-1]&active[1:]]
            feet[side]=dict(predicted_support_steps=len(support),predicted_support_horizontal_speed_p95_m_s=float(np.percentile(support,95)) if len(support) else None,scope='Same spliced prediction mask across stages for matched comparison; source-stage mask is not a source contact assertion.')
        stages[label]['feet']=feet
        if label!='source':assert stages[label]['preserved_world_error']<1e-5
    verify_clearance(folder)
    result=dict(case=record['case'],job=record['job'],corrected_native_anchor_position_error_m=anchor_position,corrected_native_anchor_rotation_error_degrees=anchor_rotation,unblended_transfer_oracle_error=unblended_error,splice_oracle_error=splice_error,unblended_anchor_mapped_rotation_error_degrees=anchor_rot,unblended_anchor_root_error_m=anchor_root,unblended_anchor_mapped_position_error_m=anchor_positions,stages=stages,scope='Shared established calibration, independent hierarchy and per-node SciPy Slerp assembly. Native anchors separate from target anatomy; source preserved. Surface solver bounds separately verified. Not animator/contact/dynamics approval.')
    save(folder/'transfer-verification.json',result);print(record['case'],result,flush=True);return result


def verify(out):
    out=Path(out);results=[];manifest=[]
    for case in read(out/'design.json')['cases']:
        folder=out/case;results.append(verify_case(folder))
        n=read(folder/'candidate/report.json')['frames']
        for stage in ('raw-splice','input','candidate','unblended'):
            path=folder/stage/'character.glb';frames=n if stage!='unblended' else len(np.load(folder/'corrected-native.npz')['root_positions'])
            manifest.append(dict(id=case+'-'+stage,path=path.relative_to(out).as_posix(),sha256=sha256(path),frames=frames,fps=30))
    save(out/'verification.json',dict(cases=results,quality_approved=False,created_at=now()));save(out/'manifest.json',dict(cases=manifest))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);verify(p.parse_args().output)
