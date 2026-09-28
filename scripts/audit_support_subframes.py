"""Independent quarter-frame floor audit of completed support corrections."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from audit_authoring_intent import check_files
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def audit(study, output):
    complete, protocol = read(study/'completion.json'), read(study/'protocol.json')
    if complete['protocol_sha256'] != sha256(study/'protocol.json'):
        raise ValueError('Source protocol changed')
    check_files(study, complete['files'])
    output.mkdir(parents=True, exist_ok=False)
    plan = dict(at=now(), study=str(study), completion_sha256=sha256(study/'completion.json'),
        fractions=[.25, .75], floor_preservation_epsilon_m=1e-6,
        implementation_sha256=sha256(__file__),
        scope='Post-study diagnostic at additional decoded sample times; does not change frozen selection or certify continuous-time clearance.')
    save(output/'protocol.json', plan)
    rows = []
    with threadpool_limits(limits=1):
        for case, item in zip(protocol['cases'], complete['rows']):
            if case['id'] != item['id']: raise ValueError('Population mismatch')
            row = dict(id=item['id'], status=item['status'], quality_approved=False)
            if case['eligible'] and item['status'] in ('candidate_preserved', 'input_retained'):
                folder = study/item['id']
                paths = [folder/'base/selected/character.glb', Path(item['selected'])]
                if sha256(paths[1]) != item['selected_sha256']: raise ValueError('Selected clip changed')
                rigs = [RigAsset.load(p) for p in paths]
                clocks = [AnimationSampler(r.document, r.binary, 0) for r in rigs]
                frames = read(folder/'base/spec.json')['frames']
                maxima = [0., 0.]; excess = 0.; worsened = 0; worst = None; samples = []
                for edge in range(frames-1):
                    for fraction in plan['fractions']:
                        time = (edge+fraction)/30
                        depths = [np.maximum(-r.vertices(c.sample(time))[:, 1], 0) for r, c in zip(rigs, clocks)]
                        if depths[0].shape != depths[1].shape: raise ValueError('Skin topology changed')
                        delta = depths[1]-depths[0]; vertex = int(np.argmax(delta)); value = float(delta[vertex])
                        for i in (0, 1): maxima[i] = max(maxima[i], float(depths[i].max()))
                        failed = value > plan['floor_preservation_epsilon_m']
                        worsened += int(failed)
                        if worst is None or value > excess:
                            excess = value; worst = dict(edge=edge, fraction=fraction, time_s=time, vertex=vertex,
                                before_depth_m=float(depths[0][vertex]), selected_depth_m=float(depths[1][vertex]))
                        samples.append(dict(time_s=time, before_max_depth_m=float(depths[0].max()),
                            selected_max_depth_m=float(depths[1].max()), maximum_per_vertex_depth_increase_m=value,
                            worsened=bool(failed)))
                row.update(samples=len(samples), maximum_depth_m=dict(input=maxima[0], selected=maxima[1]),
                    maximum_per_vertex_depth_increase_m=excess, worsened_samples=worsened,
                    preservation_passed=worsened == 0, worst=worst,
                    input_sha256=sha256(paths[0]), selected_sha256=sha256(paths[1]))
                save(output/(item['id']+'.json'), dict(**row, timeline=samples))
                print(item['id'], 'worsened', worsened, 'depth_excess_m', excess, flush=True)
            rows.append(row)
            save(output/'progress.json', dict(at=now(), rows=rows))
    save(output/'completion.json', dict(at=now(), protocol_sha256=sha256(output/'protocol.json'), rows=rows,
        evaluated_cases=sum('samples' in r for r in rows), evaluated_times=sum(r.get('samples', 0) for r in rows),
        cases_with_worsened_samples=sum(r.get('worsened_samples', 0)>0 for r in rows),
        quality_approved=False, continuous_time_certified=False,
        files={p.name:sha256(p) for p in output.glob('*.json')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); audit(args.study.resolve(), args.output.resolve())
