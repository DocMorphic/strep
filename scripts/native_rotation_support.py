"""Conservative support of append-only native LINEAR rotation edits.

This proves input/function identity outside the returned closed intervals for
the native decoder, assuming a valid source clip. Scene/object tracks and actor
placements require separate identity checks before inheriting geometric results.
A multi-time observation is unchanged only if all its probes avoid this support;
central rates and rate derivatives require expansion by their probe radii.
This does not assess geometry, dynamics or engine behavior.
"""
import numpy as np
from gltf_tools import accessor


def rotation_support(source, source_binary, candidate, candidate_binary, nodes):
    """Validate unchanged static inputs/clocks and bound changed-key support."""
    nodes = list(nodes)
    if (any(type(n) is not int or n < 0 or n >= len(source.get('nodes', [])) for n in nodes)
            or len(set(nodes)) != len(nodes)):
        raise ValueError('Distinct source node indices required')
    if candidate_binary[:len(source_binary)] != source_binary:
        raise ValueError('Source binary prefix changed')
    dynamic = {'animations', 'accessors', 'bufferViews', 'buffers'}
    if set(source) != set(candidate) or any(source[k] != candidate[k] for k in source if k not in dynamic):
        raise ValueError('Static document changed')
    for key in ['accessors', 'bufferViews']:
        if candidate.get(key, [])[:len(source.get(key, []))] != source.get(key, []):
            raise ValueError('Source accessor/view prefix changed')
    old_buffers, new_buffers = source.get('buffers', []), candidate.get('buffers', [])
    if (len(old_buffers) != 1 or len(new_buffers) != 1 or old_buffers[0].get('uri')
            or new_buffers[0].get('uri') or new_buffers[0]['byteLength'] < old_buffers[0]['byteLength']
            or {k:v for k,v in old_buffers[0].items() if k != 'byteLength'} !=
               {k:v for k,v in new_buffers[0].items() if k != 'byteLength'}):
        raise ValueError('One unchanged embedded source buffer required')
    if len(source.get('animations', [])) != 1 or len(candidate.get('animations', [])) != 1:
        raise ValueError('One native animation required')
    old, new = source['animations'][0], candidate['animations'][0]
    if ({k:v for k,v in old.items() if k not in ['channels', 'samplers']} !=
            {k:v for k,v in new.items() if k not in ['channels', 'samplers']}
            or len(old['channels']) != len(new['channels'])
            or new['samplers'][:len(old['samplers'])] != old['samplers']):
        raise ValueError('Source animation/channel/sampler structure changed')
    duration = 0.
    for channel in old['channels']:
        if channel['target']['path'] not in ['rotation', 'translation', 'scale']:
            raise ValueError('Unsupported native animation path')
        clock = accessor(source, source_binary, old['samplers'][channel['sampler']]['input']).reshape(-1)
        if not len(clock) or not np.isfinite(clock).all() or clock[0] < 0 or np.any(np.diff(clock) <= 0):
            raise ValueError('Finite increasing native clock required')
        duration = max(duration, float(clock[-1]))
    if duration <= 0:
        raise ValueError('Positive native animation duration required')
    rows, seen, intervals = [], set(), []
    for channel, changed in zip(old['channels'], new['channels']):
        node = channel['target']['node']
        if channel['target']['path'] != 'rotation' or node not in nodes:
            if changed != channel:
                raise ValueError('Nonselected channel changed')
            continue
        if node in seen:
            raise ValueError('Duplicate selected rotation channel')
        seen.add(node)
        if {k:v for k,v in channel.items() if k != 'sampler'} != {k:v for k,v in changed.items() if k != 'sampler'}:
            raise ValueError('Selected channel target changed')
        before, after = old['samplers'][channel['sampler']], new['samplers'][changed['sampler']]
        if (before.get('interpolation', 'LINEAR') != 'LINEAR'
                or {k:v for k,v in before.items() if k != 'output'} !=
                   {k:v for k,v in after.items() if k != 'output'}):
            raise ValueError('Only same-clock native LINEAR rotation outputs may change')
        clock = accessor(source, source_binary, before['input']).reshape(-1)
        a = accessor(source, source_binary, before['output'])
        b = accessor(candidate, candidate_binary, after['output'])
        if (len(clock) < 1 or a.shape != (len(clock), 4) or b.shape != a.shape
                or not np.isfinite(a).all() or not np.isfinite(b).all()
                or np.max(abs(np.linalg.norm(a.astype(float), axis=1)-1)) > 1e-5
                or np.max(abs(np.linalg.norm(b.astype(float), axis=1)-1)) > 1e-5):
            raise ValueError('Matching finite native unit-quaternion rows required')
        keys = np.flatnonzero(np.any(a != b, axis=1))
        spans = [[float(clock[k-1]) if k else 0.,
                  float(clock[k+1]) if k+1 < len(clock) else duration] for k in keys]
        intervals.extend(spans)
        rows.append(dict(node=node,changed_key_indices=keys.tolist(),support_intervals_s=spans))
    if seen != set(nodes):
        raise ValueError('Every selected node needs one native rotation channel')
    merged = []
    for left, right in sorted(intervals):
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    return dict(duration_s=duration,rows=rows,support_intervals_s=merged,
                unchanged_outside_closed_support=True,static_document_and_binary_prefix_exact=True,
                native_key_clocks_exact=True,quality_approved=False,release_approved=False)
