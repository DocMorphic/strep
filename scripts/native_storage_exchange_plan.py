"""Complete discrete exchange proposals under the original storage budget.

This planner does not observe motion, check authoring permissions or select a
candidate. Every proposed export still needs the original native and scene
gates. It restores one absolute component before adding another at capacity;
it never accumulates neighboring Float32 steps or enlarges the policy.
"""
import copy

FIELDS = ('actor', 'node', 'key_index', 'component', 'step')
IDENTITY = FIELDS[:-1]


def _row(row, *, option=False):
    if (not isinstance(row, dict) or set(row) != set(FIELDS)
            or type(row['actor']) is not str or not row['actor']
            or any(type(row[k]) is not int or row[k] < 0 for k in ('node', 'key_index', 'component'))
            or row['component'] > 3 or type(row['step']) is not int
            or row['step'] not in ((-1, 0, 1) if option else (-1, 1))):
        raise ValueError('Explicit absolute quaternion component choice required')
    return tuple(row[k] for k in IDENTITY)


def _seed(corrections, maximum_corrections):
    if (type(maximum_corrections) is not int or not 1 <= maximum_corrections <= 64
            or not isinstance(corrections, list) or len(corrections) > maximum_corrections):
        raise ValueError('Original bounded complete correction population required')
    used = {}
    for row in corrections:
        identity = _row(row)
        if identity in used:
            raise ValueError('Duplicate absolute correction identity')
        used[identity] = row
    return used


def exchange_plan(corrections, options, maximum_corrections, *, maximum_candidates=16384):
    """Preserve option order and enumerate every eligible one-restoration swap.

    Existing-identity replacements/restores, and additions below capacity,
    remain direct proposals. At capacity, each unused nonzero option is paired
    with every current restoration in seed order. The complete population is
    counted before construction; an insufficient budget rejects the whole plan.
    No native observation, applicability, feasibility or quality is implied.
    """
    used = _seed(corrections, maximum_corrections)
    if (not isinstance(options, list) or len(options) > 1024
            or type(maximum_candidates) is not int or not 1 <= maximum_candidates <= 16384):
        raise ValueError('Explicit complete option and candidate budgets required')
    seen = set()
    count = 0
    for option in options:
        identity = _row(option, option=True)
        absolute = identity + (option['step'],)
        if absolute in seen:
            raise ValueError('Duplicate absolute option')
        seen.add(absolute)
        if (identity not in used and option['step'] == 0
                or identity in used and option['step'] == used[identity]['step']):
            raise ValueError('A proposal must change an existing absolute value')
        count += len(corrections) if identity not in used and len(used) == maximum_corrections else 1
    if count > maximum_candidates:
        raise ValueError('Complete exchange population exceeds the candidate budget')
    result = []
    for option in options:
        identity = tuple(option[k] for k in IDENTITY)
        restorations = corrections if identity not in used and len(used) == maximum_corrections else [None]
        for restored in restorations:
            result.append(dict(choice=copy.deepcopy(option), restored=copy.deepcopy(restored)))
    assert len(result) == count
    return result


def apply_exchange(corrections, proposal, maximum_corrections):
    """Apply one explicit proposal to a copy of its current correction list."""
    used = _seed(corrections, maximum_corrections)
    if not isinstance(proposal, dict) or set(proposal) != {'choice', 'restored'}:
        raise ValueError('Explicit complete exchange proposal required')
    choice, restored = proposal['choice'], proposal['restored']
    identity = _row(choice, option=True)
    removed = set()
    if restored is not None:
        restoration = _row(restored)
        if (restoration not in used or used[restoration] != restored
                or identity in used or choice['step'] == 0
                or len(used) != maximum_corrections):
            raise ValueError('Restoration must exactly match the current at-capacity seed')
        removed.add(restoration)
    if (identity not in used and choice['step'] == 0
            or identity in used and used[identity]['step'] == choice['step']):
        raise ValueError('A proposal must change an existing absolute value')
    removed.add(identity)
    output = [copy.deepcopy(r) for r in corrections if tuple(r[k] for k in IDENTITY) not in removed]
    if choice['step']:
        output.append(copy.deepcopy(choice))
    _seed(output, maximum_corrections)
    return output
