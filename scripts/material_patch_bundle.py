"""Portable authored material patches and explicit unchanged-rig transfer.

Selections are supplied explicitly. No anatomical review, contact timing, motion
fit, rendering, engine work, training admission or quality approval is inferred.
"""
import argparse
import copy
from pathlib import Path
import re
import shutil
from rig_material_patch import MaterialSurface, require
from rig_material_identity import descriptor, digest, compare, METHODS as IDENTITY_METHODS
from strep import ROOT, read, save, sha256, now

METHODS = tuple(dict.fromkeys(IDENTITY_METHODS + ('material_patch_bundle.py',)))
SELECTION_SCHEMA = 'strep-material-patch-selection-v1'
MAXIMUM_ASSET_BYTES = 128*1024**2
MAXIMUM_TRANSFER_DEPTH = 3
SCOPE = ('Explicit source-bound material patch authoring/unchanged-rig transfer. No anatomical '
         'or contact-target approval, point correspondence, timing, motion, engine or human quality result.')


def fields(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names), 'Explicit '+label+' fields required')


def sha_binding(value, label):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value),
            'Explicit lowercase SHA256 '+label+' required')


def surface(character, profile, source):
    for path in (Path(character), Path(profile)):
        require(path.is_file() and 0 < path.stat().st_size <= MAXIMUM_ASSET_BYTES, 'Bounded regular asset/profile file required')
    fields(source, ('character_sha256','profile_sha256','reference_pose','weight_normalization'), 'material source')
    value = MaterialSurface(character, profile, character_sha256=source['character_sha256'],
                            profile_sha256=source['profile_sha256'])
    require(source == value.source, 'Exact declared material source required')
    return value


def source_binding(character, profile):
    for path in (Path(character), Path(profile)):
        require(path.is_file() and 0 < path.stat().st_size <= MAXIMUM_ASSET_BYTES, 'Bounded regular asset/profile file required')
    return dict(character_sha256=sha256(character), profile_sha256=sha256(profile),
                reference_pose='default_nodes', weight_normalization='RigAsset per-vertex sum')


def selections(value, material):
    fields(value, ('schema','source','patches'), 'material selection')
    require(value['schema'] == SELECTION_SCHEMA and value['source'] == material.source, 'Source-bound selection schema required')
    rows = value['patches']
    require(isinstance(rows, list) and 1 <= len(rows) <= 64, 'Select 1-64 explicit material patches; no invented defaults')
    used = set(); result = []
    for row in rows:
        fields(row, ('id','role','face_references','selector'), 'authored material patch')
        name = row['id']
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name)
                and name not in used, 'Distinct safe patch IDs required')
        used.add(name)
        fields(row['selector'], ('include_children','minimum_weight','minimum_twice_area_m2',
                                'maximum_faces','maximum_vertices'), 'patch selector')
        result.append((name, material.patch(row['role'], row['face_references'], **row['selector'])))
    return result


def files(folder):
    result = {}
    for path in sorted(folder.rglob('*')):
        require(not path.is_symlink() and path.resolve().is_relative_to(folder), 'Portable files must stay inside bundle')
        if path.is_file(): result[path.relative_to(folder).as_posix()] = sha256(path)
    return result


def inventory(character, profile, output, roles):
    """Complete candidate data plus an empty explicit-selection template."""
    output = Path(output).resolve()
    require(not output.exists(), 'Fresh inventory output required')
    require(isinstance(roles, list) and 1 <= len(roles) <= 64 and all(isinstance(r, str) for r in roles)
            and len(set(roles)) == len(roles), 'Distinct explicit mapped roles required')
    source = source_binding(character, profile); material = surface(character, profile, source)
    rows = [material.candidates(r, include_children=True, minimum_weight=1.) for r in roles]
    material.check_inputs(); output.mkdir(parents=True)
    save(output/'inventory.json', dict(schema='strep-material-patch-inventory-v1',source=source,candidates=rows,
        selected_patches=0,anatomy_verified=False,contact_target_approved=False,quality_approved=False,release_approved=False))
    save(output/'selection-template.json',dict(schema=SELECTION_SCHEMA,source=source,patches=[]))
    material.check_inputs()
    return rows


def patch_record(name, patch, output):
    path = f'patches/{name}.json'; save(output/path, patch)
    return dict(id=name,path=path,sha256=sha256(output/path),faces=len(patch['face_references']),vertices=len(patch['vertices']))


def create(character, profile, selection, output):
    character, profile, selection, output = [Path(p).resolve() for p in (character,profile,selection,output)]
    require(not output.exists(), 'Fresh authored material output required')
    require(selection.is_file() and 0 < selection.stat().st_size <= 8*1024**2, 'Bounded explicit selection JSON required')
    value = read(selection); fields(value, ('schema','source','patches'), 'material selection')
    material = surface(character, profile, value['source'])
    patches = selections(value, material)
    return build(material, selection, value, patches, output, parent=None)


def transfer(parent, character, profile, output, *, character_sha256, profile_sha256):
    parent, character, profile, output = [Path(p).resolve() for p in (parent,character,profile,output)]
    require(not output.exists() and not output.is_relative_to(parent), 'Fresh separate transferred output required')
    previous = verify(parent)
    require(previous['transfer_depth'] < MAXIMUM_TRANSFER_DEPTH, 'Transfer chain exceeds explicit maximum depth')
    original_selection = read(parent/'input/selection.json')
    original = surface(parent/'input/character.glb',parent/'input/rig-profile.json',original_selection['source'])
    binding = dict(character_sha256=character_sha256,profile_sha256=profile_sha256,
                   reference_pose='default_nodes',weight_normalization='RigAsset per-vertex sum')
    target = surface(character,profile,binding)
    comparison = compare(original,target)
    value = copy.deepcopy(original_selection); value['source'] = dict(target.source)
    patches = selections(value,target)
    for manifest, (_, patch) in zip(previous['patches'],patches):
        before = read(parent/manifest['path']); before['source'] = dict(target.source)
        require(before == patch, 'Transferred patch changes material geometry or selection')
    return build(target, None, value, patches, output, parent=parent, comparison=comparison)


def build(material, selection_path, value, patches, output, *, parent, comparison=None):
    original_inputs = dict(material.inputs)
    if selection_path is not None: original_inputs[str(selection_path)] = sha256(selection_path)
    methods = {n:sha256(ROOT/'scripts'/n) for n in METHODS}
    parent_files = {} if parent is None else files(parent)
    output.mkdir(parents=True)
    try:
        save(output/'pipeline.json',dict(status='processing'))
        target = output/'input'; target.mkdir()
        shutil.copyfile(material.character,target/'character.glb'); shutil.copyfile(material.profile_path,target/'rig-profile.json')
        if selection_path is None: save(target/'selection.json',value)
        else: shutil.copyfile(selection_path,target/'selection.json')
        for name in METHODS:
            path = output/'implementation'/name; path.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT/'scripts'/name,path)
        save(output/'identity.json',descriptor(material))
        depth = 0
        if parent is not None:
            shutil.copytree(parent,output/'parent')
            require(files(output/'parent') == parent_files, 'Complete parent bundle changed during copying')
            save(output/'transfer.json',comparison)
            depth = read(parent/'result.json')['transfer_depth']+1
        request = dict(schema='strep-material-patch-bundle-request-v1',at=now(),mode='create' if parent is None else 'transfer',
            source=dict(material.source),input_sha256={n:sha256(target/n) for n in ('character.glb','rig-profile.json','selection.json')},
            implementation_sha256=methods,identity_sha256=sha256(output/'identity.json'),
            parent_result_sha256=None if parent is None else sha256(output/'parent/result.json'),
            parent_file_sha256=parent_files,transfer_sha256=None if parent is None else sha256(output/'transfer.json'))
        save(output/'request.json',request)
        manifests = [patch_record(name,patch,output) for name,patch in patches]
        require(all(sha256(p) == h for p,h in original_inputs.items()), 'Original authoring input changed')
        require(all(sha256(ROOT/'scripts'/n) == sha256(output/'implementation'/n) == h for n,h in methods.items()), 'Authoring method changed')
        if parent is not None: require(files(parent) == parent_files,'Original parent bundle changed')
        save(output/'result.json',dict(schema='strep-material-patch-bundle-v1',status='complete',
            request_sha256=sha256(output/'request.json'),patches=manifests,transfer_depth=depth,
            selected_geometry_patches=len(manifests),anatomy_verified=False,contact_target_approved=False,
            quality_approved=False,release_approved=False,scope=SCOPE))
        checked = verify(output)
        save(output/'pipeline.json',dict(status='complete'))
        return checked
    except Exception as error:
        save(output/'pipeline.json',dict(status='failed',error=str(error))); raise


def verify(output, *, expected_result_sha256=None, _depth=0):
    require(type(_depth) is int and 0 <= _depth <= MAXIMUM_TRANSFER_DEPTH, 'Bounded material transfer recursion required')
    output = Path(output).resolve()
    if expected_result_sha256 is not None:
        sha_binding(expected_result_sha256, 'result binding')
        require(sha256(output/'result.json') == expected_result_sha256, 'Material result differs from caller binding')
    snapshot = files(output); request = read(output/'request.json'); result = read(output/'result.json')
    fields(request, ('schema','at','mode','source','input_sha256','implementation_sha256','identity_sha256',
                     'parent_result_sha256','parent_file_sha256','transfer_sha256'), 'bundle request')
    fields(result, ('schema','status','request_sha256','patches','transfer_depth','selected_geometry_patches',
                   'anatomy_verified','contact_target_approved','quality_approved','release_approved','scope'), 'bundle result')
    require(request['schema'] == 'strep-material-patch-bundle-request-v1' and request['mode'] in ('create','transfer')
            and result['schema'] == 'strep-material-patch-bundle-v1' and result['status'] == 'complete'
            and result['request_sha256'] == sha256(output/'request.json'), 'Complete bound material result required')
    require(all(result[k] is False for k in ('anatomy_verified','contact_target_approved','quality_approved','release_approved'))
            and result['scope'] == SCOPE, 'Geometry authoring cannot grant contact or quality approval')
    require(set(request['implementation_sha256']) == set(METHODS), 'Every authored patch method must be bound')
    for name,h in request['implementation_sha256'].items():
        require(sha256(ROOT/'scripts'/name) == sha256(output/'implementation'/name) == h,'Archived authoring method changed')
    require(set(request['input_sha256']) == {'character.glb','rig-profile.json','selection.json'},'Complete portable authoring inputs required')
    for name,h in request['input_sha256'].items(): require(sha256(output/'input'/name) == h,'Portable authoring input changed')
    material = surface(output/'input/character.glb',output/'input/rig-profile.json',request['source'])
    value = read(output/'input/selection.json'); patches = selections(value,material)
    require(sha256(output/'identity.json') == request['identity_sha256']
            and read(output/'identity.json') == descriptor(material),'Complete static identity replay differs')
    require(type(result['selected_geometry_patches']) is int and result['selected_geometry_patches'] == len(patches)
            and type(result['transfer_depth']) is int, 'Complete integer geometry patch count/depth required')
    expected = set(['request.json','result.json','pipeline.json','identity.json']+
        ['input/'+n for n in request['input_sha256']]+['implementation/'+n for n in METHODS])
    actual = []
    for name,patch in patches:
        path = f'patches/{name}.json'; expected.add(path)
        require(read(output/path) == patch,'Complete authored material patch replay differs')
        actual.append(dict(id=name,path=path,sha256=sha256(output/path),faces=len(patch['face_references']),vertices=len(patch['vertices'])))
    require(result['patches'] == actual,'Complete authored patch population/identity/reduction changed')
    if request['mode'] == 'create':
        require(result['transfer_depth'] == 0 and request['parent_result_sha256'] is None
                and request['transfer_sha256'] is None and request['parent_file_sha256'] == {},'Create cannot invent a transfer parent')
    else:
        parent = output/'parent'; expected.add('transfer.json')
        sha_binding(request['parent_result_sha256'], 'parent result binding')
        require(files(parent) == request['parent_file_sha256'],'Complete portable parent changed')
        previous = verify(parent,expected_result_sha256=request['parent_result_sha256'],_depth=_depth+1)
        original_value = read(parent/'input/selection.json')
        original = surface(parent/'input/character.glb',parent/'input/rig-profile.json',original_value['source'])
        require(sha256(output/'transfer.json') == request['transfer_sha256']
                and read(output/'transfer.json') == compare(original,material),'Complete material transfer identity differs')
        original_value['source'] = dict(material.source)
        require(original_value == value and result['transfer_depth'] == previous['transfer_depth']+1
                <= MAXIMUM_TRANSFER_DEPTH,'Preserve every original material selection and bounded parent depth')
        expected.update('parent/'+name for name in request['parent_file_sha256'])
    require(set(snapshot) == expected and files(output) == snapshot,'Exact portable bundle population and immutable replay required')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command',required=True)
    inspect = sub.add_parser('inventory'); inspect.add_argument('character',type=Path); inspect.add_argument('profile',type=Path)
    inspect.add_argument('output',type=Path); inspect.add_argument('--roles',nargs='+',required=True)
    author = sub.add_parser('create'); author.add_argument('character',type=Path); author.add_argument('profile',type=Path)
    author.add_argument('selection',type=Path); author.add_argument('output',type=Path)
    reuse = sub.add_parser('transfer'); reuse.add_argument('parent',type=Path); reuse.add_argument('character',type=Path)
    reuse.add_argument('profile',type=Path); reuse.add_argument('output',type=Path)
    reuse.add_argument('--character-sha256',required=True); reuse.add_argument('--profile-sha256',required=True)
    check = sub.add_parser('verify'); check.add_argument('output',type=Path); check.add_argument('--expected-result-sha256')
    args = parser.parse_args()
    if args.command == 'inventory': inventory(args.character,args.profile,args.output,args.roles)
    elif args.command == 'create': create(args.character,args.profile,args.selection,args.output)
    elif args.command == 'transfer': transfer(args.parent,args.character,args.profile,args.output,
        character_sha256=args.character_sha256,profile_sha256=args.profile_sha256)
    else: verify(args.output,expected_result_sha256=args.expected_result_sha256)
