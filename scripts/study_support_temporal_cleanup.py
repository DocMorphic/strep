"""Frozen population study of full-clip root cleanup after support correction."""
import argparse
import ast
import copy
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from authored_root_correction import POLICY, export, load_motion
from support_temporal_cleanup import SupportProblem
from verify_support_temporal_cleanup import inspect
from run_godot_rig_import import run as engine
from study_whole_support_breadth import check_engine
from scipy.spatial.transform import Rotation


def prepare(snapshot, output):
    summary = read(snapshot/'summary.json')
    study = Path(summary['study'])
    if sha256(study/'protocol.json') != summary['protocol_sha256']:
        raise ValueError('Source population changed')
    if sha256(snapshot/'captured-results.json') != summary['captured_results_sha256']:
        raise ValueError('Source results changed')
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for row in summary['rows']:
        case = {k: row[k] for k in ('id', 'family', 'action', 'rig', 'status')}
        if row['status'] != 'complete':
            cases.append(case)
            continue
        source = study/'takes'/row['id']
        for name in ('verification', 'traces'):
            if sha256(source/(name+'.json')) != row[name+'_sha256']:
                raise ValueError('Frozen result changed: '+row['id'])
        proof = read(source/'verification.json')
        if not proof['bounds_and_preservation_passed']:
            raise ValueError('Source original bounds unverified')
        for variant, key in (('input', 'source_sha256'), ('candidate', 'candidate_sha256')):
            if sha256(source/variant/'character.glb') != proof[key]:
                raise ValueError('Frozen motion changed')
        folder = output/row['id']; folder.mkdir()
        for variant in ('input', 'candidate'):
            (folder/variant).mkdir()
            for name in ('character.glb', 'contacts.json'):
                shutil.copyfile(source/variant/name, folder/variant/name)
        for old, new in (('spec.json', 'contact-spec.json'), ('request.json', 'support-request.json'),
                         ('verification.json', 'original-verification.json'), ('traces.json', 'original-traces.json')):
            shutil.copyfile(source/old, folder/new)
        spec = read(folder/'contact-spec.json')
        if spec['contacts'] or spec['fps'] != 30:
            raise ValueError('This development adapter requires the original 30fps drafted support protocol')
        save(folder/'result.json', {k: spec[k] for k in ('frames', 'fps', 'root_node')})
        case.update(source='input', candidate='candidate',
                    files={p.relative_to(folder).as_posix(): sha256(p) for p in folder.rglob('*') if p.is_file()})
        cases.append(case)
    dest = output/'implementation'; dest.mkdir()
    pending, seen = [Path(__file__).name], set()
    while pending:
        name = pending.pop()
        if name in seen: continue
        seen.add(name); path = ROOT/'scripts'/name
        shutil.copyfile(path, dest/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for module in modules:
                child = (module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).exists(): pending.append(child)
    shutil.copyfile(ROOT/'scripts/godot_import_audit.gd', dest/'godot_import_audit.gd')
    seen.add('godot_import_audit.gd')
    policy = copy.deepcopy(POLICY)
    policy.update(minimum_relative_energy_improvement=.001, support_speed_tolerance_m_s=.00006)
    save(output/'protocol.json', dict(at=now(), cases=cases, policy=policy,
        snapshot=str(snapshot), snapshot_sha256=sha256(snapshot/'summary.json'),
        solver_bootstrap_sha256=sha256(ROOT/'reports/conic-solver-bootstrap-v1.json'),
        implementation={n: sha256(dest/n) for n in sorted(seen)}, quality_approved=False,
        scope='Every completed case from one frozen 24-case population snapshot; unfinished rows retained. '
        'One full-clip convex root-only proposal per completed case, four fixed exported fractions. '
        'Preserve original root budgets, pose channels, achieved floor, anchors, support height, '
        'root and patch accelerations, plus stance/entry/release and adjacent edge speeds. '
        'Require at least 0.1 percent actual root acceleration energy reduction. '
        'Numerical retention is not realism, held-out validation, or repair of inherited source failures.'))
    save(output/'freeze.json', dict(protocol_sha256=sha256(output/'protocol.json')))
    print('Prepared', len(cases), 'population rows', flush=True)


def run(output):
    protocol = read(output/'protocol.json')
    if read(output/'freeze.json')['protocol_sha256'] != sha256(output/'protocol.json'):
        raise ValueError('Frozen protocol changed')
    if (output/'runner.json').exists(): raise ValueError('Preserve prior run')
    proc = psutil.Process()
    save(output/'runner.json', dict(pid=proc.pid, created=proc.create_time(), at=now()))
    def validate():
        if read(output/'freeze.json')['protocol_sha256'] != sha256(output/'protocol.json'):
            raise ValueError('Protocol changed during study')
        check_files(ROOT/'scripts', protocol['implementation'])
        check_files(output/'implementation', protocol['implementation'])
        if sha256(ROOT/'reports/conic-solver-bootstrap-v1.json') != protocol['solver_bootstrap_sha256']:
            raise ValueError('Conic solver binding changed')
    rows, engine_cases = [], []
    validate()
    with threadpool_limits(limits=1):
        for case in protocol['cases']:
            row = dict(id=case['id'], family=case['family'], action=case['action'], rig=case['rig'], quality_approved=False)
            if case['status'] != 'complete':
                row.update(status='unfinished_source', source_status=case['status'])
                rows.append(row)
                continue
            folder = output/case['id']; dest = folder/'cleanup'; dest.mkdir(exist_ok=False)
            save(output/'pipeline.json', dict(at=now(), status='processing', case=case['id'], processed=len(rows), planned=len(protocol['cases'])))
            try:
                p = SupportProblem(folder, case, protocol['policy'])
                offsets, proposal = p.propose(); save(dest/'proposal.json', proposal)
                attempts, selected = [], p.source
                if offsets is not None:
                    np.save(dest/'proposed-offsets.npy', offsets)
                    for fraction in protocol['policy']['fractions']:
                        path = dest/('candidate-'+str(fraction)+'.glb')
                        export(p.rig, p.root, offsets*fraction, path)
                        audit = inspect(folder, path, protocol['policy'])
                        save(path.with_suffix('.json'), audit)
                        attempts.append(dict(fraction=fraction, path=str(path), audit_sha256=sha256(path.with_suffix('.json')),
                                             accepted=audit['all_checks_passed']))
                        if audit['all_checks_passed']:
                            selected = path
                            break
                row.update(status='candidate_preserved' if selected != p.source else 'input_retained',
                    selected=str(selected), selected_sha256=sha256(selected), attempts=attempts, proposal_status=proposal['status'])
                # Always retain explicit root/contact tracks for the selected asset.
                package = dest/'selected'; package.mkdir()
                shutil.copyfile(selected, package/'character.glb')
                shutil.copyfile(folder/'candidate/contacts.json', package/'contacts.json')
                _, world = load_motion(selected, p.frames); root = world[::2, p.root]
                save(package/'root-motion.json', dict(node=p.root, times_s=(np.arange(p.frames, dtype=np.float32)/30).tolist(),
                    positions_m=root[:, :3, 3].tolist(), rotations_xyzw=Rotation.from_matrix(root[:, :3, :3]).as_quat().tolist(),
                    space='Mapped pelvis world track; no engine root extraction'))
                save(package/'provenance.json', dict(source_files=case['files'], original_status='unapproved_development_support_correction',
                    correction_status=row['status'], selected_sha256=sha256(selected), quality_approved=False))
                for version, path in (('input', p.source), ('selected', package/'character.glb')):
                    engine_cases.append(dict(id=case['id']+'-'+version, path=str(path), sha256=sha256(path),
                                             frames=p.frames, fps=30, sample_by_time=True))
                check_files(folder, case['files'])
            except Exception as exc:
                row.update(status='failed', error=str(exc), traceback=traceback.format_exc())
            save(dest/'result.json', row); rows.append(row)
            save(output/'results.json', dict(rows=rows, quality_approved=False))
            print(case['id'], row['status'], row.get('error', ''), flush=True)
    validate()
    save(output/'manifest.json', dict(cases=engine_cases))
    save(output/'pipeline.json', dict(at=now(), status='engine', cases=len(engine_cases), quality_approved=False))
    engine(output, output/'engine')
    frames = check_engine(read(output/'engine/verification.json'), engine_cases)
    validate()
    save(output/'completion.json', dict(at=now(), protocol_sha256=sha256(output/'protocol.json'), rows=rows,
        engine_actor_frames=frames, engine_verification_sha256=sha256(output/'engine/verification.json'),
        files={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file() and
               'implementation' not in p.parts and p.name not in ('pipeline.json', 'completion.json') and 'engine' not in p.parts},
        quality_approved=False))
    save(output/'pipeline.json', dict(at=now(), status='complete', planned=len(rows),
        candidate_preserved=sum(r['status']=='candidate_preserved' for r in rows),
        input_retained=sum(r['status']=='input_retained' for r in rows),
        failed=sum(r['status']=='failed' for r in rows), unfinished_source=sum(r['status']=='unfinished_source' for r in rows),
        engine_actor_frames=frames, quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run'))
    parser.add_argument('output', type=Path)
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        if args.snapshot is None: parser.error('A frozen population snapshot is required')
        prepare(args.snapshot.resolve(), args.output.resolve())
    else: run(args.output.resolve())
