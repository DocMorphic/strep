"""Propose held-boundary edit windows without changing authored pins or rate caps."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read,save,sha256
from point_rate_reachability import endpoint_bound
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def constraints(spec, guard, tolerance_m):
    result=[]
    for row in guard['rows']:
        if row['phase'] not in ['approach','release']:continue
        pins=[pin for pin in spec['regions'][row['region']]['segments']
              if pin.get('vertex_id')==row['vertex_id'] and
              (pin['start_frame']==row['last_frame'] if row['phase']=='approach'
               else pin['end_frame']==row['first_frame'])]
        if len(pins)!=1 or pins[0]['space']!='world':raise ValueError('Unambiguous stationary material-point interval required')
        pin=pins[0]
        result.append(dict(region=row['region'],vertex_id=row['vertex_id'],phase=row['phase'],
            contact_frame=pin['start_frame'] if row['phase']=='approach' else pin['end_frame'],
            target=pin['position_m'],tolerance_m=tolerance_m,speed_limit_m_s=row['reference_ceilings'][0],
            acceleration_limit_m_s2=row['reference_ceilings'][1]))
    expected=sum(len(entry['segments']) for entry in spec['regions'].values() if entry['mode']=='explicit')*2
    if len(result)!=expected:raise ValueError('Every stationary pin requires both transition constraints')
    return result


def plan(tracks, rows, window, frames):
    """Search every expanded integer boundary, retaining original phase ceilings.

    Boundary poses move to earlier/later source times. Both proposed endpoints
    remain interior keys so the original outside-motion policy still holds.
    """
    if type(frames)!=int or frames<4 or not isinstance(window,(list,tuple)) or len(window)!=2 or any(type(x)!=int for x in window):
        raise ValueError('Frame count and two integer edit-window endpoints required')
    first,last=window
    if not 1<=first<last<=frames-2:raise ValueError('Both requested endpoints must be held interior keys')
    if not rows or any(row.get('phase') not in ['approach','release'] for row in rows):raise ValueError('Transition constraints required')
    identities=[(r['region'],r['vertex_id'],r['phase'],r['contact_frame']) for r in rows]
    if len(set(identities))!=len(identities):raise ValueError('Duplicate transition constraints')
    for name,vertex in {(r['region'],r['vertex_id']) for r in rows}:
        counts=[sum(r['region']==name and r['vertex_id']==vertex and r['phase']==phase for r in rows) for phase in ['approach','release']]
        if counts[0]!=counts[1]:raise ValueError('Each material point needs matching approach and release constraints')
    for row in rows:
        if type(row.get('vertex_id'))!=int or row['vertex_id']<0 or not isinstance(row.get('region'),str) or not row['region']:
            raise ValueError('Named material point required')
        if type(row.get('acceleration_limit_m_s2')) not in (int,float) or not np.isfinite(row['acceleration_limit_m_s2']) or row['acceleration_limit_m_s2']<0:
            raise ValueError('Finite nonnegative retained acceleration cap required')
        if type(row.get('contact_frame'))!=int or not first<row['contact_frame']<last:
            raise ValueError('Contact transitions must be strictly inside the requested window')
        points=np.asarray(tracks[row['vertex_id']],dtype=float)
        if points.shape!=(frames,3) or not np.isfinite(points).all():raise ValueError('Complete finite native-frame point tracks required')
    def check(boundary,phase):
        outcomes=[]
        for row in rows:
            if row['phase']!=phase:continue
            outcome=endpoint_bound(tracks[row['vertex_id']][boundary],row['target'],row['tolerance_m'],
                row['speed_limit_m_s'],abs(row['contact_frame']-boundary)/30)
            outcomes.append(dict(region=row['region'],vertex_id=row['vertex_id'],phase=phase,
                                 contact_frame=row['contact_frame'],fixed_frame=boundary,**outcome))
        return dict(boundary_frame=boundary,rows=outcomes,
                    endpoint_tests_pass=all(not r['endpoint_distance_incompatible'] for r in outcomes))
    approach=[check(boundary,'approach') for boundary in range(first,0,-1)]
    release=[check(boundary,'release') for boundary in range(last,frames-1)]
    a=next((r for r in approach if r['endpoint_tests_pass']),None)
    b=next((r for r in release if r['endpoint_tests_pass']),None)
    proposed=[a['boundary_frame'],b['boundary_frame']] if a and b else None
    requested=approach[0]['rows']+release[0]['rows']
    return dict(requested_window=list(window),frames=frames,proposed_window=proposed,
        requested_conflicts=sum(r['endpoint_distance_incompatible'] for r in requested),requested_rows=requested,
        proposal_rows=a['rows']+b['rows'] if proposed else None,
        approach_candidates=approach,release_candidates=release,
        changes_requested_scope=proposed is not None and proposed!=list(window),
        original_phase_limits=rows,rate_limits_recomputed=False,quality_approved=False,
        scope='Nearest expanded held-boundary window passing necessary endpoint-distance tests, with original per-phase speed and acceleration caps retained verbatim. Proposal changes which source poses are held. No requested window, target, contact time, tolerance or rate cap is applied or changed. Not proof of acceleration, rig, geometry, force, balance or semantic feasibility; null means no tested held-boundary expansion passes.')


def from_export(path,spec,guard,window,frames,tolerance_m):
    rows=constraints(spec,guard,tolerance_m);vertices=sorted({r['vertex_id'] for r in rows})
    rig=RigAsset.load(path);clock=AnimationSampler(rig.document,rig.binary,0)
    if abs(clock.duration-(frames-1)/30)>1e-5:raise ValueError('Export clock differs from native frame count')
    tracks={v:[] for v in vertices}
    with threadpool_limits(limits=1):
        for f in range(frames):
            mesh=rig.vertices(clock.sample(f/30))
            for vertex in vertices:
                if type(vertex)!=int or not 0<=vertex<len(mesh):raise ValueError('Material point outside export')
                tracks[vertex].append(mesh[vertex].tolist())
    return plan(tracks,rows,window,frames)


def describe(report):
    lines=[f"Requested edit range: frames {report['requested_window'][0]}–{report['requested_window'][1]}. "
           f"{report['requested_conflicts']} held-pose travel conflicts."]
    for row in report['requested_rows']:
        if row['endpoint_distance_incompatible']:
            lines.append(f"{row['region']} {row['phase']}: needs at least {row['minimum_travel_m']*1000:.3f} mm; "
                         f"speed limit and time allow {row['maximum_travel_m']*1000:.3f} mm.")
    proposed=report['proposed_window']
    if proposed is None:
        lines.append('No expanded held-boundary range passes every endpoint-distance test with the existing rate limits. No range is proposed.')
    else:
        lines.append(f"Proposed range: frames {proposed[0]}–{proposed[1]}. It has not been applied.")
    lines.append('Targets, contact times, tolerances and rate limits remain unchanged. Passing this test would not guarantee acceleration, collision, rig or physical feasibility.')
    return '\n'.join(lines)


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh planning output required')
    protocol=read(study/'protocol.json');recipe=read(study/'recipe.json')
    if not protocol.get('export_point_rate_guard'):raise ValueError('Recorded point-rate trial required')
    window=protocol['edit_window']
    if recipe['localization']['locked_boundary_keys']!=window:raise ValueError('Both source boundary poses must be held')
    source=Path(protocol['source']);scene=read(source/'portable-scene.json');path=source/scene['actors']['A']['preview_glb']
    for p in [path,source/'portable-scene.json']:
        if protocol['inputs'].get(str(p))!=sha256(p):raise ValueError('Source differs from frozen protocol')
    result=from_export(path,protocol['contact_spec'],recipe['export_point_rates'],window,
                       scene['frame_count'],protocol['config']['point_tolerance_m'])
    result.update(inputs={str(p):sha256(p) for p in [study/'protocol.json',study/'recipe.json',path]},
                  planner_sha256=sha256(__file__))
    save(output,result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();result=run(a.study,a.output)
    print(describe(result))
