"""Frozen population trial of coupled leg/root support-boundary correction."""
import argparse
import ast
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from coupled_support_context import context, block
from coupled_support_block import solve
from midpoint_support_block import MidpointCoupledBlock
from verify_coupled_support import inspect
from rig_loop import encode
from authored_root_correction import load_motion
from run_godot_rig_import import run as engine
from study_whole_support_breadth import check_engine


def prepare(summary_folder, output, midpoint_constraints=False, steps_per_block=3, extended_backtracking=False):
    if type(steps_per_block) is not int or not 1 <= steps_per_block <= 30:
        raise ValueError('Use a finite step budget from1 to30 per block')
    summary = read(summary_folder/'summary.json'); previous = Path(summary['study'])
    complete = read(previous/'completion.json')
    if summary['study_completion_sha256'] != sha256(previous/'completion.json'):
        raise ValueError('Source study changed')
    check_files(previous, complete['files'])
    cases = []; output.mkdir(parents=True, exist_ok=False)
    for row in summary['rows']:
        case = {k: row[k] for k in ('id', 'family', 'action', 'rig', 'status')}
        case['eligible'] = bool(row.get('foot_peaks_still_above_raw_reporting_bin'))
        if not case['eligible']:
            cases.append(case); continue
        retained = next(r for r in complete['rows'] if r['id'] == row['id'])
        if sha256(retained['selected']) != retained['selected_sha256']:
            raise ValueError('Selected motion changed')
        original = ROOT/'reports/whole-support-breadth-v1/takes'/row['id']
        base = output/row['id']/'base'; base.mkdir(parents=True)
        (base/'input').mkdir(); (base/'selected').mkdir()
        for name in ('character.glb', 'contacts.json'):
            shutil.copyfile(original/'input'/name, base/'input'/name)
        for name in ('spec.json', 'request.json', 'fit.npz', 'traces.json', 'verification.json'):
            shutil.copyfile(original/name, base/name)
        shutil.copyfile(retained['selected'], base/'selected/character.glb')
        case.update(selected_sha256=retained['selected_sha256'],
            files={p.relative_to(base).as_posix(): sha256(p) for p in base.rglob('*') if p.is_file()})
        cases.append(case)
    dest = output/'implementation'; dest.mkdir()
    pending, seen = [Path(__file__).name], set()
    while pending:
        name = pending.pop()
        if name in seen: continue
        seen.add(name); path = ROOT/'scripts'/name; shutil.copyfile(path, dest/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for module in modules:
                child = (module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).exists(): pending.append(child)
    shutil.copyfile(ROOT/'scripts/godot_import_audit.gd', dest/'godot_import_audit.gd'); seen.add('godot_import_audit.gd')
    save(output/'protocol.json', dict(at=now(), cases=cases, summary=str(summary_folder),
        summary_sha256=sha256(summary_folder/'summary.json'), steps_per_block=steps_per_block, trusts=[.005, .001, .0002],
        midpoint_constraints=midpoint_constraints,
        blocks_per_case=2, frames_per_block=12, fractions=[2.**-n for n in range(11 if extended_backtracking else 4)],
        solver_bootstrap_sha256=sha256(ROOT/'reports/conic-solver-bootstrap-v1.json'),
        implementation={n: sha256(dest/n) for n in sorted(seen)}, quality_approved=False,
        scope=f"All {sum(c['eligible'] for c in cases)} remaining foot-peak-regression cases in the frozen {len(cases)}-row population. "
        'Root and original editable leg joints; at most two disjoint twelve-frame blocks selected by '
        f'largest supported speed excess over the raw per-foot peak. One finite {steps_per_block}-step solve per block. '
        'Preserve original bounds and achieved floor, root/foot accelerations, local rotation steps, '
        'support anchors/heights and boundary speeds. Actual decoded full-file acceptance and engine import. '
        'No semantic, physical, human or release approval; failed candidates are retained.'))
    save(output/'freeze.json', dict(protocol_sha256=sha256(output/'protocol.json')))
    print(dict(population=len(cases), eligible=sum(c['eligible'] for c in cases)), flush=True)


def run(output):
    protocol = read(output/'protocol.json')
    if (output/'runner.json').exists(): raise ValueError('Preserve previous run')
    p = psutil.Process(); save(output/'runner.json', dict(pid=p.pid, created=p.create_time(), at=now()))
    def validate():
        if read(output/'freeze.json')['protocol_sha256'] != sha256(output/'protocol.json'):
            raise ValueError('Protocol changed')
        check_files(ROOT/'scripts', protocol['implementation']); check_files(output/'implementation', protocol['implementation'])
        if sha256(ROOT/'reports/conic-solver-bootstrap-v1.json') != protocol['solver_bootstrap_sha256']:
            raise ValueError('Solver binding changed')
    def phase(status, **fields):
        save(output/'pipeline.json', dict(at=now(), status=status, quality_approved=False, **fields))
        print(status, fields, flush=True)
    rows, engine_cases = [], []
    validate()
    with threadpool_limits(limits=1):
        for case in protocol['cases']:
            row = dict(id=case['id'], family=case['family'], action=case['action'], rig=case['rig'], quality_approved=False)
            if not case['eligible']:
                row.update(status='not_targeted' if case['status'] in ('candidate_preserved', 'input_retained') else 'unfinished_source')
                rows.append(row); continue
            folder, base = output/case['id'], output/case['id']/'base'
            selected = base/'selected/character.glb'
            try:
                check_files(base, case['files']); phase('context', case=case['id'])
                ctx = context(base, selected)
                save(folder/'selection.json', dict(blocks=ctx['selection'], reconstruction_error_m=ctx['reconstruction_error_m']))
                values = ctx['initial'].copy(); logs = []; edited = set()
                for index, target in enumerate(ctx['selection']):
                    phase('fitting', case=case['id'], block=index+1, blocks=len(ctx['selection']))
                    p = block(ctx, target['frames'], values)
                    if protocol.get('midpoint_constraints'):
                        p = MidpointCoupledBlock(ctx['fitter'], ctx['oracle'], values,
                            ctx['source_world'], ctx['source_points'], target['frames'], ctx['envelope'], ctx['targets'])
                    values, solver = solve(p, protocol['steps_per_block'], protocol['trusts'], protocol['fractions'])
                    logs.append(dict(target=target, solver=solver)); edited.update(target['frames'])
                    save(folder/'solver.json', dict(blocks=logs, quality_approved=False))
                np.savez_compressed(folder/'parameters.npz', initial=ctx['initial'], parameters=values)
                accepted = False; take = folder/'take'; take.mkdir()
                shutil.copytree(base/'input', take/'input')
                for name in ('request.json', 'spec.json'): shutil.copyfile(base/name, take/name)
                shutil.copyfile(base/'traces.json', take/'raw-traces.json')
                dest = take/'candidate'; dest.mkdir()
                world = np.array([ctx['fitter'].pose(f, v)[0] for f, v in enumerate(values)])
                phase('exporting', case=case['id'])
                times, export_proof = encode(ctx['fitter'].rig, world, set(ctx['oracle'].animated), ctx['fitter'].spec['root_node'],
                                            dest/'character.glb', 'Coupled support boundary development correction')
                root = ctx['fitter'].spec['root_node']
                save(dest/'root-motion.json', dict(node=root, times_s=times.tolist(), positions_m=world[:, root, :3, 3].tolist(),
                    rotations_xyzw=Rotation.from_matrix(world[:, root, :3, :3]).as_quat().tolist()))
                shutil.copyfile(base/'input/contacts.json', dest/'contacts.json')
                phase('verifying', case=case['id'])
                audit = inspect(take, selected, sorted(edited)); save(folder/'audit.json', audit)
                accepted = audit['passed']
                if accepted: selected = dest/'character.glb'
                row.update(status='candidate_preserved' if accepted else 'input_retained',
                    selected=str(selected), selected_sha256=sha256(selected), audit_sha256=sha256(folder/'audit.json'),
                    export=export_proof)
                package = folder/'selected'; package.mkdir()
                shutil.copyfile(selected, package/'character.glb')
                shutil.copyfile(base/'input/contacts.json', package/'contacts.json')
                _, clock = load_motion(selected, ctx['fitter'].spec['frames']); track = clock[::2, root]
                save(package/'root-motion.json', dict(node=root, times_s=times.tolist(), positions_m=track[:, :3, 3].tolist(),
                    rotations_xyzw=Rotation.from_matrix(track[:, :3, :3]).as_quat().tolist()))
                save(package/'provenance.json', dict(source_files=case['files'], correction_status=row['status'],
                    inherited_status='unapproved_support_correction', quality_approved=False))
                for version, path in (('input', base/'selected/character.glb'), ('selected', package/'character.glb')):
                    engine_cases.append(dict(id=case['id']+'-'+version, path=str(path), sha256=sha256(path),
                        frames=ctx['fitter'].spec['frames'], fps=30, sample_by_time=True))
                check_files(base, case['files'])
            except Exception as exc:
                row.update(status='failed', error=str(exc), traceback=traceback.format_exc(),
                           selected=str(base/'selected/character.glb'), selected_sha256=sha256(base/'selected/character.glb'))
            rows.append(row); save(folder/'result.json', row); save(output/'results.json', dict(rows=rows, quality_approved=False))
            phase('case_complete', case=case['id'], outcome=row['status'], error=row.get('error'))
        # Include skipped and unfinished rows in the final population file too.
        save(output/'results.json', dict(rows=rows, quality_approved=False))
    validate(); save(output/'manifest.json', dict(cases=engine_cases))
    if engine_cases:
        phase('engine', clips=len(engine_cases)); engine(output, output/'engine')
        engine_frames = check_engine(read(output/'engine/verification.json'), engine_cases)
    else: engine_frames = 0
    validate()
    save(output/'completion.json', dict(at=now(), protocol_sha256=sha256(output/'protocol.json'), rows=rows,
        engine_actor_frames=engine_frames,
        files={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file() and
               'implementation' not in p.parts and 'engine' not in p.parts and p.name not in ('pipeline.json', 'completion.json')},
        engine_verification_sha256=sha256(output/'engine/verification.json') if engine_frames else None,
        quality_approved=False))
    phase('complete', counts={s: sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})},
          engine_actor_frames=engine_frames)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run')); parser.add_argument('output', type=Path)
    parser.add_argument('--summary', type=Path)
    parser.add_argument('--midpoint-constraints', action='store_true')
    parser.add_argument('--extended-backtracking', action='store_true')
    parser.add_argument('--steps-per-block', type=int, default=3); args = parser.parse_args()
    if args.command == 'prepare':
        if args.summary is None: parser.error('Frozen summary required')
        prepare(args.summary.resolve(), args.output.resolve(), args.midpoint_constraints, args.steps_per_block, args.extended_backtracking)
    else: run(args.output.resolve())
