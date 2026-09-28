"""Full-clock comparison of development paths with an audit-derived fitting clock."""
import argparse
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT, read, save, sha256, now
from compare_partner_paths import load
from contact_witness_clock import enrich


FIXED = ['seed', 'source_scene_sha256', 'sources', 'source_summary_sha256',
         'pose_results_sha256', 'palm_region_sha256', 'knots', 'envelope_frames',
         'joint_edit_degrees', 'adjacent_rotation_vector_edit_degrees',
         'iterations', 'inner_max_iterations', 'component_trust_degrees', 'safeguard_trials']


def protocol(strict, screen, candidate):
    for key in FIXED:
        if not strict['request'][key] == screen['request'][key] == candidate['request'][key]:
            raise ValueError('Fixed protocol differs: '+key)
    if not strict['initial'] == screen['initial'] == candidate['initial']:
        raise ValueError('Initializer differs')
    if strict['request']['frames'] != screen['request']['frames']:
        raise ValueError('Original fitting clocks differ')
    if candidate['request']['selection_screen'] != screen['request']['selection_screen']:
        raise ValueError('Selection thresholds changed')
    if screen['request']['selection_screen']['max_sample_penetration_m'] != .005:
        raise ValueError('Comparison requires the original 5 mm screen')
    curves = dict(raw=strict['variants']['raw']['curve'],
                  strict=strict['variants']['candidate']['curve'],
                  screen=screen['variants']['candidate']['curve'])
    for audit in [screen, candidate]:
        if audit['variants']['raw']['curve'] != curves['raw']:
            raise ValueError('Raw geometry differs')
        for actor in ['A', 'B']:
            for file in ['character.glb', 'motion.npz']:
                key = 'assets/'+actor+'/raw/'+file
                if strict['manifest']['assets'][key] != audit['manifest']['assets'][key]:
                    raise ValueError('Raw asset differs')
    plan = enrich(strict['request']['frames'], curves)
    if candidate['request']['sampling_plan'] != plan or candidate['request']['frames'] != plan['frames']:
        raise ValueError('Fitting clock does not preserve the complete witness plan')
    if not plan['added_frames']:
        raise ValueError('No added fitting witnesses')
    return curves, plan


def changes(before, after, fitting_frames):
    if before['frames'] != after['frames'] or before['frames'] != [i*.5 for i in range(299)]:
        raise ValueError('Require matching full clocks')
    rows = list(zip(before['frames'], before['body_depth_m'], after['body_depth_m']))
    if len(rows) != 299:
        raise ValueError('Incomplete geometry')
    newly = [f for f, a, b in rows if a <= .005 < b]
    return dict(newly_failing_frames=newly,
                newly_failing_in_fit=[f for f in newly if f in fitting_frames],
                newly_failing_outside_fit=[f for f in newly if f not in fitting_frames],
                cleared_frames=[f for f, a, b in rows if b <= .005 < a],
                worsened_frames=[f for f, a, b in rows if b > a+1e-8],
                maximum_increase_m=max(b-a for _, a, b in rows),
                peak_change_m=max(after['body_depth_m'])-max(before['body_depth_m']),
                floor_curve_unchanged=before['floor_depth_m'] == after['floor_depth_m'])


def compare(strict_folder, screen_folder, candidate_folder, output):
    strict, screen, candidate = [load(p) for p in [strict_folder, screen_folder, candidate_folder]]
    curves, plan = protocol(strict, screen, candidate)
    request = candidate['request']
    witness = Path(request['witness_comparison'])
    for file, key in [('summary.json', 'witness_summary_sha256'), ('curves.json', 'witness_curves_sha256')]:
        if sha256(witness/file) != request[key]:
            raise ValueError('Witness evidence changed')
    witness_summary = read(witness/'summary.json')
    if (read(witness/'curves.json') != curves
        or witness_summary['curves_sha256'] != sha256(witness/'curves.json')
        or witness_summary['strict_completion_sha256'] != strict['completion_sha256']
        or witness_summary['screen_completion_sha256'] != screen['completion_sha256']):
        raise ValueError('Witness evidence does not bind these full audits')
    curves['enriched'] = candidate['variants']['candidate']['curve']
    rows = []
    for name, item in [('raw', strict['variants']['raw']), ('strict', strict['variants']['candidate']),
                       ('screen', screen['variants']['candidate']), ('enriched', candidate['variants']['candidate'])]:
        curve, event = item['curve'], item['event']
        rows.append(dict(method=name, max_body_depth_m=curve['max_depth_m'], peak_frame=curve['peak_frame'],
                         failed_samples=len(curve['failed_frames']), floor_max_m=curve['floor_max_m'],
                         event_gap_m=event['gap_m'], opposing_normal_degrees=event['region']['opposing_normal_degrees']))
    save(output/'curves.json', curves)
    save(output/'summary.json', dict(at=now(), rows=rows, sampling_plan=plan,
         full_clock_changes={name:changes(curves[name], curves['enriched'], plan['frames']) for name in ['raw', 'strict', 'screen']},
         completions={name:dict(folder=audit['folder'], sha256=audit['completion_sha256'])
                      for name, audit in [('strict', strict), ('screen', screen), ('enriched', candidate)]},
         curves_sha256=sha256(output/'curves.json'), quality_approved=False,
         scope='Same development seed, initializer, edit limits and iteration budget; enriched fitting clock uses prior failures. All four 299-sample curves retained. More samples entail more work; this is not equal wall time, held-out evaluation, continuous collision or realism approval.'))


def run(strict, screen, candidate, output, wait=False):
    strict, screen, candidate, output = [Path(p).resolve() for p in [strict, screen, candidate, output]]
    if output.exists():
        raise ValueError('Preserve previous comparison')
    owner = read(candidate/'request.json')
    output.mkdir(parents=True)
    (output/'implementation').mkdir()
    names = ['compare_enriched_partner_path.py', 'compare_partner_paths.py', 'contact_witness_clock.py', 'audit_paired_guides.py', 'strep.py']
    for name in names:
        shutil.copyfile(ROOT/'scripts'/name, output/'implementation'/name)
    process = psutil.Process()
    request = dict(at=now(), pid=process.pid, created=process.create_time(),
                   candidate=str(candidate), candidate_request_sha256=sha256(candidate/'request.json'),
                   owner=dict(pid=owner['pid'], created=owner['created']),
                   implementation={n:sha256(output/'implementation'/n) for n in names}, quality_approved=False)
    save(output/'request.json', request)
    def phase(status, **details):
        save(output/'pipeline.json', dict(status=status, at=now(), quality_approved=False, **details))
        print(status, flush=True)
    try:
        if wait:
            from audit_paired_guides import await_owner
            phase('waiting_for_exact_geometry_owner')
            await_owner(request['owner'], 'pid', 'created', candidate, {'complete'})
        if sha256(candidate/'request.json') != request['candidate_request_sha256']:
            raise ValueError('Completion request changed')
        for name, digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
                raise ValueError('Comparison implementation changed')
        phase('comparing')
        compare(strict, screen, candidate, output)
        save(output/'completion.json', dict(at=now(), summary_sha256=sha256(output/'summary.json'), quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed', error=str(exc), traceback=traceback.format_exc())
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['strict', 'screen', 'candidate', 'output']:
        p.add_argument(name, type=Path)
    p.add_argument('--wait', action='store_true')
    a = p.parse_args()
    run(a.strict, a.screen, a.candidate, a.output, a.wait)
