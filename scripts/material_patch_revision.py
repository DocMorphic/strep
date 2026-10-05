"""Apply verified authored skin regions to an existing native Studio draft.

Explicit vertex orders define correspondence. Original scene settings, contact
timing/limits and revision lineage remain protected by the existing validator.
"""
import argparse
import copy
from pathlib import Path
from material_patch_bundle import verify as verify_bundle, METHODS as BUNDLE_METHODS, fields, sha_binding
from native_contact_revision import apply, validate, portable_record, SCHEMA as REVISION_SCHEMA, DRAFT_FIELDS
from native_scene_contacts import SceneContacts
from rig_material_patch import require
from strep import ROOT, read, save, sha256, now

METHODS = tuple(dict.fromkeys(BUNDLE_METHODS + ('native_contact_revision.py','material_patch_revision.py')))
SCHEMA = 'strep-material-patch-revision-v1'


def revise(baseline, spec, *, specification_base, scene_base, baseline_sha256):
    fields(baseline,DRAFT_FIELDS,'original Studio draft')
    fields(spec,('schema','baseline_sha256','edits'),'material revision')
    sha_binding(baseline_sha256, 'original draft binding')
    sha_binding(spec['baseline_sha256'], 'declared original draft binding')
    require(spec['schema'] == SCHEMA and spec['baseline_sha256'] == baseline_sha256,
            'Exact original draft binding required')
    rows = spec['edits']
    require(isinstance(rows,list) and 1 <= len(rows) <= 64,'Explicit bounded material revisions required')
    original = SceneContacts(baseline['scene'],scene_base)
    contacts = {c['id']:c for c in baseline['scene']['contacts']}
    bundles = {}; bindings = []; converted = []

    def patch(entry, actor):
        fields(entry,('bundle','result_sha256','patch_id','vertex_indices','reduction'),'material patch reference')
        require(isinstance(entry['bundle'],str) and bool(entry['bundle']),'Explicit bundle path required')
        sha_binding(entry['result_sha256'], 'material result binding')
        path = (Path(specification_base)/entry['bundle']).resolve()
        key = path,entry['result_sha256']
        if key not in bundles:
            bundles[key] = verify_bundle(path,expected_result_sha256=entry['result_sha256'])
        manifest = next((p for p in bundles[key]['patches'] if p['id'] == entry['patch_id']),None)
        require(manifest is not None,'Existing explicitly named material patch required')
        require(sha256(path/manifest['path']) == manifest['sha256'],'Material patch changed after bundle verification')
        value = read(path/manifest['path'])
        require(value['source']['character_sha256'] == baseline['scene']['actors'][actor]['sha256'],
                'Material patch must bind the exact animated actor file; transfer explicitly first')
        indices = entry['vertex_indices']; refs = value['vertices']
        require(isinstance(indices,list) and 1 <= len(indices) <= len(refs)
                and all(type(i) is int and 0 <= i < len(refs) for i in indices)
                and len(set(indices)) == len(indices),'Explicit distinct existing patch vertex order required')
        require(entry['reduction'] in ('individual','centroid'),'Explicit native contact reduction required')
        binding = dict(actor=actor,bundle=str(path),result_sha256=entry['result_sha256'],
            patch_id=entry['patch_id'],patch_sha256=manifest['sha256'],vertex_indices=list(indices),
            reduction=entry['reduction'])
        bindings.append(binding)
        return dict(glb_sha256=value['source']['character_sha256'],
                    vertices=[copy.deepcopy(refs[i]) for i in indices],reduction=entry['reduction'])

    for row in rows:
        fields(row,('id','source','partner'),'material contact edit')
        require(isinstance(row['id'],str) and row['id'] in contacts,'Existing contact ID required')
        contact = contacts[row['id']]
        source = None if row['source'] is None else patch(row['source'],contact['actor'])
        partner = None
        if row['partner'] is not None:
            require(contact['target']['space'] == 'actor','Only actor targets have partner material patches')
            partner = patch(row['partner'],contact['target']['actor'])
        converted.append(dict(id=row['id'],source=source,partner=partner))
    updated = apply(baseline,converted)
    updated['contact_revision'] = dict(schema=REVISION_SCHEMA,baseline=copy.deepcopy(baseline),edits=converted)
    actual,_ = validate(updated)
    checked = SceneContacts(actual['scene'],scene_base)
    original.check_inputs(); checked.check_inputs()
    for (path,bound), result in bundles.items():
        require(verify_bundle(path,expected_result_sha256=bound) == result,'Material bundle changed during revision')
    return updated,dict(schema=SCHEMA,material_bindings=bindings,
        original_actor_sha256=dict(original.inputs),native_revision=portable_record(updated),
        explicit_vertex_correspondence=True,contact_timing_limits_and_other_fields_unchanged=True,
        anatomical_review_pending=True,animation_edited=False,motion_contacts_measured=False,
        quality_approved=False,release_approved=False)


def run(baseline_path, specification_path, output):
    baseline_path,specification_path,output = [Path(p).resolve() for p in (baseline_path,specification_path,output)]
    receipt = output.with_suffix(output.suffix+'.material.json')
    require(not output.exists() and not receipt.exists(),'Fresh revised draft and receipt paths required')
    # Keep all original relative actor paths valid without changing protected draft fields.
    require(output.parent == baseline_path.parent,'Save revised draft beside its baseline to preserve relative paths')
    inputs = {str(p):sha256(p) for p in (baseline_path,specification_path)}
    methods = {n:sha256(ROOT/'scripts'/n) for n in METHODS}
    updated,proof = revise(read(baseline_path),read(specification_path),specification_base=specification_path.parent,
        scene_base=baseline_path.parent,baseline_sha256=inputs[str(baseline_path)])
    require(all(sha256(p) == h for p,h in inputs.items()),'Original draft/specification changed during revision')
    require(all(sha256(ROOT/'scripts'/n) == h for n,h in methods.items()),'Material revision method changed')
    save(output,updated)
    save(receipt,dict(at=now(),schema='strep-material-patch-revision-receipt-v1',status='complete',
        inputs_sha256=inputs,implementation_sha256=methods,revised_draft_sha256=sha256(output),proof=proof,
        quality_approved=False,release_approved=False))
    return updated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path); parser.add_argument('specification',type=Path); parser.add_argument('output',type=Path)
    args = parser.parse_args(); run(args.baseline,args.specification,args.output)
