"""Compile explicit region scene contacts without discarding their meaning.

The resulting region package is not accepted by legacy point-only solvers.
Raw source and authored scene remain unchanged. Optional evaluation measures
the current source animation; compilation itself is never a contact success.
"""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from compile_scene_contacts import compile_contacts
from scene_constraints import pose, sample_object, evaluate
from scene_region_contact import compile_region, mesh_fingerprint


def compile_regions(scene, actor_id, contact_ids, skin, project_root=ROOT):
    source = copy.deepcopy(scene)
    chosen = [c for c in scene['contacts'] if c['id'] in contact_ids]
    if not chosen or any('region_contact' not in c for c in chosen):
        raise ValueError('Select explicitly authored region contacts')
    # Validate the shared scene, selected actor/IDs, clock and source hashes
    # through the existing compiler before constructing region coordinates.
    for contact in source['contacts']:
        contact.pop('region_contact', None)
    anchor_spec, provenance = compile_contacts(source, actor_id, contact_ids, skin, project_root)
    compiled = []
    origin, rotation = pose(scene['actors'][actor_id]['transform'])
    for contact in chosen:
        tolerance=contact.get('tolerance_m',.03)
        if type(tolerance) not in [int,float] or not np.isfinite(tolerance) or tolerance<=0:
            raise ValueError('Anchor tolerance must be positive and finite')
        vertices, faces, geometry, normal = compile_region(contact, scene, skin)
        obj = scene['objects'][contact['target']['object']]
        position, orientation = sample_object(obj, scene['frame_count'])
        a, b = contact['start_frame'], contact['end_frame']
        compiled.append(dict(contact_id=contact['id'], start_frame=a, end_frame=b,
                             anchor_tolerance_m=tolerance,
                             binding=copy.deepcopy(contact['region_contact']),
                             vertex_ids=vertices.tolist(), geometry=geometry.record(),
                             object_id=contact['target']['object'],
                             object_positions_m=((position-origin)@rotation).tolist(),
                             object_rotations=(rotation.T@orientation).tolist(),
                             desired_normals=(np.einsum('fij,j->fi', orientation, normal)@rotation).tolist()))
    # Compile an explicitly labelled anchor subproblem, never replace the input
    # scene or claim the anchor spec alone represents distributed acceptance.
    return dict(schema='strep-compiled-scene-regions-v1', actor=actor_id,
                fps=scene['fps'], frame_count=scene['frame_count'],
                mesh_sha256=mesh_fingerprint(skin), regions=compiled,
                anchor_subproblem=anchor_spec, source_provenance=provenance,
                solver_supported=True, solver_version=14, quality_approved=False,
                scope='Actor-native anchor AND distributed contact requirements. Not an executable legacy point-only solver specification.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('--actor', required=True)
    parser.add_argument('--contact', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    data = read(args.scene)
    scene = data.get('scene', data)
    skin = dict(np.load(ASSET, allow_pickle=False))
    digest = sha256(args.scene)
    mesh_digest = sha256(ASSET)
    methods = ['compile_scene_regions.py', 'scene_region_contact.py', 'scene_constraints.py',
               'compile_scene_contacts.py', 'object_geometry.py', 'floor_contact.py',
               'contact_spec.py', 'support_contact.py', 'inspect_motion.py']
    implementations = {name:sha256(ROOT/'scripts'/name) for name in methods}
    result = compile_regions(scene, args.actor, args.contact, skin)
    assessment = evaluate(scene, skin) if args.evaluate else None
    if sha256(args.scene) != digest:
        raise ValueError('Authored scene changed during compilation')
    if sha256(ASSET) != mesh_digest:
        raise ValueError('Mesh changed during compilation')
    for entry in result['source_provenance']['sources'].values():
        if sha256(ROOT/entry['path']) != entry['sha256']:
            raise ValueError('Actor motion changed during compilation')
    for name, expected in implementations.items():
        if sha256(ROOT/'scripts'/name) != expected:
            raise ValueError('Implementation changed during compilation')
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'implementation').mkdir()
    for name in methods:
        shutil.copyfile(ROOT/'scripts'/name, args.output/'implementation'/name)
    save(args.output/'region-constraints.json', result)
    save(args.output/'authored-scene.json', scene)
    if assessment is not None:
        save(args.output/'source-evaluation.json', assessment)
    save(args.output/'provenance.json', dict(at=now(), scene_sha256=digest, mesh_file_sha256=mesh_digest,
         implementation=implementations,
         candidate_generated=False, quality_approved=False))
    print(dict(output=str(args.output), region_contacts=len(result['regions']), candidate_generated=False))
