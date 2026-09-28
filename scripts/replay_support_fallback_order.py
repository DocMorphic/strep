"""Check fallback selection on frozen real proposals; no new motion export."""
import copy
from pathlib import Path
import sys
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from compare_midpoint_support import verified
from coupled_support_context import context
from midpoint_support_block import MidpointCoupledBlock
from probe_support_backtracking import replay
import support_backtracking_fallback as fallback


def run(study,output):
    protocol,completion=verified(study)
    # Only search-control changes are allowed; the real constraint evaluator is identical.
    for name,digest in protocol['implementation'].items():
        if name not in ('coupled_support_block.py','study_coupled_support.py') and sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Source constraint implementation changed')
    output.mkdir(parents=True,exist_ok=False)
    p=psutil.Process();save(output/'runner.json',dict(pid=p.pid,created=p.create_time()))
    inputs={str(study/'completion.json'):sha256(study/'completion.json')}
    for name in ['support_backtracking_fallback.py','replay_support_fallback_order.py','probe_support_backtracking.py','coupled_support_block.py']:
        inputs[str(ROOT/'scripts'/name)]=sha256(ROOT/'scripts'/name)
    rows=[]
    with threadpool_limits(limits=1):
        for case,block_index,iteration in [('motion-036-rig-02',1,1),('motion-031-rig-02',0,-1)]:
            folder=study/case;path=folder/'solver.json';inputs[str(path)]=sha256(path)
            logs=read(path)['blocks'];ctx=context(folder/'base',folder/'base/selected/character.glb')
            values=ctx['initial'].copy()
            for saved in logs[:block_index]:values=replay(values,saved['solver'])
            source=logs[block_index]['solver'];iteration=iteration if iteration>=0 else len(source['history'])-1
            prefix=copy.deepcopy(source);prefix['history']=prefix['history'][:iteration]
            values=replay(values,prefix)
            problem=MidpointCoupledBlock(ctx['fitter'],ctx['oracle'],values,ctx['source_world'],ctx['source_points'],
                source['frames'],ctx['envelope'],ctx['targets'])
            expected_x=values[problem.frames].ravel().copy()
            recorded=source['history'][iteration]['attempts'];by_trust={a['trust']:a for a in recorded};calls=[]
            def recorded_direction(problem_arg,x,trust):
                if problem_arg is not problem or not np.array_equal(x,expected_x):raise ValueError('Proposal replay state changed')
                a=copy.deepcopy(by_trust[trust]);calls.append(trust)
                if abs(problem.pair(x)[0]-a.get('objective',problem.pair(x)[0]))>1e-10:raise ValueError('Recorded proposal objective differs')
                delta=np.asarray(a['delta']) if 'delta' in a else None
                a.pop('trials',None);return delta,a
            original_direction=fallback.direction
            try:
                fallback.direction=recorded_direction
                result,log=fallback.solve(problem,steps=1,trusts=tuple(by_trust))
            finally:fallback.direction=original_direction
            retained=[dict(trust=a['trust'],**t) for a in log['history'][0]['attempts'] for t in a['trials'] if t['accepted']]
            if len(retained)!=1:raise ValueError('Expected exactly one demonstrated retained step')
            if case=='motion-036-rig-02' and (retained[0]['trust']!=.001 or retained[0]['fraction']!=.5 or retained[0]['phase']!='original'):
                raise ValueError('Legacy trust priority was not preserved')
            if case=='motion-031-rig-02' and retained[0]['phase']!='fallback':raise ValueError('Expected original search exhaustion before fallback')
            rows.append(dict(case=case,block=block_index,iteration=iteration,direction_source='recorded, not recomputed',
                calls=calls,initial_objective=log['initial_objective'],final_objective=log['final_objective'],retained=retained,log=log))
            save(output/'progress.json',dict(rows=rows))
            del problem,ctx
    for name,digest in inputs.items():
        if sha256(name)!=digest:raise ValueError('Replay evidence changed')
    save(output/'completion.json',dict(at=now(),inputs=inputs,rows=rows,quality_approved=False,
        scope='Two real recorded-proposal selection checks. No recomputed conic directions, multi-step rollout, export, engine or human validation.'))
    print([dict(case=r['case'],phase=r['retained'][0]['phase'],objective=r['final_objective']) for r in rows])


if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
