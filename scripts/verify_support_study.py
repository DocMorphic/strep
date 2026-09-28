"""Independent artifact, provenance and rig-invariant checks for support fitting."""
import zipfile
import hashlib
import numpy as np
from strep import ROOT,read,save,sha256,now
from inspect_motion import skeleton_metadata


def verify():
    folder=ROOT/'reports/support-contact-v1';summary=read(folder/'summary.json')
    names,parents,_=skeleton_metadata(77);records=[]
    for trial in summary['trials']:
        path=folder/'takes'/trial['id']
        for file,digest in trial['hashes'].items():assert sha256(path/file)==digest
        old=trial['previous_trial'];source=next(ROOT/'reports'/s/'takes'/trial['id'] for s in ['body-contact-v1','body-contact-holdout-v1'] if (ROOT/'reports'/s/'takes'/trial['id']).exists())
        for part in ['raw','limb','previous']:
            for file in (path/part).iterdir():
                original=source/file.name if part=='previous' else source/part/file.name
                assert sha256(file)==sha256(original)
        candidate=dict(np.load(path/'motion.npz'));raw=dict(np.load(path/'raw/motion.npz'))
        for v in candidate.values():assert np.isfinite(v).all()
        np.testing.assert_array_equal(candidate['root_positions'][:,[0,2]],raw['root_positions'][:,[0,2]])
        np.testing.assert_array_equal(candidate['foot_contacts'],raw['foot_contacts'])
        np.testing.assert_allclose(candidate['global_rot_mats'][:,0],raw['global_rot_mats'][:,0],atol=1e-6)
        bone_error=0.
        for j,p in enumerate(parents):
            if p<0:continue
            a=np.linalg.norm(raw['posed_joints'][:,j]-raw['posed_joints'][:,p],axis=-1)
            b=np.linalg.norm(candidate['posed_joints'][:,j]-candidate['posed_joints'][:,p],axis=-1)
            bone_error=max(bone_error,float(abs(a-b).max()))
        assert bone_error<4e-6
        for key in ['local_rot_mats','global_rot_mats']:
            r=candidate[key];np.testing.assert_allclose(r@r.swapaxes(-1,-2),np.broadcast_to(np.eye(3),r.shape),atol=2e-6)
        track=read(path/'root-motion.json');np.testing.assert_array_equal(track['positions_m'],candidate['root_positions'])
        recipe=read(path/'recipe.json')
        np.testing.assert_allclose(candidate['root_positions'][:,1]-raw['root_positions'][:,1],recipe['root_lift_m'],atol=2e-7)
        assert 'smooth_root_pos' not in candidate
        with zipfile.ZipFile(path/'animation-pack.zip') as z:
            expected={p.name for p in path.iterdir() if p.is_file() and p.suffix!='.zip'}|{'LICENSE.txt'}
            assert set(z.namelist())==expected
            for name in z.namelist():
                original=ROOT/'vendor/kimodo/LICENSE' if name=='LICENSE.txt' else path/name
                assert hashlib.sha256(z.read(name)).hexdigest()==sha256(original)
        records.append(dict(id=trial['id'],max_bone_length_error_m=bone_error,flags=trial['flags'],
            old_flags=old['flags'],old_peak_added_speed_m_s=old['floor_correction']['distortion']['added_joint_velocity_m_s']['max'],
            new_peak_added_speed_m_s=trial['floor_correction']['distortion']['added_joint_velocity_m_s']['max']))
    for record in summary['unchanged']:
        assert sha256(ROOT/'reports'/record['collection']/'takes'/record['id']/'motion.npz')==record['motion_sha256']
    # One exact repeat against the independently run prototype, same frozen solver.
    proto=dict(np.load(ROOT/'reports/support-contact-prototype-v2/get-up-seed-11.npz'))
    repeated=dict(np.load(folder/'takes/get-up-seed-11/motion.npz'))
    assert proto.keys()==repeated.keys() and all(np.array_equal(proto[k],repeated[k]) for k in proto)
    result=dict(verified_at=now(),trials=records,unchanged_clips=len(summary['unchanged']),exact_repeat_seed_11=True,
                verification_sha256=sha256(__file__),scope='Artifact integrity and numerical rig checks; not semantic realism or engine import.')
    save(folder/'verification.json',result);print(result)


if __name__=='__main__':verify()
