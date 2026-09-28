"""Select a bounded temporal block from independently audited release failures."""
import math


def select_block(events, releases, count):
    if type(count) is not int or count < 3:
        raise ValueError('At least three frames required')
    failed = [event for event in events if not event['candidate_passed']]
    if not failed:
        raise ValueError('No independently measured release failure')
    if any(not math.isfinite(event[key]) for event in failed for key in ['candidate_m_s2', 'limit_m_s2']):
        raise ValueError('Finite release measurements required')
    ranked = sorted(failed, key=lambda e: (-(e['candidate_m_s2']-e['limit_m_s2']), e['side'], e['release_frame']))
    event = ranked[0]
    matching = [r for r in releases if (r['side'], r['release_frame']) == (event['side'], event['release_frame'])]
    if len(matching) != 1:
        raise ValueError('Exactly one matching release required')
    release = matching[0]; centers = release['centers']
    if not centers or any(type(c) is not int or not 1 <= c < count-1 for c in centers):
        raise ValueError('Release acceleration centers outside clip')
    if centers != sorted(set(centers)) or any(b-a != 1 for a, b in zip(centers, centers[1:])):
        raise ValueError('Ordered contiguous acceleration centers required')
    if abs(release['original_limit_m_s2']-event['limit_m_s2']) > 1e-10:
        raise ValueError('Original and audited release limits differ')
    return dict(side=event['side'], release_frame=event['release_frame'], centers=centers,
        frames=list(range(max(0, centers[0]-2), min(count, centers[-1]+3))),
        limit_m_s2=event['limit_m_s2'], excess_m_s2=event['candidate_m_s2']-event['limit_m_s2'],
        failed_population=[dict(side=e['side'], release_frame=e['release_frame'],
            excess_m_s2=e['candidate_m_s2']-e['limit_m_s2']) for e in ranked],
        policy='Largest positive absolute audited release acceleration excess; deterministic side/frame tie break. Include all release acceleration centers and two neighboring frames on either side, clipped to clip bounds. Retain every unselected failure.')
