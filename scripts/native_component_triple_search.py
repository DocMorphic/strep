"""Explicit three-choice stored-key proposals under the original one-neighbor policy."""
import copy
from itertools import combinations,product,chain
from native_component_pair_search import option_identity
from native_component_storage_search import apply_choice,plan as single_plan
from native_component_storage_repair import ComponentAdjustedEdits
from native_rotation_storage_search import search as checked_search


def apply_triple(corrections,bundle):
    if not isinstance(bundle,dict) or set(bundle)!={'choices'} or not isinstance(bundle['choices'],list) or len(bundle['choices'])!=3:
        raise ValueError('Exactly three explicit component choices required')
    identities=[option_identity(r) for r in bundle['choices']]
    same_key=len({i[:4] for i in identities})==1 and len({i[4] for i in identities})==3
    keys=sorted(i[3] for i in identities)
    adjacent=len({i[:3]+(i[4],) for i in identities})==1 and keys==list(range(keys[0],keys[0]+3))
    if not (same_key or adjacent):raise ValueError('Three same-key components or three consecutive keys on one component required')
    result=copy.deepcopy(corrections)
    for row in bundle['choices']:result=apply_choice(result,row)
    return result


def triple_options(options,*,maximum_candidates=65536):
    if type(maximum_candidates) is not int or not 1<=maximum_candidates<=65536 or not isinstance(options,list):
        raise ValueError('Explicit complete triple population budget required')
    by_key={};by_component={};seen=set()
    for index,row in enumerate(options):
        identity=option_identity(row);absolute=identity+(row['step'],)
        if absolute in seen:raise ValueError('Duplicate absolute component option')
        seen.add(absolute)
        by_key.setdefault(identity[:4],{}).setdefault(identity[4],[]).append(index)
        by_component.setdefault(identity[:3]+(identity[4],),{}).setdefault(identity[3],[]).append(index)
    groups={};count=0
    def add(group,parts):
        nonlocal count
        count+=len(parts[0])*len(parts[1])*len(parts[2])
        if count>maximum_candidates:raise ValueError('Complete triple population exceeds declared budget')
        groups.setdefault(group,[]).append(parts)
    for key,components in by_key.items():
        for selected in combinations(components,3):add(key[:3]+('same-key',),[components[c] for c in selected])
    for identity,keys in by_component.items():
        for key in sorted(keys):
            if key+1 in keys and key+2 in keys:add(identity[:3]+('consecutive-keys',),[keys[key],keys[key+1],keys[key+2]])
    iterators=[iter(chain.from_iterable(product(*parts) for parts in specs)) for specs in groups.values()]
    result=[]
    while iterators:
        remaining=[]
        for iterator in iterators:
            item=next(iterator,None)
            if item is not None:
                result.append(dict(choices=[copy.deepcopy(options[i]) for i in item]));remaining.append(iterator)
        iterators=remaining
    assert len(result)==count
    return result


def plan(problem,worlds,corrections,*,allowed_paths=('rotation','translation')):
    options,failures=single_plan(problem,worlds,corrections,allowed_paths=allowed_paths)
    return triple_options(options),failures


def search(problem,value,policy,corrections,decode,*,stages=8,probes_per_stage=32):
    corrected,report=checked_search(problem,value,policy,corrections,decode,stages=stages,probes_per_stage=probes_per_stage,
        _adjusted_type=ComponentAdjustedEdits,_planner=lambda p,w,c:plan(p,w,c,allowed_paths=policy['allowed_paths']),
        _chooser=apply_triple,_result_schema='strep-native-component-triple-search-v1')
    report.update(maximum_triple_population=65536,
        scope='Finite first-improvement search of three absolute one-neighbor choices: distinct components at one key or one component at three consecutive keys on one actor/track. Complete bounded family population interleaved across tracks; finite exported prefixes are not exhaustive. All original controls, authoring, policy, caps, scales and decoded conditions remain required. No geometry, quality or feasibility certificate.')
    return corrected,report
