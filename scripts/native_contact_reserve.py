"""Explicit tighter solver targets; original contact acceptance stays separate.

This adapter copies an existing SceneProblem's contact rows only. It does not
change source rates, edit permissions, scene intent, geometry or acceptance.
"""
import copy
import math
import re
import numpy as np

SCHEMA = 'strep-native-contact-reserve-v1'


def guided_problem(problem, request, contacts_sha256, *, initial=None):
    if (not isinstance(request, dict)
            or set(request) != {'schema', 'contacts_sha256', 'reserves_m'}
            or request['schema'] != SCHEMA
            or not isinstance(contacts_sha256, str)
            or re.fullmatch(r'[0-9a-f]{64}', contacts_sha256) is None
            or request['contacts_sha256'] != contacts_sha256):
        raise ValueError('Exact contact-bound reserve request required')
    reserves = request['reserves_m']
    if not isinstance(reserves, dict) or not reserves:
        raise ValueError('Explicit nonempty contact reserve mapping required')
    original = {row['entry']['authored']['id']: row for row in problem.rows}
    if len(original) != len(problem.rows) or set(reserves) - set(original):
        raise ValueError('Distinct existing contact identifiers required')
    bindings = {}
    for identifier, reserve in reserves.items():
        limit = original[identifier]['entry']['authored']['limits']['position_m']
        if (type(reserve) not in (int, float) or not math.isfinite(reserve)
                or not isinstance(limit, (int, float)) or isinstance(limit, bool)
                or not math.isfinite(limit) or not 0 < reserve < limit):
            raise ValueError('Finite positive reserve smaller than its original position limit required')
        bindings[identifier] = dict(original_limit_m=float(limit), reserve_m=float(reserve),
                                    solver_target_m=float(limit - reserve))
    guided = copy.copy(problem)
    guided.rows = copy.deepcopy(problem.rows)
    for row in guided.rows:
        authored = row['entry']['authored']
        if authored['id'] in bindings:
            authored['limits']['position_m'] = bindings[authored['id']]['solver_target_m']
    if initial is not None:
        value = problem.edits.controls(initial)
        if np.any(value < problem.lower) or np.any(value > problem.upper):
            raise ValueError('Reserve seed exceeds original control bounds')
        guided.initial = value.copy()
    else:
        guided.initial = problem.initial.copy()
    return guided, dict(schema=SCHEMA, contacts_sha256=contacts_sha256,
        targets=bindings, role='optimization-guidance-only',
        original_acceptance_limits_unchanged=True, source_rate_caps_unchanged=True,
        query_populations_unchanged=True, geometry_policy_unchanged=True,
        quality_approved=False, release_approved=False)
