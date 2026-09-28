"""Compare complete off-origin and canonical-origin development experiments."""
import argparse
import copy
from pathlib import Path

import numpy as np

from strep import ROOT, now, read, save, sha256


def verified(folder):
    complete = read(folder / 'completion.json')
    if read(folder / 'pipeline.json')['status'] != 'complete':
        raise ValueError('Audit is not complete')
    for name, digest in complete['inputs'].items():
        if sha256(name) != digest:
            raise ValueError('Audited source changed: ' + name)
    if (sha256(folder / 'results.json') != complete['results_sha256']
            or sha256(folder / 'engine/verification.json') != complete['engine_sha256']):
        raise ValueError('Result or engine evidence changed')
    rows = read(folder / 'results.json')['rows']
    for row in rows:
        diagnostics = [('posture.json', 'posture_sha256'), ('mesh-floor.json', 'mesh_floor_sha256')]
        if 'dynamics' in row or 'dynamics_sha256' in row:
            diagnostics.append(('dynamics.json', 'dynamics_sha256'))
        for name, key in diagnostics:
            if sha256(folder / row['id'] / name) != row[key]:
                raise ValueError('Detailed diagnostic changed')
        if 'dynamics' in row and read(folder / row['id'] / 'dynamics.json') != row['dynamics']:
            raise ValueError('Embedded dynamics differ from detailed diagnostic')
    return complete, rows


def run(before, after, output):
    if output.exists():
        raise ValueError('Preserve earlier comparisons')
    bc, br = verified(before)
    ac, ar = verified(after)
    if bc['model_and_sampling'] != ac['model_and_sampling']:
        raise ValueError('Checkpoint or sampling settings differ')
    if [r['id'] for r in br] != [r['id'] for r in ar] or len(ar) != 8:
        raise ValueError('Paired populations differ')
    caches = [next(Path(n) for n in c['inputs'] if Path(n).name == 'manifest.json'
                   and Path(n).parent.name == 'conditioning') for c in [bc, ac]]
    bm, am = [read(p) for p in caches]
    if bm['entries'] != am['entries'] or bm['encoder_revisions'] != am['encoder_revisions']:
        raise ValueError('Conditioning tensors or encoder revisions differ')
    batches = [read(p.parent.parent / 'request.json') for p in caches]
    sources = []
    normalized = copy.deepcopy(batches)
    for batch in normalized:
        guided = [r for r in batch['requests'] if r.get('generation_constraints')]
        if len(guided) != 1 or len(guided[0]['generation_constraints']) != 1:
            raise ValueError('Expected one starting guide')
        guide = guided[0]['generation_constraints'][0]
        path = ROOT / guide.pop('motion')
        if sha256(path) != guide.pop('sha256'):
            raise ValueError('Guide source changed')
        with np.load(path, allow_pickle=False) as z:
            sources.append(dict(z))
    if normalized[0] != normalized[1]:
        raise ValueError('Requests differ beyond guide source')
    bs, ass = sources
    if set(bs) != set(ass):
        raise ValueError('Guide arrays differ')
    anchor = normalized[0]['requests'][1]['generation_constraints'][0]['source_frames'][0]
    offset = bs['smooth_root_pos'][anchor] - ass['smooth_root_pos'][anchor]
    if offset[1] != 0 or np.any(ass['smooth_root_pos'][anchor, [0, 2]] != 0):
        raise ValueError('Canonical source changed height or did not start at origin')
    for key in bs:
        if key in ('posed_joints', 'root_positions', 'smooth_root_pos'):
            np.testing.assert_allclose(bs[key] - ass[key], np.broadcast_to(offset, bs[key].shape), rtol=0, atol=2e-7)
        else:
            np.testing.assert_array_equal(bs[key], ass[key])
    rows = []
    for b, a in zip(br, ar):
        if (b['condition'], b['seed']) != (a['condition'], a['seed']):
            raise ValueError('Condition/seed mismatch')
        bp = read(before / b['id'] / 'posture.json')
        ap = read(after / a['id'] / 'posture.json')
        if bp['rules'] != ap['rules']:
            raise ValueError('Diagnostic rules changed')
        rows.append(dict(id=a['id'], seed=a['seed'], condition=a['condition'],
            native_npz_identical=bp['source_sha256'] == ap['source_sha256'],
            before_order_proxy=b['upright_kneel_upright_proxy_present'],
            after_order_proxy=a['upright_kneel_upright_proxy_present'],
            before_floor_m=b['mesh_floor_max_m'], after_floor_m=a['mesh_floor_max_m'],
            before_guide_maximum=b['guide_audit']['guides'][0]['maximum'] if b['guide_audit'] else None,
            after_guide_maximum=a['guide_audit']['guides'][0]['maximum'] if a['guide_audit'] else None,
            before_guide_screen=b['guide_audit']['numerical_screen_passed'] if b['guide_audit'] else None,
            after_guide_screen=a['guide_audit']['numerical_screen_passed'] if a['guide_audit'] else None))
    output.mkdir(parents=True)
    save(output / 'comparison.json', dict(at=now(), before_completion_sha256=sha256(before / 'completion.json'),
         after_completion_sha256=sha256(after / 'completion.json'), rows=rows,
         conditioning_features_identical=True, requests_differ_only_in_guide_source=True,
         guide_source_uniform_xz_translation_verified=True, subtracted_offset_xyz_m=offset.tolist(),
         baseline_npz_all_identical=all(r['native_npz_identical'] for r in rows if r['condition'] == 'baseline'),
         before_engine_actor_frames=bc['engine_actor_frames'], after_engine_actor_frames=ac['engine_actor_frames'],
         quality_approved=False, human_review=None,
         scope='Fixed posture diagnostics, native-source identities and recorded guide/floor metrics. '
               'Model settings match; no action correctness, generalization or human quality approval.'))
    lines = ['# Guide-origin comparison', '',
             '| Seed | Original / canonical order proxy | Original / canonical joint error (mm) | Original / canonical floor depth (mm) |',
             '|---:|---|---:|---:|']
    for r in rows:
        if r['condition'] != 'upright-start':
            continue
        lines.append(f"| {r['seed']} | {r['before_order_proxy']} / {r['after_order_proxy']} | "
                     f"{r['before_guide_maximum']['joint_position_error_m']*1000:.2f} / "
                     f"{r['after_guide_maximum']['joint_position_error_m']*1000:.2f} | "
                     f"{r['before_floor_m']*1000:.2f} / {r['after_floor_m']*1000:.2f} |")
    lines += ['', 'Posture order is a development proxy, not action correctness. Engine import is separately verified; human review remains absent.']
    (output / 'comparison.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    print(rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('before', 'after', 'output'):
        p.add_argument(key, type=Path)
    args = p.parse_args()
    run(args.before.resolve(), args.after.resolve(), args.output.resolve())
