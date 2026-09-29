"""Matched maximum versus per-vertex object inequalities on an authored scene."""
import argparse
import os
from pathlib import Path
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from fit_scene_regions import run as fit
from audit_scene_region_fit import run as audit
from run_godot_rig_import import run as engine


def summary(folder, audit_folder):
    result = read(folder / 'result.json')
    proof = read(audit_folder / 'verification.json')
    if sha256(folder / 'result.json') != proof['result_sha256']:
        raise ValueError('Audit does not match fitting result')
    recipe = read(folder / 'recipe.json')
    candidate = proof['variants']['candidate']
    source = proof['variants']['source']
    contacts = [c for row in candidate['rows'] for c in row['contacts']]
    return dict(seconds=result['seconds'], sampling=recipe['object_sampling'],
                object_constraints=recipe['object_inequalities'],
                contact_failures=candidate['contact_failures'], contact_samples=candidate['contact_samples'],
                geometry_failures=candidate['geometry_failures'], geometry_samples=len(candidate['rows']),
                minimum_object_clearance_m=min(v for row in candidate['rows'] for v in row['object_clearances_m'].values()),
                anchor_max_m=max(c['anchor_error_m'] for c in contacts),
                normal_max_degrees=max(c['normal_error_degrees'] for c in contacts if c['normal_error_degrees'] is not None),
                peak_joint_speed_m_s=candidate['peak_joint_speed_m_s'],
                peak_joint_acceleration_m_s2=candidate['peak_joint_acceleration_m_s2'],
                source_speed_m_s=source['peak_joint_speed_m_s'],
                source_acceleration_m_s2=source['peak_joint_acceleration_m_s2'],
                edit_bounds_passed=proof['hard_edit_bounds_passed'],
                stages=recipe['stage_records'], result_sha256=sha256(folder / 'result.json'),
                audit_sha256=sha256(audit_folder / 'verification.json'), quality_approved=False)


def run(scene, actor, contacts, output, stages, iterations, seconds):
    scene, output = scene.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Preserve previous comparison')
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError('Output must remain within the project')
    output.mkdir(parents=True)
    protocol = dict(at=now(), scene=str(scene), scene_sha256=sha256(scene),
                    actor=actor, contacts=contacts, stages=stages, iterations=iterations,
                    seconds_per_method=seconds, implementation_sha256=sha256(__file__),
                    scope='Equal stage/iteration caps with full skin coverage and balanced region loss. '
                          'Per-vertex mode changes multiplier layout and sums vertex merits, increasing '
                          'total penalty when multiple vertices violate. Not an equal-weight or runtime comparison. '
                          'Targets, floor samples, edit bounds and acceptance limits stay fixed.')
    save(output / 'protocol.json', protocol)
    save(output / 'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    rows, cases = [], []
    with threadpool_limits(limits=1):
        for mode in ['maximum', 'per_vertex']:
            folder, audit_folder = output / mode, output / (mode + '-audit')
            save(output / 'pipeline.json', dict(status='processing', method=mode, at=now()))
            row = dict(method=mode, status='processing')
            rows.append(row)
            save(output / 'results.json', dict(rows=rows, quality_approved=False))
            try:
                fit(scene, actor, contacts, folder, stages, iterations, seconds, 'balanced', True, mode)
                audit(folder, audit_folder)
                row.update(status='complete', **summary(folder, audit_folder))
                for variant in ['source', 'candidate']:
                    path = folder / (variant + '.glb')
                    frames = read(folder / 'authored-scene.json')['frame_count']
                    cases.append(dict(id=mode + '-' + variant, path=str(path), sha256=sha256(path),
                                      frames=frames, fps=30, sample_by_time=True))
            except Exception as exc:
                row.update(status='failed', error=str(exc))
            save(output / 'results.json', dict(rows=rows, quality_approved=False))
            print(dict(method=mode, status=row['status'], contact_failures=row.get('contact_failures'),
                       minimum_object_clearance_m=row.get('minimum_object_clearance_m')), flush=True)
    if sha256(scene) != protocol['scene_sha256'] or sha256(__file__) != protocol['implementation_sha256']:
        raise ValueError('Comparison input or runner changed')
    if cases:
        save(output / 'manifest.json', dict(cases=cases))
        engine(output, output / 'engine')
    failed = sum(row['status'] == 'failed' for row in rows)
    save(output / 'completion.json', dict(at=now(), protocol_sha256=sha256(output / 'protocol.json'),
         results_sha256=sha256(output / 'results.json'), failed=failed,
         engine_sha256=sha256(output / 'engine/verification.json') if cases else None,
         engine_actor_frames=sum(c['frames'] for c in cases), quality_approved=False))
    save(output / 'pipeline.json', dict(status='failed' if failed else 'complete', at=now()))
    if failed:
        raise RuntimeError('One or more fitting methods failed; preserved in results.json')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('scene', type=Path)
    p.add_argument('--actor', required=True)
    p.add_argument('--contact', action='append', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--stages', type=int, default=6)
    p.add_argument('--iterations', type=int, default=100)
    p.add_argument('--seconds', type=float, default=600)
    a = p.parse_args()
    run(a.scene, a.actor, a.contact, a.output, a.stages, a.iterations, a.seconds)
