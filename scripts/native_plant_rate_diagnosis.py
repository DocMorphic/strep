"""Matched rate ablations for diagnosis only; never select a corrected asset.

All modes retain the original source caps for independent serialized audits.
An omitted search row is not an authored relaxation or a feasibility proof.
"""
import argparse
from pathlib import Path
import shutil
import sys
import numpy as np
import scipy
from scipy.sparse import diags
from strep import read, save, sha256, now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_foot_plant import policy_rows, preserve
from native_joint_plant import JointPlantProblem
from native_joint_plant_job import restore, authored_audit
from native_support_feasibility import merit
from native_support_roundtrip import preview_values
from native_leg_floor import export_rotations
from paired_temporal_neighbor import rotation_channels
from sampled_motion_caps import features, measures


MODES = {
    'original': (),
    'omit_translation_rates': (0, 1),
    'omit_angular_rates': (2, 3),
    'omit_all_rates': (0, 1, 2, 3),
}
METRICS = ('speed', 'acceleration', 'angular_speed', 'angular_acceleration')
UNITS = ('m/s', 'm/s^2', 'rad/s', 'rad/s^2')


def original_rate_details(problem, world):
    """Localize all-joint original-bin excesses without rebuilding the caps."""
    rates = measures(features(world[problem.rate_ids], problem.rig.joints), problem.caps.dt)
    details = []
    for metric, (actual, cap, order) in enumerate(zip(rates, problem.caps.caps, (1, 2, 1, 2))):
        excess = actual - cap - problem.caps.tolerance
        count = int(np.count_nonzero(excess > 0))
        worst = None
        if count:
            sample, column = np.unravel_index(np.argmax(excess), excess.shape)
            node = problem.rig.joints[column]
            time = (problem.uniform[sample + 1] if metric == 3 else
                    (problem.uniform[sample] + problem.uniform[sample + order]) / 2)
            worst = dict(node=int(node), name=problem.rig.document['nodes'][node].get('name'),
                time_s=float(time), actual=float(actual[sample, column]),
                source_bin_cap=float(cap[sample, column]), excess=float(excess[sample, column]))
        details.append(dict(metric=METRICS[metric], units=UNITS[metric], failed_rows=count,
            tolerance=problem.caps.tolerance, worst=worst))
    return details


class DiagnosticPlantProblem(JointPlantProblem):
    def __init__(self, rig, reader, rows, limits, seed_reader, *, mode):
        if not isinstance(mode, str) or mode not in MODES:
            raise ValueError('Choose a named diagnostic rate mode')
        self.diagnostic_mode = mode
        super().__init__(rig, reader, rows, limits, seed_reader)

    def rate_slices(self):
        offset = 0
        result = []
        for order in (1, 2, 1, 2):
            count = (len(self.uniform) - order) * len(self.columns)
            result.append(slice(offset, offset + count))
            offset += count
        return result

    def core_constraints(self, values, world):
        result = super().core_constraints(values, world)
        for metric in MODES[self.diagnostic_mode]:
            result[self.rate_slices()[metric]] = 0.
        return result

    def original_constraints(self, values, world):
        return np.r_[JointPlantProblem.core_constraints(self, values, world),
                     self.contact_constraints(world)]

    def sparsity(self, *, native_roundtrip=None):
        if native_roundtrip is None:
            native_roundtrip = self.native_roundtrip
        pattern = super().sparsity(native_roundtrip=native_roundtrip)
        active = np.ones(pattern.shape[0], dtype=int)
        copies = 2 if native_roundtrip else 1
        count = len(active) // copies
        for copy in range(copies):
            for metric in MODES[self.diagnostic_mode]:
                section = self.rate_slices()[metric]
                active[copy * count + section.start:copy * count + section.stop] = 0
        pattern = (diags(active) @ pattern).tocsr()
        pattern.eliminate_zeros()
        return pattern


def run(source, base, draft, policy_path, output, *, seed=None, mode='original',
        iterations=8, trust=.001):
    if not isinstance(mode, str) or mode not in MODES:
        raise ValueError('Choose a named diagnostic rate mode')
    if (type(iterations) is not int or not 1 <= iterations <= 16
            or type(trust) not in (int, float) or not np.isfinite(trust) or not 0 < trust <= .02):
        raise ValueError('Bounded diagnostic iterations and trust required')
    source, base, draft, policy_path, output = map(lambda p: Path(p).resolve(),
        (source, base, draft, policy_path, output))
    seed = base if seed is None else Path(seed).resolve()
    if output.exists():
        raise ValueError('Choose a fresh diagnostic output directory')
    inputs = {str(p): sha256(p) for p in (source, base, draft, policy_path, seed)}
    spec = read(draft)
    rig = RigAsset.load(source)
    reader = NativeSupportSampler(rig.document, rig.binary, 0)
    _, rows = validate(spec, rig, reader, sha256(source))
    limits = policy_rows(read(policy_path), source, base, draft, rows)
    baseline = authored_audit(source, base, spec, limits)
    warm_audit = authored_audit(source, seed, spec, limits)
    warm = RigAsset.load(seed)
    warm_reader = NativeSupportSampler(warm.document, warm.binary, 0)
    preserve(reader, warm_reader, rows)
    # warm_audit above checks static payloads as well as protected tracks.
    problem = DiagnosticPlantProblem(rig, reader, rows, limits, warm_reader, mode=mode)
    problem.native_roundtrip = True
    output.mkdir()
    archive = output / 'implementation'
    archive.mkdir()
    from native_review_support import method_names
    names = set(method_names()) | {
        'native_plant_rate_diagnosis.py', 'native_joint_plant.py', 'native_joint_plant_job.py',
        'native_foot_plant.py', 'native_support_rates.py', 'native_support_feasibility.py',
        'native_support_roundtrip.py', 'native_support_orientation.py',
        'native_support_swivel.py', 'native_support_path.py', 'strep.py',
    }
    methods = {}
    for name in sorted(names):
        path = Path(__file__).resolve().parent / name
        methods[str(path)] = sha256(path)
        shutil.copyfile(path, archive / name)
    save(output / 'request.json', dict(at=now(), inputs_sha256=inputs,
        implementation_sha256=methods, mode=mode, omitted_search_metrics=[METRICS[i] for i in MODES[mode]],
        iterations=iterations, trust_radians=trust, spec=spec, policy=read(policy_path),
        python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
        scope='Diagnostic search only; independent original gates and selected base stay unchanged'))
    save(output / 'pipeline.json', dict(status='processing'))
    probes = []
    cache = {}
    try:
        def decode(path):
            digest = sha256(path)
            if digest not in cache:
                asset = RigAsset.load(path)
                sampler = NativeSupportSampler(asset.document, asset.binary, 0)
                world = np.array([sampler.sample(float(t)) for t in problem.times])
                channels = rotation_channels(asset.document, asset.binary)
                values = {n: channels[n][2] for n in problem.nodes}
                cache[digest] = (problem.constraints(values, world),
                    problem.original_constraints(values, world), values, path.name,
                    original_rate_details(problem, world))
            return cache[digest]

        def evaluate(x, label):
            values, _ = problem.rotations(x)
            raw_path = output / f'probe-{label}.glb'
            export_rotations(rig.document, rig.binary, values, raw_path)
            raw, original, values, decoded_from, rate_details = decode(raw_path)
            preview_path = output / f'probe-{label}.preview.glb'
            export_rotations(rig.document, rig.binary, preview_values(values, problem.channels), preview_path)
            shadow, original_shadow, _, shadow_from, shadow_details = decode(preview_path)
            record = dict(label=label, file=raw_path.name, sha256=sha256(raw_path),
                preview_file=preview_path.name, preview_sha256=sha256(preview_path),
                raw_decoded_from=decoded_from, preview_decoded_from=shadow_from,
                original_raw_rate_details=rate_details, original_preview_rate_details=shadow_details,
                diagnostic_merit=list(merit(np.r_[raw, shadow])),
                original_merit=list(merit(np.r_[original, original_shadow])),
                diagnostic_model_constraints_pass=bool(np.all(np.r_[raw, shadow] <= 0)),
                original_model_constraints_pass=bool(np.all(np.r_[original, original_shadow] <= 0)))
            probes.append(record)
            save(raw_path.with_suffix('.json'), dict(record, parameters=x.tolist()))
            return np.r_[raw, shadow]

        def observe(info):
            save(output / 'progress.json', dict(status='running', history=info, probes=probes))
            print(dict(mode=mode, iteration=info['iteration'], after=info['after_merit']), flush=True)

        x, optimization = restore(problem, evaluate, iterations=iterations, trust=trust,
                                  native_roundtrip=True, observe=observe)
        evaluate(x, 'final')
        final = probes[-1]
        shutil.copyfile(output / final['file'], output / 'diagnostic.glb')
        raw_audit = authored_audit(source, output / 'diagnostic.glb', spec, limits)
        shadow_audit = authored_audit(source, output / final['preview_file'], spec, limits)
        # No selection, including if an ablation happens to satisfy the old gates.
        shutil.copyfile(base, output / 'candidate.glb')
        if any(sha256(p) != digest for p, digest in {**inputs, **methods}.items()):
            raise ValueError('Diagnostic inputs or methods changed')
        result = dict(status='complete', at=now(), mode=mode,
            omitted_search_metrics=[METRICS[i] for i in MODES[mode]],
            baseline=baseline, warm_seed_audit=warm_audit,
            original_raw_audit=raw_audit, original_preview_audit=shadow_audit,
            final_probe=final, optimization=optimization, probes=probes,
            independently_decoded_unique_glbs=len(cache), diagnostic_sha256=sha256(output / 'diagnostic.glb'),
            candidate_sha256=sha256(output / 'candidate.glb'), retained_input=True,
            authored_limits_changed=False, diagnostic_only=True, engine_contacts_verified=False,
            native_npz_conversion_verified=False, quality_approved=False,
            training_admitted=False, release_approved=False)
        save(output / 'result.json', result)
        save(output / 'pipeline.json', dict(status='complete'))
        return result
    except Exception as exc:
        save(output / 'pipeline.json', dict(status='failed', error=str(exc)))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'base', 'draft', 'policy', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--seed', type=Path)
    parser.add_argument('--mode', choices=tuple(MODES), required=True)
    parser.add_argument('--iterations', type=int, default=8)
    parser.add_argument('--trust', type=float, default=.001)
    args = parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(), threadpool_limits(limits=1):
        result = run(args.source, args.base, args.draft, args.policy, args.output,
                     seed=args.seed, mode=args.mode, iterations=args.iterations, trust=args.trust)
        print(dict(mode=result['mode'], diagnostic_only=True,
                   original_pass=result['original_raw_audit']['passed']), flush=True)
