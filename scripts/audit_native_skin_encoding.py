"""Explain captured native/imported skin differences without changing acceptance.

The additive path is native pose -> observed pose -> loader Float32 weights ->
packed weights -> observed bind functions. It is an ordered numerical
decomposition, not an anatomical or causal motion-quality assessment.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now
from native_support_skin import NativeSupportSkin
from native_scene_imported_skin import source_engine_weights
from native_engine_contacts import features, packed_weights
from verify_native_actor_scene_engine import load

TERMS = ('pose', 'float32_normalization', 'weight_packing', 'bind_import')


class SkinEncodingComparison:
    def __init__(self, rig, imported):
        source = NativeSupportSkin(rig)
        count = len(rig.joints)
        nodes = np.array([rig.joints.index(n) for n in source.nodes.ravel()]).reshape(source.nodes.shape)
        loader_weights = source_engine_weights(rig)
        self.functions = (
            features(nodes, source.weights, source.points, count),
            features(nodes, loader_weights, source.points, count),
            features(nodes, packed_weights(loader_weights), source.points, count, quantized=True),
            features(imported.nodes, imported.weights, imported.points, count, quantized=True),
        )
        if any(f.shape != self.functions[0].shape for f in self.functions):
            raise ValueError('Complete source-ordered imported vertex functions required')
        self.source_weight_sums = source.weights.sum(axis=1)
        self.imported_weight_sums = imported.weights.sum(axis=1)
        self.bone_count = count

    def sample(self, native_world, observed_world):
        worlds = [np.asarray(w, float) for w in (native_world, observed_world)]
        if any(w.shape != (self.bone_count, 4, 4) or not np.isfinite(w).all() for w in worlds):
            raise ValueError('Complete finite source-ordered world bones required')
        pose = lambda w, f: np.einsum('bij,vbj->vi', w[:, :3, :], f)
        positions = [pose(worlds[0], self.functions[0])]
        positions += [pose(worlds[1], f) for f in self.functions]
        terms = {name: positions[i+1]-positions[i] for i, name in enumerate(TERMS)}
        terms['total'] = positions[-1]-positions[0]
        terms['telescoping_residual'] = terms['total']-sum(terms[name] for name in TERMS)
        return positions[0], positions[-1], terms


def run(contacts, policy, actor_engine, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh skin-encoding audit output required')
    with worker_lock(), threadpool_limits(limits=1):
        scene, _, observed, times, bindings = load(contacts, policy, actor_engine)
        producer = read(Path(actor_engine)/'result.json')
        methods = {p.name: sha256(p) for p in (ROOT/'scripts').glob('*.py')}
        output.mkdir(parents=True)
        shutil.copyfile(__file__, output/'auditor.py')
        save(output/'pipeline.json', dict(status='processing', quality_approved=False, release_approved=False))
        try:
            rows = {}; arrays = {'times_s': times}; names = TERMS+('total', 'telescoping_residual')
            for name, actor in scene.actors.items():
                rig = actor['rig']; skin = observed.skins[name]
                comparison = SkinEncodingComparison(rig, skin)
                errors = {term: [] for term in names}; peak = None
                _, rotation = actor['placement']
                for i, time in enumerate(times):
                    native_world = actor['sampler'].sample(float(time))
                    native, measured, terms = comparison.sample(native_world[rig.joints], observed.worlds[name][i])
                    if (not np.allclose(native, rig.vertices(native_world), rtol=0, atol=1e-12)
                            or not np.allclose(measured, skin.vertices(observed.worlds[name][i]), rtol=0, atol=1e-12)):
                        raise ValueError('Source and raw imported skin reconstruction must agree')
                    terms = {term: value @ rotation.T for term, value in terms.items()}
                    norms = {term: np.linalg.norm(value, axis=1) for term, value in terms.items()}
                    for term in names: errors[term].append(float(norms[term].max()))
                    if peak is None or errors['total'][-1] > peak['total_error_m']:
                        vertex = int(norms['total'].argmax())
                        peak = dict(time_s=float(time), vertex=vertex, total_error_m=errors['total'][-1],
                            total_vector_world_m=terms['total'][vertex].tolist(),
                            terms_at_same_vertex_world_m={term: terms[term][vertex].tolist() for term in TERMS},
                            source_weight_sum=float(comparison.source_weight_sums[vertex]),
                            imported_weight_sum=float(comparison.imported_weight_sums[vertex]))
                maxima = {term: max(values) for term, values in errors.items()}
                recorded = producer['skin_errors'][name]
                if (abs(maxima['total']-recorded['maximum_engine_native_vertex_error_m']) > 1e-12
                        or maxima['telescoping_residual'] > 1e-12):
                    raise ValueError('Original recorded skin discrepancy and additive identity required')
                rows[name] = dict(samples=len(times), vertices=len(comparison.functions[0]),
                    maximum_errors_m=maxima, peak=peak, recorded_skin_check=recorded)
                arrays.update({name+'_'+term+'_maximum_errors_m': np.array(values) for term, values in errors.items()})
            np.savez_compressed(output/'observations.npz', **arrays)
            load(contacts, policy, actor_engine)
            if (any(sha256(p) != h for p, h in bindings.items())
                    or methods != {p.name: sha256(p) for p in (ROOT/'scripts').glob('*.py')}
                    or sha256(__file__) != sha256(output/'auditor.py')):
                raise ValueError('Bound producer or audit implementation changed')
            result = dict(schema='strep-native-skin-encoding-audit-v1', at=now(), status='complete', actors=rows,
                observations_sha256=sha256(output/'observations.npz'), source_bindings_sha256=bindings,
                implementation_sha256=methods, original_selected=True, raw_imported_weights_renormalized=False,
                recorded_sampled_conditions_pass=producer['all_sampled_conditions_pass'],
                quality_approved=False, training_admitted=False, release_approved=False,
                scope='Actor-only retained original clock and observed raw skin. Ordered additive numerical decomposition; '
                      'component maxima can occur at different vertices/times and are not additive. '
                      'No correction, threshold change, new engine execution, GPU skin, motion realism or release approval.')
            save(output/'result.json', result)
            save(output/'pipeline.json', dict(status='complete', quality_approved=False, release_approved=False))
            return result
        except Exception as exc:
            save(output/'pipeline.json', dict(status='failed', error=str(exc), quality_approved=False, release_approved=False))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('contacts', 'policy', 'actor_engine', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    run(args.contacts, args.policy, args.actor_engine, args.output)
