"""Reload exported GLBs to verify target-contact edits and root sidecars."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read,save,sha256,now
from target_rig_contact import RigAsset,baseline,audit


def run(study):
    study=Path(study).resolve();manifest=read(study/'manifest.json');source=Path(manifest['source_study']);checks=[]
    for item in manifest['cases']:
        folder=study/item['id'];spec=read(folder/'contact-spec.json');record=read(folder/'audit.json')
        src=source/item['id']/'character.glb';dst=folder/'character.glb'
        if sha256(src)!=spec['glb_sha256'] or sha256(dst)!=item['sha256'] or sha256(dst)!=record['glb_sha256']:
            raise ValueError('Changed GLB in preservation audit')
        rig=RigAsset.load(src);decoded=RigAsset.load(dst)
        before,_=baseline(rig,item['frames']);after,_=baseline(decoded,item['frames'])
        old_local=np.array([np.linalg.inv(before[:,p])@before[:,n] if p>=0 else before[:,n] for n,p in enumerate(rig.parents)]).transpose(1,0,2,3)
        new_local=np.array([np.linalg.inv(after[:,p])@after[:,n] if p>=0 else after[:,n] for n,p in enumerate(rig.parents)]).transpose(1,0,2,3)
        edited={e['node'] for e in spec['edit_joints'].values()}|{spec['root_node']}
        untouched=[n for n in range(len(rig.parents)) if n not in edited]
        nonroot=[n for n in range(len(rig.parents)) if n!=spec['root_node']]
        local_error=float(np.max(np.abs(old_local[:,untouched]-new_local[:,untouched])))
        translation_error=float(np.max(np.abs(old_local[:,nonroot,:3,3]-new_local[:,nonroot,:3,3])))
        root=read(folder/'root-motion.json');expected=after[:,spec['root_node']]
        position_error=float(np.max(np.abs(np.array(root['positions_m'])-expected[:,:3,3])))
        basis_error=float(np.max(np.abs(Rotation.from_quat(root['rotations_xyzw']).as_matrix()-expected[:,:3,:3])))
        np.testing.assert_allclose(root['times_s'],np.arange(item['frames'])/item['fps'],atol=1e-6)
        if max(local_error,translation_error,position_error,basis_error)>1e-5:
            raise ValueError('GLB changed unedited local pose, bone lengths or root sidecar')
        measured=audit(rig,spec,before,after,None,read(folder/'solver.json'))
        if measured['flags']!=record['flags']:raise ValueError('Export changed acceptance flags')
        for metric in ['floor_depth_max_m','patch_contact_error_max_m','patch_predicted_support_speed_p95_m_s']:
            if abs(measured['after'][metric]-record['after'][metric])>1e-5:raise ValueError('Export changed contact diagnostics')
        checks.append(dict(id=item['id'],frames=item['frames'],glb_sha256=sha256(dst),untouched_local_matrix_max_error=local_error,
            nonroot_translation_max_error_m=translation_error,root_sidecar_position_max_error_m=position_error,root_sidecar_basis_max_error=basis_error,
            exported_metrics=measured['after'],exported_flags=measured['flags']))
    save(study/'preservation-verification.json',dict(created_at=now(),checks=checks,implementation_sha256=sha256(__file__),
         scope='Reloaded actual GLB poses and evaluated full target mesh; unedited local pose, nonroot translations, root sidecar and acceptance flags. No human or physics approval.'))
    print(checks)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True)
    run(parser.parse_args().study)
