"""Read-only, source-bound necessary displacement checks before support fitting."""
import argparse
from pathlib import Path
import re
from support_centroid_bounds import bound, number
from strep import read, save, sha256

SCHEMA = 'strep-native-support-preflight-v1'


def analyze(rig, reader, spec, digest):
    import numpy as np
    from native_engine_clock import audit_clock
    if (not isinstance(spec, dict) or set(spec) != {'schema','glb_sha256','animation_index','supports'}
            or spec['schema'] != SCHEMA or spec['glb_sha256'] != digest
            or type(spec['animation_index']) is not int or spec['animation_index'] != 0):
        raise ValueError('Source-bound native support preflight specification required')
    supports = spec['supports']
    if not isinstance(supports, list) or not 1 <= len(supports) <= 64:
        raise ValueError('One to 64 explicit support intervals required')
    population = sum(len(p['positions']) for p in rig.primitives)
    rows = []; names = set()
    fields = {'id','vertex_ids','interval_s','target_xyz_m','plane','clearance_m','horizontal_tolerance_m','maximum_vertex_displacement_m'}
    for row in supports:
        if not isinstance(row, dict) or set(row) != fields or not isinstance(row['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', row['id']) or row['id'] in names:
            raise ValueError('Distinct named support targets required')
        names.add(row['id']); ids = row['vertex_ids']; interval = row['interval_s']; plane = row['plane']
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 20000
                or any(type(v) is not int or not 0 <= v < population for v in ids) or len(set(ids)) != len(ids)):
            raise ValueError('Distinct in-range mesh vertex indices required')
        if not isinstance(interval, list) or len(interval) != 2:
            raise ValueError('Explicit support interval required')
        a,b = [number(t, 'support time', 0., reader.duration) for t in interval]
        if a >= b: raise ValueError('Increasing support interval required')
        if not isinstance(plane, dict) or set(plane) != {'normal_xyz','offset_m'}:
            raise ValueError('Explicit world plane required')
        args = (row['target_xyz_m'], plane['normal_xyz'], plane['offset_m'], row['clearance_m'], row['horizontal_tolerance_m'], row['maximum_vertex_displacement_m'])
        bound([[0.,0.,0.]], *args)  # Reject malformed geometry before sampling.
        rows.append((row, args))
    clock = audit_clock(reader.duration, [c[2] for c in reader.channels], [t for r,_ in rows for t in r['interval_s']], 0.)
    if len(clock) > 20000: raise ValueError('Complete audit clock exceeds 20000 samples; no truncation')
    reports = {r['id']: dict(id=r['id'], vertex_ids=r['vertex_ids'], interval_s=r['interval_s'], observations=[]) for r,_ in rows}
    for time in clock:
        active = [(r,args) for r,args in rows if r['interval_s'][0] <= time <= r['interval_s'][1]]
        if not active: continue
        vertices = rig.vertices(reader.sample(float(time)))
        if vertices.shape != (population,3) or not np.isfinite(vertices).all():
            raise ValueError('Complete finite decoded mesh required')
        for row,args in active:
            reports[row['id']]['observations'].append(dict(time_s=float(time), **bound(vertices[row['vertex_ids']].tolist(), *args)))
    conflicts = 0
    for row in reports.values():
        bad = [o for o in row['observations'] if o['status'] == 'incompatible_support_target']
        row['incompatible_samples'] = len(bad); conflicts += len(bad)
        row['worst_conflict'] = max(bad, key=lambda o:o['minimum_required_vertex_max_displacement_m']-o['maximum_vertex_displacement_m']) if bad else None
    return dict(schema=SCHEMA, status='incompatible_support_target' if conflicts else 'not_ruled_out',
        glb_sha256=digest, supports=list(reports.values()), incompatible_contact_times=conflicts,
        clock='Native keys, adjacent midpoints, uniform 120 Hz and exact authored interval endpoints; inclusive interval sampling',
        scope='Every selected vertex must clear the plane and stay within its source-relative movement limit; the arithmetic centroid must meet the planar target. Necessary geometric relaxation only, not articulated feasibility, temporal quality or continuous-time certification.',
        feasibility_proven=False, formal_interval_certificate=False, quality_approved=False, release_approved=False)


def run(character, specification, output):
    from action_worker_lock import worker_lock
    character, specification, output = (Path(p).resolve() for p in (character, specification, output))
    if output.exists(): raise ValueError('Fresh output directory required')
    with worker_lock():
        from threadpoolctl import threadpool_limits
        from rig_asset import RigAsset
        from native_support_clock import NativeSupportSampler
        with threadpool_limits(limits=1):
            sources = {str(p):sha256(p) for p in Path(__file__).parent.glob('*.py')}
            digest, spec_digest = sha256(character), sha256(specification)
            rig = RigAsset.load(character)
            if len(rig.document.get('animations', [])) != 1: raise ValueError('One native animation required')
            reader = NativeSupportSampler(rig.document, rig.binary, 0)
            spec = read(specification); result = analyze(rig, reader, spec, digest)
            if sha256(character) != digest or sha256(specification) != spec_digest:
                raise ValueError('Inputs changed during support preflight')
            for path,h in sources.items():
                if sha256(path) != h: raise ValueError('Producer changed during support preflight')
            output.mkdir(parents=True, exist_ok=False)
            save(output/'spec.json', spec)
            save(output/'request.json', dict(schema=SCHEMA, character=str(character), character_sha256=digest,
                specification=str(specification), specification_sha256=spec_digest, implementation_sha256=sources))
            result['request_sha256'] = sha256(output/'request.json')
            result['spec_snapshot_sha256'] = sha256(output/'spec.json')
            save(output/'result.json', result)
            return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('character', type=Path); parser.add_argument('specification', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); result = run(args.character, args.specification, args.output)
    print(dict(status=result['status'], incompatible_contact_times=result['incompatible_contact_times'], quality_approved=False))
