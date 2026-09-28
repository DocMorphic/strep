"""Verify saved scene candidates against source files and decoded GLB skin points."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from floor_contact import Surface
from build_soma_preview import ASSET
from gltf_tools import read_glb,sample_animation
from inspect_motion import skeleton_metadata
from scene_constraints import pose


def verify(root):
    root=Path(root).resolve();summary=read(root/'summary.json');skin=dict(np.load(ASSET));surface=Surface(skin)
    names,parents,_=skeleton_metadata(77);records=[]
    for trial in summary['trials']:
        scene=read(root/trial['id']/'candidate.json')['scene'];before=read(root/trial['id']/'authored-scene.json')
        after=read(root/trial['id']/'after.json');by_id={c['id']:c for c in after['contacts']}
        for actor,entry in scene['actors'].items():
            path=ROOT/entry['motion'];raw_path=ROOT/before['actors'][actor]['motion'];folder=path.parent
            raw=dict(np.load(raw_path));motion=dict(np.load(path));base=dict(np.load(folder/'limb-motion.npz'));previous=dict(np.load(folder/'previous-motion.npz'))
            assert sha256(raw_path)==trial['actors'][actor]['source_sha256']==sha256(folder/'raw-motion.npz')
            assert sha256(path)==entry['source_sha256']
            np.testing.assert_array_equal(motion['root_positions'][:,[0,2]],raw['root_positions'][:,[0,2]])
            # Floor preparation orthonormalizes matrices through SciPy Rotation;
            # report floating-point differences instead of claiming byte identity.
            heading_error=float(np.abs(motion['local_rot_mats'][:,0]-raw['local_rot_mats'][:,0]).max())
            assert heading_error<1e-6
            np.testing.assert_array_equal(motion['foot_contacts'],raw['foot_contacts'])
            fingers=[i for i,n in enumerate(names) if 'Hand' in n and n not in ['LeftHand','RightHand']]
            finger_error=float(np.abs(motion['local_rot_mats'][:,fingers]-raw['local_rot_mats'][:,fingers]).max())
            assert finger_error<1e-6
            lengths=lambda m:np.linalg.norm(m['posed_joints'][:,1:]-m['posed_joints'][:,np.array(parents[1:])],axis=-1)
            np.testing.assert_allclose(lengths(motion),lengths(raw),atol=2e-6,rtol=0)
            root_track=read(folder/'root-motion.json');np.testing.assert_array_equal(root_track['positions_m'],motion['root_positions'])
            lift=motion['root_positions'][:,1]-base['root_positions'][:,1]
            relative=previous['local_rot_mats'].transpose(0,1,3,2)@motion['local_rot_mats']
            angle=np.rad2deg(np.linalg.norm(Rotation.from_matrix(relative.reshape(-1,3,3)).as_rotvec(),axis=1)).max()
            assert lift.min()>=-2e-7 and lift.max()<=summary['config']['max_root_lift_m']+2e-7
            assert angle<=summary['config']['max_rotation_degrees']+1e-4
            doc,binary=read_glb(folder/'soma.glb');p,r=pose(entry['transform']);error=0.;checked=0
            for c in scene['contacts']:
                if c['actor']!=actor:continue
                target=np.array(after['contact_tracks'][c['id']]['target_world_m']);expected=np.array(after['contact_tracks'][c['id']]['actual_world_m'])
                for frame in range(c['start_frame'],c['end_frame']+1):
                    glb=sample_animation(doc,binary,0,frame)[1:78]
                    native=surface.vertices(glb[:,:3,:3],glb[:,:3,3],[c['effector']['surface_vertex']])[0]
                    world=r@native+p;error=max(error,float(np.linalg.norm(world-expected[frame])));checked+=1
                    measured=float(np.linalg.norm(world-target[frame]))
                    assert abs(measured-after['contact_tracks'][c['id']]['errors_m'][frame])<1e-5
            assert error<1e-5
            targets=read(folder/'evaluation.json')['target_evaluation']['intervals']
            compilation=read(folder/'compilation.json')['contacts']
            for contact,interval in zip(compilation,targets):
                # This runner supplies one interval per hand in insertion order.
                assert contact['region']==interval['region']
                assert abs(by_id[contact['contact_id']]['max_interval_error_m']-interval['max_error_m'])<1e-6
            records.append(dict(scene=trial['id'],actor=actor,raw_unchanged=True,root_xz_exact=True,
                max_root_rotation_element_delta=heading_error,max_finger_rotation_element_delta=finger_error,
                predicted_foot_labels_unchanged=True,rigid_bones_verified=True,root_track_exact=True,
                glb_contact_samples_checked=checked,max_glb_contact_error_m=error,
                rotation_delta_degrees=float(angle),root_lift_range_m=[float(lift.min()),float(lift.max())]))
    result=dict(verified_at=now(),verifier_sha256=sha256(__file__),actors=records,
        scope='Artifact/coordinate integrity and edit budget verification, not successful interaction or realism approval.')
    save(root/'verification.json',result);print('Verified',len(records),'actor exports')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);args=parser.parse_args();verify(args.report)
