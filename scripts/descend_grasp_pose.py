"""Physical-coordinate local clearance descent; a pose diagnostic, not a clip."""
import argparse
import shutil
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem, norm_slack_and_jacobian
from support_contact_v8 import torch_primitive_clearance_violation
from restore_grasp_pose import protected_pass, clearance_violation
from grasp_physical_step import epigraph_step, norm_remainder


def selected_rows(p, x, selected):
    protected_count = len(p.contacts)+len(p.normals)+1
    protected = p.geometry_slack(x, .0001)[:protected_count]
    _, _, _, vertices = p.fk(x)
    rows = []
    for index, ids in selected:
        geometry, _, position, rotation = p.objects[index]
        values = torch_primitive_clearance_violation(vertices[None], position, rotation, geometry, p.config['object_clearance_m'])[0]
        rows.append(-values[ids]/.01)
    return torch.cat(rows), protected


def run(study, seed_report, output):
    torch.set_num_threads(2)
    study, seed_report, output = [Path(s).resolve() for s in (study, seed_report, output)]
    fit = study/'fit'; summary = read(fit/'summary.json')
    seed_result, seed_protocol = read(seed_report/'result.json'), read(seed_report/'protocol.json')
    if summary['solver_version'] != 13 or sha256(fit/'summary.json') != seed_protocol['fit_summary_sha256']:
        raise ValueError('Matched V13 study required')
    if sha256(ASSET) != summary['mesh_sha256'] or sha256(seed_report/'pose.npz') != seed_result['pose_sha256']:
        raise ValueError('Mesh or seed changed')
    for name, digest in seed_protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Seed input changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), seed_protocol['frame'])
    x = np.array(seed_result['parameters']); before, _ = p.independent(x)
    if not protected_pass(before, p.config): raise ValueError('Protected seed gates must pass')
    output.mkdir(parents=True, exist_ok=False); (output/'implementation').mkdir()
    files = ['descend_grasp_pose.py', 'grasp_physical_step.py', 'grasp_pose_witness.py', 'restore_grasp_pose.py',
             'support_contact_v8.py', 'support_contact_v5.py', 'floor_contact.py', 'scene_solver_context.py', 'object_geometry.py']
    limits = dict(steps=12, trusts_degrees=[.25, .05, .01, .002], root_trust_at_largest_m=.0005,
                  active_band_m=.003, maximum_active_rows=500, protected_margin_normalized=1e-5,
                  backtracks=8, minimum_improvement_m=1e-6, seconds=300,
                  maximum_rss_bytes=2*1024**3, minimum_available_bytes=int(1.25*1024**3))
    protocol = dict(at=now(), study=study.relative_to(ROOT).as_posix(), frame=p.frame, limits=limits,
                    inputs=seed_protocol['inputs'], fit_summary_sha256=sha256(fit/'summary.json'),
                    seed_result_sha256=sha256(seed_report/'result.json'), seed_protocol_sha256=sha256(seed_report/'protocol.json'),
                    implementation={n: sha256(ROOT/'scripts'/n) for n in files}, quality_approved=False,
                    scope='Single pose, original physical rotation-norm/root/point/normal/floor limits. LP epigraph uses vertices within 3mm of current worst violation across all objects; exact full-skin nonlinear audit rechecks all omitted vertices and objects. A failed local step is not infeasibility or optimality proof.')
    save(output/'protocol.json', protocol)
    for n in files: shutil.copyfile(ROOT/'scripts'/n, output/'implementation'/n)
    start = time.monotonic(); history = []; peak = 0; current = before; status = 'complete'; stop = 'step_limit'
    def guard():
        nonlocal peak
        rss = psutil.Process().memory_info().rss; peak = max(peak, rss)
        if time.monotonic()-start > limits['seconds'] or rss > limits['maximum_rss_bytes'] or psutil.virtual_memory().available < limits['minimum_available_bytes']:
            raise TimeoutError('Physical descent resource guard')
    try:
        for stage in range(limits['steps']):
            guard()
            with torch.no_grad():
                _, _, _, vertices = p.fk(p.t(x))
                violations = [torch_primitive_clearance_violation(vertices[None], position, rotation, geometry, p.config['object_clearance_m'])[0].numpy()
                              for geometry, _, position, rotation in p.objects]
            worst = max(v.max() for v in violations)
            selected = [(i, np.flatnonzero(v >= worst-limits['active_band_m'])) for i, v in enumerate(violations)]
            selected = [(i, ids) for i, ids in selected if len(ids)]
            if sum(len(ids) for _, ids in selected) > limits['maximum_active_rows']:
                stop = 'active_row_resource_limit'; break
            variable = p.t(x).requires_grad_(); s, c = selected_rows(p, variable, selected)
            all_rows = torch.cat([s, c]); jac = []
            for row in all_rows:
                jac.append(torch.autograd.grad(row, variable, retain_graph=True)[0].detach().numpy()); guard()
            sj, cj = np.array(jac[:len(s)]), np.array(jac[len(s):])
            surface, protected = s.detach().numpy(), c.detach().numpy()
            norm, nj = norm_slack_and_jacobian(x, p.limits)
            full_c, full_j = np.r_[protected, norm], np.r_[cj, nj]
            # Fixed-row finite difference, including all active skin rows.
            direction = np.random.default_rng(718+stage).normal(size=p.dim); direction /= np.linalg.norm(direction); h = 1e-6
            with torch.no_grad():
                plus = torch.cat(selected_rows(p, p.t(x+h*direction), selected)).numpy()
                minus = torch.cat(selected_rows(p, p.t(x-h*direction), selected)).numpy()
            error = float(np.max(np.abs(np.array(jac)@direction-(plus-minus)/(2*h))))
            np.testing.assert_allclose(np.array(jac)@direction, (plus-minus)/(2*h), atol=2e-5, rtol=2e-4)
            linear_file = output/f'linearization-{stage:02d}.npz'
            np.savez(linear_file, parameters=x, surface=surface, surface_jac=sj, protected=full_c, protected_jac=full_j)
            record = dict(stage=stage, before=current, linearization_sha256=sha256(linear_file),
                          selected=[dict(object_index=i, vertices=ids.tolist()) for i, ids in selected],
                          derivative_error=error, attempts=[], accepted=False)
            history.append(record)
            for trust in limits['trusts_degrees']:
                radius = np.r_[np.full(p.dim-1, np.deg2rad(trust)), limits['root_trust_at_largest_m']*trust/limits['trusts_degrees'][0]]
                lower, upper = -radius.copy(), radius.copy()
                lower[-1] = max(lower[-1], -x[-1]); upper[-1] = min(upper[-1], p.config['max_root_lift_m']-x[-1])
                margins = np.r_[np.full(len(protected), limits['protected_margin_normalized']), norm_remainder(radius, p.limits)]
                delta, lp = epigraph_step(surface, sj, full_c, full_j, margins, radius, lower, upper)
                attempt = dict(trust_degrees=trust, lp=lp, backtracks=[]); record['attempts'].append(attempt)
                if delta is None: continue
                attempt['delta'] = delta.tolist()
                for backtrack in range(limits['backtracks']):
                    fraction = .5**backtrack; candidate = x+fraction*delta; audit, _ = p.independent(candidate)
                    improved = clearance_violation(current, p.config)-clearance_violation(audit, p.config)
                    permitted = protected_pass(audit, p.config)
                    accepted = bool(permitted and improved >= limits['minimum_improvement_m'])
                    attempt['backtracks'].append(dict(fraction=fraction, audit=audit, protected_pass=permitted, improvement_m=improved, accepted=accepted))
                    if accepted:
                        x, current = candidate, audit; record.update(accepted=True, after=audit); break
                if record['accepted']: break
            save(output/'progress.json', dict(history=history, seconds=time.monotonic()-start, status='running'))
            print(dict(stage=stage, accepted=record['accepted'], violation_m=clearance_violation(current, p.config), rows=len(surface)), flush=True)
            if current['pose_witness_passed']: stop = 'full_pose_witness'; break
            if not record['accepted']: stop = 'no_guarded_improvement'; break
    except TimeoutError as e:
        status, stop = 'interrupted_resource_guard', str(e)
    final, motion = p.independent(x); np.savez(output/'pose.npz', **motion)
    with torch.no_grad(): _, _, _, tv = p.fk(p.t(x))
    nv = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0])
    skin_error = float(np.max(np.abs(tv.numpy()-nv)))
    if skin_error > 2e-6: raise ValueError('Independent skin mismatch')
    for n, digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/n) != digest: raise ValueError('Implementation changed')
    for n, digest in protocol['inputs'].items():
        if sha256(ROOT/n) != digest: raise ValueError('Input changed')
    save(output/'result.json', dict(at=now(), status=status, stop_reason=stop, seed=before, candidate=final,
         parameters=x.tolist(), history=history, seconds=time.monotonic()-start, sampled_peak_rss_bytes=peak,
         independent_skin_max_error_m=skin_error, pose_sha256=sha256(output/'pose.npz'), protocol_sha256=sha256(output/'protocol.json'), quality_approved=False))
    save(output/'pipeline.json', dict(status=status, pose_witness_passed=final['pose_witness_passed'], quality_approved=False))
    print(dict(status=status, stop=stop, audit=final), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=2): run(args.study, args.seed_report, args.output)
