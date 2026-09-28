"""Independent decoded per-joint audit plus existing root/contact preservation."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from verify_repaired_root_release import run as preservation_audit


def angles(path,nodes,count,fps):
    rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
    world=np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)])
    local=localize(world,rig.parents)[:,nodes,:3,:3]
    relative=local[:-1].transpose(0,1,3,2)@local[1:]
    return Rotation.from_matrix(relative.reshape(-1,3,3)).magnitude().reshape(count-1,len(nodes))


def run(folder,output):
    if output.exists():raise ValueError('Preserve previous audit')
    output.mkdir(parents=True);preservation_audit(folder,output/'preservation')
    base=read(output/'preservation/completion.json');request=read(folder/'request.json');spec=read(folder/'take/spec.json')
    angular=read(folder/'envelope.json')['angular'];source=Path(request['source']);nodes=[j['node'] for j in spec['edit_joints'].values()]
    if nodes!=angular['nodes']:raise ValueError('Joint order changed')
    paths=[source/'take/input/character.glb',Path(request['prior'])/'candidate/character.glb',source/'take/candidate/character.glb',folder/'take/candidate/character.glb']
    tracks=[angles(path,nodes,spec['frames'],spec['fps']) for path in paths]
    reference=np.maximum(tracks[0].max(axis=0),tracks[1].max(axis=0))+np.radians(1e-5)
    expected=np.maximum(tracks[2],reference[None]);np.testing.assert_array_equal(reference,angular['reference_global_caps_radians']);np.testing.assert_array_equal(expected,angular['safety_caps_radians'])
    caps=2*np.sin(expected/2);length=2*np.sin(tracks[3]/2);margin=(caps**2-length**2)/np.maximum(caps**2,1e-6)
    target=angular['target'];value=tracks[3][target['end_frame']-1,target['joint_index']]
    checks=dict(**base['checks'],original_comparisons_preserved=not base['failed_full_checks'],all_angular_safety_caps=bool(np.isfinite(margin).all() and margin.min()>=-1e-8))
    joints=[dict(role=role,node=node,raw_max_degrees=float(np.degrees(tracks[0][:,j]).max()),prior_max_degrees=float(np.degrees(tracks[1][:,j]).max()),source_max_degrees=float(np.degrees(tracks[2][:,j]).max()),
        candidate_max_degrees=float(np.degrees(tracks[3][:,j]).max()),reference_cap_degrees=float(np.degrees(reference[j])),original_joint_peak_passed=bool(tracks[3][:,j].max()<=reference[j]),
        peak_end_frame=int(tracks[3][:,j].argmax()+1)) for j,(role,node) in enumerate(zip(spec['edit_joints'],nodes))]
    result=dict(at=now(),completion_sha256=sha256(folder/'completion.json'),implementation_sha256=sha256(__file__),preservation_audit_sha256=sha256(output/'preservation/completion.json'),
        decoded_audit=base['decoded_audit'],decoded_audit_sha256=base['decoded_audit_sha256'],all_repaired_root_checks_passed=base['all_repaired_root_checks_passed'],
        checks=checks,all_preservation_checks_passed=all(checks.values()),minimum_angular_normalized_margin=float(margin.min()),target=target,target_degrees=float(np.degrees(value)),target_passed=bool(value<=target['limit_radians']),
        joints=joints,all_joint_peak_comparisons_passed=all(j['original_joint_peak_passed'] for j in joints),engine_actor_frames=base['engine_actor_frames'],files={str(p):sha256(p) for p in paths},quality_approved=False,
        scope='Fresh exported local relative rotation angles for every edited joint and every frame edge. New per-joint development comparison; no physiological limit, human judgement or retroactive old-study approval.')
    save(output/'completion.json',result);print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder.resolve(),a.output.resolve())
