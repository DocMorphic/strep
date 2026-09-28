"""Reconstruct bounded accepted proposal histories without solver caches."""
import numpy as np


def reconstruct(initial,solver,request,frames,free):
    selected=np.ix_(frames,free);coordinates=initial[selected].ravel().copy()
    np.testing.assert_array_equal(coordinates,solver['starting_coordinates'])
    if len(solver['history'])>request['steps']:raise ValueError('Exceeded step budget')
    schedule=request.get('proposal_schedule',[dict(trust=t) for t in request['trusts']])
    for step in solver['history']:
        accepted=[]
        if len(step['attempts'])>len(schedule):raise ValueError('Exceeded trust budget')
        for index,attempt in enumerate(step['attempts']):
            entry=schedule[index]
            if attempt['trust']!=entry['trust'] or len(attempt['trials'])>8:raise ValueError('Proposal budget differs')
            if 'buffer_scale' in entry:
                if attempt['buffer_scale']!=entry['buffer_scale']:raise ValueError('Buffer schedule differs')
                expected={k:v*entry['buffer_scale'] for k,v in request['proposal_buffers'].items()}
                if attempt['proposal_buffers']!=expected:raise ValueError('Proposal buffers differ')
            for i,trial in enumerate(attempt['trials']):
                if trial['fraction']!=.5**i:raise ValueError('Safeguard schedule differs')
                if trial['accepted']:
                    delta=np.asarray(attempt['proposed_delta'])
                    if delta.shape!=coordinates.shape or not np.isfinite(delta).all() or np.abs(delta).max()>attempt['trust']+1e-12:
                        raise ValueError('Accepted step exceeds coordinate bounds')
                    if not trial['geometry'] or trial['minimum_constraint']<-1e-8 or trial['objective']>=step['objective_before']-1e-9:
                        raise ValueError('Accepted-step record contradicts safeguards')
                    accepted.append(trial['fraction']*delta)
        if len(accepted)!=int(step['accepted']):raise ValueError('Ambiguous accepted step')
        if accepted:coordinates+=accepted[0]
    np.testing.assert_allclose(coordinates,solver['final_coordinates'],atol=1e-14,rtol=0)
    expected=initial.copy();expected[selected]=coordinates.reshape(len(frames),len(free));return expected
