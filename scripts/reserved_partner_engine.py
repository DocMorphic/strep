"""Bound headless import of complete reserved neutral partner skins/layouts.

No animation prompt, GPU rendering, interaction, physics or release approval.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from reserved_partner_fixtures import verify as verify_fixtures, METHODS as FIXTURE_METHODS
from rig_asset import RigAsset
from native_scene_engine import METHODS as ENGINE_METHODS
from native_scene_imported_skin import ImportedSceneSkin
from native_engine_contacts import matrices
from strep import ROOT, read, save, sha256, now

METHODS = tuple(dict.fromkeys(FIXTURE_METHODS+ENGINE_METHODS+
    ('reserved_partner_engine.py', 'godot_reserved_partner_audit.gd', 'action_worker_lock.py')))
JOINT_POSITION_LIMIT_M = 1e-5
BASIS_COMPONENT_LIMIT = 1e-5
SKIN_POSITION_LIMIT_M = 1e-4
MESH_SPACE_COMPONENT_LIMIT = 1e-7
ENGINE_VERSION = (4, 7, 2)


def require(condition, message):
    if not condition: raise ValueError(message)


def limits():
    return dict(joint_position_m=JOINT_POSITION_LIMIT_M, basis_component=BASIS_COMPONENT_LIMIT,
                skin_position_m=SKIN_POSITION_LIMIT_M, mesh_space_component=MESH_SPACE_COMPONENT_LIMIT)


def inputs(construction):
    construction = Path(construction).resolve()
    verify_fixtures(construction)
    result = read(construction/'result.json')
    bindings = {str(p): sha256(p) for p in construction.rglob('*') if p.is_file()}
    pairs = []
    for row in result['pairings']:
        folder = construction/'pairs'/row['id']; scene = read(folder/'scene.json'); actors = {}
        for name, entry in scene['actors'].items():
            character = (folder/entry['files']['character.glb']['path']).resolve()
            profile = (folder/entry['files']['rig-profile.json']['path']).resolve()
            require(character.is_relative_to(construction) and profile.is_relative_to(construction),
                    'Contained bound partner assets required')
            actors[name] = dict(rig_id=entry['rig_id'], path=str(character), sha256=sha256(character),
                profile_path=str(profile), profile_sha256=sha256(profile), placement=entry['placement'],
                role_order=entry['role_order'])
        pairs.append(dict(id=row['id'], actors=actors))
    return dict(schema='strep-reserved-partner-engine-request-v1', pairs=pairs,
                target_engine=list(ENGINE_VERSION), limits=limits(), motion_trials_executed=0), bindings


def transform(placement):
    q = placement['rotation_xyzw']
    require(q in ([0, 0, 0, 1], [0, 1, 0, 0]), 'Canonical opposing neutral placement required')
    position = np.asarray(placement['translation_m'], float)
    require(position.shape == (3,) and np.isfinite(position).all(), 'Finite placement required')
    matrix = np.eye(4)
    matrix[:3, :3] = np.diag([1., 1., 1.] if q == [0, 0, 0, 1] else [-1., 1., -1.])
    matrix[:3, 3] = position
    return matrix


def nearest_joint_parents(rig, names):
    source_names = {rig.document['nodes'][node]['name']: node for node in rig.joints}
    source_ids = {node: names.index(name) for name, node in source_names.items()}
    result = []
    for name in names:
        ancestor = rig.parents[source_names[name]]
        while ancestor != -1 and ancestor not in source_ids: ancestor = rig.parents[ancestor]
        result.append(-1 if ancestor == -1 else source_ids[ancestor])
    return result


def reduce(request, raw):
    require(request.get('schema') == 'strep-reserved-partner-engine-request-v1'
            and request.get('limits') == limits() and request.get('target_engine') == list(ENGINE_VERSION)
            and request.get('motion_trials_executed') == 0, 'Unchanged explicit neutral request and limits required')
    engine = raw.get('engine', {})
    require(tuple(engine.get(k) for k in ('major', 'minor', 'patch')) == ENGINE_VERSION,
            'Version-pinned skin encoding requires Godot 4.7.2')
    require(raw.get('compression_disabled') is True and raw.get('gpu_skin_baked') is False
            and raw.get('animation_played') is False, 'Explicit headless uncompressed neutral observation required')
    rows = raw.get('pairs'); requested = request['pairs']
    require(isinstance(requested, list) and len(requested) == 3
            and len({p['id'] for p in requested}) == len(requested), 'Complete three distinct directed pairs required')
    require(isinstance(rows, list) and [r.get('id') for r in rows] == [r['id'] for r in requested],
            'Complete ordered engine pairing population required')
    checks = []; arrays = {}
    for index, (item, row) in enumerate(zip(requested, rows)):
        require(set(item['actors']) == set(row.get('actors', {})) == {'A', 'B'}, 'Every placed actor required')
        actors = {}
        for name in ('A', 'B'):
            entry, observed = item['actors'][name], row['actors'][name]
            require(sha256(entry['path']) == entry['sha256']
                    and sha256(entry['profile_path']) == entry['profile_sha256'], 'Bound neutral rig/profile changed')
            rig = RigAsset.load(entry['path']); profile = read(entry['profile_path'])
            require(not rig.document.get('animations') and observed.get('nonreset_animations') == [],
                    'Neutral import must not execute an animation')
            require(observed.get('rig_id') == entry['rig_id'], 'Directed actor/rig identity changed')
            require(entry['role_order'] == list(profile['mapping']), 'Complete ordered mapped roles required')
            skin = ImportedSceneSkin(rig, observed)
            found = observed['bone_names']
            parents = observed.get('bone_parents')
            require(isinstance(parents, list) and all(type(p) is int for p in parents)
                    and parents == nearest_joint_parents(rig, found),
                    'Imported complete joint hierarchy differs')
            raw_world = matrices(observed['bones_world'])
            require(raw_world.shape == (len(rig.joints), 4, 4), 'Every neutral bone world transform required')
            world = np.empty_like(raw_world); world[skin.bone_map] = raw_world
            placement = transform(entry['placement'])
            expected_world = placement @ rig.reference[rig.joints]
            pose_error = float(np.linalg.norm(world[:, :3, 3]-expected_world[:, :3, 3], axis=1).max())
            basis_error = float(abs(world[:, :3, :3]-expected_world[:, :3, :3]).max())
            require(pose_error <= JOINT_POSITION_LIMIT_M and basis_error <= BASIS_COMPONENT_LIMIT,
                    'Imported neutral bone placement exceeds fixed limits')
            actor_matrix = matrices(observed['placement_world'])
            require(actor_matrix.shape == (4, 4) and float(abs(actor_matrix-placement).max()) <= MESH_SPACE_COMPONENT_LIMIT,
                    'Actual actor placement differs from canonical layout')
            skeleton_matrix = matrices(observed['skeleton_world'])
            require(skeleton_matrix.shape == (4, 4), 'Complete skeleton-space transform required')
            mesh_world = observed.get('mesh_world')
            require(isinstance(mesh_world, list) and len({m['node'] for m in mesh_world}) == len(mesh_world)
                    and {m['node'] for m in mesh_world} == {m['node'] for m in observed['meshes']},
                    'Every unique imported mesh-space transform required')
            mesh_error = 0.
            for mesh in mesh_world:
                matrix = matrices(mesh['matrix'])
                require(matrix.shape == (4, 4), 'Complete imported mesh transform required')
                mesh_error = max(mesh_error, float(abs(matrix-skeleton_matrix).max()))
            require(mesh_error <= MESH_SPACE_COMPONENT_LIMIT, 'Mesh/skeleton spaces differ; cannot omit the mesh transform')
            expected_points = rig.vertices(rig.reference) @ placement[:3, :3].T+placement[:3, 3]
            imported_points = skin.vertices(world)
            skin_error = float(np.linalg.norm(imported_points-expected_points, axis=1).max())
            require(skin_error <= SKIN_POSITION_LIMIT_M, 'Imported full neutral skin exceeds fixed position limit')
            roles = [rig.joints.index(profile['mapping'][r]) for r in entry['role_order']]
            prefix = f'pair_{index}_{name}_'
            arrays.update({prefix+'expected_vertices_world_m': expected_points,
                prefix+'imported_vertices_world_m': imported_points,
                prefix+'expected_bones_world': expected_world, prefix+'imported_bones_world': world,
                prefix+'expected_role_positions_m': expected_world[roles, :3, 3],
                prefix+'imported_role_positions_m': world[roles, :3, 3]})
            actors[name] = dict(rig_id=entry['rig_id'], bones=len(rig.joints), role_origins=len(roles),
                maximum_joint_position_error_m=pose_error, maximum_basis_component_error=basis_error,
                maximum_skin_position_error_m=skin_error, maximum_mesh_space_component_error=mesh_error,
                imported_minimum_y_m=float(imported_points[:, 1].min()),
                expected_minimum_y_m=float(expected_points[:, 1].min()), imported_skin=skin.report,
                full_static_import_pass=True)
        checks.append(dict(id=item['id'], actors=actors))
    return dict(pairs=checks, static_import_pass=True, limits=limits(),
        actors=2*len(checks), complete_vertex_observations=sum(a['imported_skin']['source_vertices'] for r in checks for a in r['actors'].values()),
        complete_role_origins=sum(a['role_origins'] for r in checks for a in r['actors'].values()),
        complete_bones=sum(a['bones'] for r in checks for a in r['actors'].values()),
        imported_skin_weights_renormalized=False, motion_trials_executed=0,
        physics_checked=False, gpu_render_checked=False, animated_collision_checked=False,
        anatomical_facing_reviewed=False, interaction_contacts_checked=False,
        quality_approved=False, release_approved=False), arrays


def run(construction, output, engine):
    construction, output, engine = [Path(p).resolve() for p in (construction, output, engine)]
    require(not output.exists() and not output.is_relative_to(construction) and not construction.is_relative_to(output),
            'Fresh separate neutral import output required')
    with worker_lock(), threadpool_limits(limits=1):
        request, bindings = inputs(construction)
        bindings[str(engine)] = sha256(engine)
        for name in METHODS: bindings[str(ROOT/'scripts'/name)] = sha256(ROOT/'scripts'/name)
        output.mkdir(parents=True); project = output/'project'; project.mkdir()
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep reserved neutral partner import"\n', encoding='utf-8')
        script = ROOT/'scripts/godot_reserved_partner_audit.gd'; shutil.copyfile(script, project/'audit.gd')
        for name in METHODS:
            target = output/'implementation'/name; target.parent.mkdir(exist_ok=True); shutil.copyfile(ROOT/'scripts'/name, target)
        save(output/'request.json', request); save(output/'bindings.json', bindings)
        save(output/'pipeline.json', dict(at=now(), status='processing', stage='headless-neutral-partner-import'))
        try:
            with (output/'engine.log').open('w', encoding='utf-8') as log:
                child = subprocess.run([str(engine), '--headless', '--path', str(project), '--script', 'audit.gd', '--',
                    str(output/'request.json'), str(output/'engine-output.json')], stdout=log, stderr=subprocess.STDOUT,
                    timeout=300, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            require(child.returncode == 0, 'Neutral partner import failed; retained engine.log')
            raw = read(output/'engine-output.json'); checked, arrays = reduce(request, raw)
            np.savez_compressed(output/'observations.npz', **arrays)
            save(output/'verification.json', checked)
            require(all(sha256(p) == h for p, h in bindings.items()), 'Bound neutral import input/method changed')
            require(sha256(project/'audit.gd') == bindings[str(script)] and read(output/'request.json') == request,
                    'Executed engine script or request changed')
            result = dict(schema='strep-reserved-partner-engine-result-v1', at=now(), status='complete',
                engine=raw['engine'], construction_result_sha256=sha256(construction/'result.json'),
                construction=str(construction), **checked,
                files_sha256={name: sha256(output/name) for name in
                    ('request.json', 'bindings.json', 'engine.log', 'engine-output.json', 'observations.npz', 'verification.json')})
            save(output/'result.json', result); save(output/'pipeline.json', dict(at=now(), status='complete')); return result
        except Exception as exc:
            save(output/'pipeline.json', dict(at=now(), status='failed', error=str(exc))); raise


def verify(output):
    output = Path(output).resolve(); result = read(output/'result.json')
    require(result.get('schema') == 'strep-reserved-partner-engine-result-v1' and result.get('status') == 'complete',
            'Complete neutral partner engine result required')
    require(set(result['files_sha256']) == {'request.json', 'bindings.json', 'engine.log', 'engine-output.json', 'observations.npz', 'verification.json'},
            'Complete engine observation inventory required')
    for name, digest in result['files_sha256'].items(): require(sha256(output/name) == digest, 'Saved engine evidence changed')
    bindings = read(output/'bindings.json')
    require(all(sha256(path) == digest for path, digest in bindings.items()), 'Bound neutral inputs or methods changed')
    construction = Path(result['construction'])
    require(sha256(construction/'result.json') == result['construction_result_sha256'], 'Neutral construction changed')
    request, _ = inputs(construction)
    require(request == read(output/'request.json'), 'Saved engine request differs from reserved layouts')
    for name in METHODS:
        require(sha256(output/'implementation'/name) == sha256(ROOT/'scripts'/name), 'Archived neutral engine method differs')
    require(sha256(output/'project/audit.gd') == sha256(ROOT/'scripts/godot_reserved_partner_audit.gd'), 'Executed script differs')
    raw = read(output/'engine-output.json'); checked, arrays = reduce(request, raw)
    require(checked == read(output/'verification.json') and all(result.get(k) == v for k, v in checked.items())
            and result['engine'] == raw['engine'], 'Saved neutral import reduction differs')
    with np.load(output/'observations.npz', allow_pickle=False) as saved:
        require(set(saved.files) == set(arrays), 'Complete neutral imported array population required')
        require(all(np.array_equal(saved[k], v) for k, v in arrays.items()), 'Saved imported neutral observations differ')
    return checked


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    audit = commands.add_parser('run'); audit.add_argument('construction', type=Path); audit.add_argument('output', type=Path)
    audit.add_argument('engine', type=Path)
    replay = commands.add_parser('verify'); replay.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'run': run(args.construction, args.output, args.engine)
    else: verify(args.output)
