"""Explicit matching rules for distinct controlled support experiments."""


def match_backtracking_protocols(before, after):
    variable = {'at', 'scope', 'implementation', 'fractions'}
    if {k:v for k,v in before.items() if k not in variable} != {k:v for k,v in after.items() if k not in variable}:
        raise ValueError('Backtracking comparison changed inputs, limits or iteration budget')
    steps = before['steps_per_block']
    if type(steps) is not int or not 1 <= steps <= 30 or not before.get('midpoint_constraints'):
        raise ValueError('Finite identical step budgets and midpoint constraints required')
    a,b = before['fractions'],after['fractions']
    if not isinstance(a,list) or not isinstance(b,list) or any(type(f) not in (int,float) for f in a+b):
        raise ValueError('Numeric fraction schedules required')
    if a != [1., .5, .25, .125] or not 5 <= len(b) <= 11 or b != [2.**-n for n in range(len(b))]:
        raise ValueError('Expected an extension of the original dyadic backtracking schedule')
    if set(before['implementation']) != set(after['implementation']):
        raise ValueError('Implementation dependency set changed')
    changed = sorted(k for k in before['implementation'] if before['implementation'][k] != after['implementation'][k])
    if not set(changed) <= {'coupled_support_block.py', 'study_coupled_support.py'}:
        raise ValueError('Constraint, export or validation implementation changed')
    return changed


def match_studies(before, after, kind):
    if kind == 'iterations':
        from compare_support_iterations import match_protocols
        return match_protocols(before, after)
    if kind == 'backtracking':
        return match_backtracking_protocols(before, after)
    raise ValueError('Unknown comparison kind')
