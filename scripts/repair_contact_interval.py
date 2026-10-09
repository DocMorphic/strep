"""Repair the worst measured contact window, then check the whole saved interval.

Diagnostic original-source study; never edits a source clip or approves export.
"""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from action_worker_lock import worker_lock
from guarded_pose_restoration import DEFINITIONS
from audit_contact_interval import METHODS as AUDIT_METHODS,POSE_TRACKS,pose_tracks,overlay_pose_tracks,evaluate_interval
from contact_interval_coverage import partition_frames,select_window
from coupled_pose_window import CoupledPoseWindow
from protected_inequality_step import fit,retain
from pose_restoration_policy import proposal_headroom,row_diagnostics
from pose_proposal_archive import ProposalArchive
from contact_interval_resume import resume_interval,seed_window,IntervalReplaySession

METHODS=AUDIT_METHODS+['repair_contact_interval.py','contact_interval_resume.py','geometry_conic_start.py']


class ExactSavedOrigin:
    """Keep the exact source arrays at the seed; construct only new proposals."""
    def __init__(self,window,source):
        self.window=window;self.seed=window.seed.copy();self.scale=window.scale.copy()
        self.normalized_seed=self.seed/self.scale
        self.source={key:value[window.frames].copy() for key,value in pose_tracks(source).items()}
        # Complete shape, precision, rig/root and geometry preflight.
        self.initial_rows=window.saved_representation(self.seed,motion=self.source)

    def controls(self,normalized):
        normalized=self.window.controls(normalized)
        # Division followed by multiplication need not reproduce the seed.
        return self.seed.copy() if np.array_equal(normalized,self.normalized_seed) else normalized*self.scale

    def motion(self,controls):
        controls=self.window.controls(controls)
        if np.array_equal(controls,self.seed):return {k:v.copy() for k,v in self.source.items()}
        return pose_tracks(self.window.independent(controls)[1])

    def rows(self,controls):
        return self.window.saved_representation(controls,motion=self.motion(controls))

    def audit(self,controls,motion=None):
        motion=self.motion(controls) if motion is None else motion
        positions={p.frame:p.t(motion['posed_joints'][i]) for i,p in enumerate(self.window.problems)}
        audits=[]
        for i,p in enumerate(self.window.problems):
            neighbors={f:positions.get(f,fixed) for f,fixed in p.neighbors.items()}
            audit=p.audit_motion({key:value[i:i+1] for key,value in motion.items()},neighbors=neighbors)
            audits.append(dict(frame=p.frame,**audit))
        return dict(frames=audits,window_checks_passed=all(a['pose_checks_passed'] for a in audits),
            quality_approved=False,release_approved=False,
            scope='Exact saved keyed window and current exterior neighbors; no interpolation, dynamics, metadata, engine or human certificate.')


def compare_interval(labels,before,current_labels,after):
    if labels!=current_labels:raise ValueError('Every original saved interval row must remain present')
    mask=np.zeros(len(labels),dtype=bool)
    diagnostics=row_diagnostics(labels,before,after,mask)
    preserved=not diagnostics['source_passing_lost'] and not diagnostics['protected_source_regressed']
    accepted=retain(before,after,failure_policy='merit',tradeoff_mask=mask)
    return dict(source_rows_preserved=preserved,update_retained=accepted,
        quality_approved=False,release_approved=False),diagnostics


def _run(study,output,frames,width,iterations,trust,seconds,solve_iterations,resume,exclusions,*,replay_session=None,proposal_geometry_solver='supporting-planes'):
    summary=read(study/'fit/summary.json')
    if (summary.get('solver_version')!=17 or read(study/'pipeline.json')['status']!='complete'
            or len(summary['trials'])!=1 or sha256(ASSET)!=summary['mesh_sha256']):
        raise ValueError('One completed V17 original source and unchanged native skin required')
    folder=study/'fit/assets'/summary['trials'][0]['id']/'A'
    paths=[folder/name for name in ['raw-motion.npz','limb-motion.npz','previous-motion.npz','motion.npz','recipe.json']]
    paths+=[ASSET,DEFINITIONS,study/'fit/summary.json',study/'pipeline.json']
    bindings={str(path):sha256(path) for path in paths};original_bindings=bindings.copy()
    source_payload=dict(np.load(folder/'motion.npz',allow_pickle=False));source=pose_tracks(source_payload)
    skin=dict(np.load(ASSET,allow_pickle=False));torch.set_num_threads(2)
    factory=lambda block:CoupledPoseWindow(folder,skin,block,row_chunk=4)
    if replay_session is not None:
        if type(replay_session) is not IntervalReplaySession:raise ValueError('Owned interval replay session required')
        factory=replay_session.prepare(study,factory,source,frames,width,original_bindings,METHODS,DEFINITIONS,ExactSavedOrigin,
            implementation_bindings={str(ROOT/'scripts'/n):sha256(ROOT/'scripts'/n) for n in METHODS})
    parameters={};receipt=None
    if resume is not None:
        source,parameters,receipt,extra=resume_interval(resume,study,factory,source,frames,width,original_bindings,METHODS,DEFINITIONS,ExactSavedOrigin,replay_session=replay_session)
        bindings.update(extra)
    output.mkdir(parents=True,exist_ok=False);archive=output/'implementation';archive.mkdir()
    for name in METHODS:shutil.copyfile(ROOT/'scripts'/name,archive/name)
    shutil.copyfile(DEFINITIONS,archive/'kimodo-skeleton-definitions.py')
    protocol=dict(at=now(),source_study=study.relative_to(ROOT).as_posix(),frames=frames,width=width,fps=30,
        inputs_sha256=bindings,methods_sha256={name:sha256(archive/name) for name in METHODS},
        native_metadata_sha256=sha256(DEFINITIONS),source_motion_sha256=sha256(folder/'motion.npz'),
        pose_tracks=list(POSE_TRACKS),omitted_source_tracks=sorted(set(source_payload)-set(POSE_TRACKS)),
        iterations=iterations,trust_normalized=trust,seconds=seconds,proposal_solve_iterations=solve_iterations,row_chunk=4,
        interval_resume=receipt,selection_exclusions=exclusions,
        origin='Exact saved original or fully replayed preserving interval state; reconstructed solver seed is never substituted for the saved origin. Original references and limits remain fixed.',
        acceptance='Every originally passing saved row stays passing, every failed saved row is nonregressing, and worst/squared violation improves. Check the complete requested interval and both exterior body boundaries after the bounded local fit.',
        metadata_approved=False,quality_approved=False,release_approved=False)
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='processing',quality_approved=False,release_approved=False))
    observations=[]
    def observe(kind):
        def observer(index,block,labels,slacks,audits):
            path=output/kind/('window-'+str(index)+'.json');path.parent.mkdir(exist_ok=True)
            save(path,dict(frames=block,labels=labels,slacks=slacks.tolist(),physical=[dict(frame=f,**audits[f]) for f in block],
                quality_approved=False,release_approved=False))
            observations.append(dict(kind=kind,index=index,frames=block,path=path.relative_to(output).as_posix(),sha256=sha256(path)))
            save(output/'progress.json',dict(status='processing',observations=observations))
            print(dict(stage=kind,window=index,frames=block),flush=True)
        return observer
    baseline,labels,before=evaluate_interval(factory,frames,source,parameters,width=width,observer=observe('baseline'))
    parameters={r['frame']:np.asarray(r['controls']) for r in baseline['parameters']}
    block=select_window(frames,baseline,width,exclusions)
    if block is None:raise ValueError('Every window in this coverage pass has already been attempted')
    window=seed_window(factory,block,source,parameters)
    origin=ExactSavedOrigin(window,source);scale=window.scale;z=origin.normalized_seed.copy()
    lower=np.tile(np.r_[np.full(window.pose_dim-1,-1.),0.],len(block));upper=np.ones(window.dim)
    if np.any(z<lower) or np.any(z>upper):raise ValueError('Original solver seed outside unchanged normalized bounds')
    original_limits=[dict(frame=p.frame,position_m=.22,added_speed_m_s=1.5,point_working_m=p.point_limits.tolist(),
        normal_degrees=p.config['normal_tolerance_degrees'],floor_m=p.config['clearance_m'],
        root_lift_m=p.config['max_root_lift_m'],rotation_radians=p.limits.tolist()) for p in window.problems]
    headroom=proposal_headroom(window.labels,point=1e-5,normal=1e-3,object=1e-3,body=1e-3)
    mask=np.zeros(len(window.labels),dtype=bool);point_rows=np.array([label.startswith('point:') for label in window.labels])
    protocol.update(selected_frames=block,selection='Largest measured normalized violation, then squared violation, then earliest frame among explicitly unattempted windows.',
        original_limits=original_limits,pose_dim=window.pose_dim,inequality_labels=window.labels,representation_labels=window.representation_labels,
        tradeoff_mask=mask.tolist(),proposal_feasible_mask=point_rows.tolist(),proposal_headroom_normalized=headroom.tolist(),
        proposal='nonlinear',proposal_start='geometry-descent',proposal_priority='worst-first',proposal_geometry_solver=proposal_geometry_solver,
        proposal_margin_fallback=True,proposal_trial_correction=True,proposal_tangent_guard=True,representation_guard=True)
    save(output/'protocol.json',protocol)
    def measure(candidate):
        with torch.no_grad():return window.geometry_slack(torch.as_tensor(origin.controls(candidate),dtype=torch.float64)).numpy()
    def linearize(candidate):
        values,jac=window.pair(origin.controls(candidate));return values,jac*scale[None]
    def vectorize(candidate):
        vectors=window.vector_linearization(origin.controls(candidate));vectors['jacobian']*=scale[None,None];return vectors
    started=time.monotonic();dense,djac=window.dense_pair(window.seed);dense_seconds=time.monotonic()-started
    started=time.monotonic();assembled,jac=window.pair(window.seed);assembled_seconds=time.monotonic()-started
    np.testing.assert_allclose(dense,assembled,rtol=1e-10,atol=1e-10);np.testing.assert_allclose(djac,jac,rtol=2e-7,atol=2e-7)
    reconstructed=pose_tracks(window.independent(window.seed)[1]);reconstructed_rows=window.saved_representation(window.seed,motion=reconstructed)
    save(output/'preflight.json',dict(dense_seconds=dense_seconds,assembled_seconds=assembled_seconds,
        value_max_error=float(np.abs(dense-assembled).max()),jacobian_max_error=float(np.abs(djac-jac).max()),
        saved_seed_max_difference=float(np.abs(origin.initial_rows-reconstructed_rows).max()),
        exact_saved_seed_audit=origin.audit(window.seed),reconstructed_seed_rows=reconstructed_rows.tolist(),
        exact_saved_seed_rows=origin.initial_rows.tolist(),quality_approved=False,release_approved=False))
    trials=[]
    def observer(label,candidate,slacks,retained):
        controls=origin.controls(candidate);motion=origin.motion(controls);audit=origin.audit(controls,motion)
        directory=output/'trials'/label;directory.mkdir(parents=True,exist_ok=False)
        np.savez_compressed(directory/'window.npz',**motion)
        save(directory/'audit.json',dict(label=label,retained=retained,candidate=audit,solver_slacks=slacks.tolist(),
            represented_slacks=origin.rows(controls).tolist(),parameters=controls.tolist(),
            motion_sha256=sha256(directory/'window.npz'),quality_approved=False,release_approved=False))
        trials.append(dict(label=label,retained=retained,audit_sha256=sha256(directory/'audit.json')))
        save(output/'fit-progress.json',dict(status='processing',trials=trials))
        if retained:print(dict(stage='fit',label=label,minimum_solver_slack=float(slacks.min())),flush=True)
    value,report=fit(measure,linearize,z,lower,upper,iterations=iterations,trust=trust,seconds=seconds,
        failure_policy='merit',tradeoff_mask=mask,proposal='nonlinear',solve_iterations=solve_iterations,
        proposal_feasible_mask=point_rows,proposal_headroom=headroom,proposal_tangent_guard=True,
        proposal_start='geometry-descent',proposal_priority='worst-first',vectorize=vectorize,
        proposal_margin_fallback=True,proposal_trial_correction=True,record_store=ProposalArchive(output),observer=observer,
        proposal_geometry_solver=proposal_geometry_solver,
        representation_measure=lambda candidate:origin.rows(origin.controls(candidate)))
    controls=origin.controls(value);motion=origin.motion(controls)
    np.testing.assert_array_equal(origin.initial_rows,report['initial_represented_slacks'])
    np.testing.assert_array_equal(origin.rows(controls),report['final_represented_slacks'])
    proposed=overlay_pose_tracks(source,block,motion)
    parameters.update({f:controls[i*window.pose_dim:(i+1)*window.pose_dim] for i,f in enumerate(block)})
    current,current_labels,after=evaluate_interval(factory,frames,proposed,parameters,width=width,observer=observe('proposed'))
    decision,diagnostics=compare_interval(labels,before,current_labels,after)
    retained=proposed if decision['update_retained'] else source
    for name,data in [('baseline-motion.npz',source),('proposed-motion.npz',proposed),('retained-motion.npz',retained)]:np.savez_compressed(output/name,**data)
    save(output/'baseline.json',baseline);save(output/'proposed.json',current);save(output/'row-diagnostics.json',diagnostics)
    if any(sha256(Path(path))!=digest for path,digest in bindings.items()):raise ValueError('Bound original interval inputs changed')
    if any(sha256(ROOT/'scripts'/name)!=digest or sha256(archive/name)!=digest for name,digest in protocol['methods_sha256'].items()):
        raise ValueError('Interval repair implementation changed during study')
    if sha256(archive/'kimodo-skeleton-definitions.py')!=protocol['native_metadata_sha256']:raise ValueError('Native metadata changed')
    result=dict(at=now(),status='complete',selected_frames=block,frame_count=len(frames),row_count=len(labels),
        decision=decision,fit=report,trials=trials,observations=observations,parameters=controls.tolist(),
        protocol_sha256=sha256(output/'protocol.json'),files_sha256={name:sha256(output/name) for name in
            ['baseline-motion.npz','proposed-motion.npz','retained-motion.npz','baseline.json','proposed.json','row-diagnostics.json','preflight.json']},
        local_stop=report['stop'],scope=current['scope'],quality_approved=False,release_approved=False)
    save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
    return result


def run(study,output,frames,*,width=3,iterations=8,trust=.03,seconds=300,solve_iterations=10,resume=None,exclusions=None,proposal_geometry_solver='supporting-planes'):
    windows=partition_frames(frames,width);exclusions=[] if exclusions is None else exclusions
    select_window(frames,dict(ranked_windows=[dict(frames=w) for w in windows]),width,exclusions)
    if (type(iterations) is not int or not 1<=iterations<=100 or type(solve_iterations) is not int or not 1<=solve_iterations<=300
            or type(trust) not in [int,float] or not np.isfinite(trust) or not 1e-5<=trust<=.3
            or type(seconds) not in [int,float] or not np.isfinite(seconds) or not 1<=seconds<=1800
            or (resume is not None and (not isinstance(resume,(str,Path)) or not str(resume)))
            or proposal_geometry_solver not in ['supporting-planes','conic']):
        raise ValueError('Explicit original-bound repair budgets required')
    study=Path(study).resolve();output=Path(output).resolve();resume=Path(resume).resolve() if resume is not None else None
    inputs=[study]+([resume] if resume is not None else [])
    if (any(not p.is_relative_to(ROOT.resolve()) for p in inputs+[output])
            or any(output.is_relative_to(p) or p.is_relative_to(output) for p in inputs)):
        raise ValueError('Separate immutable in-project original source and repair output required')
    if output.exists():raise FileExistsError(output)
    with worker_lock(),threadpool_limits(limits=2):
        options={} if proposal_geometry_solver=='supporting-planes' else dict(proposal_geometry_solver=proposal_geometry_solver)
        try:return _run(study,output,frames,width,iterations,trust,seconds,solve_iterations,resume,exclusions,**options)
        except Exception as exc:
            if output.exists():save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),quality_approved=False,release_approved=False))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study');parser.add_argument('output')
    parser.add_argument('--start',type=int,required=True);parser.add_argument('--end',type=int,required=True)
    parser.add_argument('--width',type=int,default=3);parser.add_argument('--iterations',type=int,default=8)
    parser.add_argument('--trust',type=float,default=.03);parser.add_argument('--seconds',type=float,default=300)
    parser.add_argument('--solve-iterations',type=int,default=10);parser.add_argument('--resume-interval',type=Path)
    parser.add_argument('--proposal-geometry-solver',choices=['supporting-planes','conic'],default='supporting-planes')
    parser.add_argument('--exclude-window',type=int,nargs='+',action='append',default=[]);args=parser.parse_args()
    run(args.study,args.output,list(range(args.start,args.end+1)),width=args.width,iterations=args.iterations,
        trust=args.trust,seconds=args.seconds,solve_iterations=args.solve_iterations,resume=args.resume_interval,exclusions=args.exclude_window,
        proposal_geometry_solver=args.proposal_geometry_solver)
