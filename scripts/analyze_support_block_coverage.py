"""Attribute retained support-speed excess to edited and untouched time windows."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits

from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from support_temporal_cleanup import support_mask


def classify(speed, active, target, edited):
    speed = np.asarray(speed, float)
    active = np.asarray(active, bool)
    if speed.ndim != 1 or active.shape != (len(speed)+1,) or not np.isfinite(speed).all() or np.any(speed < 0):
        raise ValueError('Finite speed at every ordered edge and matching support mask required')
    if not np.isfinite(target) or target < 0:
        raise ValueError('Finite nonnegative raw reference required')
    if any(type(f) is not int or not 0 <= f < len(active) for f in edited):
        raise ValueError('Editable frames must belong to this clock')
    editable = np.zeros(len(active), bool)
    editable[list(edited)] = True
    support = active[:-1] & active[1:]
    rows = []
    for edge in np.flatnonzero(support & (speed > target + .001)):
        inside = int(editable[edge]) + int(editable[edge+1])
        rows.append(dict(step_end_frame=int(edge+1), speed_m_s=float(speed[edge]),
                         excess_m_s=float(speed[edge]-target),
                         coverage=('untouched', 'boundary', 'inside')[inside]))
    return rows


def run(summary_folder, output):
    if output.exists():
        raise ValueError('Preserve previous diagnostic')
    summary = read(summary_folder/'summary.json')
    study = Path(summary['study'])
    done = read(study/'completion.json')
    if sha256(study/'completion.json') != summary['completion_sha256']:
        raise ValueError('Completed study identity changed')
    protocol = read(study/'protocol.json')
    if sha256(study/'protocol.json') != done['protocol_sha256']:
        raise ValueError('Study protocol changed')
    if [r['id'] for r in summary['rows']] != [c['id'] for c in protocol['cases']]:
        raise ValueError('Keep the full population denominator')
    output.mkdir(parents=True)
    inputs = {str(p): sha256(p) for p in [summary_folder/'summary.json', study/'completion.json', study/'protocol.json']}

    def evidence(path):
        digest = sha256(path)
        if digest != done['files'][path.relative_to(study).as_posix()]:
            raise ValueError('Study artifact changed: '+str(path))
        inputs[str(path)] = digest
        return read(path)

    rows = []
    with threadpool_limits(limits=1):
        for case in protocol['cases']:
            row = {k: case[k] for k in ('id', 'action', 'family', 'rig')}
            row['eligible'] = case['eligible']
            if not case['eligible']:
                rows.append(row)
                continue
            folder = study/case['id']
            result = evidence(folder/'result.json')
            if result['status'] != 'candidate_preserved':
                raise ValueError('Diagnostic requires the recorded selected candidate')
            audit = evidence(folder/'audit.json')
            spec = evidence(folder/'take/spec.json')
            annotations = evidence(folder/'take/input/contacts.json')
            selection = evidence(folder/'selection.json')
            solver = evidence(folder/'solver.json')
            path = Path(result['selected'])
            if sha256(path) != result['selected_sha256'] or sha256(path) != audit['candidate_sha256']:
                raise ValueError('Selected export changed')
            inputs[str(path)] = sha256(path)
            rig = RigAsset.load(path)
            sampler = AnimationSampler(rig.document, rig.binary, 0)
            centers = []
            for frame in range(spec['frames']):
                vertices = rig.vertices(sampler.sample(float(np.float32(frame/30))))
                centers.append([vertices[p['vertices']].mean(axis=0) for p in spec['patches'].values()])
            speed = np.linalg.norm(np.diff(np.asarray(centers)[:, :, [0, 2]], axis=0), axis=2)*30
            edited = sorted({f for block in selection['blocks'] for f in block['frames']})
            feet = []
            for index, side in enumerate(spec['patches']):
                active = support_mask(annotations, side, spec['frames'])
                expected = next(r for r in audit['feet'] if r['side'] == side)
                support = active[:-1] & active[1:]
                peak = float(speed[support, index].max()) if support.any() else None
                if peak != expected['support_peak_after_m_s']:
                    raise ValueError('Decoded support peak differs from retained audit')
                target = expected['raw_peak_target_m_s']
                failing = classify(speed[:, index], active, target, edited) if target is not None else []
                feet.append(dict(side=side,raw_peak_target_m_s=target,selected_peak_m_s=peak,regressing_edges=failing))
            blocks = []
            for block in solver['blocks']:
                log = block['solver']; history = log['history']
                blocks.append(dict(frames=block['target']['frames'],initial_objective=log['initial_objective'],
                    final_objective=log['final_objective'],iterations=len(history),
                    accepted_steps=sum(bool(h['accepted']) for h in history),
                    stopped_at_step_limit=bool(len(history)==protocol['steps_per_block'] and history[-1]['accepted']),
                    last_step_rejected=bool(history and not history[-1]['accepted'])))
            row.update(status=result['status'],selected_sha256=result['selected_sha256'],feet=feet,blocks=blocks)
            rows.append(row)
            save(output/'pipeline.json',dict(status='measuring',completed=len(rows),total=len(protocol['cases'])))
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed while measuring')
    failing = [dict(case=row['id'],side=foot['side'],**edge) for row in rows for foot in row.get('feet',[]) for edge in foot['regressing_edges']]
    counts = {kind:sum(r['coverage']==kind for r in failing) for kind in ['inside','boundary','untouched']}
    cases_by_kind = {kind:sorted({r['case'] for r in failing if r['coverage']==kind}) for kind in counts}
    save(output/'summary.json',dict(at=now(),study=str(study),population=len(rows),targeted=sum(r['eligible'] for r in rows),
        regressing_cases=len({r['case'] for r in failing}),edge_counts=counts,cases_by_coverage=cases_by_kind,rows=rows,inputs=inputs,
        implementation_sha256=sha256(__file__),quality_approved=False,
        scope='Independent decoded integer-frame patch speeds on the complete frozen development population. '
              'A regressing edge exceeds the raw per-foot support peak by more than0.001m/s, a reporting bin, not realism acceptance. '
              'Inside/boundary/untouched describes which endpoint poses were editable, not causality or solver infeasibility. '
              'Predicted support remains unconfirmed; no new motion, human rating or release approval.'))
    save(output/'pipeline.json',dict(status='complete',summary_sha256=sha256(output/'summary.json')))
    print(dict(population=len(rows),regressing_cases=len({r['case'] for r in failing}),edge_counts=counts,cases_by_coverage=cases_by_kind))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.summary.resolve(),args.output.resolve())
