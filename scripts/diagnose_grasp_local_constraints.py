"""Frozen linear-model constraint sensitivity; never a relaxed quality result."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from grasp_physical_step import epigraph_step, norm_remainder
from grasp_pose_witness import PoseProblem, BODY
from build_soma_preview import ASSET


def run(report, output):
    report, output = Path(report).resolve(), Path(output).resolve()
    protocol, result = read(report/'protocol.json'), read(report/'result.json')
    stage = result['history'][-1]
    linear_file = report/f"linearization-{stage['stage']:02d}.npz"
    if sha256(linear_file) != stage['linearization_sha256']: raise ValueError('Linearization changed')
    fit = ROOT/protocol['study']/'fit'; summary = read(fit/'summary.json')
    if sha256(fit/'summary.json') != protocol['fit_summary_sha256'] or sha256(ASSET) != summary['mesh_sha256']:
        raise ValueError('Study/mesh changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), protocol['frame'])
    with np.load(linear_file, allow_pickle=False) as saved: linear = dict(saved)
    x = linear['parameters']; count = len(p.contacts)+len(p.normals)+1
    labels = p.labels[:count]+['norm:'+p.names[j] for j in p.editable]
    groups = [('unchanged', [])]+[(label, [i]) for i, label in enumerate(labels[:count])]
    groups += [('all_finger_budgets', list(range(count+len(BODY), len(labels)))),
               ('all_body_budgets', list(range(count, count+len(BODY)))),
               ('both_normal_targets', list(range(len(p.contacts), len(p.contacts)+len(p.normals))))]
    trust = protocol['limits']['trusts_degrees'][0]
    radius = np.r_[np.full(p.dim-1, np.deg2rad(trust)), protocol['limits']['root_trust_at_largest_m']]
    lower, upper = -radius.copy(), radius.copy()
    lower[-1] = max(lower[-1], -x[-1]); upper[-1] = min(upper[-1], p.config['max_root_lift_m']-x[-1])
    margin = np.r_[np.full(count, protocol['limits']['protected_margin_normalized']), norm_remainder(radius, p.limits)]
    output.mkdir(parents=True, exist_ok=False)
    save(output/'protocol.json', dict(at=now(), source_result_sha256=sha256(report/'result.json'),
         linearization_sha256=sha256(linear_file), stage=stage['stage'], trust_degrees=trust,
         omitted_groups={name: [labels[i] for i in ids] for name, ids in groups},
         implementation_sha256=sha256(Path(__file__)), lp_implementation_sha256=sha256(ROOT/'scripts/grasp_physical_step.py'),
         scope='Frozen local linear model. Omit named rows only to diagnose predicted sensitivity. No relaxed pose, nonlinear feasibility, global optimality or quality claim.'))
    shutil.copyfile(Path(__file__), output/Path(__file__).name)
    rows = []
    for name, omitted in groups:
        keep = np.array([i for i in range(len(labels)) if i not in omitted])
        delta, record = epigraph_step(linear['surface'], linear['surface_jac'], linear['protected'][keep],
                                     linear['protected_jac'][keep], margin[keep], radius, lower, upper)
        rows.append(dict(omitted=name, lp=record, delta=None if delta is None else delta.tolist()))
    baseline = rows[0]['lp']['primary_optimum']
    for row in rows:
        row['predicted_improvement_vs_unchanged_m'] = (baseline-row['lp']['primary_optimum'])*.01 if row['lp']['success'] else None
    save(output/'result.json', dict(at=now(), rows=rows, quality_approved=False, pose_generated=False))
    print([dict(omitted=row['omitted'], predicted_extra_improvement_mm=1000*row['predicted_improvement_vs_unchanged_m'] if row['predicted_improvement_vs_unchanged_m'] is not None else None) for row in rows])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.report, args.output)
