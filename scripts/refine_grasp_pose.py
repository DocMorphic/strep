"""Local physical-angle nonlinear restoration with exact rotation-norm constraints."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem,norm_slack_and_jacobian
from restore_grasp_pose import elastic_row_layout,protected_pass,clearance_violation
from elastic_hand_step import solve as elastic_solve


def run(study,seed_report,output):
    torch.set_num_threads(2);study=Path(study).resolve();seed_report=Path(seed_report).resolve();output=Path(output).resolve();fit=study/'fit';summary=read(fit/'summary.json');seed_result=read(seed_report/'result.json');seed_protocol=read(seed_report/'protocol.json');frame=seed_protocol['frame']
    if summary['solver_version']!=13 or seed_protocol['fit_summary_sha256']!=sha256(fit/'summary.json'):raise ValueError('Completed V13 seed required')
    if sha256(seed_report/'pose.npz')!=seed_result['pose_sha256'] or sha256(ASSET)!=summary['mesh_sha256']:raise ValueError('Seed or mesh changed')
    for name,digest in seed_protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Seed input changed')
    folder=fit/'assets'/summary['trials'][0]['id']/'A';p=PoseProblem(folder,dict(np.load(ASSET,allow_pickle=False)),frame);seed=np.array(seed_result['parameters']);seed_audit,_=p.independent(seed)
    if not protected_pass(seed_audit,p.config):raise ValueError('Seed must satisfy exact protected grip/normal/floor/budget gates')
    current=seed.copy()
    order,row_scale,surface_count=elastic_row_layout(p.labels)
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    methods=['refine_grasp_pose.py','restore_grasp_pose.py','elastic_hand_step.py','grasp_pose_witness.py','grasp_pose_witness_bounded.py','support_contact_v8.py','support_contact_v5.py','floor_contact.py','scene_solver_context.py','object_geometry.py']
    limits=dict(stages=8,trust_degrees=[.5,.1,.02],root_trust_m=.001,backtracks=8,minimum_improvement_m=1e-6,seconds=300,maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3))
    protocol=dict(coordinate_mode='physical',at=now(),study=study.relative_to(ROOT).as_posix(),frame=frame,seed_result_sha256=sha256(seed_report/'result.json'),seed_protocol_sha256=sha256(seed_report/'protocol.json'),inputs=seed_protocol['inputs'],fit_summary_sha256=sha256(fit/'summary.json'),implementation={n:sha256(ROOT/'scripts'/n) for n in methods},limits=limits,smooth_max_m=.0001,object_rows=[p.labels[i] for i in order[:surface_count]],protected_rows=[p.labels[i] for i in order[surface_count:]]+['norm:'+p.names[j] for j in p.editable],constraint_units='Leading object rows converted to metres; other rows retain PoseProblem normalization. Shared elastic helper relaxes only object rows.',selection='Accept a backtracked proposal only if original exact protected gates pass and maximum exact object-clearance violation drops by at least1micrometre. No slack accepted as clearance.',scope='Physical-angle trust-box single-pose diagnostic with original nonlinear rotation-norm inequalities and root bounds. Explicit elastic slack is temporary optimization assistance, not animation approval. No temporal, inferred support tracking, anatomy, balance or self-collision validation.',quality_approved=False)
    save(output/'protocol.json',protocol)
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,snap/n)
    start=time.monotonic();cache=None;history=[];evaluations=0;peak=0
    def physical(x):return np.asarray(x)
    def pair(x):
        nonlocal cache,evaluations,peak
        if cache is not None and np.array_equal(cache[0],x):return cache[1:]
        variable=p.t(x).requires_grad_();slack=p.geometry_slack(variable,.0001)
        jac=np.array([torch.autograd.grad(value,variable,retain_graph=True)[0].detach().numpy() for value in slack]);values=slack.detach().numpy()
        norm,norm_jac=norm_slack_and_jacobian(x,p.limits)
        values=np.r_[values[order]*row_scale,norm];jac=np.r_[jac[order]*row_scale[:,None],norm_jac];evaluations+=1;rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
        if time.monotonic()-start>limits['seconds'] or rss>limits['maximum_rss_bytes'] or psutil.virtual_memory().available<limits['minimum_available_bytes']:raise TimeoutError('Restoration resource guard')
        cache=(x.copy(),values,jac)
        return values,jac
    status='complete';stop='stage_limit';current_audit=seed_audit;parameter_scale=np.r_[np.repeat(p.limits,3),p.config['max_root_lift_m']]
    # Check physical-coordinate full geometry and nonlinear norm derivatives at seed.
    values,jac=pair(current);direction=np.random.default_rng(716).normal(size=p.dim);direction/=np.linalg.norm(direction);h=1e-6
    with torch.no_grad():
        plus=np.r_[p.geometry_slack(p.t(current+h*direction),.0001).numpy()[order]*row_scale,norm_slack_and_jacobian(current+h*direction,p.limits)[0]]
        minus=np.r_[p.geometry_slack(p.t(current-h*direction),.0001).numpy()[order]*row_scale,norm_slack_and_jacobian(current-h*direction,p.limits)[0]]
    fd=(plus-minus)/(2*h);np.testing.assert_allclose(jac@direction,fd,atol=2e-5,rtol=2e-4)
    save(output/'preflight.json',dict(seed=seed_audit,directional_max_error=float(np.abs(jac@direction-fd).max()),surface_rows=surface_count,initial_protected_normalized_minimum=float(values[surface_count:].min()),scope='Exact seed gates pass; conservative smoothed floor may require extra clearance in the optimization problem.'))
    try:
        for stage in range(limits['stages']):
            record=dict(stage=stage,before=current_audit,attempts=[],accepted=False);history.append(record)
            anchor=current.copy()
            def objective(x):
                delta=(x-anchor)/parameter_scale
                return .0001*.5*float(delta@delta),.0001*delta/parameter_scale
            for trust in limits['trust_degrees']:
                radius=np.r_[np.full(p.dim-1,np.deg2rad(trust)),limits['root_trust_m']];lower=anchor-radius;upper=anchor+radius;lower[-1]=max(0,lower[-1]);upper[-1]=min(p.config['max_root_lift_m'],upper[-1])
                result=elastic_solve(objective,pair,anchor,lower,upper,surface_count)
                attempt=dict(trust_degrees=trust,solver_success=bool(result.success),message=str(result.message),iterations=int(result.nit),evaluations=int(result.nfev),restoration_slack_m=result.restoration_slack_m,relaxed_constraint_min=result.relaxed_constraint_min,proposal_parameters=physical(result.x).tolist(),backtracks=[]);record['attempts'].append(attempt)
                for step in range(limits['backtracks']):
                    alpha=.5**step;trial=anchor+alpha*(result.x-anchor);audit,_=p.independent(physical(trial));protected=protected_pass(audit,p.config);improvement=clearance_violation(current_audit,p.config)-clearance_violation(audit,p.config)
                    accept=bool(protected and improvement>=limits['minimum_improvement_m']);attempt['backtracks'].append(dict(fraction=alpha,audit=audit,protected_pass=protected,clearance_improvement_m=improvement,accepted=accept))
                    if accept:current=trial;current_audit=audit;record['accepted']=True;record['after']=audit;break
                if record['accepted']:break
            save(output/'progress.json',dict(status='running',history=history,evaluations=evaluations,seconds=time.monotonic()-start,sampled_peak_rss_bytes=peak))
            print(dict(stage=stage,accepted=record['accepted'],clearance_violation_m=clearance_violation(current_audit,p.config),evaluations=evaluations),flush=True)
            if current_audit['pose_witness_passed']:stop='full_pose_witness';break
            if not record['accepted']:stop='no_guarded_improvement';break
    except TimeoutError as e:status='interrupted_resource_guard';stop=str(e)
    parameters=physical(current);audit,motion=p.independent(parameters);np.savez(output/'pose.npz',**motion)
    with torch.no_grad():_,_,_,tv=p.fk(p.t(parameters))
    nv=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);skin_error=float(np.max(np.abs(tv.numpy()-nv)))
    if skin_error>2e-6:raise ValueError('Independent skin mismatch')
    for name,digest in protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed')
    for n,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/n)!=digest:raise ValueError('Implementation changed')
    save(output/'result.json',dict(at=now(),status=status,stop_reason=stop,seconds=time.monotonic()-start,evaluations=evaluations,sampled_peak_rss_bytes=peak,seed=seed_audit,candidate=audit,parameters=parameters.tolist(),history=history,independent_skin_max_error_m=skin_error,pose_sha256=sha256(output/'pose.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    save(output/'pipeline.json',dict(status=status,pose_witness_passed=audit['pose_witness_passed'],quality_approved=False));print(dict(status=status,stop=stop,audit=audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('seed_report',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.seed_report,args.output)
