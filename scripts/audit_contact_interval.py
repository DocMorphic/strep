"""Measure every saved native contact key and its fixed exterior body edges.

Diagnostic source/continuation comparison; never replaces a clip or approves it.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from action_worker_lock import worker_lock
from coupled_pose_window import CoupledPoseWindow
from scene_pose_restoration import reference_slacks
from guarded_pose_restoration import _resume_seed,DEFINITIONS
from guarded_window_restoration import METHODS as WINDOW_METHODS
from window_restoration_resume import resume_window
from contact_interval_coverage import validate_frames,partition_frames,summarize_rows,rank_windows
from pose_restoration_policy import row_diagnostics

METHODS=WINDOW_METHODS+['audit_contact_interval.py','contact_interval_coverage.py']
POSE_TRACKS=('local_rot_mats','global_rot_mats','posed_joints','root_positions')


def pose_tracks(motion):
    if not isinstance(motion,dict) or any(not isinstance(motion.get(key),np.ndarray) for key in POSE_TRACKS):
        raise ValueError('Every saved pose track required; metadata cannot substitute for pose arrays')
    return {key:motion[key].copy() for key in POSE_TRACKS}


def overlay_pose_tracks(source,frames,saved):
    """Merge shared poses, preserving higher root precision and omitting metadata."""
    validate_frames(frames);source=pose_tracks(source);saved=pose_tracks(saved)
    n=len(source['posed_joints'])
    if frames[-1]>=n:raise ValueError('Predecessor frames outside original clock')
    for key in POSE_TRACKS:
        if saved[key].shape!=(len(frames),*source[key].shape[1:]) or not np.isfinite(saved[key]).all():
            raise ValueError('Complete finite predecessor native pose shape required')
        if key=='root_positions':
            if source[key].dtype not in [np.dtype('float32'),np.dtype('float64')] or saved[key].dtype not in [np.dtype('float32'),np.dtype('float64')]:
                raise ValueError('Original finite floating root precision required')
            source[key]=source[key].astype(np.result_type(source[key].dtype,saved[key].dtype))
        elif saved[key].dtype!=source[key].dtype:
            raise ValueError('Original native pose precision differs')
        source[key][frames]=saved[key]
    return source


def evaluate_interval(factory,frames,motion,parameters=None,*,width=3,observer=None):
    """Use exact saved arrays and current exterior keys; retain original references."""
    windows=partition_frames(frames,width)
    if not isinstance(motion,dict) or not isinstance(motion.get('posed_joints'),np.ndarray) or motion['posed_joints'].ndim!=3:
        raise ValueError('Complete finite saved native clock and pose arrays required')
    positions=motion['posed_joints'];n=len(positions)
    shapes={'posed_joints':(n,77,3),'local_rot_mats':(n,77,3,3),'global_rot_mats':(n,77,3,3),'root_positions':(n,3)}
    if any(key not in motion or not isinstance(motion[key],np.ndarray) or motion[key].shape!=shape
           or motion[key].dtype.kind!='f' or not np.isfinite(motion[key]).all() for key,shape in shapes.items()) or frames[-1]>=n:
        raise ValueError('Complete finite saved native clock and pose arrays required')
    if any(not isinstance(v,np.ndarray) or v.ndim==0 or len(v)!=n for v in motion.values()):
        raise ValueError('Every native track must share the original frame clock')
    parameters={} if parameters is None else parameters
    if not isinstance(parameters,dict) or any(type(f) is not int or f not in frames for f in parameters):
        raise ValueError('Explicit measured-frame controls required')
    values={};audits={};controls={};first=None
    for index,block in enumerate(windows):
        window=factory(block)
        if first is None:first=window.problems[0]
        seed=window.seed.reshape(len(block),window.pose_dim)
        parts=[np.asarray(parameters.get(f,seed[i]),dtype=float) for i,f in enumerate(block)]
        if any(p.shape!=(window.pose_dim,) or not np.isfinite(p).all() for p in parts):
            raise ValueError('Complete finite original native controls required')
        exterior={f for p in window.problems for f in p.neighbors if f not in block}
        window.set_fixed_neighbors({f:positions[f] for f in exterior})
        saved={key:value[block].copy() for key,value in motion.items()}
        slacks=window.saved_representation(np.concatenate(parts),motion=saved)
        for label,value in zip(window.representation_labels,slacks):
            if label in values and values[label]!=float(value):raise ValueError('Overlapping native rows differ')
            values[label]=float(value)
        for i,p in enumerate(window.problems):
            neighbors={f:p.t(positions[f]) for f in p.neighbors}
            audit=p.audit_motion({key:value[i:i+1] for key,value in saved.items()},neighbors=neighbors)
            if p.frame in audits and audits[p.frame]!=audit:raise ValueError('Overlapping physical audits differ')
            audits[p.frame]=audit;controls[p.frame]=parts[i].tolist()
        if observer:observer(index,block,window.representation_labels,slacks,audits)
    exterior_frames=[f for f in [frames[0]-1,frames[-1]+1] if 0<=f<n]
    for frame in exterior_frames:
        neighbors={f:first.t(positions[f]) for f in [frame-1,frame+1] if 0<=f<n}
        slacks=reference_slacks(first.t(positions[frame]),first.references,neighbors,frame,.22-first.headroom_m,
            1.5-30*first.headroom_m,grouped=True).numpy()
        labels=[prefix+':'+name+':frame-'+str(frame) for prefix in ['all-reference-position']+
            ['all-reference-speed:'+str(f) for f in sorted(neighbors)] for name in first.names]
        if len(labels)!=len(slacks):raise ValueError('Complete fixed-boundary body rows required')
        values.update(zip(labels,slacks.tolist()))
    measured=sorted(frames+exterior_frames);labels=sorted(values,key=lambda label:(int(label.rsplit(':frame-',1)[1]),label))
    slacks=np.array([values[label] for label in labels]);summary=summarize_rows(measured,labels,slacks)
    summary.update(contact_frames=frames,exterior_body_only_frames=exterior_frames,
        physical_contact_keys_passed=all(a['pose_checks_passed'] for a in audits.values()),
        per_frame_physical=[dict(frame=f,**audits[f]) for f in frames],
        ranked_windows=rank_windows(frames,summary,width),parameters=[dict(frame=f,controls=controls[f]) for f in frames],
        scope='Complete requested saved contact keys, all native vertices/weights and fixed exterior body edges; no between-key, foot-slide, full-clip, anatomy/dynamics, self-collision, metadata/export, engine or human certificate.')
    return summary,labels,slacks


def _run(study,output,frames,width,resume):
    summary=read(study/'fit/summary.json')
    if (summary.get('solver_version')!=17 or read(study/'pipeline.json')['status']!='complete'
            or len(summary['trials'])!=1 or sha256(ASSET)!=summary['mesh_sha256']):
        raise ValueError('One completed V17 source and unchanged native skin required')
    folder=study/'fit/assets'/summary['trials'][0]['id']/'A'
    inputs=[folder/name for name in ['raw-motion.npz','limb-motion.npz','previous-motion.npz','motion.npz','recipe.json']]
    inputs+=[ASSET,DEFINITIONS,study/'fit/summary.json',study/'pipeline.json']
    bindings={str(path):sha256(path) for path in inputs};original_bindings=bindings.copy()
    skin=dict(np.load(ASSET,allow_pickle=False));source=dict(np.load(folder/'motion.npz',allow_pickle=False))
    motion=pose_tracks(source);torch.set_num_threads(2)
    factory=lambda block:CoupledPoseWindow(folder,skin,block,row_chunk=4)
    parameters={};proposed={k:v.copy() for k,v in motion.items()};receipt=None
    if resume is not None:
        block=read(resume/'protocol.json')['frames']
        if not set(block).issubset(frames):raise ValueError('Bound predecessor keys must belong to the complete requested interval')
        window=factory(block)
        # Shape/precision preflight precedes expensive history replay. These
        # arrays are not trusted until the full bound replay succeeds below.
        overlay_pose_tracks(motion,block,dict(np.load(resume/'window.npz',allow_pickle=False)))
        limits=[dict(frame=p.frame,position_m=.22,added_speed_m_s=1.5,point_working_m=p.point_limits.tolist(),
            normal_degrees=p.config['normal_tolerance_degrees'],floor_m=p.config['clearance_m'],
            root_lift_m=p.config['max_root_lift_m'],rotation_radians=p.limits.tolist()) for p in window.problems]
        seed,_,receipt,extra=resume_window(resume,study,window,original_bindings,limits,WINDOW_METHODS,DEFINITIONS,_resume_seed)
        bindings.update(extra)
        saved=dict(np.load(resume/'window.npz',allow_pickle=False))
        proposed=overlay_pose_tracks(motion,block,saved)
        parameters={f:seed[i*window.pose_dim:(i+1)*window.pose_dim] for i,f in enumerate(block)}
    output.mkdir(parents=True,exist_ok=False);archive=output/'implementation';archive.mkdir()
    for name in METHODS:shutil.copyfile(ROOT/'scripts'/name,archive/name)
    shutil.copyfile(DEFINITIONS,archive/'kimodo-skeleton-definitions.py')
    protocol=dict(at=now(),source_study=study.relative_to(ROOT).as_posix(),frames=frames,width=width,fps=30,resume=receipt,
        inputs_sha256=bindings,methods_sha256={name:sha256(archive/name) for name in METHODS},native_metadata_sha256=sha256(DEFINITIONS),
        source_motion_sha256=sha256(folder/'motion.npz'),scope='Exact saved pose audit and bound predecessor overlay only; no clip replacement or correction solve.',
        pose_tracks=list(POSE_TRACKS),omitted_source_tracks=sorted(set(source)-set(POSE_TRACKS)),metadata_approved=False,
        omitted_predecessor_tracks=[] if resume is None else sorted(set(saved)-set(POSE_TRACKS)),
        original_root_dtype=str(motion['root_positions'].dtype),proposed_root_dtype=str(proposed['root_positions'].dtype),
        quality_approved=False,release_approved=False)
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='processing',quality_approved=False,release_approved=False))
    observations=[]
    def observe(kind):
        def observer(index,block,labels,slacks,audits):
            directory=output/kind;directory.mkdir(exist_ok=True)
            path=directory/('window-'+str(index)+'.json')
            save(path,dict(frames=block,labels=labels,slacks=slacks.tolist(),physical=[dict(frame=f,**audits[f]) for f in block],
                quality_approved=False,release_approved=False))
            observations.append(dict(kind=kind,index=index,frames=block,path=path.relative_to(output).as_posix(),sha256=sha256(path)))
            save(output/'progress.json',dict(status='processing',observations=observations))
            print(dict(stage=kind,window=index,frames=block),flush=True)
        return observer
    baseline,labels,before=evaluate_interval(factory,frames,motion,width=width,observer=observe('baseline'))
    current,current_labels,after=evaluate_interval(factory,frames,proposed,parameters,width=width,observer=observe('proposed'))
    if labels!=current_labels:raise ValueError('Every original interval row must remain present')
    diagnostics=row_diagnostics(labels,before,after,np.zeros(len(labels),dtype=bool))
    np.savez_compressed(output/'baseline-motion.npz',**motion);np.savez_compressed(output/'proposed-motion.npz',**proposed)
    save(output/'baseline.json',baseline);save(output/'proposed.json',current);save(output/'row-diagnostics.json',diagnostics)
    if any(sha256(Path(path))!=digest for path,digest in bindings.items()):raise ValueError('Bound interval inputs changed')
    if any(sha256(ROOT/'scripts'/name)!=digest or sha256(archive/name)!=digest for name,digest in protocol['methods_sha256'].items()):
        raise ValueError('Interval implementation changed during study')
    if sha256(archive/'kimodo-skeleton-definitions.py')!=protocol['native_metadata_sha256']:raise ValueError('Native metadata changed')
    result=dict(at=now(),status='complete',observations=observations,frame_count=len(frames),audited_frames=current['audited_frames'],
        row_count=len(labels),overlay_source_rows_preserved=not diagnostics['source_passing_lost'] and not diagnostics['protected_source_regressed'],
        complete_keyed_rows_passed=current['complete_keyed_rows_passed'],physical_contact_keys_passed=current['physical_contact_keys_passed'],
        protocol_sha256=sha256(output/'protocol.json'),files_sha256={name:sha256(output/name) for name in
            ['baseline-motion.npz','proposed-motion.npz','baseline.json','proposed.json','row-diagnostics.json']},
        quality_approved=False,release_approved=False)
    save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
    return result


def run(study,output,frames,*,width=3,resume=None):
    partition_frames(frames,width)
    study=Path(study).resolve();output=Path(output).resolve();resume=Path(resume).resolve() if resume is not None else None
    inputs=[study]+([resume] if resume is not None else [])
    if (any(not p.is_relative_to(ROOT.resolve()) for p in inputs+[output])
            or any(output.is_relative_to(p) or p.is_relative_to(output) for p in inputs)):
        raise ValueError('Separate immutable in-project interval studies required')
    if output.exists():raise FileExistsError(output)
    with worker_lock(),threadpool_limits(limits=2):
        try:return _run(study,output,frames,width,resume)
        except Exception as exc:
            if output.exists():save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),quality_approved=False,release_approved=False))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study');parser.add_argument('output')
    parser.add_argument('--start',type=int,required=True);parser.add_argument('--end',type=int,required=True)
    parser.add_argument('--width',type=int,default=3);parser.add_argument('--resume-window',type=Path)
    args=parser.parse_args()
    run(args.study,args.output,list(range(args.start,args.end+1)),width=args.width,resume=args.resume_window)
