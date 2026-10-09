"""Experimental guarded contact-window repair with immutable diagnostic outputs."""
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
from guarded_pose_restoration import _resume_seed,METHODS as POSE_METHODS,DEFINITIONS
from coupled_pose_window import CoupledPoseWindow
from protected_inequality_step import fit
from pose_restoration_policy import tradeoff_policy,proposal_headroom,row_diagnostics
from pose_proposal_archive import ProposalArchive
from window_restoration_resume import resume_window as _resume_window

METHODS=POSE_METHODS+['coupled_pose_window.py','guarded_window_restoration.py','window_restoration_resume.py']


def _run(study,output,frames,iterations,trust,seconds,solve_iterations,row_chunk,resume,window_resume,margin_fallback):
    summary=read(study/'fit/summary.json')
    if (summary.get('solver_version')!=17 or read(study/'pipeline.json')['status']!='complete'
            or len(summary['trials'])!=1 or sha256(ASSET)!=summary['mesh_sha256']):
        raise ValueError('One completed V17 source and unchanged native skin required')
    folder=study/'fit/assets'/summary['trials'][0]['id']/'A'
    inputs=[folder/name for name in ['raw-motion.npz','limb-motion.npz','previous-motion.npz','motion.npz','recipe.json']]
    inputs+=[ASSET,DEFINITIONS,study/'fit/summary.json',study/'pipeline.json']
    bindings={str(path):sha256(path) for path in inputs}
    original_bindings=bindings.copy()
    skin=dict(np.load(ASSET,allow_pickle=False));torch.set_num_threads(2)
    window=CoupledPoseWindow(folder,skin,frames,row_chunk=row_chunk)
    seed=window.seed.copy();resumes=[];original_limits=[]
    for i,p in enumerate(window.problems):
        limits=dict(position_m=.22,added_speed_m_s=1.5,point_working_m=p.point_limits.tolist(),
            normal_degrees=p.config['normal_tolerance_degrees'],floor_m=p.config['clearance_m'],
            root_lift_m=p.config['max_root_lift_m'],rotation_radians=p.limits.tolist())
        original_limits.append(dict(frame=p.frame,**limits))
        if p.frame in resume:
            labels,_=tradeoff_policy(p.labels,[p.names[j] for j in p.editable])
            parameters,expected,record,extra=_resume_seed(resume[p.frame],study,p.frame,original_bindings,limits,labels,p)
            seed[i*window.pose_dim:(i+1)*window.pose_dim]=parameters
            _,motion=p.independent(parameters)
            for key in ['posed_joints','global_rot_mats']:np.testing.assert_allclose(motion[key],expected[key],rtol=0,atol=2e-6)
            resumes.append(dict(frame=p.frame,**record));bindings.update(extra)
    window_record=None
    if window_resume is not None:
        seed,_,window_record,extra=_resume_window(window_resume,study,window,original_bindings,original_limits,METHODS,DEFINITIONS,_resume_seed)
        bindings.update(extra)
    scale=window.scale;z=seed/scale
    lower=np.tile(np.r_[np.full(window.pose_dim-1,-1.),0.],len(frames));upper=np.ones(window.dim)
    if np.any(z<lower) or np.any(z>upper):raise ValueError('Seed outside original normalized controls')
    labels,mask=tradeoff_policy(window.labels,[],failure_policy='merit',normal_policy='preserve',object_policy='preserve')
    assert not mask.any()
    point_rows=np.array([label.startswith('point:') for label in labels],dtype=bool)
    headroom=proposal_headroom(labels,point=1e-5,normal=1e-3,object=1e-3,body=1e-3)
    output.mkdir(parents=True,exist_ok=False);archive=output/'implementation';archive.mkdir()
    for name in METHODS:shutil.copyfile(ROOT/'scripts'/name,archive/name)
    shutil.copyfile(DEFINITIONS,archive/'kimodo-skeleton-definitions.py')
    protocol=dict(at=now(),source_study=study.relative_to(ROOT).as_posix(),frames=frames,fps=30,
        inputs_sha256=bindings,methods_sha256={name:sha256(ROOT/'scripts'/name) for name in METHODS},
        native_metadata_sha256=sha256(DEFINITIONS),original_limits=original_limits,resumes=resumes,
        window_resume=window_record,
        iterations=iterations,trust_normalized=trust,seconds=seconds,proposal_solve_iterations=solve_iterations,
        row_chunk=row_chunk,nonlinear_replay_call_limit=1000,vertices_per_frame=len(skin['bind_vertices']),influences_per_vertex=8,
        pose_dim=window.pose_dim,inequality_labels=labels,tradeoff_mask=mask.tolist(),
        proposal='nonlinear',proposal_start='geometry-descent',proposal_priority='worst-first',
        proposal_feasible_mask=point_rows.tolist(),proposal_headroom_normalized=headroom.tolist(),
        failure_policy='merit',point_policy='preserve',normal_policy='preserve',object_policy='preserve',
        archive_proposals=True,proposal_tangent_guard=True,
        proposal_margin_fallback=margin_fallback,
        temporal_edges=[dict(frame=p.frame,neighbor=f,neighbor_edited=f in frames) for p in window.problems for f in p.neighbors],
        acceptance='Every original row preserved against min(previous,0); complete worst/squared violation must improve. Internal speed rows use both candidate frames, outside keys stay fixed. No threshold relaxation.',
        scope='Two to five native contact keys; no full-clip, between-key, anatomy/dynamics, self-collision, engine or human certificate.',
        quality_approved=False,release_approved=False)
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='processing',quality_approved=False,release_approved=False))
    def measure(candidate):
        with torch.no_grad():return window.geometry_slack(torch.as_tensor(candidate*scale,dtype=torch.float64)).numpy()
    def linearize(candidate):
        values,jac=window.pair(candidate*scale)
        return values,jac*scale[None]
    def vectorize(candidate):
        vectors=window.vector_linearization(candidate*scale);vectors['jacobian']*=scale[None,None]
        return vectors
    started=time.monotonic();dense_values,dense_jac=window.dense_pair(seed);dense_seconds=time.monotonic()-started
    started=time.monotonic();values,jac=window.pair(seed);coupled_seconds=time.monotonic()-started
    np.testing.assert_allclose(values,dense_values,rtol=1e-10,atol=1e-10)
    np.testing.assert_allclose(jac,dense_jac,rtol=2e-7,atol=2e-7)
    seed_audit,seed_motion=window.independent(seed)
    for i,p in enumerate(window.problems):
        with torch.no_grad():rotation,position,_,vertices=p.fk(p.t(seed[i*window.pose_dim:(i+1)*window.pose_dim]))
        np.testing.assert_allclose(position.numpy(),seed_motion['posed_joints'][i],rtol=0,atol=2e-6)
        np.testing.assert_allclose(rotation.numpy(),seed_motion['global_rot_mats'][i],rtol=0,atol=2e-6)
        np.testing.assert_allclose(vertices.numpy(),p.surface.vertices(seed_motion['global_rot_mats'][i],seed_motion['posed_joints'][i]),rtol=0,atol=2e-6)
    save(output/'preflight.json',dict(seed=seed_audit,dense_seconds=dense_seconds,coupled_seconds=coupled_seconds,
        dense_value_max_error=float(np.abs(values-dense_values).max()),dense_jacobian_max_error=float(np.abs(jac-dense_jac).max()),
        dependencies=[sparse.dependencies for sparse in window.sparse],quality_approved=False,release_approved=False))
    observations=[]
    def observer(label,candidate,slacks,retained):
        directory=output/'trials'/label;directory.mkdir(parents=True,exist_ok=False)
        audit,motion=window.independent(candidate*scale);np.savez_compressed(directory/'window.npz',**motion)
        save(directory/'audit.json',dict(label=label,retained=retained,candidate=audit,solver_slacks=slacks.tolist(),
            parameters=(candidate*scale).tolist(),motion_sha256=sha256(directory/'window.npz'),quality_approved=False,release_approved=False))
        observations.append(dict(label=label,retained=retained,audit_sha256=sha256(directory/'audit.json'),window_checks_passed=audit['window_checks_passed']))
        save(output/'progress.json',dict(status='processing',observations=observations))
        if retained and label!='final':print(dict(label=label,window_checks_passed=audit['window_checks_passed'],minimum_slack=float(slacks.min())),flush=True)
    value,report=fit(measure,linearize,z,lower,upper,iterations=iterations,trust=trust,seconds=seconds,
        failure_policy='merit',tradeoff_mask=mask,proposal='nonlinear',solve_iterations=solve_iterations,
        proposal_feasible_mask=point_rows,proposal_headroom=headroom,proposal_tangent_guard=True,
        proposal_start='geometry-descent',proposal_priority='worst-first',vectorize=vectorize,
        proposal_margin_fallback=margin_fallback,
        record_store=ProposalArchive(output),observer=observer)
    candidate,motion=window.independent(value*scale)
    if any(sha256(Path(path))!=digest for path,digest in bindings.items()):raise ValueError('Original/resume inputs changed')
    if any(sha256(ROOT/'scripts'/name)!=digest or sha256(archive/name)!=digest for name,digest in protocol['methods_sha256'].items()):
        raise ValueError('Window implementation changed during study')
    if sha256(archive/'kimodo-skeleton-definitions.py')!=protocol['native_metadata_sha256']:raise ValueError('Native metadata changed')
    final=measure(value);source=measure(z);diagnostics=row_diagnostics(labels,source,final,mask)
    if diagnostics['source_passing_lost'] or diagnostics['protected_source_regressed']:raise ValueError('Window source protection failed')
    np.testing.assert_array_equal(final,report['final_slacks']);np.testing.assert_array_equal(source,report['initial_slacks'])
    save(output/'row-diagnostics.json',diagnostics);np.savez_compressed(output/'window.npz',**motion)
    status='interrupted_resource_guard' if report['stop']=='time_or_measurement_budget' else 'complete'
    result=dict(at=now(),status=status,seed=seed_audit,candidate=candidate,fit=report,observations=observations,
        parameters=(value*scale).tolist(),protocol_sha256=sha256(output/'protocol.json'),motion_sha256=sha256(output/'window.npz'),
        row_diagnostics_sha256=sha256(output/'row-diagnostics.json'),quality_approved=False,release_approved=False)
    save(output/'result.json',result);save(output/'pipeline.json',dict(status=status,quality_approved=False,release_approved=False))
    return result


def run(study,output,frames,*,iterations=3,trust=.03,seconds=300,solve_iterations=10,row_chunk=16,resume=None,window_resume=None,margin_fallback=False):
    study=Path(study).resolve();output=Path(output).resolve();resume={} if resume is None else resume
    if (not isinstance(frames,list) or not 2<=len(frames)<=5 or any(type(f) is not int or f<0 for f in frames)
            or frames!=list(range(frames[0],frames[0]+len(frames)))
            or type(iterations) is not int or not 1<=iterations<=100
            or type(solve_iterations) is not int or not 1<=solve_iterations<=300
            or type(row_chunk) is not int or not 1<=row_chunk<=32
            or type(margin_fallback) is not bool
            or type(trust) not in [int,float] or not np.isfinite(trust) or not 1e-5<=trust<=.3
            or type(seconds) not in [int,float] or not np.isfinite(seconds) or not 1<=seconds<=1800
            or not isinstance(resume,dict) or any(type(f) is not int or f not in frames or not isinstance(p,(str,Path)) or not str(p) for f,p in resume.items())
            or (window_resume is not None and (not isinstance(window_resume,(str,Path)) or not str(window_resume) or resume))
            or not study.is_relative_to(ROOT.resolve()) or not output.is_relative_to(ROOT.resolve())
            or output.is_relative_to(study) or study.is_relative_to(output)):
        raise ValueError('Fresh in-project window study, consecutive frames, explicit guarded budgets and bound pose resumes required')
    resume={f:Path(p).resolve() for f,p in resume.items()}
    window_resume=Path(window_resume).resolve() if window_resume is not None else None
    predecessors=list(resume.values())+([window_resume] if window_resume is not None else [])
    if any(output.is_relative_to(p) or p.is_relative_to(output) or not p.is_relative_to(ROOT.resolve()) for p in predecessors):
        raise ValueError('Window output and immutable pose resumes must remain separate')
    existed=output.exists()
    with worker_lock(),threadpool_limits(limits=2):
        try:return _run(study,output,frames,iterations,trust,seconds,solve_iterations,row_chunk,resume,window_resume,margin_fallback)
        except Exception as exc:
            if not existed and output.exists():save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),quality_approved=False,release_approved=False))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study');parser.add_argument('output');parser.add_argument('--frames',type=int,nargs='+',required=True)
    parser.add_argument('--iterations',type=int,default=3);parser.add_argument('--trust',type=float,default=.03)
    parser.add_argument('--seconds',type=float,default=300);parser.add_argument('--solve-iterations',type=int,default=10)
    parser.add_argument('--row-chunk',type=int,default=16);parser.add_argument('--resume',nargs=2,action='append',default=[],metavar=('FRAME','DIRECTORY'))
    parser.add_argument('--resume-window',help='Fully bind/replay a terminal window; cannot combine with individual pose resumes')
    parser.add_argument('--margin-fallback',action='store_true',help='Retry smaller search margins inside one shared initializer budget; original retention gates unchanged')
    args=parser.parse_args();resumes={int(frame):directory for frame,directory in args.resume}
    if len(resumes)!=len(args.resume):parser.error('Each resumed frame must appear once')
    run(args.study,args.output,args.frames,iterations=args.iterations,trust=args.trust,seconds=args.seconds,
        solve_iterations=args.solve_iterations,row_chunk=args.row_chunk,resume=resumes,window_resume=args.resume_window,margin_fallback=args.margin_fallback)
