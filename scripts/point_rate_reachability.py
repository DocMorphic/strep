"""Necessary endpoint travel checks for stationary pins with held edit boundaries."""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def endpoint_bound(fixed, target, tolerance_m, speed_limit_m_s, duration_s, position_error_budget_m=1e-6):
    points=np.asarray([fixed,target],dtype=float)
    if points.shape!=(2,3) or not np.isfinite(points).all():raise ValueError('Finite XYZ endpoints required')
    for value in [tolerance_m,speed_limit_m_s,duration_s,position_error_budget_m]:
        if type(value) not in (int,float) or not np.isfinite(value) or value<0:
            raise ValueError('Finite nonnegative limits required')
    if duration_s==0:raise ValueError('Positive transition duration required')
    distance=float(np.linalg.norm(points[0]-points[1]))
    required=max(0.,distance-tolerance_m-position_error_budget_m)
    available=speed_limit_m_s*duration_s
    return dict(distance_to_target_m=distance,minimum_travel_m=required,
        maximum_travel_m=available,travel_deficit_m=required-available,
        endpoint_distance_incompatible=required>available,
        minimum_average_speed_m_s=required/duration_s,
        tolerance_m=tolerance_m,speed_limit_m_s=speed_limit_m_s,duration_s=duration_s,
        position_error_budget_m=position_error_budget_m)


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh diagnostic path required')
    protocol=read(study/'protocol.json');recipe=read(study/'recipe.json')
    if not protocol.get('export_point_rate_guard'):raise ValueError('Recorded point-rate trial required')
    guard=recipe['export_point_rates'];locked=recipe['localization']['locked_boundary_keys']
    source=Path(protocol['source']);scene=read(source/'portable-scene.json')
    path=source/scene['actors']['A']['preview_glb']
    for p in [path,source/'portable-scene.json']:
        if protocol['inputs'].get(str(p))!=sha256(p):raise ValueError('Source differs from protocol')
    rig=RigAsset.load(path);clock=AnimationSampler(rig.document,rig.binary,0)
    rows=[]
    for row in guard['rows']:
        phase=row['phase']
        if phase not in ['approach','release']:continue
        frame=row['first_frame'] if phase=='approach' else row['last_frame']
        if frame not in locked:continue
        pins=[p for p in protocol['contact_spec']['regions'][row['region']]['segments']
              if p['vertex_id']==row['vertex_id'] and
              (p['start_frame']==row['last_frame'] if phase=='approach' else p['end_frame']==row['first_frame'])]
        if len(pins)!=1:raise ValueError('Ambiguous recorded material-point interval')
        pin=pins[0]
        if pin['space']!='world':raise ValueError('Stationary world point required')
        fixed=rig.vertices(clock.sample(frame/30))[row['vertex_id']]
        bound=endpoint_bound(fixed,pin['position_m'],protocol['config']['point_tolerance_m'],
            row['reference_ceilings'][0],(row['last_frame']-row['first_frame'])/30)
        rows.append(dict(region=row['region'],phase=phase,fixed_frame=frame,vertex_id=row['vertex_id'],**bound))
    result=dict(rows=rows,any_endpoint_distance_incompatible=any(r['endpoint_distance_incompatible'] for r in rows),
        inputs={str(p):sha256(p) for p in [study/'protocol.json',study/'recipe.json',path]},
        implementation_sha256=sha256(__file__),quality_approved=False,
        scope='Necessary straight-line distance bound from a held edit-boundary pose to a stationary tolerance ball. Uses recorded per-phase source speed ceiling and 1 micrometre boundary-position budget. A negative result does not prove feasible acceleration, geometry, rig limits or physical motion. No boundary, target or speed limit is changed.')
    save(output,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(run(args.study,args.output))
