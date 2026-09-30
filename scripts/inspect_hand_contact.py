"""Replay deepest hand contacts and draw actual mesh cross-sections, without solving.

Consumes a completed study_hand_norm_proposal run. Skin influences identify
deformation controls, not anatomical ground truth. Cross-sections are diagnostic
illustrations; the stored full-mesh signed distances remain the measured depths.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
import trimesh
from strep import ROOT, read, save, sha256, now


def influences(rig, vertices, barycentric):
    primitive = rig.primitives[0]
    nodes = np.asarray(rig.joints)[primitive['joints'][vertices]]
    weights = primitive['weights'][vertices] * np.asarray(barycentric)[:, None]
    totals = {}
    for node, weight in zip(nodes.ravel(), weights.ravel()):
        totals[int(node)] = totals.get(int(node), 0.) + float(weight)
    return [dict(node=node, name=rig.document['nodes'][node].get('name', str(node)), weight=weight)
            for node, weight in sorted(totals.items(), key=lambda item: -item[1]) if weight > 1e-8]


def sections(meshes, point, closest, source, title, path):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (1200, 475), 'white'); draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=16); small = ImageFont.load_default(size=13)
    draw.text((15, 10), title, fill='black', font=font)
    draw.text((15, 36), 'A: blue  |  B: orange  |  black dot: deepest source vertex  |  gray dot: projected nearest target point', fill='black', font=small)
    half = .07; size = 345; top = 90
    for panel, (normal_axis, axes) in enumerate([(2, (0, 1)), (1, (0, 2)), (0, (2, 1))]):
        left = 25 + panel * 400; canvas = Image.new('RGB', (size, size), '#f8fafc')
        ink = ImageDraw.Draw(canvas)
        def pixel(p):
            xy = (np.asarray(p)[list(axes)] - point[list(axes)]) / (2*half) * (size-1)
            return (float(xy[0]+(size-1)/2), float((size-1)/2-xy[1]))
        normal = np.eye(3)[normal_axis]
        for actor, mesh in enumerate(meshes):
            segments = trimesh.intersections.mesh_plane(mesh, normal, point)
            for segment in segments:
                ink.line([pixel(p) for p in segment], fill=['#146bc5', '#da690c'][actor], width=2)
        center = pixel(point); other = pixel(closest)
        ink.line([center, other], fill='#555555', width=1)
        for xy, color in [(other, '#777777'), (center, '#000000')]:
            ink.ellipse((xy[0]-3, xy[1]-3, xy[0]+3, xy[1]+3), fill=color)
        ink.line([(12, size-15), (12+int(.02/(2*half)*(size-1)), size-15)], fill='black', width=3)
        ink.text((12, size-34), '20 mm', fill='black', font=small)
        image.paste(canvas, (left, top)); draw.rectangle((left, top, left+size, top+size), outline='#aab1bb')
        draw.text((left, top-24), f'{"XYZ"[axes[0]]}/{"XYZ"[axes[1]]} plane through source {"AB"[source]} vertex', fill='black', font=small)
    draw.text((15, 451), '140 mm crop per panel. These are surface-plane intersections, not silhouettes or a clearance certificate.', fill='black', font=small)
    image.save(path)


def run(study, output, samples):
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset, array
    from rig_clip_import import AnimationSampler
    from paired_approach_basis import BoundSkin
    from continuous_terminal_hand import HandWitnessObjective
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh diagnostic output required')
    if not samples or len(set(samples)) != len(samples): raise ValueError('Unique nonempty sample IDs required')
    result = read(study/'result.json'); request = read(study/'request.json')
    if result['status'] != 'complete': raise ValueError('Completed norm study required')
    bound = {str(study/'result.json'): sha256(study/'result.json'), **request['inputs']}
    for name, digest in result['outputs'].items():
        path = (study/name).resolve()
        if path.parent != study: raise ValueError('Study-local artifact required')
        bound[str(path)] = digest
    for name, digest in request['implementation'].items():
        path = study/'implementation'/name
        if path.resolve().parent != study/'implementation': raise ValueError('Study-local method required')
        bound[str(path)] = digest
    def verify():
        for path, digest in bound.items():
            if sha256(path) != digest: raise ValueError('Changed diagnostic input: '+path)
    verify()
    # The current sampling implementation must match the study that made the GLBs.
    for name in ['strep.py', 'rig_asset.py', 'gltf_tools.py', 'rig_clip_import.py']:
        if name in request['implementation'] and sha256(ROOT/'scripts'/name) != request['implementation'][name]:
            raise ValueError('Changed sampling implementation: '+name)
    def ancestor(folder):
        path = Path(folder)/'request.json'
        if str(path.resolve()) not in bound: raise ValueError('Unbound ancestor request: '+str(path))
        return read(path)
    source = ancestor(request['study']); terminal = ancestor(source['study'])
    plan = ancestor(terminal['plan']); protocol = ancestor(plan['source_plan'])
    original = ancestor(protocol['study'])
    prepared, actors = load_actors(Path(original['prepared_request']).parent)
    geometry = read(study/'geometry.json'); rows = {row['sample']: row for row in geometry}
    if any(sample not in rows for sample in samples): raise ValueError('Sample absent from complete geometry')
    clips = read(study/'decoded.json')['clips']; rigs = []; readers = []; faces = []
    if len(clips) != 2: raise ValueError('Two bound actors required')
    for clip in clips:
        path = (study/clip['path']).resolve()
        if path.parent != study or sha256(path) != clip['sha256']: raise ValueError('Changed candidate GLB')
        bound[str(path)] = clip['sha256']; rig = RigAsset.load(path)
        if len(rig.primitives) != 1: raise ValueError('One primitive required for stable vertex IDs')
        primitive = rig.primitives[0]
        mesh = rig.document['meshes'][rig.document['nodes'][primitive['node']]['mesh']]['primitives'][primitive['primitive']]
        faces.append(array(rig.document, rig.binary, mesh['indices']).reshape(-1, 3))
        rigs.append(rig); readers.append(AnimationSampler(rig.document, rig.binary, 0))
    output.mkdir(); shutil.copyfile(__file__, output/'inspect_hand_contact.py')
    bound[str(Path(__file__).resolve())] = sha256(__file__)
    # Replay every fixed witness, preserving the objective's direction grouping.
    # This separates max-objective tradeoffs from contacts absent from its model.
    witness_path = Path(request['study'])/'witnesses.json'
    if str(witness_path.resolve()) not in bound: raise ValueError('Bound witnesses required')
    witnesses = read(witness_path)
    ids = request['sample_indices']; times = np.asarray(terminal['sample_times_s'])[ids]
    worlds = [np.array([reader.sample(t) for t in times]) for reader in readers]
    objective = HandWitnessObjective([BoundSkin(rig) for rig in rigs], actors, witnesses)
    depths = -objective.gaps(worlds)
    with np.load(study/'local-model.npz', allow_pickle=False) as data:
        before = data['depths'].copy()
    ordered = [row for source_index in [0, 1] for row in witnesses
               if row['source'] == source_index and row['target'] == 1-source_index]
    if len(ordered) != len(depths) or before.shape != depths.shape:
        raise ValueError('Fixed witness population changed')
    if abs(max(0., float(depths.max()))-result['witness_after']['witness_peak_m']) > 1e-10:
        raise ValueError('Fixed witness peak does not replay')
    witness_comparison = []
    for sample in request['hand_samples']:
        mask = np.array([ids[row['frame']] == sample for row in ordered])
        witness_comparison.append(dict(sample=sample,
            witness_count=int(mask.sum()),
            before_peak_m=max(0., float(before[mask].max())) if mask.any() else None,
            after_peak_m=max(0., float(depths[mask].max())) if mask.any() else None,
            maximum_signed_increase_m=float((depths[mask]-before[mask]).max()) if mask.any() else None,
            regression_observations=int((depths[mask] > np.maximum(.005, before[mask])+1e-8).sum())))
    save(output/'witness-comparison.json', witness_comparison)
    details = []
    for sample in samples:
        row = rows[sample]; time = row['time_s']
        points = [rig.vertices(reader.sample(time)) @ actor['rotation'].T + actor['translation']
                  for rig, reader, actor in zip(rigs, readers, actors)]
        meshes = [trimesh.Trimesh(vertices=p, faces=f, process=False) for p, f in zip(points, faces)]
        if not all(mesh.is_watertight and mesh.is_winding_consistent for mesh in meshes):
            raise ValueError('Closed wound target meshes required')
        for source_index, direction in enumerate(row['directions']):
            target = 1-source_index; vertex = direction['deepest_source_vertex']
            if vertex is None: continue
            point = points[source_index][vertex]
            closest, distance, triangle = trimesh.proximity.closest_point(meshes[target], point[None])
            depth = float(trimesh.proximity.signed_distance(meshes[target], point[None])[0])
            if abs(depth-direction['max_depth_m']) > 1e-10: raise ValueError('Stored deepest distance does not replay')
            triangle_id = int(triangle[0]); target_ids = faces[target][triangle_id]
            bary = trimesh.triangles.points_to_barycentric(points[target][target_ids][None], closest)[0]
            if not np.isfinite(bary).all() or np.any(bary < -1e-8) or abs(bary.sum()-1) > 1e-8:
                raise ValueError('Invalid nearest surface barycentric coordinates')
            picture = f'sample-{sample}-source-{source_index}.png'
            sections(meshes, point, closest[0], source_index,
                     f'Sample {sample}, {time:.6f} s, source {"AB"[source_index]}, depth {depth*1000:.3f} mm', output/picture)
            details.append(dict(sample=sample, time_s=time, source=source_index, target=target,
                source_vertex=vertex, replayed_depth_m=depth, unsigned_distance_m=float(distance[0]),
                source_point_m=point.tolist(), target_point_m=closest[0].tolist(),
                target_triangle=triangle_id, target_vertices=target_ids.tolist(), target_barycentric=bary.tolist(),
                source_influences=influences(rigs[source_index], [vertex], [1.]),
                target_influences=influences(rigs[target], target_ids, bary),
                section_image=picture, image_sha256=sha256(output/picture)))
            print(dict(sample=sample, source=source_index, depth_mm=depth*1000), flush=True)
    verify()
    save(output/'result.json', dict(at=now(), status='complete', study=str(study), inputs=bound,
        samples=samples, observations=details, quality_approved=False,
        witness_comparison_sha256=sha256(output/'witness-comparison.json'),
        scope='Replays already measured deepest vertices only; no new complete collision screen or solver. Skin weights indicate deformation controls, not anatomical labels.'))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--samples', type=int, nargs='+', required=True)
    args = parser.parse_args(); run(args.study, args.output, args.samples)
