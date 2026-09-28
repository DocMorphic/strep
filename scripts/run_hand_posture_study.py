"""Author the reference hand pose on the preserved high-five development pair."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from rig_asset import RigAsset
from verify_rig_clearance import localize
from hand_posture import run as author


def run(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve prior study')
    parent=ROOT/'reports/breadth-partners-v2';source=parent/'partner_interaction-left-high-five-seed-1301/scene.json'
    scene=copy.deepcopy(read(source)['scene']);output.mkdir(parents=True);skin=np.load(ASSET,allow_pickle=False);manifest=dict(scenes=[],assets={})
    save(output/'request.json',dict(at=now(),source_scene=str(source),source_scene_sha256=sha256(source),
        method='Author mesh default-reference local finger rotations over frames60-90, full at75. This is not an anatomically reviewed open-hand pose.',quality_approved=False))
    for name in ['A','B']:
        entry=scene['actors'][name];glb=parent/entry['preview_glb'];rig=RigAsset.load(glb);names={n.get('name'):i for i,n in enumerate(rig.document['nodes'])}
        source_motion=ROOT/entry['motion']
        if sha256(source_motion)!=entry['source_sha256']:raise ValueError('Raw source changed')
        targets=[]
        for label,node in names.items():
            if label.startswith('LeftHand') and label[-1:].isdigit():
                rest=np.linalg.inv(rig.reference[rig.parents[node]])@rig.reference[node]
                targets.append(dict(node=node,rotation_xyzw=Rotation.from_matrix(rest[:3,:3]).as_quat().tolist()))
        recipe=dict(schema='strep-hand-posture-v1',source_glb_sha256=sha256(glb),frames=scene['frame_count'],fps=30,hand_roots=[names['LeftHand']],
            poses=[dict(id='reference-hand',hand_root=names['LeftHand'],targets=targets,start_frame=60,full_start_frame=75,full_end_frame=75,end_frame=90,strength=1.)],
            limits=dict(rotation_degrees=60,correction_step_degrees=5),provenance='Authored target from the original mesh default-reference pose; anatomical and contact quality unreviewed. Body motion remains original.')
        folder=output/name;actual=author(glb,recipe,folder);motion=dict(np.load(source_motion,allow_pickle=False));raw={k:v.copy() for k,v in motion.items()}
        order=[names[str(n)] for n in skin['rig_joint_names']];ordered=actual[:,order]
        motion['posed_joints']=ordered[:,:,:3,3].copy();motion['global_rot_mats']=ordered[:,:,:3,:3].copy();local=localize(actual,rig.parents)
        for target in targets:
            node=target['node'];index=list(map(str,skin['rig_joint_names'])).index(rig.document['nodes'][node]['name']);motion['local_rot_mats'][:,index]=local[:,node,:3,:3]
        for k in ['root_positions','smooth_root_pos','foot_contacts','global_root_heading']:assert np.array_equal(motion[k],raw[k])
        assert all(motion[k].shape==raw[k].shape for k in raw)
        np.savez_compressed(folder/'motion.npz',**motion);shutil.copyfile(source_motion,folder/'input.npz')
        entry.update(motion=(folder/'motion.npz').relative_to(ROOT).as_posix(),source_sha256=sha256(folder/'motion.npz'),preview_glb=f'{name}/character.glb')
        manifest['assets'][entry['preview_glb']]=dict(sha256=sha256(folder/'character.glb'))
    scene['id']='authored-reference-hand-high-five';save(output/'scene.json',dict(scene=scene));manifest['scenes']=[dict(id=scene['id'],variants={'palm':'scene.json'})]
    save(output/'manifest.json',manifest);shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
    from run_godot_scene_import import run as engine
    engine(output,output/'engine-audit');save(output/'pipeline.json',dict(status='complete',quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
