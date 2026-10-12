"""Bounded two-choice storage proposals, checked against every original row.

Experimental explicit search; existing single-component fitting stays unchanged.
Pairs coordinate different components at one key or the same component at two
adjacent editable keys of one track. Absolute choices never accumulate steps.
"""
import copy
from native_component_storage_search import IDENTITY,apply_choice,plan as single_plan
from native_component_storage_repair import ComponentAdjustedEdits
from native_rotation_storage_search import search as checked_search

FIELDS=set(IDENTITY)|{'step'}


def option_identity(row):
    if (not isinstance(row,dict) or set(row)!=FIELDS or type(row['actor']) is not str or not row['actor']
            or type(row['path']) is not str or row['path'] not in ('rotation','translation')
            or any(type(row[k]) is not int or row[k]<0 for k in ('node','key_index','component'))
            or row['component']>=(4 if row['path']=='rotation' else 3)
            or type(row['step']) is not int or row['step'] not in (-1,0,1)):
        raise ValueError('Complete typed absolute component option required')
    return tuple(row[k] for k in IDENTITY)


def apply_pair(corrections,bundle):
    if not isinstance(bundle,dict) or set(bundle)!={'choices'} or not isinstance(bundle['choices'],list) or len(bundle['choices'])!=2:
        raise ValueError('Exactly two explicit component choices required')
    a,b=bundle['choices'];ia,ib=option_identity(a),option_identity(b)
    same_key=ia[:4]==ib[:4] and ia[4]!=ib[4]
    adjacent=ia[:3]==ib[:3] and ia[4]==ib[4] and abs(ia[3]-ib[3])==1
    if not (same_key or adjacent):raise ValueError('Distinct same-key components or adjacent-key same-component choices required')
    return apply_choice(apply_choice(corrections,a),b)


def pair_options(options,*,maximum_candidates=65536):
    """Complete pair population, interleaved across tracks and pair families.

    The full count is bounded before returning; exported finite prefixes are
    separate search budgets. No option/key/row is silently removed for capacity.
    """
    if type(maximum_candidates) is not int or not 1<=maximum_candidates<=65536 or not isinstance(options,list):
        raise ValueError('Explicit complete pair population budget required')
    identities=[option_identity(r) for r in options];seen=set();by_key={}
    for i,(row,identity) in enumerate(zip(options,identities)):
        absolute=identity+(row['step'],)
        if absolute in seen:raise ValueError('Duplicate absolute option')
        seen.add(absolute);by_key.setdefault(identity[:4],[]).append(i)
    groups={};count=0
    for i,ia in enumerate(identities):
        peers=[]
        for j in by_key[ia[:4]]:
            if j>i and identities[j][4]!=ia[4]:peers.append((j,'same-key'))
        for key in (ia[3]-1,ia[3]+1):
            for j in by_key.get(ia[:3]+(key,),[]):
                if j>i and identities[j][4]==ia[4]:peers.append((j,'adjacent-key'))
        for j,family in peers:
            count+=1
            if count>maximum_candidates:raise ValueError('Complete paired option population exceeds declared budget')
            groups.setdefault(ia[:3]+(family,),[]).append((i,j))
    result=[]
    for turn in range(max(map(len,groups.values()),default=0)):
        for group in groups.values():
            if turn<len(group):
                a,b=group[turn];result.append(dict(choices=[copy.deepcopy(options[a]),copy.deepcopy(options[b])]))
    assert len(result)==count
    return result


def plan(problem,worlds,corrections,*,allowed_paths=('rotation','translation')):
    options,failures=single_plan(problem,worlds,corrections,allowed_paths=allowed_paths)
    return pair_options(options),failures


def search(problem,value,policy,corrections,decode,*,stages=8,probes_per_stage=32):
    corrections,report=checked_search(problem,value,policy,corrections,decode,stages=stages,probes_per_stage=probes_per_stage,
        _adjusted_type=ComponentAdjustedEdits,_planner=lambda p,w,c:plan(p,w,c,allowed_paths=policy['allowed_paths']),
        _chooser=apply_pair,_result_schema='strep-native-component-pair-search-v1')
    report.update(maximum_pair_population=65536,
        scope='Finite first-improvement search of two absolute component choices on one track: different components at one key, or the same component at adjacent editable keys. Complete bounded pair population interleaved across actors/tracks/families; finite exported prefixes are not exhaustive. Original controls, policy, caps, scales and all decoded rows remain required. No geometry, motion quality or feasibility certificate.')
    return corrections,report
