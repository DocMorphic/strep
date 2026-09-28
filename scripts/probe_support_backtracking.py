"""Replay retained block states and test shorter recorded rejected directions."""
import argparse
import gc
from pathlib import Path
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from compare_midpoint_support import verified
from audit_authoring_intent import check_files
from coupled_support_context import context
from midpoint_support_block import MidpointCoupledBlock


def replay(initial, solver):
    values = np.asarray(initial, float).copy()
    frames = np.asarray(solver['frames'], int)
    if frames.ndim != 1 or not len(frames) or len(set(frames)) != len(frames) or np.any(frames < 0) or np.any(frames >= len(values)):
        raise ValueError('Valid unique frame indices required')
    x = values[frames].ravel().copy()
    for step in solver['history']:
        accepted = [(a, t) for a in step['attempts'] for t in a.get('trials', []) if t['accepted']]
        if len(accepted) != int(step['accepted']):
            raise ValueError('Accepted history is ambiguous')
        if not accepted:
            continue
        attempt, trial = accepted[0]
        delta = np.asarray(attempt['delta'], float)
        fraction = trial['fraction']
        if delta.shape != x.shape or not np.isfinite(delta).all() or not np.isfinite(fraction) or not 0 < fraction <= 1:
            raise ValueError('Invalid recorded step')
        x += fraction * delta
    values[frames] = x.reshape(len(frames), values.shape[1])
    return values


def run(study, output, selected_case):
    if output.exists():
        raise ValueError('Preserve previous probe')
    protocol, completion = verified(study)
    check_files(ROOT/'scripts', protocol['implementation'])
    if not protocol.get('midpoint_constraints'):
        raise ValueError('Expected midpoint-constrained source')
    if selected_case not in [c['id'] for c in protocol['cases'] if c['eligible']]:
        raise ValueError('Choose an eligible source case')
    output.mkdir(parents=True)
    process = psutil.Process()
    save(output/'runner.json', dict(pid=process.pid, created=process.create_time()))
    fractions = [2.**-n for n in range(4, 11)]
    consulted = {str(study/'completion.json'):sha256(study/'completion.json'),
                 str(study/'protocol.json'):sha256(study/'protocol.json'),
                 str(Path(__file__).resolve()):sha256(__file__)}
    save(output/'protocol.json', dict(at=now(), study=str(study), case=selected_case,
        fractions=fractions, source_completion_sha256=sha256(study/'completion.json'),
        implementation_sha256=sha256(__file__), quality_approved=False,
        scope='Single-case diagnostic on recorded final directions. Same nonlinear margins, midpoint guard and objective-decrease threshold. No selected asset changed or exported.'))
    rows=[]
    with threadpool_limits(limits=1):
        for case in protocol['cases']:
            row=dict(id=case['id'],eligible=case['eligible'],status='not_targeted' if not case['eligible'] else 'not_probed')
            if case['id'] != selected_case:
                rows.append(row);continue
            folder=study/case['id'];base=folder/'base'
            for name in ['solver.json','parameters.npz','selection.json']:
                consulted[str(folder/name)]=sha256(folder/name)
            logs=read(folder/'solver.json')['blocks']
            ctx=context(base,base/'selected/character.glb')
            values=ctx['initial'].copy(); blocks=[]
            for index, saved in enumerate(logs):
                solver=saved['solver'];before=values.copy();values=replay(before,solver)
                result=dict(index=index,frames=solver['frames'],residual=solver['final_objective'],trials=[])
                if solver['final_objective']>1e-9 and not solver['history'][-1]['accepted']:
                    problem=MidpointCoupledBlock(ctx['fitter'],ctx['oracle'],before,ctx['source_world'],ctx['source_points'],solver['frames'],ctx['envelope'],ctx['targets'])
                    x=values[problem.frames].ravel();old=problem.pair(x)[0]
                    if abs(old-solver['final_objective'])>1e-10:
                        raise ValueError('Replayed objective differs from recorded state')
                    for attempt_index, attempt in enumerate(solver['history'][-1]['attempts']):
                        if 'delta' not in attempt or attempt.get('predicted_change',0)>=0:continue
                        delta=np.asarray(attempt['delta'],float)
                        for fraction in fractions:
                            save(output/'pipeline.json',dict(status='probing',case=case['id'],block=index,attempt=attempt_index,fraction=fraction))
                            objective,_,constraints,trial_values=problem.pair(x+fraction*delta)
                            margins=constraints.margins()
                            feasible=all(np.isfinite(v) and v>=-1e-9 for v in margins.values())
                            geometry,excess=problem.midpoint_guard(trial_values) if feasible else (False,None)
                            improves=objective<old-max(1e-9,old*.001)
                            result['trials'].append(dict(attempt=attempt_index,trust=attempt['trust'],fraction=fraction,objective=objective,
                                margins=margins,midpoint_pass=geometry,midpoint_excess_m=excess,
                                sufficient_decrease=bool(improves),would_accept=bool(feasible and geometry and improves)))
                            if feasible and geometry and improves:break
                    del problem
                result['acceptable_shorter_steps']=sum(t['would_accept'] for t in result['trials'])
                blocks.append(result);save(output/'blocks.json',dict(blocks=blocks))
            with np.load(folder/'parameters.npz') as parameters:
                error=float(np.max(np.abs(values-parameters['parameters'])))
                if error>1e-12:raise ValueError('Replayed final parameters differ from saved output')
            row.update(status='probed',blocks=blocks,replay_parameter_error=error)
            rows.append(row);del ctx;gc.collect()
    check_files(ROOT/'scripts',protocol['implementation'])
    check_files(study,completion['files'])
    for name,digest in consulted.items():
        if sha256(name)!=digest:raise ValueError('Probe source changed')
    save(output/'completion.json',dict(at=now(),rows=rows,inputs=consulted,protocol_sha256=sha256(output/'protocol.json'),
        quality_approved=False,scope='Recorded-direction diagnostic only; accepted probe points are not exported or human-approved motions. Unprobed population rows remain explicit.'))
    save(output/'pipeline.json',dict(status='complete',completion_sha256=sha256(output/'completion.json')))
    print(dict(case=selected_case,blocks=[dict(index=b['index'],acceptable_shorter_steps=b['acceptable_shorter_steps']) for b in blocks]))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('study',type=Path);p.add_argument('case');p.add_argument('output',type=Path)
    a=p.parse_args();run(a.study.resolve(),a.output.resolve(),a.case)
