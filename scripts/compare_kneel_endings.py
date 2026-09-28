"""Compare start-only, final-frame and held-ending development pose guidance."""
import argparse
import copy
from pathlib import Path

import numpy as np

from compare_kneel_origins import verified
from compare_kneel_timing import pause_measures
from motion_window_dynamics import measure
from strep import ROOT, now, read, save, sha256


def validate_requests(start, ending):
    """The intended independent variable is guide timing, not prompt or source."""
    guided = [r for r in start['requests'] if r.get('generation_constraints')]
    if len(guided) != 1 or len(ending['requests']) != 2:
        raise ValueError('Require one start-only reference and two ending conditions')
    requests = [guided[0], *ending['requests']]
    expected_frames = [[0], [0, 179], [0, *range(170, 180)]]
    normalized = []
    for request, frames in zip(requests, expected_frames):
        item = copy.deepcopy(request)
        item.pop('id')
        item.pop('label')
        guides = item['generation_constraints']
        if len(guides) != 1 or item.get('guide_origin') != 'start_pose':
            raise ValueError('Require one canonicalized full-body guide')
        guide = guides[0]
        if (guide['type'] != 'fullbody' or guide.pop('frame_indices') != frames
                or guide.pop('source_frames') != [179] * len(frames)):
            raise ValueError('Guide timing/source frames differ from planned comparison')
        normalized.append(item)
    if normalized[0] != normalized[1] or normalized[0] != normalized[2]:
        raise ValueError('Conditions differ beyond guide timing and display identity')
    return requests


def run(start, ending, output):
    if output.exists():
        raise ValueError('Preserve previous comparisons')
    sc, sr = verified(start)
    ec, er = verified(ending)
    if sc['model_and_sampling'] != ec['model_and_sampling']:
        raise ValueError('Model or sampling settings changed')
    manifests = [next(Path(p) for p in c['inputs'] if Path(p).name == 'manifest.json'
                      and Path(p).parent.name == 'conditioning') for c in [sc, ec]]
    sm, em = [read(p) for p in manifests]
    if sm['entries'] != em['entries'] or sm['encoder_revisions'] != em['encoder_revisions']:
        raise ValueError('Conditioning tensors or encoder revisions changed')
    requests = validate_requests(*[read(p.parent.parent / 'request.json') for p in manifests])
    expected = {(condition, seed) for condition in ['start-only', 'final-frame', 'held-ending']
                for seed in requests[0]['seeds']}
    rows, inputs = [], {}
    for folder, source_rows in [(start, [r for r in sr if r['condition'] == 'upright-start']), (ending, er)]:
        inputs[str(folder / 'completion.json')] = sha256(folder / 'completion.json')
        for row in source_rows:
            trace_path = folder / row['id'] / 'posture.json'
            trace = read(trace_path)
            native = Path(trace['source'])
            if sha256(native) != trace['source_sha256']:
                raise ValueError('Native source changed')
            with np.load(native, allow_pickle=False) as z:
                motion = dict(z)
            dynamics = measure(motion)
            if 'dynamics' in row and dynamics != row['dynamics']:
                raise ValueError('Dynamics changed since audit')
            evidence_path = native.parent / 'evidence.json'
            evidence = read(evidence_path)
            for path in [native, trace_path, evidence_path]:
                inputs[str(path)] = sha256(path)
            rows.append(dict(condition='start-only' if folder == start else row['condition'], seed=row['seed'],
                id=row['id'], order_proxy=row['upright_kneel_upright_proxy_present'],
                starts_upright=row['sustained_upright_start'], ends_upright=row['sustained_upright_end'],
                pause=pause_measures(trace, motion), dynamics=dynamics,
                floor_max_m=row['mesh_floor_max_m'], foot_speed_proxies=row['foot_speed_proxies'],
                guide_audit=row['guide_audit'], requested_transition_diagnostics=evidence['sequence'],
                native_sha256=sha256(native)))
    if len(rows) != len(expected) or {(r['condition'],r['seed']) for r in rows} != expected:
        raise ValueError('Incomplete, duplicate or mislabeled comparison population')
    inputs.update({str(ROOT/'scripts'/name):sha256(ROOT/'scripts'/name) for name in
        ['compare_kneel_endings.py','compare_kneel_origins.py','compare_kneel_timing.py','motion_window_dynamics.py']})
    output.mkdir(parents=True)
    summary = dict(at=now(), inputs=inputs, rows=rows, exact_conditioning_match=True,
        requests_differ_only_by_guide_timing=True, quality_approved=False, human_review=None,
        scope='Four-seed development comparison; all methods use identical timed text and source pose. '
              'Ending guides impose a common upright pose and location. Fixed posture/contact proxies and '
              'continuous dynamics are not visual, action-correctness, physical or release approval.')
    save(output/'comparison.json',summary)
    lines = ['# Ending guide comparison', '',
        '| Guide | Seed | Ordered posture | Pause coverage | Floor (mm) | Ending joint speed (m/s) | Ending joint acceleration (m/s²) | Ending rotation step (°) |',
        '|---|---:|---|---:|---:|---:|---:|---:|']
    for row in rows:
        m = row['dynamics']['measures']
        lines.append(f"| {row['condition']} | {row['seed']} | {row['order_proxy']} | "
            f"{row['pause']['sustained_kneeling_proxy_fraction']:.0%} | {row['floor_max_m']*1000:.2f} | "
            f"{m['joint_rms_speed_m_s']['ending_peak']:.2f} | "
            f"{m['joint_rms_acceleration_m_s2']['ending_peak']:.2f} | "
            f"{m['local_rotation_step_degrees']['ending_peak']:.2f} |")
    lines += ['', 'Dynamics are peaks in the final second, indexed by arrival frame; ordinary movement can also produce high values.', '', summary['scope']]
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print({c:sum(r['order_proxy'] for r in rows if r['condition']==c) for c in ['start-only','final-frame','held-ending']})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('start','ending','output'):
        p.add_argument(name,type=Path)
    a = p.parse_args()
    run(a.start.resolve(),a.ending.resolve(),a.output.resolve())
