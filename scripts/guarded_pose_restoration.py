"""Retain only fully replayed, nonregressing native pose-repair steps.

One pose and fixed neighbors; not a full animation or release certificate.
"""
import argparse
from pathlib import Path
import shutil
import platform
import time
import numpy as np
import scipy
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from action_worker_lock import worker_lock
from scene_pose_restoration import RestorationProblem,METHODS as POSE_METHODS
from grasp_pose_witness import norm_slack_and_jacobian
from protected_inequality_step import fit
from sparse_pose_jacobian import SparsePoseJacobian
from pose_restoration_policy import tradeoff_policy,row_diagnostics

METHODS=POSE_METHODS+['guarded_pose_restoration.py','protected_inequality_step.py','sparse_pose_jacobian.py','pose_row_jacobian.py','pose_restoration_policy.py']
DEFINITIONS=ROOT/'vendor/kimodo/kimodo/skeleton/definitions.py'


def _run(study,output,frame,iterations,trust,seconds,failure_policy,proposal,solve_iterations,row_chunk,point_policy,point_proposal,point_headroom):
    summary=read(study/'fit/summary.json')
    if (summary.get('solver_version')!=17 or read(study/'pipeline.json')['status']!='complete'
            or len(summary['trials'])!=1 or sha256(ASSET)!=summary['mesh_sha256']):
        raise ValueError('One completed V17 source with unchanged native skin required')
    folder=study/'fit/assets'/summary['trials'][0]['id']/'A'
    inputs=[folder/n for n in ['raw-motion.npz','limb-motion.npz','previous-motion.npz','motion.npz','recipe.json']]
    inputs+=[ASSET,DEFINITIONS,study/'fit/summary.json',study/'pipeline.json']
    bindings={str(p):sha256(p) for p in inputs}
    skin=dict(np.load(ASSET,allow_pickle=False));torch.set_num_threads(2)
    problem=RestorationProblem(folder,skin,frame,grouping='native-joint')
    labels,mask=tradeoff_policy(problem.labels,[problem.names[j] for j in problem.editable],
        failure_policy=failure_policy,point_policy=point_policy)
    point_rows=np.array([label.startswith('point:') for label in labels],dtype=bool)
    feasible=point_rows if point_proposal=='feasible' else np.zeros_like(point_rows)
    headroom=point_rows.astype(float)*point_headroom
    seed_audit,seed_motion=problem.independent(problem.seed)
    with torch.no_grad():rot,pos,_,vertices=problem.fk(problem.t(problem.seed))
    seed_error=max(float(np.abs(pos.numpy()-problem.candidate['posed_joints'][frame]).max()),
        float(np.abs(rot.numpy()-problem.candidate['global_rot_mats'][frame]).max()))
    skin_error=float(np.abs(vertices.numpy()-problem.surface.vertices(seed_motion['global_rot_mats'][0],seed_motion['posed_joints'][0])).max())
    if max(seed_error,skin_error)>2e-6:raise ValueError('Saved seed FK and independent skin must reproduce')
    output.mkdir(parents=True,exist_ok=False);archive=output/'implementation';archive.mkdir()
    for name in METHODS:shutil.copyfile(ROOT/'scripts'/name,archive/name)
    shutil.copyfile(DEFINITIONS,archive/'kimodo-skeleton-definitions.py')
    protocol=dict(at=now(),source_study=study.relative_to(ROOT).as_posix(),frame=frame,
        inputs_sha256=bindings,methods_sha256={n:sha256(ROOT/'scripts'/n) for n in METHODS},
        native_metadata_sha256=sha256(DEFINITIONS),runtime=dict(python=platform.python_version(),numpy=np.__version__,
        scipy=scipy.__version__,torch=str(torch.__version__)),iterations=iterations,trust_normalized=trust,
        seconds=seconds,proposal=proposal,proposal_solve_iterations=solve_iterations,row_chunk=row_chunk,nonlinear_replay_call_limit=1000,
        solver_headroom_normalized=1e-6,grouping='native-joint',jacobian='Full-population active dependencies, all ties retained',
        geometry_constraint_rows=len(problem.labels),
        vertices_checked=len(skin['bind_vertices']),influences_per_vertex=8,
        original_limits=dict(position_m=.22,added_speed_m_s=1.5,point_working_m=problem.point_limits.tolist(),
            normal_degrees=problem.config['normal_tolerance_degrees'],floor_m=problem.config['clearance_m'],
            root_lift_m=problem.config['max_root_lift_m'],rotation_radians=problem.limits.tolist()),
        failure_policy=failure_policy,point_policy=point_policy,point_proposal=point_proposal,
        proposal_feasible_mask=feasible.tolist(),proposal_headroom_normalized=headroom.tolist(),
        inequality_labels=labels,tradeoff_mask=mask.tolist(),
        normalization='Archived pose slack units: point/object/floor over 10 mm, normal chord ratio, '
            'squared body/speed and local rotation-norm ratios.',
        acceptance='Every complete nonlinear row replayed. Passing rows stay feasible; edit budgets and floor rows cannot worsen. '
            'Rowwise mode also protects each failed contact/object row. Default point preservation prevents every failed hand-distance increase. '
            'Merit mode permits only explicitly masked failed-row tradeoffs '
            'when worst violation does not increase and squared violation decreases. Exact original thresholds decide feasibility.',
        scope='One native pose and fixed adjacent keys; no full-clip, support-slide, between-key, '
            'triangle/volume, self-collision, anatomy, dynamics, import or human certificate.',quality_approved=False,release_approved=False)
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='processing',stage='Guarded nonlinear restoration'))
    scale=np.r_[np.repeat(problem.limits,3),problem.config['max_root_lift_m']]
    seed=problem.seed/scale;lower=np.r_[np.full(problem.dim-1,-1.),0.];upper=np.ones(problem.dim)
    sparse=SparsePoseJacobian(problem,row_chunk=row_chunk)
    def measure(z):
        x=np.asarray(z)*scale
        with torch.no_grad():values=problem.geometry_slack(problem.t(x)).numpy()
        return np.r_[values,norm_slack_and_jacobian(x,problem.limits)[0]]
    def linearize(z):
        values,jac=sparse(np.asarray(z)*scale)
        return values,jac*scale[None]
    started=time.monotonic();dense_values,dense_jac=problem.pair(seed*scale);dense_seconds=time.monotonic()-started
    started=time.monotonic();sparse_values,sparse_jac=sparse(seed*scale);sparse_seconds=time.monotonic()-started
    np.testing.assert_allclose(sparse_values,dense_values,rtol=1e-10,atol=1e-10)
    np.testing.assert_allclose(sparse_jac,dense_jac,rtol=2e-7,atol=2e-7)
    direction=np.random.default_rng(716).normal(size=problem.dim);direction/=np.linalg.norm(direction);step=1e-6
    values,jac=linearize(seed);count=len(problem.contacts)+len(problem.normals)
    fd=(measure(seed+step*direction)-measure(seed-step*direction))/(2*step)
    np.testing.assert_allclose(jac[:count]@direction,fd[:count],atol=2e-5,rtol=2e-4)
    save(output/'preflight.json',dict(seed=seed_audit,seed_fk_max_error_m=seed_error,independent_skin_max_error_m=skin_error,
        smooth_directional_error=float(np.abs(jac[:count]@direction-fd[:count]).max()),
        sparse_dense_value_max_error=float(np.abs(sparse_values-dense_values).max()),
        sparse_dense_jacobian_max_error=float(np.abs(sparse_jac-dense_jac).max()),
        dense_seconds=dense_seconds,sparse_seconds=sparse_seconds,dependencies=sparse.dependencies))
    observed=[]
    def observer(label,z,slacks,retained):
        trial=output/'trials'/label;trial.mkdir(parents=True,exist_ok=False)
        audit,motion=problem.independent(z*scale);np.savez_compressed(trial/'pose.npz',**motion)
        save(trial/'audit.json',dict(label=label,retained=retained,candidate=audit,solver_slacks=slacks.tolist(),
            parameters=(z*scale).tolist(),pose_sha256=sha256(trial/'pose.npz'),quality_approved=False,release_approved=False))
        observed.append(dict(label=label,retained=retained,pose_checks_passed=audit['pose_checks_passed'],audit_sha256=sha256(trial/'audit.json')))
        save(output/'progress.json',dict(status='processing',observations=observed))
        if retained and label!='final':print(dict(label=label,pose_checks_passed=audit['pose_checks_passed'],minimum_slack=float(slacks.min())),flush=True)
    value,report=fit(measure,linearize,seed,lower,upper,iterations=iterations,trust=trust,seconds=seconds,
        observer=observer,failure_policy=failure_policy,tradeoff_mask=mask,proposal=proposal,solve_iterations=solve_iterations,
        proposal_feasible_mask=feasible,proposal_headroom=headroom)
    candidate,motion=problem.independent(value*scale)
    with torch.no_grad():_,_,_,vertices=problem.fk(problem.t(value*scale))
    error=float(np.abs(vertices.numpy()-problem.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])).max())
    if error>2e-6:raise ValueError('Final independent skin mismatch')
    if any(sha256(Path(p))!=h for p,h in bindings.items()) or any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in protocol['methods_sha256'].items()):
        raise ValueError('Original inputs or implementation changed during study')
    if sha256(archive/'kimodo-skeleton-definitions.py')!=protocol['native_metadata_sha256']:
        raise ValueError('Native metadata archive changed')
    final=measure(value);source=measure(seed)
    diagnostics=row_diagnostics(labels,source,final,mask)
    if diagnostics['source_passing_lost'] or diagnostics['protected_source_regressed']:
        raise ValueError('Complete labeled source protection failed')
    save(output/'row-diagnostics.json',diagnostics)
    protected=(source>=0)|~np.asarray(report['tradeoff_mask'],dtype=bool)
    if (not report['source_passing_rows_preserved'] or not report['nontradeoff_rows_preserved']
            or not np.all(final[protected]>=np.minimum(source[protected],0))):
        raise ValueError('Nonlinear source protection failed')
    np.savez_compressed(output/'pose.npz',**motion)
    status='interrupted_resource_guard' if report['stop']=='time_or_measurement_budget' else 'complete'
    save(output/'result.json',dict(at=now(),status=status,seed=seed_audit,candidate=candidate,fit=report,
        observations=observed,parameters=(value*scale).tolist(),independent_skin_max_error_m=error,
        row_diagnostics_sha256=sha256(output/'row-diagnostics.json'),
        protocol_sha256=sha256(output/'protocol.json'),pose_sha256=sha256(output/'pose.npz'),quality_approved=False,release_approved=False))
    save(output/'pipeline.json',dict(status=status,stop=report['stop'],source_rows_preserved=report['source_rows_preserved'],
        source_passing_rows_preserved=True,nontradeoff_rows_preserved=True,
        pose_checks_passed=candidate['pose_checks_passed'],quality_approved=False,release_approved=False))
    print(dict(status=status,stop=report['stop'],initial_score=report['initial_score'],final_score=report['final_score'],candidate=candidate),flush=True)


def run(study,output,frame,iterations=30,trust=.03,seconds=300,failure_policy='rowwise',proposal='linear',solve_iterations=100,row_chunk=None,
        point_policy='preserve',point_proposal='preserve',point_headroom=0.):
    study=Path(study).resolve();output=Path(output).resolve();existed=output.exists()
    if (type(frame) is not int or type(iterations) is not int or not 1<=iterations<=100
            or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-5<=trust<=.3
            or type(seconds) not in (int,float) or not np.isfinite(seconds) or not 1<=seconds<=1800
            or failure_policy not in ['rowwise','merit'] or proposal not in ['linear','nonlinear'] or point_policy not in ['preserve','tradeoff']
            or point_proposal not in ['preserve','feasible'] or type(point_headroom) not in (int,float)
            or not np.isfinite(point_headroom) or not 0<=point_headroom<=1e-3
            or type(solve_iterations) is not int or not 1<=solve_iterations<=300
            or (row_chunk is not None and (type(row_chunk) is not int or not 1<=row_chunk<=32))):
        raise ValueError('Explicit valid native frame and bounded repair options required')
    with worker_lock(),threadpool_limits(limits=2):
        try:return _run(study,output,frame,iterations,trust,seconds,failure_policy,proposal,solve_iterations,row_chunk,point_policy,point_proposal,point_headroom)
        except Exception as exc:
            if not existed and output.exists():save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,
                error=str(exc),quality_approved=False,release_approved=False))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study');parser.add_argument('output');parser.add_argument('--frame',type=int,required=True)
    parser.add_argument('--iterations',type=int,default=30);parser.add_argument('--trust',type=float,default=.03);parser.add_argument('--seconds',type=float,default=300)
    parser.add_argument('--failure-policy',choices=['rowwise','merit'],default='rowwise')
    parser.add_argument('--proposal',choices=['linear','nonlinear'],default='linear')
    parser.add_argument('--solve-iterations',type=int,default=100)
    parser.add_argument('--row-chunk',type=int)
    parser.add_argument('--point-policy',choices=['preserve','tradeoff'],default='preserve')
    parser.add_argument('--point-proposal',choices=['preserve','feasible'],default='preserve')
    parser.add_argument('--point-headroom',type=float,default=0.)
    args=parser.parse_args();run(args.study,args.output,args.frame,args.iterations,args.trust,args.seconds,args.failure_policy,args.proposal,
        args.solve_iterations,args.row_chunk,args.point_policy,args.point_proposal,args.point_headroom)
