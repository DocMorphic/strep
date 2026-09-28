"""Independent decoded-mesh and pose-bound audit for clearance experiments."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def localize(world,parents):
    local=world.copy()
    for node,parent in enumerate(parents):
        if parent>=0:local[:,node]=np.linalg.inv(world[:,parent])@world[:,node]
    return local


def verify(folder):
    folder=Path(folder);request=read(folder/'request.json');spec=read(folder/'spec.json')
    envelope=np.asarray(request['envelope']);count=len(envelope);poses={};metrics={};samplers={};rigs={};surfaces={}
    for name in ('input','candidate'):
        rig=RigAsset.load(folder/name/'character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
        world=np.array([sampler.sample(float(np.float32(f/30))) for f in range(count)])
        vertices=np.array([rig.vertices(w) for w in world]);floor=np.maximum(0,-vertices[:,:,1].min(axis=1))
        half=np.array([max(0,-float(rig.vertices(sampler.sample((f+.5)/30))[:,1].min())) for f in range(count-1)])
        feet={};annotations=read(folder/'input/contacts.json')
        for side,patch in spec['patches'].items():
            points=vertices[:,patch['vertices']];heights=points[:,:,1].min(axis=1)
            error=np.abs(heights-np.asarray(request['targets_m'][side]));editable=envelope>0
            active=np.zeros(count,bool)
            for interval in annotations.get('intervals',[]):
                if interval['joint'] in (side+'Foot',side+'ToeBase'):active[interval['start_frame']:interval['end_frame_exclusive']]=True
            speed=np.linalg.norm(np.diff(points.mean(axis=1)[:,[0,2]],axis=0),axis=1)*30
            support=speed[active[:-1]&active[1:]]
            feet[side]=dict(height_error_max_m=float(error.max()),editable_height_error_max_m=float(error[editable].max()),editable_height_error_p95_m=float(np.percentile(error[editable],95)),minimum_height_m=float(heights.min()),centroid_speed_max_m_s=float(np.linalg.norm(np.diff(points.mean(axis=1),axis=0),axis=1).max()*30),predicted_support_horizontal_speed_p95_m_s=float(np.percentile(support,95)) if len(support) else None,predicted_support_steps=len(support),heights_m=heights.tolist())
        matrices=localize(world,rig.parents)[:,:,:3,:3]
        steps=np.degrees(Rotation.from_matrix((matrices[:-1].transpose(0,1,3,2)@matrices[1:]).reshape(-1,3,3)).magnitude())
        metrics[name]=dict(floor_depth_max_m=float(floor.max()),editable_floor_depth_max_m=float(floor[envelope>0].max()),frozen_floor_depth_max_m=float(floor[envelope==0].max()),floor_failed_frames=np.flatnonzero(floor>.005).tolist(),half_frame_floor_depth_max_m=float(half.max()),editable_half_frame_floor_depth_max_m=float(half[(envelope[:-1]>0)&(envelope[1:]>0)].max()),local_rotation_step_max_degrees=float(steps.max()),feet=feet)
        poses[name]=world;samplers[name]=sampler;rigs[name]=rig
        surfaces[name]=vertices
    before=poses['input'];after=poses['candidate'];rig=rigs['input'];root=spec['root_node']
    assert sha256(folder/'input/character.glb')==request['source_glb_sha256']
    preservation=float(np.abs(after[envelope==0]-before[envelope==0]).max());assert preservation<1e-5
    original=localize(before,rig.parents);changed=localize(after,rig.parents)
    shift=after[:,root,:3,3]-before[:,root,:3,3]
    horizontal=np.linalg.norm(shift[:,[0,2]],axis=1);vertical=np.abs(shift[:,1]);rootsteps=np.linalg.norm(np.diff(shift,axis=0),axis=1)
    assert np.all(horizontal<=spec['limits']['root_horizontal_m']*envelope+1e-6)
    assert np.all(vertical<=spec['limits']['root_vertical_m']*envelope+1e-6)
    assert rootsteps.max()<=spec['limits']['root_step_m']+1e-6
    edits={};allowed={root}|{e['node'] for e in spec['edit_joints'].values()}
    for role,entry in spec['edit_joints'].items():
        n=entry['node'];delta=original[:,n,:3,:3].transpose(0,2,1)@changed[:,n,:3,:3]
        angles=np.degrees(Rotation.from_matrix(delta).magnitude());steps=np.degrees(Rotation.from_matrix(delta[:-1].transpose(0,2,1)@delta[1:]).magnitude())
        assert np.all(angles<=entry['limit_degrees']*envelope+1e-4)
        assert steps.max()<=spec['limits']['joint_step_degrees']+1e-4
        edits[role]=dict(max_degrees=float(angles.max()),step_max_degrees=float(steps.max()))
    untouched=[n for n in range(len(rig.parents)) if n not in allowed]
    assert np.abs(original[:,untouched]-changed[:,untouched]).max()<1e-5
    assert np.abs(original[:,root,:3,:3]-changed[:,root,:3,:3]).max()<1e-5
    translations=[n for n in range(len(rig.parents)) if n!=root]
    assert np.abs(original[:,translations,:3,3]-changed[:,translations,:3,3]).max()<1e-5
    track=read(folder/'candidate/root-motion.json');assert np.max(np.abs(np.array(track['positions_m'])-after[:,root,:3,3]))<1e-5
    for name in ('contacts.json','timeline.json'):
        assert (folder/'input'/name).read_bytes()==(folder/'candidate'/name).read_bytes()
    surface_change={}
    for side,patch in spec['patches'].items():
        delta=(surfaces['candidate']-surfaces['input'])[:,patch['vertices']][:,:,[0,2]]
        surface_change[side]=dict(horizontal_vertex_edit_max_m=float(np.linalg.norm(delta,axis=2).max()),horizontal_vertex_velocity_change_max_m_s=float(np.linalg.norm(np.diff(delta,axis=0),axis=2).max()*30))
    result=dict(created_at=now(),verifier_sha256=sha256(__file__),job=request['job'],checks_passed=True,source_sha256=request['source_glb_sha256'],candidate_sha256=sha256(folder/'candidate/character.glb'),metrics=metrics,preserved_frames=int((envelope==0).sum()),preserved_world_matrix_max_error=preservation,changes=dict(root_horizontal_max_m=float(horizontal.max()),root_vertical_max_m=float(vertical.max()),root_step_max_m=float(rootsteps.max()),joints=edits,foot_surfaces=surface_change),fixed_frames_prove_whole_clip_floor_infeasible=metrics['input']['frozen_floor_depth_max_m']>.005,quality_approved=False,source_model_guides_passed=request['source_model_guides_passed'],scope='Actual decoded GLB all vertices and half frames; unchanged outside envelope, per-frame edit limits, adjacent geodesic/root bounds, unedited transforms and metadata. Height fit does not prove planted support, action correctness or naturalness.')
    save(folder/'verification.json',result)
    print({k:{m:v for m,v in val.items() if m!='feet'} for k,val in metrics.items()},flush=True)
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);verify(p.parse_args().folder)
