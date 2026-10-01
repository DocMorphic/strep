"""Audit source finger motion and exhausted controls without changing a clip."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now


def run(study, output):
    from rig_asset import RigAsset
    from paired_temporal_neighbor import rotation_channels
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh pose diagnosis output required')
    result = read(study/'result.json'); request = read(study/'request.json')
    if result['status'] != 'complete': raise ValueError('Completed pose study required')
    files = {str(study/'result.json'): sha256(study/'result.json')}
    for name, digest in result['outputs'].items():
        path = (study/name).resolve()
        if path.parent != study or sha256(path) != digest: raise ValueError('Pose output changed')
        files[str(path)] = digest
    source = Path(request['source']); fits = read(study/'fits.json'); actors = []
    for i, (layout, fit) in enumerate(zip(request['actors'], fits)):
        path = source/f'authored-meeting-{i}.glb'
        if request['inputs'].get(str(path)) != sha256(path): raise ValueError('Source clip changed')
        files[str(path)] = sha256(path)
        rig = RigAsset.load(path); channels = rotation_channels(rig.document, rig.binary)
        rows = []; controls = np.asarray(fit['controls_radians']).reshape(-1, 3)
        if len(controls) != len(layout['nodes']): raise ValueError('Control layout changed')
        for j, (node, values, limit) in enumerate(zip(layout['nodes'], controls, layout['additional_control_limits_degrees'])):
            bind = Rotation.from_quat(rig.document['nodes'][node].get('rotation', [0, 0, 0, 1]))
            clock, keys = channels[node][1:]
            rotations = Rotation.from_quat(keys)
            norm = float(np.rad2deg(np.linalg.norm(values)))
            maximum = float(np.max(np.abs(values))/np.deg2rad(limit/np.sqrt(3)))
            rows.append(dict(node=node, name=rig.document['nodes'][node]['name'], finger=j >= 3,
                native_keys=len(clock), maximum_source_bind_angle_degrees=float(np.rad2deg((bind.inv()*rotations).magnitude()).max()),
                maximum_source_variation_degrees=float(np.rad2deg((rotations[0].inv()*rotations).magnitude()).max()),
                additional_control_norm_degrees=norm, additional_limit_degrees=limit,
                maximum_component_fraction=maximum, near_component_bound=maximum >= .999,
                near_norm_limit=norm >= .99*limit))
        actors.append(dict(actor=i, joints=rows, fingers_near_norm_limit=sum(r['finger'] and r['near_norm_limit'] for r in rows),
            joints_near_component_bound=sum(r['near_component_bound'] for r in rows)))
    output.mkdir()
    save(output/'diagnosis.json', dict(at=now(), inputs=files, method_sha256=sha256(__file__), actors=actors,
        component_box_fraction_of_axis_aligned_radius=float(1/np.sqrt(3)),
        interpretation='The inscribed component box restricts axis-aligned corrections to 57.735% of the unchanged joint angle budget. Saturation is not proof of anatomical infeasibility. Try joint-vector norm constraints before increasing original edit budgets; preserve original motion and geometry acceptance checks.',
        changes_animation=False, quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path); parser.add_argument('output', type=Path); args = parser.parse_args()
    run(args.study, args.output)
