"""Full-duration development transfer of the earlier five-frame box fixture.

Keeps all original object keys, contacts and limits; changes target geometry and
applies the same declared wrist perturbation over the complete source motion.
"""
import argparse
import copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256
from floor_contact import reconstruct
from inspect_motion import skeleton_metadata,validate_motion
from object_floor_placement import floor_lower_bound


def prepare(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'reports') or output.exists():raise ValueError('Fresh local report directory required')
    scene_path=ROOT/'reports/scene-regions-development-v1/authored-scene.json'
    short_path=ROOT/'reports/region-fit-box-pilot-v1/scene.json'
    scene=read(scene_path);short=read(short_path);source_path=ROOT/scene['actors']['A']['motion']
    if sha256(source_path)!=scene['actors']['A']['source_sha256']:raise ValueError('Original motion changed')
    source=dict(np.load(source_path,allow_pickle=False));names,parents,_=skeleton_metadata(77)
    local=source['local_rot_mats'].astype(float)
    for hand in ['LeftHand','RightHand']:
        local[:,names.index(hand)]=local[:,names.index(hand)]@Rotation.from_euler('x',2,degrees=True).as_matrix()
    motion=reconstruct(source,local,parents);motion.pop('smooth_root_pos',None);validate_motion(motion,30)
    condition=copy.deepcopy(scene);condition['id']='full-region-box-transfer-v1'
    condition['objects']['box']['geometry']=copy.deepcopy(short['objects']['box']['geometry'])
    condition['review_note']='Full-duration box transfer development condition. Same object tracks/region targets; not a newly generated or held-out action. All failures remain unapproved.'
    floor=floor_lower_bound(condition['objects']['box'],scene['frame_count'])
    output.mkdir(parents=True);np.savez(output/'input-motion.npz',**motion)
    condition['actors']['A']['motion']=(output/'input-motion.npz').relative_to(ROOT).as_posix()
    condition['actors']['A']['source_sha256']=sha256(output/'input-motion.npz')
    save(output/'scene.json',condition)
    save(output/'fixture.json',dict(source_scene_sha256=sha256(scene_path),source_motion_sha256=sha256(source_path),
        short_box_scene_sha256=sha256(short_path),scene_sha256=sha256(output/'scene.json'),
        input_motion_sha256=sha256(output/'input-motion.npz'),preparer_sha256=sha256(__file__),
        frames=scene['frame_count'],contacts_unchanged=condition['contacts']==scene['contacts'],
        object_keys_unchanged=all(condition['objects'][name]['keyframes']==obj['keyframes'] for name,obj in scene['objects'].items()),
        source_relative_budget_reference='Full perturbed source clip, not the five-frame repair or older V13 reference',
        perturbation='Both local wrist X rotations +2 degrees at every original frame; no resampling or repeated-frame padding',
        object_floor_bound=floor,quality_approved=False,
        scope='180-frame development transfer including approach, grasp and release. Conservative object-floor bound is diagnostic and can fail; actor repair cannot fix a prescribed object trajectory. Not independent action coverage or held-out release evidence.'))
    print(dict(scene=str(output/'scene.json'),frames=scene['frame_count'],object_floor_lower_bound_m=floor['lower_bound_m']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);prepare(p.parse_args().output)
