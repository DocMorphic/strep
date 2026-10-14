"""Explicit weight-conditioned authoring with immutable original fidelity gates.

This CLI keeps the ordinary authoring recipe unchanged. It creates a separate
derivative recipe, executes the ordinary engine/contact/geometry job, and gates
its sampled result on original-reference skin fidelity. No automatic adoption.
"""
import argparse
import copy
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now
from action_worker_lock import worker_busy
from native_scene_authoring_job import validated, plan, run as author
from native_skin_export import run as export
from audit_conditioned_skin_fidelity import run as fidelity


def require(value, message):
    if not value: raise ValueError(message)


def run(recipe, output):
    recipe, output = Path(recipe).resolve(), Path(output).resolve()
    require(not output.exists(), 'Fresh conditioned authoring output required')
    require(not worker_busy(), 'Another local study worker is active')
    _, paths, scene, sources = validated(recipe)
    require(not any(Path(p).is_relative_to(output) for p in sources), 'Output contains an original input')
    methods = {str(p): sha256(p) for suffix in ('*.py', '*.gd') for p in (ROOT/'scripts').glob(suffix)}
    output.mkdir(parents=True)
    stages = []; frozen_files = {}; snapshots = {}

    def unchanged():
        for p, digest in {**sources, **methods, **frozen_files}.items():
            require(sha256(p) == digest, 'Conditioned authoring input/method/evidence changed')

    def execute(name, function, *args, **kwargs):
        unchanged()
        require(not worker_busy(), 'Another local study worker is active between stages')
        save(output/'pipeline.json', dict(status='processing', stage=name, completed_stages=stages,
            original_selected=True, quality_approved=False, release_approved=False))
        value = function(*args, **kwargs)
        folder = output/name
        require(value.get('status') == 'complete' and read(folder/'result.json') == value,
            'Complete saved stage evidence required')
        for p in folder.rglob('*'):
            if p.is_file(): frozen_files[str(p.resolve())] = sha256(p)
        stages.append(dict(id=name, result_sha256=sha256(folder/'result.json')))
        unchanged()
        return value

    try:
        archive = output/'original-inputs'; archive.mkdir()
        for i, (name, digest) in enumerate(sources.items()):
            if Path(name) == paths['engine']: continue
            target = archive/(str(i)+Path(name).suffix); shutil.copyfile(name, target)
            require(sha256(target) == digest, 'Original snapshot differs')
            snapshots[name] = dict(path=target.relative_to(output).as_posix(), sha256=digest)
            frozen_files[str(target)] = digest
        shutil.copyfile(__file__, output/'orchestrator.py')
        frozen_files[str(output/'orchestrator.py')] = sha256(__file__)
        spec = copy.deepcopy(read(paths['contacts'])); originals = {}; exports = {}
        for name, entry in spec['actors'].items():
            source = (paths['contacts'].parent/entry['glb']).resolve()
            originals[name] = dict(path=str(source), sha256=entry['sha256'])
            exports[name] = execute('skin-'+name, export, source, output/('skin-'+name))
            entry['glb'] = str(output/('skin-'+name)/'proposal.glb')
            entry['sha256'] = exports[name]['proposal_sha256']
        inputs = output/'derivative-inputs'; inputs.mkdir()
        contacts = inputs/'contacts.json'; save(contacts, spec)
        def rebind(name):
            value = copy.deepcopy(read(paths[name])); value['contacts_sha256'] = sha256(contacts)
            target = inputs/(name+'.json'); save(target, value); return target
        policy = rebind('geometry_policy')
        edit = rebind('object_edit') if 'object_edit' in paths else None
        speed = rebind('rotation_speed_policy') if 'rotation_speed_policy' in paths else None
        derived_recipe = inputs/'recipe.json'
        plan(contacts, policy, paths['engine'], derived_recipe, edit, rotation_speed_policy=speed)
        for p in inputs.iterdir(): frozen_files[str(p)] = sha256(p)
        result = execute('authoring', author, derived_recipe, output/'authoring')
        active_contacts = Path(result['artifacts']['active_contacts'])
        common = result['artifacts']['common_policy']
        active_policy = output/'authoring'/common if common else Path(result['artifacts']['active_policy'])
        proof = execute('original-fidelity', fidelity, active_contacts, active_policy,
            output/'authoring/actors-engine', originals, output/'original-fidelity')
        unchanged(); scene.check_inputs()
        final = dict(schema='strep-native-conditioned-authoring-v1', at=now(), status='complete',
            source_recipe_sha256=sha256(recipe), original_inputs_sha256=sources, original_snapshots=snapshots,
            implementation_sha256=methods, files_sha256={str(Path(p).relative_to(output)): h for p,h in frozen_files.items()},
            stages=stages, original_actor_bindings=originals, derivative_recipe_sha256=sha256(derived_recipe),
            samples=result['samples'], authoring_sampled_conditions_pass=result['sampled_conditions_pass'],
            original_reference_fidelity_pass=proof['all_original_reference_fidelity_pass'],
            sampled_conditions_pass=bool(result['sampled_conditions_pass'] and proof['all_original_reference_fidelity_pass']),
            mesh_weights_changed=True, source_animation_and_non_weight_data_preserved=True,
            original_selected=True, studio_selection_changed=False, quality_approved=False,
            training_admitted=False, release_approved=False, real_time_playback_verified=False,
            scope='Explicit separate weight export plus ordinary sampled authoring and original-reference fidelity. Originals retained; numerical failures remain failures. No Studio adoption, game package, renderer, physics, live playback or human-quality approval.')
        save(output/'result.json', final)
        save(output/'pipeline.json', dict(status='complete', completed_stages=stages, original_selected=True))
        return final
    except Exception as exc:
        save(output/'pipeline.json', dict(status='failed', error=str(exc), completed_stages=stages,
            original_selected=True, quality_approved=False, release_approved=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.recipe, args.output)
