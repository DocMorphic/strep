"""Replay bounded path parameters without importing the fitting objective."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def verify(study,patch,problem,source):
    study,patch=Path(study).resolve(),Path(patch).resolve()
    protocol,result=read(patch/'protocol.json'),read(patch/'result.json')
    prior=read(study/'protocol.json')
    if ROOT/protocol['path_input']!=study or result['status']!='complete':raise ValueError('Completed matching path input required')
    for name,key in [('protocol.json','protocol_sha256'),('motion.npz','candidate_sha256'),('recipe.json','recipe_sha256')]:
        if sha256(patch/name)!=result[key]:raise ValueError('Path artifact changed')
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Path input changed')
    for name,digest in protocol['implementation'].items():
        if sha256(patch/'implementation'/name)!=digest:raise ValueError('Path snapshot changed')
    for name in ['source-motion.npz','source.glb','authored-scene.json','original-scene.json']:
        if sha256(patch/name)!=sha256(study/name):raise ValueError('Path changed source or scene')
    left,right=prior['edited_interval'];start,end=prior['projection_interval']
    windows=[list(range(left+1,start)),list(range(end+1,right))]
    assert protocol['path_windows']==windows and [r['frames'] for r in result['windows']]==windows
    assert read(patch/'recipe.json')['windows']==result['windows']
    arms=[problem.names.index(s+p) for s in ['Left','Right'] for p in ['Shoulder','Arm','ForeArm','Hand']]
    limits=problem.limits[[problem.lookup[j] for j in arms]]
    expected={k:v.copy() for k,v in source.items()}
    for frames,row in zip(windows,result['windows']):
        raw=np.array(row['best_raw']).reshape(len(frames),8,3)
        assert np.isfinite(raw).all()
        angles=raw*limits[None,:,None]/np.sqrt(1+(raw*raw).sum(-1))[...,None]
        assert np.all(np.linalg.norm(angles,axis=-1)<=limits+1e-12)
        local=source['local_rot_mats'].astype(float).copy()
        rotation=Rotation.from_rotvec(angles.reshape(-1,3)).as_matrix().reshape(len(frames),8,3,3)
        for i,frame in enumerate(frames):local[frame,arms]=problem.base['local_rot_mats'][frame,arms]@rotation[i]
        # Independent NumPy FK from stored local precision. In particular, do
        # not reuse the generic helper that normalizes frozen rotations.
        stored=local[frames].astype(source['local_rot_mats'].dtype)
        rotations=np.empty_like(stored,dtype=float);positions=np.empty_like(source['posed_joints'][frames],dtype=float)
        for j,parent in enumerate(problem.parents):
            if parent<0:rotations[:,j]=stored[:,j];positions[:,j]=source['root_positions'][frames]
            else:
                offsets=np.einsum('fji,fj->fi',source['global_rot_mats'][frames,parent],source['posed_joints'][frames,j]-source['posed_joints'][frames,parent])
                rotations[:,j]=rotations[:,parent]@stored[:,j]
                positions[:,j]=positions[:,parent]+np.einsum('fij,fj->fi',rotations[:,parent],offsets)
        expected['local_rot_mats'][frames]=stored
        expected['global_rot_mats'][frames]=rotations
        expected['posed_joints'][frames]=positions
    candidate=dict(np.load(patch/'motion.npz',allow_pickle=False));maximum=0.
    for key in source:
        if key=='foot_contacts':np.testing.assert_array_equal(expected[key],candidate[key])
        else:
            error=float(np.max(np.abs(expected[key]-candidate[key])));maximum=max(maximum,error)
            np.testing.assert_allclose(expected[key],candidate[key],atol=2e-7,rtol=0)
    changed=[f for window in windows for f in window];locked=np.setdiff1d(np.arange(prior['frame_count']),changed)
    for key in source:np.testing.assert_array_equal(source[key][locked],candidate[key][locked])
    np.testing.assert_array_equal(source['root_positions'],candidate['root_positions'])
    frozen=np.setdiff1d(np.arange(len(problem.names)),arms)
    np.testing.assert_array_equal(source['local_rot_mats'][:,frozen],candidate['local_rot_mats'][:,frozen])
    return candidate,dict(study=patch.relative_to(ROOT).as_posix(),result_sha256=sha256(patch/'result.json'),
        auditor_sha256=sha256(__file__),replay_maximum_error=maximum,protected_frames_exact=len(locked),root_and_non_arm_exact=True,windows=windows)


def compare(study,patch,output,names):
    """Decoded before/after motion with per-joint window joins, not just maxima."""
    protocol=read(Path(patch)/'protocol.json');times=np.arange((protocol['frame_count']-1)*4+1)/4
    variants={};values={}
    for label,folder in [('input',study),('candidate',patch)]:
        doc,binary=read_glb(Path(folder)/'candidate.glb');sampler=AnimationSampler(doc,binary,0)
        positions=np.array([sampler.sample(t/30)[doc['skins'][0]['joints'],:3,3] for t in times])
        velocity=np.linalg.norm(np.diff(positions,axis=0)*120,axis=-1)
        acceleration=np.linalg.norm(np.diff(positions,n=2,axis=0)*120**2,axis=-1)
        values[label]=(velocity,acceleration)
        f,j=np.unravel_index(acceleration.argmax(),acceleration.shape)
        variants[label]=dict(peak_speed_m_s=float(velocity.max()),peak_acceleration_m_s2=float(acceleration.max()),
                             peak_acceleration_frame=float(times[f+1]),peak_acceleration_joint=names[j])
    windows=[]
    for frames in protocol['path_windows']:
        mask=(times[1:-1]>=frames[0]-1)&(times[1:-1]<=frames[-1]+1)
        before=values['input'][1][mask].max(0);after=values['candidate'][1][mask].max(0)
        windows.append(dict(frames=frames,centers=[frames[0]-1,frames[-1]+1],joints=[dict(joint=name,
            input_peak_acceleration_m_s2=float(a),candidate_peak_acceleration_m_s2=float(b),increased=bool(b>a+1e-5)) for name,a,b in zip(names,before,after)]))
    report=dict(input_glb_sha256=sha256(Path(study)/'candidate.glb'),candidate_glb_sha256=sha256(Path(patch)/'candidate.glb'),
                variants=variants,windows=windows,quality_approved=False)
    save(Path(output)/'path-comparison.json',report)
    return report
