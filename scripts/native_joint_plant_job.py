"""Source-bound joint contact/rate search with independently decoded probes."""
from pathlib import Path
import argparse
import shutil
import sys
import numpy as np
import scipy
from strep import read,save,sha256,now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_foot_plant import policy_rows,audit,preserve
from native_joint_plant import JointPlantProblem
from native_support_feasibility import colors,colored_jacobian,direction,merit
from native_support_roundtrip import preview_values
from native_leg_floor import export_rotations
from paired_temporal_neighbor import rotation_channels


def restore(problem,evaluate,*,iterations=4,trust=.001,native_roundtrip=True,observe=None):
    if type(iterations) is not int or not 1<=iterations<=16 or type(trust) not in (int,float) or not np.isfinite(trust) or not 0<trust<=.02:
        raise ValueError('Choose 1–16 joint iterations and positive trust up to .02 radians')
    if type(native_roundtrip) is not bool:raise ValueError('Explicit native preview mode required')
    x=problem.initial.copy();current=evaluate(x,'start');initial=merit(current)
    pattern=problem.sparsity(native_roundtrip=native_roundtrip);groups=colors(pattern);history=[];radius=float(trust)
    reason='iteration_budget'
    for iteration in range(1,iterations+1):
        before=merit(current)
        if before[0]==0:reason='sampled_constraints_satisfied';break
        jac=colored_jacobian(lambda z:problem.model(z,quantized=True,native_roundtrip=native_roundtrip),
            x,problem.lower,problem.upper,pattern,groups,step=1e-5)
        delta,info=direction(x,current,jac,problem.lower,problem.upper,radius)
        info.update(iteration=iteration,before_merit=list(before),probes=[]);chosen=None
        if delta is not None:
            for backoff in range(10):
                fraction=.5**backoff;z=np.clip(x+delta*fraction,problem.lower,problem.upper)
                g=evaluate(z,f'{iteration}-{backoff}');score=merit(g)
                ok=score[0]<before[0]-1e-12 or abs(score[0]-before[0])<=1e-12 and score[1]<before[1]-1e-15
                info['probes'].append(dict(fraction=fraction,merit=list(score),accepted=bool(ok)))
                if ok:x=z;current=g;chosen=fraction;break
        info.update(selected_fraction=chosen,after_merit=list(merit(current)));history.append(info)
        if observe:observe(info)
        if chosen is None:
            radius*=.25
            if radius<1e-8:reason='serialized_line_search_stalled';break
    if merit(current)[0]==0:reason='sampled_constraints_satisfied'
    return x,dict(initial_merit=list(initial),final_merit=list(merit(current)),iterations=len(history),
        maximum_iterations=iterations,trust_radians=trust,structural_colors=len(groups),difference_step_radians=1e-5,
        native_roundtrip=native_roundtrip,history=history,reason=reason,quality_approved=False)


def authored_audit(source,candidate,spec,limits):
    result=audit(source,candidate,spec,limits)
    result['authored_clearance_pass']=all(row['minimum_height_m']>=condition['clearance_m']-1e-8
        for row,condition in zip(result['support_screens']['supports'],spec['supports']))
    result['passed']=bool(result['passed'] and result['authored_clearance_pass'])
    return result


def run(source,base,draft,policy_path,output,*,seed=None,iterations=4,trust=.001,native_roundtrip=True,coordinates=False,
        frame_sampling=False,exterior_seed_ramp=False):
    if type(iterations) is not int or not 1<=iterations<=16 or type(trust) not in (int,float) or not np.isfinite(trust) or not 0<trust<=.02:
        raise ValueError('Bounded joint iterations/trust required')
    if type(native_roundtrip) is not bool:raise ValueError('Explicit native preview mode required')
    if type(coordinates) is not bool:raise ValueError('Explicit coordinate mode required')
    if type(frame_sampling) is not bool or type(exterior_seed_ramp) is not bool:raise ValueError('Explicit frame/ramp modes required')
    if coordinates and trust>.001:raise ValueError('Coordinate trust is limited to .001 radians')
    source,base,draft,policy_path,output=map(lambda p:Path(p).resolve(),(source,base,draft,policy_path,output))
    seed=base if seed is None else Path(seed).resolve()
    if output.exists():raise ValueError('Choose a fresh joint-plant output directory')
    inputs={str(p):sha256(p) for p in (source,base,draft,policy_path,seed)}
    spec=read(draft);rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    _,rows=validate(spec,rig,reader,sha256(source));limits=policy_rows(read(policy_path),source,base,draft,rows)
    baseline=authored_audit(source,base,spec,limits);warm_audit=authored_audit(source,seed,spec,limits)
    warm=RigAsset.load(seed);warm_reader=NativeSupportSampler(warm.document,warm.binary,0);preserve(reader,warm_reader,rows)
    problem_type=JointPlantProblem
    if frame_sampling:
        from native_frame_plant import FramePlantProblem
        problem_type=FramePlantProblem
    problem=problem_type(rig,reader,rows,limits,warm_reader)
    if exterior_seed_ramp:
        from native_frame_plant import exterior_ramp
        problem.initial=exterior_ramp(problem,problem.initial)
    problem.native_roundtrip=native_roundtrip
    output.mkdir();shutil.copyfile(base,output/'input.glb');archive=output/'implementation';archive.mkdir()
    from native_review_support import method_names
    names=set(method_names())|{'native_joint_plant.py','native_joint_plant_job.py','native_foot_plant.py',
        'native_support_rates.py','native_support_feasibility.py','native_support_roundtrip.py',
        'native_support_orientation.py','native_support_swivel.py','native_support_path.py'}
    if coordinates:names.add('native_support_coordinates.py')
    if frame_sampling or exterior_seed_ramp:names.update({'native_frame_plant.py','engine_contact_sampling.py'})
    methods={}
    for name in sorted(names):
        path=Path(__file__).resolve().parent/name;methods[str(path)]=sha256(path);shutil.copyfile(path,archive/name)
    request=dict(at=now(),inputs_sha256=inputs,implementation_sha256=methods,spec=spec,policy=read(policy_path),
        iterations=iterations,trust_radians=trust,native_roundtrip=native_roundtrip,coordinate_search=coordinates,
        python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
        scope='Interior leg rotations, source anchor contacts/support/rates; real native NPZ conversion still independent',quality_approved=False)
    if frame_sampling:
        from engine_contact_sampling import contract,contract_sha256
        request.update(frame_sampling_contract=contract(),frame_sampling_contract_sha256=contract_sha256(),
                       proposal_skin='Native, not imported engine skin')
    if exterior_seed_ramp:request['exterior_seed_ramp']='Cubic Hermite exterior native rotation-vector controls; LINEAR exported keys, no C1 guarantee'
    save(output/'request.json',request)
    save(output/'pipeline.json',dict(status='processing'));probes=[];decoded_cache={}
    try:
        def evaluate(x,label):
            values,_=problem.rotations(x);path=output/f'probe-{label}.glb';export_rotations(rig.document,rig.binary,values,path)
            def decoded(file):
                digest=sha256(file)
                if digest in decoded_cache:
                    g,q,original=decoded_cache[digest]
                    return g,q,original
                asset=RigAsset.load(file);s=NativeSupportSampler(asset.document,asset.binary,0)
                world=np.array([s.sample(float(t)) for t in problem.times]);channels=rotation_channels(asset.document,asset.binary)
                q={n:channels[n][2] for n in problem.nodes}
                g=problem.constraints(q,world);decoded_cache[digest]=(g,q,file.name)
                return g,q,None
            raw,q,reused=decoded(path);record=dict(label=label,file=path.name,sha256=sha256(path),raw_merit=list(merit(raw)),
                raw_decode_reused_from=reused,
                raw_constraints_pass=bool(np.all(raw<=0)))
            g=raw
            if native_roundtrip:
                preview=output/f'probe-{label}.preview.glb'
                export_rotations(rig.document,rig.binary,preview_values(q,problem.channels),preview)
                native,_,reused=decoded(preview);record.update(preview_file=preview.name,preview_sha256=sha256(preview),preview_decode_reused_from=reused,
                    preview_merit=list(merit(native)),preview_constraints_pass=bool(np.all(native<=0)))
                g=np.r_[raw,native]
            record['merit']=list(merit(g));probes.append(record)
            save(path.with_suffix('.json'),dict(record,parameters=x.tolist(),quality_approved=False))
            return g
        def observe(info):
            save(output/'progress.json',dict(status='running',history=info,probes=probes,quality_approved=False))
            print(dict(iteration=info['iteration'],before=info['before_merit'],after=info['after_merit'],
                selection=info.get('selected_screen_index',info.get('selected_fraction'))),flush=True)
        if coordinates:
            from native_support_coordinates import restore as coordinate_restore
            x,optimization=coordinate_restore(problem,problem.initial,evaluate,iterations=iterations,trust=trust,observe=observe)
        else:x,optimization=restore(problem,evaluate,iterations=iterations,trust=trust,native_roundtrip=native_roundtrip,observe=observe)
        optimization.update(method='quantized_coordinate_search' if coordinates else 'lp_minimax_then_l1',
            independently_decoded_unique_glbs=len(decoded_cache))
        evaluate(x,'final');final=probes[-1]
        shutil.copyfile(output/final['file'],output/'proposal.glb')
        report=authored_audit(source,output/'proposal.glb',spec,limits)
        preview_report=authored_audit(source,output/final['preview_file'],spec,limits) if native_roundtrip else None
        accepted=bool(report['passed'] and final['raw_constraints_pass'] and
            (not native_roundtrip or preview_report['passed'] and final['preview_constraints_pass']) and not baseline['passed'])
        shutil.copyfile(output/'proposal.glb' if accepted else base,output/'candidate.glb')
        chosen=authored_audit(source,output/'candidate.glb',spec,limits)
        controls=dict(schema='strep-native-joint-plant-controls-v1',parameters=x.tolist(),lower=problem.lower.tolist(),upper=problem.upper.tolist(),
            intervals=[dict(id=d['row']['id'],chain=d['row']['chain'],clock_s=d['clock'].tolist(),edit_keys=d['row']['edit_keys'],
                key_indices=d['free'].tolist(),control_indices=d['ids'].tolist(),patch_vertex_references=d['patch_vertex_references']) for d in problem.data])
        save(output/'controls.json',controls)
        if any(sha256(p)!=d for p,d in {**inputs,**methods}.items()):raise ValueError('Joint plant inputs or methods changed')
        result=dict(status='complete',at=now(),retained_input=not accepted,
            retention_reason=None if accepted else 'input_already_satisfies_all_gates' if baseline['passed'] else 'joint_plant_proposal_failed_gates',
            baseline=baseline,warm_seed_audit=warm_audit,proposal=report,preview_proposal=preview_report,selected=chosen,
            optimization=optimization,probes=probes,candidate_sha256=sha256(output/'candidate.glb'),proposal_sha256=sha256(output/'proposal.glb'),
            output_support_samples_pass=chosen['support_screens']['support_samples_pass'],
            quality_approved=False,training_admitted=False,release_approved=False,native_npz_conversion_verified=False)
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete'));return result
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','base','draft','policy','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--seed',type=Path);parser.add_argument('--iterations',type=int,default=4)
    parser.add_argument('--trust',type=float,default=.001);parser.add_argument('--raw-only',action='store_true')
    parser.add_argument('--coordinates',action='store_true',help='Bounded FP32 key coordinate screens with independent decoded acceptance')
    parser.add_argument('--frame-sampling',action='store_true',help='Constrain every fixed game-frame clock in native skin; actual engine import remains independent')
    parser.add_argument('--exterior-seed-ramp',action='store_true',help='Initialize exterior correction keys with Hermite ramps inside the original edit window')
    args=parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=1):
        result=run(args.source,args.base,args.draft,args.policy,args.output,seed=args.seed,iterations=args.iterations,trust=args.trust,
                   native_roundtrip=not args.raw_only,coordinates=args.coordinates,
                   frame_sampling=args.frame_sampling,exterior_seed_ramp=args.exterior_seed_ramp)
        print(dict(retained_input=result['retained_input'],reason=result['retention_reason'],merit=result['optimization']['final_merit']))
