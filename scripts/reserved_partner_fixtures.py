"""Portable grounded neutral partner layouts, with complete saved-data reductions.

No motion prompts, model inference, interaction contacts or engine work. Local
+Z axes oppose each other; anatomical facing still requires review.
"""
import argparse
from pathlib import Path
import re
import shutil
import numpy as np
from rig_asset import RigAsset
from strep import ROOT, read, save, sha256, now

METHODS = ('reserved_partner_fixtures.py', 'rig_asset.py', 'gltf_tools.py', 'strep.py')
PARENTS = {'Hips': None, 'Spine2': 'Hips', 'Chest': 'Spine2', 'Neck1': 'Chest', 'Head': 'Neck1',
    'LeftArm': 'Chest', 'LeftForeArm': 'LeftArm', 'LeftHand': 'LeftForeArm',
    'RightArm': 'Chest', 'RightForeArm': 'RightArm', 'RightHand': 'RightForeArm',
    'LeftLeg': 'Hips', 'LeftShin': 'LeftLeg', 'LeftFoot': 'LeftShin', 'LeftToeBase': 'LeftFoot',
    'RightLeg': 'Hips', 'RightShin': 'RightLeg', 'RightFoot': 'RightShin', 'RightToeBase': 'RightFoot'}


def require(value, message):
    if not value: raise ValueError(message)


def validate_catalog(catalog, rigs, rigs_digest):
    fields = ('schema', 'rig_catalog_sha256', 'floor_y_m', 'minimum_initial_z_clearance_m',
              'pairings', 'use_policy', 'anatomical_facing_reviewed', 'contact_targets_bound',
              'motion_trials_executed', 'release_approved')
    require(isinstance(catalog, dict) and set(catalog) == set(fields), 'Complete explicit partner catalog required')
    require(catalog['schema'] == 'strep-reserved-partner-layouts-v1'
            and catalog['rig_catalog_sha256'] == rigs_digest, 'Exact reserved rig catalog binding required')
    require(type(catalog['floor_y_m']) in (int, float) and catalog['floor_y_m'] == 0,
            'Canonical zero-height floor required')
    clearance = catalog['minimum_initial_z_clearance_m']
    require(type(clearance) in (int, float) and np.isfinite(clearance) and clearance > 0,
            'Positive finite initial separation bound required')
    require(all(catalog[k] is False for k in ('anatomical_facing_reviewed', 'contact_targets_bound',
            'motion_trials_executed', 'release_approved')), 'Neutral layouts cannot grant task or release approval')
    require(isinstance(catalog['use_policy'], str) and bool(catalog['use_policy']), 'Reservation use policy required')
    reserved = rigs.get('partner_pairings'); rig_rows = rigs.get('rigs')
    require(isinstance(reserved, list) and len(reserved) == 3 and isinstance(rig_rows, list) and len(rig_rows) == 3,
            'Complete three-rig and three-directed-pair reservation required')
    ids = [r['id'] for r in rig_rows]
    require(len(set(ids)) == 3, 'Distinct reserved rig IDs required')
    rows = catalog['pairings']
    require(isinstance(rows, list) and len(rows) == len(reserved), 'All reserved directed pairings required')
    require(len({p['id'] for p in reserved}) == 3, 'Distinct reserved pairing IDs required')
    for row, expected in zip(rows, reserved):
        require(isinstance(row, dict) and set(row) == {'id', 'actor_a', 'actor_b', 'rig_origin_separation_z_m'},
                'Explicit pairing and rig-origin separation fields required')
        require({k: row[k] for k in ('id', 'actor_a', 'actor_b')} == expected,
                'Preserve complete reserved pairing identity, direction and order')
        require(isinstance(row['id'], str) and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', row['id']),
                'Safe pairing ID required')
        require(row['actor_a'] in ids and row['actor_b'] in ids and row['actor_a'] != row['actor_b'],
                'Distinct existing paired rigs required')
        distance = row['rig_origin_separation_z_m']
        require(type(distance) in (int, float) and np.isfinite(distance) and 0 < distance <= 100,
                'Positive finite rig-origin separation up to 100 m required')


def load_static(character, profile_path, expected):
    require(sha256(character) == expected['character_sha256'] and sha256(profile_path) == expected['profile_sha256'],
            'Unchanged reserved character and profile bytes required')
    rig = RigAsset.load(character); profile = read(profile_path)
    require(not rig.document.get('animations'), 'Neutral reservation cannot contain animation')
    require(all(p['joints'] is not None for p in rig.primitives), 'Every neutral primitive must be skinned')
    require(profile.get('schema') == 'strep-rig-profile-v1' and profile.get('reference_pose') == 'default_nodes'
            and profile.get('character_sha256') == expected['character_sha256'], 'Exact default-pose profile required')
    require(profile.get('world_offset_m') == [0, 0, 0], 'Neutral layout requires explicit zero profile offset')
    mapping = profile.get('mapping')
    require(isinstance(mapping, dict) and set(mapping) == set(PARENTS), 'Complete reserved nineteen-role mapping required')
    require(all(type(n) is int and n in rig.joints for n in mapping.values())
            and len(set(mapping.values())) == len(mapping), 'Distinct existing mapped skin joints required')
    for role, node in mapping.items():
        parent_role = PARENTS[role]
        if parent_role is not None:
            ancestor = rig.parents[node]
            while ancestor != -1 and ancestor not in mapping.values(): ancestor = rig.parents[ancestor]
            require(ancestor == mapping[parent_role], 'Reserved mapping hierarchy changed')
    points = rig.vertices(rig.reference)
    require(points.shape[1:] == (3,) and len(points) and np.isfinite(points).all(), 'Complete finite neutral surface required')
    return rig, profile, points


def layout(points, *, actor, separation_z_m):
    points = np.asarray(points, float)
    require(points.ndim == 2 and points.shape[1:] == (3,) and len(points) and np.isfinite(points).all(),
            'Complete finite neutral vertex population required')
    require(actor in ('A', 'B'), 'Explicit A or B actor required')
    require(type(separation_z_m) in (int, float) and np.isfinite(separation_z_m) and 0 < separation_z_m <= 100,
            'Positive finite separation required')
    signs = np.array([1., 1., 1.] if actor == 'A' else [-1., 1., -1.])
    translation = np.array([0., -points[:, 1].min(), (-.5 if actor == 'A' else .5)*separation_z_m])
    placed = points*signs+translation
    return dict(translation_m=translation.tolist(), rotation_xyzw=[0, 0, 0, 1] if actor == 'A' else [0, 1, 0, 0]), placed


def reduce(scene, arrays, *, minimum_clearance_m):
    require(set(scene) == {'schema', 'pairing', 'actors', 'rig_origin_separation_z_m', 'floor',
        'contacts', 'animations', 'anatomical_facing_reviewed', 'coordinate_convention'},
        'Complete explicit neutral scene fields required')
    require(scene.get('schema') == 'strep-neutral-partner-fixture-v1' and set(scene.get('actors', {})) == {'A', 'B'},
            'Complete two-actor neutral scene required')
    require(scene.get('contacts') == [] and scene.get('animations') == []
            and scene.get('anatomical_facing_reviewed') is False, 'No task/contact/facing approval in neutral scene')
    require(set(arrays) == {f'{a}_{suffix}' for a in ('A', 'B') for suffix in
            ('source_vertices_m', 'placed_vertices_m', 'source_role_positions_m', 'placed_role_positions_m')},
            'Complete saved neutral surface and role populations required')
    require(type(minimum_clearance_m) in (int, float) and np.isfinite(minimum_clearance_m) and minimum_clearance_m > 0,
            'Positive finite clearance requirement needed')
    bounds={}; counts={}; role_counts={}
    for actor in ('A', 'B'):
        entry = scene['actors'][actor]; pose = entry['placement']
        require(set(entry) == {'rig_id', 'files', 'placement', 'role_order', 'neutral_bounds_world_m'}
                and set(pose) == {'translation_m', 'rotation_xyzw'}, 'Explicit neutral actor and placement fields required')
        require(pose['rotation_xyzw'] == ([0, 0, 0, 1] if actor == 'A' else [0, 1, 0, 0]),
                'Exact canonical opposing local axes required')
        matrix = np.diag([1., 1., 1.] if actor == 'A' else [-1., 1., -1.])
        translation = np.asarray(pose['translation_m'], float)
        require(translation.shape == (3,) and np.isfinite(translation).all() and translation[0] == 0,
                'Finite canonical placement required')
        for source_key, placed_key in [('source_vertices_m', 'placed_vertices_m'),
                                       ('source_role_positions_m', 'placed_role_positions_m')]:
            source, placed = [np.asarray(arrays[f'{actor}_{k}']) for k in (source_key, placed_key)]
            require(source.dtype == placed.dtype == np.dtype('float64') and source.ndim == 2
                    and source.shape[1:] == (3,) and len(source) and source.shape == placed.shape
                    and np.isfinite(source).all() and np.isfinite(placed).all(), 'Complete finite binary64 observations required')
            # Independent matrix arithmetic, rather than producer component signs.
            require(np.array_equal(source@matrix.T+translation, placed), 'Saved complete placed observations changed')
        source = arrays[f'{actor}_source_vertices_m']; placed = arrays[f'{actor}_placed_vertices_m']
        require(translation[1] == -source[:, 1].min() and placed[:, 1].min() == 0, 'Exact canonical grounding required')
        bounds[actor] = [placed.min(0).tolist(), placed.max(0).tolist()]
        counts[actor] = len(source); role_counts[actor] = len(arrays[f'{actor}_source_role_positions_m'])
        require(role_counts[actor] == len(PARENTS), 'All nineteen mapped role origins required')
        require(entry['neutral_bounds_world_m'] == bounds[actor], 'Complete saved bounds changed')
    gap = bounds['B'][0][2]-bounds['A'][1][2]
    require(gap >= minimum_clearance_m, 'Initial complete neutral bounds do not meet required separation')
    return dict(status='complete',pairing=scene['pairing'],vertices=counts,role_origins=role_counts,
        bounds_world_m=bounds,initial_z_clearance_m=gap,grounded=True,initial_bounds_separated=True,
        contact_targets_bound=False,motion_quality_approved=False,release_approved=False,
        scope='Complete decoded neutral vertices and mapped joint origins. Static opposing local axes and '
              'grounded AABB separation only; shared rig decoder/weight normalization. No animated import, '
              'anatomical facing, material hand targets, interaction, dynamics or human/release approval.')


def run(catalog_path, rig_catalog_path, output, *, source_root=ROOT):
    catalog_path, rig_catalog_path, output, source_root = [Path(p).resolve() for p in
        (catalog_path, rig_catalog_path, output, source_root)]
    require(not output.exists(), 'Fresh neutral partner output required')
    catalog, rigs = read(catalog_path), read(rig_catalog_path)
    validate_catalog(catalog, rigs, sha256(rig_catalog_path))
    proof_path=source_root/rigs['construction_verification']
    require(sha256(proof_path) == rigs['construction_verification_sha256'], 'Unchanged original rig construction proof required')
    proof=read(proof_path)
    require(proof['reserved_action_trials'] == 0 and proof['quality_approved'] is False
            and {r['id'] for r in proof['rows']} == {r['id'] for r in rigs['rigs']}, 'Complete neutral rig construction evidence required')
    bindings={str(p):sha256(p) for p in (catalog_path, rig_catalog_path, proof_path)}
    for p,h in proof['inputs'].items():
        require(sha256(p)==h, 'Original rig construction input changed');bindings[p]=h
    methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
    output.mkdir(parents=True);checks=[];manifest=[]
    try:
        for n in METHODS:
            target=output/'implementation'/n;target.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'scripts'/n,target)
        for name,path in [('catalog.json',catalog_path),('rig-catalog.json',rig_catalog_path),('rig-construction-proof.json',proof_path)]:
            shutil.copyfile(path,output/name)
        save(output/'pipeline.json',dict(status='processing',motion_trials_executed=0))
        table={r['id']:r for r in rigs['rigs']}
        for pair in catalog['pairings']:
            folder=output/'pairs'/pair['id'];folder.mkdir(parents=True);arrays={};actors={}
            for actor,rig_id in [('A',pair['actor_a']),('B',pair['actor_b'])]:
                row=table[rig_id];character=source_root/row['character'];profile_path=source_root/row['profile']
                rig,profile,points=load_static(character,profile_path,row)
                target=folder/'actors'/actor;target.mkdir(parents=True)
                files={}
                for name,source in [('character.glb',character),('rig-profile.json',profile_path),
                        *[(n,character.parent/n) for n in ('LICENSE.md','provenance.json','packing.json')]]:
                    bindings[str(source)]=sha256(source);shutil.copyfile(source,target/name)
                    files[name]=dict(path=(target/name).relative_to(folder).as_posix(),sha256=sha256(target/name))
                    require(files[name]['sha256']==bindings[str(source)], 'Partner attachment changed during copying')
                placement,placed=layout(points,actor=actor,separation_z_m=pair['rig_origin_separation_z_m'])
                roles=list(PARENTS);origins=rig.reference[[profile['mapping'][r] for r in roles],:3,3].astype(float)
                signs=np.array([1.,1.,1.] if actor=='A' else [-1.,1.,-1.])
                arrays.update({f'{actor}_source_vertices_m':points,f'{actor}_placed_vertices_m':placed,
                    f'{actor}_source_role_positions_m':origins,
                    f'{actor}_placed_role_positions_m':origins*signs+placement['translation_m']})
                actors[actor]=dict(rig_id=rig_id,files=files,placement=placement,role_order=roles,
                    neutral_bounds_world_m=[placed.min(0).tolist(),placed.max(0).tolist()])
            scene=dict(schema='strep-neutral-partner-fixture-v1',pairing=pair['id'],actors=actors,
                rig_origin_separation_z_m=pair['rig_origin_separation_z_m'],floor=dict(normal_xyz=[0,1,0],offset_m=0),
                contacts=[],animations=[],anatomical_facing_reviewed=False,
                coordinate_convention='Y up; A local +Z points toward B, B local +Z toward A. Anatomical facing unreviewed.')
            save(folder/'scene.json',scene);np.savez_compressed(folder/'observations.npz',**arrays)
            checked=reduce(scene,arrays,minimum_clearance_m=catalog['minimum_initial_z_clearance_m'])
            save(folder/'verification.json',checked);checks.append(checked)
            manifest.append(dict(id=pair['id'],scene_sha256=sha256(folder/'scene.json'),
                observations_sha256=sha256(folder/'observations.npz'),verification_sha256=sha256(folder/'verification.json')))
        require(all(sha256(p)==h for p,h in bindings.items()), 'Original partner input changed')
        require(all(sha256(ROOT/'scripts'/n)==sha256(output/'implementation'/n)==h for n,h in methods.items()), 'Partner method changed')
        save(output/'request.json',dict(at=now(),inputs_sha256=bindings,implementation_sha256=methods,
            catalog_sha256=sha256(output/'catalog.json'),rig_catalog_sha256=sha256(output/'rig-catalog.json'),
            construction_proof_sha256=sha256(output/'rig-construction-proof.json')))
        save(output/'result.json',dict(schema='strep-reserved-partner-fixtures-v1',status='complete',
            request_sha256=sha256(output/'request.json'),pairings=manifest,checks=checks,
            motion_trials_executed=0,engine_executed=False,contact_targets_bound=False,
            anatomical_facing_reviewed=False,quality_approved=False,release_approved=False))
        save(output/'pipeline.json',dict(status='complete',motion_trials_executed=0))
        verify(output);return read(output/'result.json')
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),motion_trials_executed=0));raise


def verify(output):
    """Rebuild every neutral array from bundled assets; no original paths needed."""
    output=Path(output).resolve();result=read(output/'result.json');request=read(output/'request.json')
    require(result.get('schema')=='strep-reserved-partner-fixtures-v1' and result.get('status')=='complete'
            and result['request_sha256']==sha256(output/'request.json'), 'Complete bound partner result required')
    require(all(result[k] is False for k in ('engine_executed','contact_targets_bound','anatomical_facing_reviewed',
            'quality_approved','release_approved')) and result['motion_trials_executed']==0, 'Neutral scope must remain unchanged')
    for n,h in request['implementation_sha256'].items():
        require(sha256(output/'implementation'/n)==h==sha256(ROOT/'scripts'/n), 'Matching archived partner method required')
    for name,key in [('catalog.json','catalog_sha256'),('rig-catalog.json','rig_catalog_sha256'),
                     ('rig-construction-proof.json','construction_proof_sha256')]:
        require(sha256(output/name)==request[key], 'Partner input snapshot changed')
    catalog,rigs=read(output/'catalog.json'),read(output/'rig-catalog.json')
    validate_catalog(catalog,rigs,sha256(output/'rig-catalog.json'))
    proof=read(output/'rig-construction-proof.json')
    table={r['id']:r for r in rigs['rigs']};checks=[]
    require([r['id'] for r in result['pairings']]==[p['id'] for p in catalog['pairings']], 'Complete pairing result population required')
    for manifest,pair in zip(result['pairings'],catalog['pairings']):
        folder=output/'pairs'/pair['id'];scene=read(folder/'scene.json')
        for name,key in [('scene.json','scene_sha256'),('observations.npz','observations_sha256'),('verification.json','verification_sha256')]:
            require(sha256(folder/name)==manifest[key], 'Saved partner evidence changed')
        require(scene['pairing']==pair['id'] and scene['rig_origin_separation_z_m']==pair['rig_origin_separation_z_m']
                and scene['floor']==dict(normal_xyz=[0,1,0],offset_m=0), 'Canonical saved partner scene changed')
        with np.load(folder/'observations.npz',allow_pickle=False) as saved:
            arrays={k:saved[k] for k in saved.files}
        for actor,key in [('A','actor_a'),('B','actor_b')]:
            entry=scene['actors'][actor];expected=table[pair[key]]
            require(entry['rig_id']==expected['id'] and entry['role_order']==list(PARENTS), 'Directed rig/role correspondence changed')
            require(set(entry['files'])=={'character.glb','rig-profile.json','LICENSE.md','provenance.json','packing.json'}, 'Complete portable rig attachments required')
            for name,ref in entry['files'].items():
                require(set(ref)=={'path','sha256'} and ref['path']==f'actors/{actor}/{name}'
                        and sha256(folder/ref['path'])==ref['sha256'], 'Portable partner file changed')
                original_folder=expected['character'].replace('\\','/').rsplit('/',1)[0]
                suffix=original_folder+'/'+name
                declared=[h for p,h in proof['inputs'].items()
                    if p.replace('\\','/').endswith('/'+suffix) or p.replace('\\','/')==suffix]
                require(len(declared)==1 and ref['sha256']==declared[0], 'Copied rig bytes differ from original construction binding')
            rig,profile,points=load_static(folder/f'actors/{actor}/character.glb',folder/f'actors/{actor}/rig-profile.json',expected)
            origins=rig.reference[[profile['mapping'][r] for r in PARENTS],:3,3]
            require(np.array_equal(points,arrays[f'{actor}_source_vertices_m'])
                    and np.array_equal(origins,arrays[f'{actor}_source_role_positions_m']), 'Complete neutral source observations changed')
            placement,_=layout(points,actor=actor,separation_z_m=pair['rig_origin_separation_z_m'])
            require(entry['placement']==placement, 'Predetermined initial placement changed')
        checked=reduce(scene,arrays,minimum_clearance_m=catalog['minimum_initial_z_clearance_m'])
        require(checked==read(folder/'verification.json'), 'Saved static partner reduction changed');checks.append(checked)
    require(checks==result['checks'], 'Complete static partner summaries changed')
    return checks


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('build');build.add_argument('catalog',type=Path);build.add_argument('rig_catalog',type=Path);build.add_argument('output',type=Path)
    check=sub.add_parser('verify');check.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.command=='build':run(args.catalog,args.rig_catalog,args.output)
    else:verify(args.output)
