"""Decode reserved rig fixtures and verify geometry, mappings and static engine evidence."""
import argparse
from pathlib import Path
import numpy as np
from rig_asset import RigAsset,array
from retarget_rig import resolve_profile
from rig_clip_import import AnimationSampler
from strep import ROOT,now,read,save,sha256


def run(study):
    dest=study/'verification.json'
    if dest.exists():raise ValueError('Preserve earlier fixture verification')
    construction=read(study/'construction.json');manifest=read(study/'manifest.json')
    proofs=read(study/'engine/verification.json')['checks']
    expected={r['id']:r for r in manifest['cases']}
    if set(expected)!={r['id'] for r in construction['rows']} or len(expected)!=3:
        raise ValueError('Incomplete reserved fixture set')
    if {(r['id'],r['frames'],r['source_sha256']) for r in proofs}!={(n,2,r['sha256']) for n,r in expected.items()}:
        raise ValueError('Missing actual two-pose import evidence')
    inputs=[study/'construction.json',study/'manifest.json',study/'engine/verification.json'];rows=[]
    for row in construction['rows']:
        folder=study/'rigs'/row['id'];source=Path(row['source']);character=folder/'character.glb'
        for p,h in [(source,row['source_sha256']),(character,row['character_sha256']),(folder/'rig-profile.json',row['profile_sha256'])]:
            if sha256(p)!=h:raise ValueError('Fixture or source changed')
            inputs.append(p)
        for name,h in row['attachments'].items():
            if sha256(folder/name)!=h:raise ValueError('Source attribution/license bytes changed')
            inputs.append(folder/name)
        original=RigAsset.load(source);rig=RigAsset.load(character);profile=read(folder/'rig-profile.json')
        if profile['character_sha256']!=sha256(character):raise ValueError('Profile targets another character')
        mapping,offset=resolve_profile(rig,profile)
        np.testing.assert_array_equal(rig.parents,original.parents);np.testing.assert_array_equal(rig.joints,original.joints)
        scale=np.array(row['scale_xyz']);before=original.vertices(original.reference);after=rig.vertices(rig.reference)
        # Compare ground-relative coordinates without trusting the builder's shift.
        target=before*scale;target[:,1]-=target[:,1].min()
        geometry_error=float(np.linalg.norm(after-target,axis=1).max())
        expected_joints=original.reference[:,:3,3]*scale
        expected_joints[:,1]-=(before*scale)[:,1].min()
        joint_error=float(np.linalg.norm(rig.reference[:,:3,3]-expected_joints,axis=1).max())
        rotation_error=float(abs(rig.reference[:,:3,:3]-original.reference[:,:3,:3]).max())
        if max(geometry_error,joint_error,rotation_error)>1e-5:raise ValueError('Decoded proportional geometry differs')
        normal_error=0.
        for old,p in zip(original.primitives,rig.primitives):
            np.testing.assert_array_equal(old['joints'],p['joints']);np.testing.assert_array_equal(old['weights'],p['weights'])
            primitive=rig.document['meshes'][rig.document['nodes'][p['node']]['mesh']]['primitives'][p['primitive']]
            normals=array(rig.document,rig.binary,primitive['attributes']['NORMAL'])
            normal_error=max(normal_error,float(abs(np.linalg.norm(normals,axis=1)-1).max()))
        if normal_error>1e-5:raise ValueError('Invalid normal lengths')
        static=Path(expected[row['id']]['path'])
        if sha256(static)!=expected[row['id']]['sha256']:raise ValueError('Static import clip changed')
        inputs.append(static);animated=RigAsset.load(static);sampler=AnimationSampler(animated.document,animated.binary,0)
        pose_error=max(float(abs(sampler.sample(f/30)-rig.reference).max()) for f in range(2))
        if pose_error>1e-5:raise ValueError('Import check does not represent fixture neutral pose')
        rows.append(dict(id=row['id'],mapped_roles=len(mapping),skin_joints=len(rig.joints),
            geometry_error_m=geometry_error,joint_position_error_m=joint_error,rotation_basis_error=rotation_error,
            normal_unit_error=normal_error,static_pose_error=pose_error,
            source_animation_count=len(original.document.get('animations',[])),reserved_animation_count=len(rig.document.get('animations',[])),
            engine_static_actor_frames=2,motion_quality_approved=False))
    save(dest,dict(at=now(),inputs={str(p):sha256(p) for p in inputs},implementation_sha256=sha256(Path(__file__)),
        rows=rows,engine_static_actor_frames=6,rig_topology_families=1,reserved_action_trials=0,
        quality_approved=False,human_review=None,scope='Construction-only validation. Static engine checks and neutral humanoid mappings do not establish retargeted motion, deformation quality, independent rig-family generalization or release approval.'))
    print(rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path)
    run(parser.parse_args().study.resolve())
