"""Explicit extra-rotation planting with decoded gates and actual engine selection.

Native diagnostic mode never selects a correction. Normal execution additionally
requires the original legacy and every fixed imported frame-clock contact gate.
"""
import argparse
from pathlib import Path
import shutil
import sys
import numpy as np
import scipy
from strep import read, save, sha256, now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_support_permissions import validate_permissions, audit
from native_foot_plant import policy_rows
from native_toe_plant import ToePlantProblem
from native_joint_plant_job import restore
from native_support_feasibility import merit
from native_support_roundtrip import preview_values
from native_leg_floor import export_rotations
from paired_temporal_neighbor import rotation_channels
from engine_contact_sampling import contract, contract_sha256


def run(source, base, draft, public_policy, permissions_path, output, *, seed=None,
        search_policy=None, iterations=8, trust=.001, engine_check=True):
    if (type(iterations) is not int or not 1 <= iterations <= 16
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 0 < trust <= .02
            or type(engine_check) is not bool):
        raise ValueError('Bounded iterations/trust and explicit engine mode required')
    source, base, draft, public_policy, permissions_path, output = map(lambda p: Path(p).resolve(),
        (source, base, draft, public_policy, permissions_path, output))
    seed = base if seed is None else Path(seed).resolve()
    search_policy = public_policy if search_policy is None else Path(search_policy).resolve()
    if output.exists(): raise ValueError('Choose a fresh extra-rotation planting directory')
    inputs = {str(p): sha256(p) for p in (source, base, draft, public_policy, permissions_path, seed, search_policy)}
    spec = read(draft); permission_spec = read(permissions_path)
    rig = RigAsset.load(source); reader = NativeSupportSampler(rig.document, rig.binary, 0)
    _, rows = validate(spec, rig, reader, sha256(source))
    additions = validate_permissions(permission_spec, rig, rows, sha256(source), sha256(draft))
    public_limits = policy_rows(read(public_policy), source, base, draft, rows)
    search_limits = policy_rows(read(search_policy), source, base, draft, rows)
    if any(search_limits[k][v] > public_limits[k][v] for k in public_limits for v in ('anchor', 'speed')):
        raise ValueError('Proposal limits cannot be looser than original public limits')
    baseline = audit(source, base, draft, permissions_path, public_limits)
    warm_audit = audit(source, seed, draft, permissions_path, public_limits)
    warm = RigAsset.load(seed); warm_reader = NativeSupportSampler(warm.document, warm.binary, 0)
    problem = ToePlantProblem(rig, reader, rows, search_limits, warm_reader, additions)
    problem.native_roundtrip = True
    output.mkdir(); shutil.copyfile(base, output / 'input.glb'); shutil.copyfile(base, output / 'candidate.glb')
    archive = output / 'implementation'; archive.mkdir()
    from native_review_support import method_names
    names = set(method_names()) | {'native_support_permissions.py', 'native_toe_plant.py', 'native_toe_plant_job.py',
        'native_joint_plant.py', 'native_joint_plant_job.py', 'native_frame_plant.py', 'native_foot_plant.py',
        'native_support_rates.py', 'native_support_feasibility.py', 'native_support_roundtrip.py',
        'native_support_orientation.py', 'native_support_swivel.py', 'native_support_path.py',
        'engine_contact_sampling.py', 'native_engine_contacts.py', 'strep.py'}
    methods = {}
    for name in sorted(names):
        p = Path(__file__).resolve().parent / name; methods[str(p)] = sha256(p); shutil.copyfile(p, archive / name)
    save(output / 'request.json', dict(at=now(), inputs_sha256=inputs, implementation_sha256=methods,
        spec=spec, permissions=permission_spec, public_policy=read(public_policy), search_policy=read(search_policy),
        iterations=iterations, trust_radians=trust, engine_check=engine_check, native_roundtrip=True,
        frame_sampling_contract=contract(), frame_sampling_contract_sha256=contract_sha256(),
        python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
        scope='Explicit extra foot rotations under a new permission contract; original source rates and public contact limits retained',
        quality_approved=False, training_admitted=False, release_approved=False))
    save(output / 'pipeline.json', dict(status='processing', stage='fit'))
    probes = []; cache = {}
    try:
        def decoded(path):
            digest = sha256(path)
            if digest in cache:
                g, q, label = cache[digest]; return g, q, label
            asset = RigAsset.load(path); sampler = NativeSupportSampler(asset.document, asset.binary, 0)
            world = np.array([sampler.sample(float(t)) for t in problem.times])
            channels = rotation_channels(asset.document, asset.binary); q = {n: channels[n][2] for n in problem.nodes}
            g = problem.constraints(q, world); cache[digest] = (g, q, path.name); return g, q, None
        def evaluate(x, label):
            values, _ = problem.rotations(x); path = output / f'probe-{label}.glb'
            export_rotations(rig.document, rig.binary, values, path)
            raw, q, reused = decoded(path)
            preview = output / f'probe-{label}.preview.glb'
            export_rotations(rig.document, rig.binary, preview_values(q, problem.channels), preview)
            shadow, _, shadow_reused = decoded(preview)
            g = np.r_[raw, shadow]
            record = dict(label=label, file=path.name, sha256=sha256(path), preview_file=preview.name,
                preview_sha256=sha256(preview), raw_decode_reused_from=reused, preview_decode_reused_from=shadow_reused,
                raw_merit=list(merit(raw)), preview_merit=list(merit(shadow)), merit=list(merit(g)),
                raw_constraints_pass=bool(np.all(raw <= 0)), preview_constraints_pass=bool(np.all(shadow <= 0)))
            probes.append(record); save(path.with_suffix('.json'), dict(record, parameters=x.tolist(), quality_approved=False))
            return g
        def observe(info):
            save(output / 'progress.json', dict(status='running', history=info, probes=probes))
            print(dict(iteration=info['iteration'], before=info['before_merit'], after=info['after_merit'],
                selection=info['selected_fraction']), flush=True)
        x, optimization = restore(problem, evaluate, iterations=iterations, trust=trust, native_roundtrip=True, observe=observe)
        optimization['independently_decoded_unique_glbs'] = len(cache)
        evaluate(x, 'final'); final = probes[-1]
        shutil.copyfile(output / final['file'], output / 'proposal.glb')
        raw_audit = audit(source, output / 'proposal.glb', draft, permissions_path, public_limits)
        shadow_audit = audit(source, output / final['preview_file'], draft, permissions_path, public_limits)
        native_pass = bool(raw_audit['passed'] and shadow_audit['passed']
            and final['raw_constraints_pass'] and final['preview_constraints_pass'])
        controls = dict(schema='strep-native-extra-rotation-plant-controls-v1', parameters=x.tolist(),
            lower=problem.lower.tolist(), upper=problem.upper.tolist(), leg_control_count=problem.leg_size,
            leg_intervals=[dict(id=d['row']['id'], chain=d['row']['chain'], edit_keys=d['row']['edit_keys'],
                clock_s=d['clock'].tolist(), key_indices=d['free'].tolist(), control_indices=d['ids'].tolist(),
                patch_vertex_references=d['patch_vertex_references']) for d in problem.data],
            additional_rotations=[dict(id=e['row']['id'], node=e['node'], maximum_angle_degrees=e['angle'],
                edit_keys=e['row']['edit_keys'], key_indices=e['free'].tolist(), control_indices=e['ids'].tolist()) for e in problem.extras])
        save(output / 'controls.json', controls)
        engine = None
        if engine_check:
            from native_engine_contacts import run as imported_contacts
            save(output / 'pipeline.json', dict(status='processing', stage='actual_engine_import'))
            engine = imported_contacts(source, output / 'proposal.glb', draft, public_policy, output / 'engine', base=base, frame_sampling=True)
        engine_pass = bool(engine and engine['cases'][1]['all_contact_populations_pass'])
        accepted = bool(native_pass and engine_pass and not baseline['passed'])
        # Check binding invariants before replacing the safe input selection.
        if any(sha256(p) != h for p, h in {**inputs, **methods}.items()):
            raise ValueError('Extra-rotation planting inputs or methods changed')
        if accepted: shutil.copyfile(output / 'proposal.glb', output / 'candidate.glb')
        chosen = audit(source, output / 'candidate.glb', draft, permissions_path, public_limits)
        result = dict(status='complete', at=now(), retained_input=not accepted,
            retention_reason=None if accepted else 'native_diagnostic_only' if not engine_check else
                'input_already_satisfies_native_gates' if baseline['passed'] else 'proposal_failed_native_or_imported_gates',
            baseline=baseline, warm_seed_audit=warm_audit, proposal=raw_audit, preview_proposal=shadow_audit,
            selected=chosen, optimization=optimization, probes=probes, native_model_and_audits_pass=native_pass,
            actual_engine_contacts_pass=engine_pass, engine_check=engine_check,
            engine_result_sha256=sha256(output / 'engine/result.json') if engine else None,
            candidate_sha256=sha256(output / 'candidate.glb'), proposal_sha256=sha256(output / 'proposal.glb'),
            uses_extended_rotation_permissions=True, original_leg_only_preservation_verified=False,
            quality_approved=False, training_admitted=False, release_approved=False, native_npz_conversion_verified=False)
        save(output / 'result.json', result); save(output / 'pipeline.json', dict(status='complete')); return result
    except Exception as exc:
        # No failed or unverified engine run can leave a correction selected.
        shutil.copyfile(output / 'input.glb', output / 'candidate.glb')
        save(output / 'pipeline.json', dict(status='failed', error=str(exc))); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'base', 'draft', 'public_policy', 'permissions', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--seed', type=Path); parser.add_argument('--search-policy', type=Path)
    parser.add_argument('--iterations', type=int, default=8); parser.add_argument('--trust', type=float, default=.001)
    parser.add_argument('--native-diagnostic-only', action='store_true', help='No engine import and no correction selection')
    args = parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(), threadpool_limits(limits=1):
        result = run(args.source, args.base, args.draft, args.public_policy, args.permissions, args.output,
            seed=args.seed, search_policy=args.search_policy, iterations=args.iterations, trust=args.trust,
            engine_check=not args.native_diagnostic_only)
    print(dict(retained_input=result['retained_input'], native_pass=result['native_model_and_audits_pass'],
        actual_engine_contacts_pass=result['actual_engine_contacts_pass']))
