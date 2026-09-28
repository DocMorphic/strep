"""Verify protected motion arrays and contact after model representation conversion.

This is target feasibility, never evidence of a usable animation.
"""
import argparse
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from kimodo.skeleton import SOMASkeleton30, SOMASkeleton77
from build_soma_preview import ASSET
from floor_contact import Surface
from plan_paired_contact_target import inspect


def protected(original, candidate, deltas, rotation):
    if set(original)!=set(candidate):raise ValueError('Motion fields changed')
    changed={'root_positions','posed_joints','smooth_root_pos'}
    for key in original:
        expected=original[key].copy()
        if key in changed:
            for frame,delta in deltas.items():expected[frame]+=np.asarray(delta)@rotation
        if not np.array_equal(expected,candidate[key]):raise ValueError('Unexpected motion change: '+key)


def run(plan):
    plan=Path(plan).resolve();destination=plan/'model-representation-verification.json'
    if destination.exists():raise ValueError('Preserve previous verification')
    if read(plan/'pipeline.json')['status']!='complete':raise ValueError('No successful authored target to verify')
    request=read(plan/'request.json');proof=read(plan/'verification.json');study=Path(request['source_study'])
    if proof['request_sha256']!=sha256(plan/'request.json') or proof['trials_sha256']!=sha256(plan/'trials.json'):raise ValueError('Changed planning evidence')
    if request['source_protocol_sha256']!=sha256(study/'protocol.json'):raise ValueError('Changed source protocol')
    for name,digest in request['implementation'].items():
        if sha256(plan/'implementation'/name)!=digest:raise ValueError('Changed implementation snapshot')
    spec=read(study/'protocol.json');patchfile=Path(spec['guide_export'])/'refinement/palm-region.json'
    if sha256(ASSET)!=request['skin_sha256'] or sha256(patchfile)!=request['patch_sha256']:raise ValueError('Changed surface inputs')
    scene=read(plan/'scene.json')['scene'];skin=dict(np.load(ASSET,allow_pickle=False));surface=Surface(skin)
    patches=read(patchfile);small,full=SOMASkeleton30(),SOMASkeleton77();points=[];actors=[]
    with threadpool_limits(limits=1):
        for name in ['A','B']:
            entry=scene['actors'][name];source=request['source_guides'][name];sourcepath=ROOT/source['path'];path=ROOT/entry['motion']
            if sha256(path)!=entry['source_sha256'] or sha256(sourcepath)!=source['sha256']:raise ValueError('Changed target arrays')
            original=dict(np.load(sourcepath,allow_pickle=False));motion=dict(np.load(path,allow_pickle=False))
            delta={a['frame']:a['world_root_delta_m'] for a in proof['anchors'] if a['actor']==name}
            if set(delta)!=set(request['guide_frames']):raise ValueError('Incomplete anchor population')
            if any(np.any(np.abs(d)>np.array(request['root_component_limits_m'])+1e-10) for d in delta.values()):raise ValueError('Exceeded root budget')
            rot=Rotation.from_quat(entry['transform']['rotation_xyzw']).as_matrix();shift=np.asarray(entry['transform']['translation_m'])
            protected(original,motion,delta,rot)
            local=torch.tensor(motion['local_rot_mats'],dtype=torch.float32)
            restored=small.to_SOMASkeleton77(small.from_SOMASkeleton77(local))
            r,p,_=full.fk(restored,torch.tensor(motion['root_positions'],dtype=torch.float32));floors=[]
            for frame in request['guide_frames']:
                vertices=surface.vertices(r[frame].numpy(),p[frame].numpy())@rot.T+shift
                floors.append(dict(frame=frame,depth_m=max(0.,-float(vertices[:,1].min()))))
                if frame==request['event_frame']:points.append(vertices)
            actors.append(dict(actor=name,source_sha256=sha256(sourcepath),target_sha256=sha256(path),protected_arrays_passed=True,roundtrip_anchor_floors=floors))
        geometry=inspect(points,[patches['A'],patches['B']],skin['faces'],scene['contacts'][0]['effector']['surface_vertex'])
    passed=geometry['passed'] and all(f['depth_m']<=.005 for a in actors for f in a['roundtrip_anchor_floors'])
    result=dict(at=now(),request_sha256=sha256(plan/'request.json'),planning_proof_sha256=sha256(plan/'verification.json'),scene_sha256=sha256(plan/'scene.json'),
        verifier_sha256=sha256(__file__),geometry_implementation_sha256=sha256(ROOT/'scripts/plan_paired_contact_target.py'),actors=actors,roundtrip_geometry=geometry,
        target_screens_passed=passed,quality_approved=False,playback_ready=False,
        scope='Exact expected root edits, all protected arrays, unchanged frames, declared bounds and exact SOMA77-to30-to77 target conversion. Independent of generation; shared geometry diagnostic. No motion, continuous collision, physical or animator approval.')
    save(destination,result);print({'target_screens_passed':passed,'quality_approved':False},flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan',type=Path);run(p.parse_args().plan)
