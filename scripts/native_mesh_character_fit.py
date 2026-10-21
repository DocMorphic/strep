"""Bounded character-track proposals against unchanged moving mesh grips.

Contact models use exact grip points; geometry always uses original triangles.
Every proposed clip is saved and decoded. Originals remain selected even when
all declared sampled conditions pass. No prop movement is authorized here.
"""
import argparse
import copy
import os
from pathlib import Path
import shutil
import uuid
import numpy as np
from native_mesh_prop_scene import MeshPropScene, _json, _path, guarded_output, METHODS as MESH_METHODS
from native_scene_contacts import fields
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem, METHODS as FIT_METHODS
from native_scene_norms import linearize
from native_surface_model import include_times
from native_mesh_floor_guard import add_floor_guards
from native_mesh_character_surface import collect as collect_surface, add_guards as add_surface_guards
from native_control_neighborhood import refine as refine_controls
from native_scene_conic import direction, solver_identity
from native_contact_norms import protect_rows, row_regression
from native_mesh_prop_pose import conditions, metrics
from native_observation_archive import ObservationArchive, verify
from native_support_feasibility import merit
from engine_contact_sampling import frame_populations
from strep import read, save, sha256

METHODS = tuple(sorted(set(MESH_METHODS) | set(FIT_METHODS) |
                       {'native_mesh_character_fit.py', 'native_mesh_prop_pose.py', 'native_mesh_floor_guard.py',
                        'native_mesh_character_surface.py','native_triangle_pair_projection.py','native_surface_lift.py','native_control_neighborhood.py'}))


class MeshCharacterProblem(SceneProblem):
    def __init__(self, permissions_path):
        self.permission_path = Path(permissions_path).resolve()
        permission, digest = _json(self.permission_path)
        fields(permission, ('schema', 'mesh_scene', 'mesh_scene_sha256', 'actors'), 'mesh character permissions')
        if permission['schema'] != 'strep-native-mesh-character-edit-v1':
            raise ValueError('Explicit mesh character edit schema required')
        self.mesh = MeshPropScene(_path(self.permission_path.parent, permission['mesh_scene']))
        if permission['mesh_scene_sha256'] != self.mesh._manifest_sha256:
            raise ValueError('Permissions must bind the exact original mesh scene')
        self.inputs = {**self.mesh.inputs, str(self.permission_path): digest}
        native = dict(schema='strep-native-scene-edit-v2', contacts_sha256=self.mesh._actor_scene_sha256,
                      actors=copy.deepcopy(permission['actors']))
        edits = SceneEdits(native, self.mesh._scene, self.mesh._actor_scene_sha256)
        # Private point-target view only. These entries have poses, NOT proxy
        # geometry, and are never passed to SceneContacts or a geometry audit.
        view = copy.copy(self.mesh._scene)
        view.objects = {**view.objects, **{n: {k: p[k] for k in ('times', 'positions', 'rotations')}
                                        for n, p in self.mesh._props.items()}}
        view.rows = list(view.rows)
        for entry in self.mesh._rows:
            row = entry['authored']
            authored = {k: copy.deepcopy(row[k]) for k in ('id', 'actor', 'vertices', 'reduction', 'mode', 'interval_s', 'limits')}
            authored['target'] = dict(space='object', object=row['prop'], points_m=[entry['point'].tolist()])
            view.rows.append(dict(authored=authored, ids=entry['ids'].copy(), target_ids=entry['point'][None].copy()))
        if not view.rows:
            raise ValueError('Declare at least one contact to correct')
        clocks = [np.arange(int(np.floor(view.duration*120))+1)/120]
        clocks += [c[2] for a in view.actors.values() for c in a['sampler'].channels]
        clocks += [o['times'] for o in view.objects.values()]
        for entry in view.rows:
            row = entry['authored']; clocks.append(np.array(row['interval_s']))
            if row['mode'] == 'hold': clocks += [p['times_s'] for p in frame_populations(row['interval_s'])]
        count = len(np.unique(np.concatenate(clocks)))
        if count > 10000 or count*sum(len(a['rig'].parents) for a in view.actors.values())*16*8 > 128*1024**2:
            raise ValueError('Complete character proposal clock exceeds memory budget; no rows dropped')
        super().__init__(view, edits)
        self.check_inputs()

    def check_inputs(self):
        self.mesh.check_inputs()
        if any(sha256(path) != digest for path, digest in self.inputs.items()):
            raise ValueError('Original mesh character inputs changed')

    def write(self, value, folder):
        self.check_inputs(); folder = Path(folder); folder.mkdir(parents=True, exist_ok=False)
        manifest = read(self.mesh._manifest_path)
        actor_path = _path(self.mesh._manifest_path.parent, manifest['actor_scene'])
        actors = read(actor_path); files = {}; audits = {}
        for name, entry in actors['actors'].items():
            source = _path(actor_path.parent, entry['glb'])
            if name in self.edits.actors:
                path = folder/(name+'.glb'); self.edits.export(name, value, path)
                audits[name] = self.edits.audit(name, path, entry['animation_index'])
                # No additional serialization allowance for authored edit caps.
                audits[name]['strict_edit_caps_pass'] = all(r['maximum_change'] <= r['limit'] for r in audits[name]['tracks'])
                files[name] = path; entry.update(glb=path.name, sha256=sha256(path))
            else:
                entry['glb'] = str(source)
        save(folder/'actor-scene.json', actors)
        manifest['actor_scene'] = 'actor-scene.json'; manifest['actor_scene_sha256'] = sha256(folder/'actor-scene.json')
        for entry in manifest['props'].values(): entry['glb'] = str(_path(self.mesh._manifest_path.parent, entry['glb']))
        for entry in manifest['mesh_contacts']: entry['grip'] = str(_path(self.mesh._manifest_path.parent, entry['grip']))
        save(folder/'mesh-scene.json', manifest)
        residual, worlds = self.decoded(files, value)
        save(folder/'edit-audit.json', audits)
        np.savez_compressed(folder/'decoded-constraints.npz', controls=value, residual=residual, times_s=self.times)
        self.check_inputs()
        return MeshPropScene(folder/'mesh-scene.json'), residual, worlds, audits


def _finish_geometry_journal(folder,receipt):
    from native_mesh_geometry_journal import advance,finalize
    folder=Path(folder).resolve();journal=folder/'geometry-journal'
    if (folder/'geometry.json').exists():raise ValueError('Geometry is already published; do not overwrite its evidence')
    while not receipt['population_complete']:
        receipt=advance(journal,receipt['checkpoint'],receipt['sha256'],maximum_samples=4096)
    complete=folder/'geometry-complete'
    if complete.exists():complete=folder/('geometry-complete-'+uuid.uuid4().hex)
    result=finalize(journal,receipt['checkpoint'],receipt['sha256'],complete,materialize_observations=False)
    # A prior interrupted finalization stays in its original directory. Publish
    # the pointer before an atomic fresh link, so a killed copy cannot leave a
    # partial JSON at the fitter's complete-report path.
    save(folder/'geometry-journal-result.json',dict(directory=complete.name,
        result_sha256=sha256(complete/'result.json'),geometry_sha256=result['geometry_sha256'],
        optimizer_completed=False,quality_approved=False,release_approved=False))
    os.link(complete/'geometry.json',folder/'geometry.json')
    if sha256(folder/'geometry.json')!=result['geometry_sha256']:raise ValueError('Completed geometry report changed')
    return read(folder/'geometry.json')


def resume_geometry(scene,policy,folder,checkpoint,checkpoint_sha256):
    """Finish only a pinned interrupted audit; never reconstruct fit completion."""
    from native_mesh_geometry_journal import verify as verify_journal
    folder=Path(folder).resolve();journal=folder/'geometry-journal'
    if (folder/'geometry.json').exists():raise ValueError('Geometry is already published; do not overwrite its evidence')
    derived=copy.deepcopy(policy);derived['mesh_scene_sha256']=scene._manifest_sha256
    request=read(journal/'request.json')
    if (read(folder/'geometry-policy.json')!=derived
            or request['mesh_scene']!=str(scene._manifest_path.resolve())
            or request['policy']!=str(folder/'geometry-policy.json')):
        raise ValueError('Geometry recovery must retain the exact original scene and policy')
    checked=verify_journal(journal,checkpoint,checkpoint_sha256)
    receipt=dict(checkpoint=checkpoint,sha256=checkpoint_sha256,population_complete=checked['population_complete'])
    return _finish_geometry_journal(folder,receipt)


def audit_geometry(scene, policy, folder, *, checkpoint_geometry=False):
    if type(checkpoint_geometry) is not bool:raise ValueError('Explicit geometry checkpoint choice required')
    folder=Path(folder).resolve()
    if checkpoint_geometry and any((folder/name).exists() for name in ('geometry-policy.json','geometry-journal','geometry.json')):
        raise ValueError('Fresh checkpointed audit required; resume with its explicit checkpoint')
    derived = copy.deepcopy(policy); derived['mesh_scene_sha256'] = scene._manifest_sha256
    save(folder/'geometry-policy.json', derived)
    if checkpoint_geometry:
        from native_mesh_geometry_journal import prepare
        journal=folder/'geometry-journal'
        receipt=prepare(scene._manifest_path,folder/'geometry-policy.json',journal)
        return _finish_geometry_journal(folder,receipt)
    with ObservationArchive(folder/'geometry-observations.npz') as sink:
        report, _ = scene.geometry(derived, observation_sink=sink)
    verify(folder/'geometry-observations.npz'); save(folder/'geometry.json', report)
    return report


def fit(permissions_path, policy_path, output, *, iterations=4, trust=.02, backtracks=8, checkpoint_geometry=False, surface_guidance=False, refine_storage=False, linear_axis_rows=False):
    if type(checkpoint_geometry) is not bool:raise ValueError('Explicit geometry checkpoint choice required')
    if type(surface_guidance) is not bool:raise ValueError('Explicit surface guidance choice required')
    if type(refine_storage) is not bool:raise ValueError('Explicit storage refinement choice required')
    if type(linear_axis_rows) is not bool:raise ValueError('Explicit axis-linear representation choice required')
    if linear_axis_rows and not surface_guidance:raise ValueError('Axis-linear character proposals require surface guidance')
    if type(iterations) is not int or not 1 <= iterations <= 16 or type(backtracks) is not int or not 1 <= backtracks <= 12:
        raise ValueError('Choose 1-16 iterations and 1-12 backtracks')
    if type(trust) not in (int, float) or not np.isfinite(trust) or not 0 < trust <= .25:
        raise ValueError('Choose a finite positive trust fraction at most 0.25')
    problem = MeshCharacterProblem(permissions_path)
    policy_path = Path(policy_path).resolve(); policy, policy_digest = _json(policy_path)
    geometry_times, _, _ = problem.mesh._clock(policy)
    combined=np.unique(np.r_[problem.times,geometry_times])
    if len(combined)>10000 or len(combined)*sum(len(a['rig'].parents) for a in problem.scene.actors.values())*16*8>128*1024**2:
        raise ValueError('Complete geometry/character clock exceeds memory budget; no samples dropped')
    include_times(problem,geometry_times)
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Fresh character fitting output required')
    output.mkdir(parents=True); archive = output/'implementation'; archive.mkdir()
    method_names=METHODS
    if checkpoint_geometry:
        from native_mesh_geometry_journal import METHODS as JOURNAL_METHODS
        method_names=tuple(sorted(set(METHODS)|set(JOURNAL_METHODS)))
    methods = {name: sha256(Path(__file__).parent/name) for name in method_names}
    for name in methods: shutil.copyfile(Path(__file__).parent/name, archive/name)
    bindings = {**problem.inputs, str(policy_path): policy_digest}
    save(output/'input.json', dict(schema='strep-native-mesh-character-fit-v1', inputs_sha256=bindings,
         implementation_sha256=methods, solver=solver_identity(), iterations=iterations, trust=trust, backtracks=backtracks,
         checkpoint_geometry=checkpoint_geometry,surface_guidance=surface_guidance,refine_storage=refine_storage,
         linear_axis_rows=linear_axis_rows,
         source_rows=problem.protected_rows, contact_clock_s=problem.times.tolist(), geometry_clock_s=geometry_times.tolist(),
         props_editable=False, source_rebased=False, original_selected=True, quality_approved=False))
    value = problem.initial.copy(); history = []; probes = []
    source_folder = output/'original'; source_folder.mkdir()
    source_contacts, arrays = problem.mesh.contact_audit(); save(source_folder/'contacts.json', source_contacts)
    np.savez_compressed(source_folder/'contact-observations.npz', **arrays)
    geometry = audit_geometry(problem.mesh, policy, source_folder,checkpoint_geometry=checkpoint_geometry)
    surface_bank={};floor_bank={}
    if surface_guidance:
        collect_surface(problem.mesh,policy,geometry,surface_bank,floor_bank=floor_bank)
        save(output/'surface-witnesses.json',list(surface_bank.values()))
        save(output/'floor-witnesses.json',list(floor_bank.values()))
    original_conditions = conditions(geometry); current_conditions = original_conditions.copy()
    current_metrics = metrics(geometry)
    current = problem.model(value); worlds = problem.source_world
    if np.any(current[:problem.protected_rows] > 0): raise ValueError('Original native source conditions must pass')
    np.savez_compressed(source_folder/'constraints.npz', residual=current, times_s=problem.times)
    selected = None; stop = 'iteration_limit'
    for iteration in range(iterations):
        if np.all(current <= 0):
            stop = 'contacts_pass' if all(current_conditions.values()) else 'contacts_pass_geometry_unresolved'; break
        system, jacobian, differences = linearize(problem, value, step=.001, maximum_elements=16_000_000,
            difference_source='continuous', base_worlds=worlds, difference_scheme='central')
        np.testing.assert_allclose(system.residual(), current, atol=1e-9, rtol=1e-12)
        guarded, derivative, guard = protect_rows(system, jacobian, problem.protected_rows, current[problem.protected_rows:])
        guarded,derivative,hard,floor=add_floor_guards(problem,value,worlds,policy,geometry,guarded,derivative,guard['hard_rows'],trust,
            additional_witnesses=list(floor_bank.values()))
        previous_surface_count=len(surface_bank)+len(floor_bank)
        if surface_guidance:
            guarded,derivative,hard,surface=add_surface_guards(problem,value,worlds,surface_bank,guarded,derivative,hard,trust)
        delta, solver = direction(guarded, derivative, value, problem.lower, problem.upper, trust, hard_rows=hard,linear_axis_rows=bool(linear_axis_rows and surface_bank))
        record = dict(iteration=iteration, differences=differences, solver=solver, contact_protection=guard, floor_protection=floor, accepted_probe=None)
        if surface_guidance:record['surface_protection']=surface
        if delta is None:
            history.append(record); stop = 'no_guarded_direction'; break
        pending=[(backoff,value+delta*(.5**backoff),None) for backoff in range(backtracks)]
        while pending:
            backoff,proposed,refinement=pending.pop(0);folder = output/f'probe-{len(probes):03d}'
            candidate, residual, decoded_worlds, audits = problem.write(proposed, folder)
            source_pass = bool(np.all(residual[:problem.protected_rows] <= 0))
            edit_pass = all(a['passed'] and a['strict_edit_caps_pass'] for a in audits.values())
            contact_protected = bool(np.all(row_regression(current[problem.protected_rows:], residual[problem.protected_rows:]) <= 0))
            improved = merit(residual) < merit(current)
            row = dict(probe=len(probes), iteration=iteration, fraction=.5**backoff, source_rows_pass=source_pass,
                       strict_edit_caps_pass=edit_pass, contact_rows_no_worse=contact_protected,
                       contact_merit_improves=improved, geometry_evaluated=False, accepted=False,
                       original_selected=True, quality_approved=False, release_approved=False)
            if refinement is not None:row['storage_refinement']=refinement
            contact, observations = candidate.contact_audit()
            save(folder/'contacts.json', contact); np.savez_compressed(folder/'contact-observations.npz', **observations)
            row['all_declared_point_contacts_pass'] = contact['all_declared_point_contacts_pass']
            if source_pass and edit_pass and contact_protected and improved:
                checked = audit_geometry(candidate, policy, folder,checkpoint_geometry=checkpoint_geometry); flags = conditions(checked); measure = metrics(checked)
                if surface_guidance:
                    row['surface_guidance_observation']=collect_surface(candidate,policy,checked,surface_bank,floor_bank=floor_bank)
                    save(output/'surface-witnesses.json',list(surface_bank.values()))
                    save(output/'floor-witnesses.json',list(floor_bank.values()))
                if flags.keys() != original_conditions.keys(): raise ValueError('Geometry condition population changed')
                no_new = not any(current_conditions[k] and not flags[k] for k in flags)
                no_worse = all(measure[k] <= current_metrics[k] for k in measure)
                row.update(geometry_evaluated=True, geometry_conditions_pass=checked['sampled_conditions_pass'],
                           geometry_conditions_no_regression=no_new, geometry_metrics_no_worse=no_worse, geometry_metrics=measure)
                row['accepted'] = bool(no_new and no_worse)
                if row['accepted']:
                    value, current, worlds = proposed, residual, decoded_worlds
                    current_conditions, current_metrics, geometry = flags, measure, checked
                    selected = folder.name; record['accepted_probe'] = row['probe']
            probes.append(row); save(folder/'decision.json', row); save(output/'probes.json', probes)
            if row['accepted']: break
            if refine_storage and refinement is None and not source_pass and edit_pass and contact_protected and improved:
                choice,search=refine_controls(problem,proposed,value,current,trust,folder/'control-neighborhood')
                row['control_neighborhood']=search;save(folder/'decision.json',row);save(output/'probes.json',probes)
                if choice is not None:pending.insert(0,(backoff,choice,dict(parent_probe=row['probe'],search_directory=folder.name+'/control-neighborhood',selected_preview_probe=search['selected_preview_probe'])))
        history.append(record); save(output/'history.json', history)
        if record['accepted_probe'] is None:
            if surface_guidance and len(surface_bank)+len(floor_bank)>previous_surface_count:
                stop='surface_guidance_iteration_limit';continue
            stop = 'no_decoded_nonregressing_step'; break
    save(output/'history.json', history)
    if np.all(current <= 0):
        stop = 'contacts_pass' if geometry['sampled_conditions_pass'] else 'contacts_pass_geometry_unresolved'
    problem.check_inputs()
    if any(sha256(p) != digest for p, digest in bindings.items()) or any(sha256(Path(__file__).parent/n) != h or sha256(archive/n)!=h for n,h in methods.items()):
        raise ValueError('Original source or fitting implementation changed')
    result = dict(status='complete', stop_reason=stop, candidate=selected, accepted_steps=sum(p['accepted'] for p in probes),
                  probes=len(probes), final_contact_merit=list(merit(current)), all_native_and_contact_rows_pass=bool(np.all(current<=0)),
                  sampled_geometry_pass=geometry['sampled_conditions_pass'],
                  sampled_candidate_pass=bool(selected is not None and np.all(current<=0) and geometry['sampled_conditions_pass']
                      and read(output/selected/'contacts.json')['all_declared_point_contacts_pass']),
                  source_rebased=False, props_changed=False, original_selected=True,checkpoint_geometry=checkpoint_geometry,
                  engine_verified=False, quality_approved=False, release_approved=False,
                  scope='Existing authorized character tracks only; fixed original bounds and source rates, all authored point contacts, every declared geometry time and original mesh triangles. Rebuilt worst-vertex floor witnesses guide the step; complete decoded geometry decides acceptance. Nonregressing accepted steps remain diagnostic candidates. No mesh-collision-directed search, prop fitting, continuous collision, dynamics, semantic or animator approval.')
    if surface_guidance:
        result.update(surface_guidance=True,surface_triangle_time_pairs=len(surface_bank),retained_floor_vertex_time_pairs=len(floor_bank),
            scope='Bounded character proposals with rebuilt actor/mesh-prop triangle directions and floor vertices from complete current and rejected geometry reports. All original source/edit/contact protections and complete decoded geometry acceptance remain. No prop edits, partner/containment-directed search, continuous collision, dynamics, semantic or animator approval.')
    if refine_storage:result.update(refine_storage=True,storage_refinement_scope='Nearby existing translation knot controls only; full independent decoded acceptance unchanged.')
    if linear_axis_rows:result['linear_axis_rows']=True
    save(output/'result.json', result); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('permissions', 'policy', 'output'): parser.add_argument(name, type=Path)
    parser.add_argument('--iterations', type=int, default=4)
    parser.add_argument('--trust', type=float, default=.02)
    parser.add_argument('--backtracks', type=int, default=8)
    parser.add_argument('--checkpoint-geometry',action='store_true',
        help='Retain complete geometry frames with indexed observations. Does not resume optimizer state.')
    parser.add_argument('--surface-guidance',action='store_true',help='Guide character proposals with retained actor/prop triangle pairs; decoded geometry still decides acceptance.')
    parser.add_argument('--refine-storage',action='store_true',help='Try nearby authorized translation controls after source checks fail; all decoded acceptance checks remain required.')
    parser.add_argument('--linear-axis-rows',action='store_true',help='Experimental compact scalar constraints with surface guidance; may change the local search outcome. Default remains the original norm solver.')
    parser.add_argument('--worker', action='store_true'); args=parser.parse_args()
    if args.worker:
        from action_worker_lock import worker_lock
        from threadpoolctl import threadpool_limits
        with worker_lock(), threadpool_limits(limits=1): print(fit(args.permissions, args.policy, args.output, iterations=args.iterations, trust=args.trust, backtracks=args.backtracks,checkpoint_geometry=args.checkpoint_geometry,surface_guidance=args.surface_guidance,refine_storage=args.refine_storage,linear_axis_rows=args.linear_axis_rows))
    else:
        from resource_admission import ResourcePolicy
        from run_guarded_job import run
        from audit_guarded_job import audit
        output=guarded_output(args.output)
        result=run(Path(__file__),output/'guard',ResourcePolicy(expected_rss_bytes=512*1024**2,max_tree_rss_bytes=512*1024**2,
            stable_seconds=15,admission_seconds=600,max_seconds=900),worker_args=[str(args.permissions.resolve()),str(args.policy.resolve()),str(output/'fit'),'--iterations',str(args.iterations),'--trust',str(args.trust),'--backtracks',str(args.backtracks),'--worker']+(['--checkpoint-geometry'] if args.checkpoint_geometry else [])+(['--surface-guidance'] if args.surface_guidance else [])+(['--refine-storage'] if args.refine_storage else [])+(['--linear-axis-rows'] if args.linear_axis_rows else []))
        save(output/'resource-replay.json',audit(output/'guard'));raise SystemExit({'complete':0,'failed':1,'deferred':2}[result['status']])
