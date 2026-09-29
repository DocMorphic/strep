"""Report stationary pins incompatible with the current native joint-change screen."""
import argparse
from pathlib import Path
import numpy as np
from strep import read, save, sha256
from contact_pose_reachability import point_bound


def analyze(references, skin, spec):
    from floor_contact import Surface
    from contact_spec import validate
    from support_contact import regions
    from inspect_motion import validate_motion
    if not isinstance(references, dict) or not references or any(not isinstance(k, str) or not k for k in references):
        raise ValueError('Named reference motions required')
    surface = Surface(skin)
    if not np.array_equal(surface.inverse[:, 3, :], np.tile([0., 0., 0., 1.], (len(surface.inverse), 1))):
        raise ValueError('Affine bind transforms required')
    validate(spec, spec['frame_count'], regions(skin))
    pins = [(name, p) for name, entry in spec['regions'].items() if entry['mode'] == 'explicit' for p in entry['segments']]
    if not pins or any(p['space'] != 'world' or 'vertex_id' not in p for _, p in pins):
        raise ValueError('Bound stationary material-point pins required')
    rows=[]
    for name, motion in references.items():
        validate_motion(motion, 30)
        if len(motion['root_positions']) != spec['frame_count']:
            raise ValueError('Reference and contact clocks differ')
        for region, pin in pins:
            vertex = pin['vertex_id'];indices = surface.indices[vertex];weights = surface.weights[vertex]
            local = np.einsum('vij,j->vi', surface.inverse[indices], surface.points[vertex])[:, :3]
            for frame in range(pin['start_frame'], pin['end_frame']+1):
                positions = motion['posed_joints'][frame, indices]
                inputs = dict(positions=positions.tolist(), weights=weights.tolist(), local_points=local.tolist(), target=pin['position_m'])
                rows.append(dict(reference=name, region=region, vertex_id=vertex, frame=frame,
                                 certificate_inputs=inputs, **point_bound(**inputs)))
    conflicts = [r for r in rows if r['any_verified_conflict']]
    worst = max(rows, key=lambda r: r['joint_displacement_lower_bound_m'])
    return dict(status='incompatible_with_pose_screen' if conflicts else 'not_ruled_out',
                conflicting_frame_reference_pairs=len(conflicts), rows=rows,
                worst={k: worst[k] for k in ['reference', 'region', 'vertex_id', 'frame', 'joint_displacement_lower_bound_m', 'joint_budget_m']},
                policy='Current .22 m native joint-change screen and .005 m native pin tolerance. Conservative rotation operator norm assumption 1.02; 1 micrometre arithmetic reserve. No acceptance limits changed.',
                quality_approved=False)


def describe(report):
    if report['status'] == 'not_ruled_out':
        return 'No conflict proved by the joint-change bound. This does not establish a feasible or realistic motion.'
    worst = report['worst']
    return (f"{worst['region']} at frame {worst['frame']} requires at least "
            f"{worst['joint_displacement_lower_bound_m']*100:.2f} cm of joint displacement from {worst['reference']}; "
            f"the current body screen permits {worst['joint_budget_m']*100:.2f} cm. "
            'This pin cannot pass both current native checks under the stated rigid-skin assumptions. '
            'Review its target, interval or source motion. No request or acceptance limit has been changed.')


if __name__ == '__main__':
    from build_soma_preview import ASSET
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Source take with original raw/ and limb/ motion.npz references')
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():parser.error('Use a new output file; preserve prior diagnoses')
    inputs = {str(p.resolve()): sha256(p) for p in [args.spec, ASSET, *[args.source/n/'motion.npz' for n in ['raw', 'limb']]]}
    result = analyze({n: dict(np.load(args.source/n/'motion.npz')) for n in ['raw', 'limb']}, dict(np.load(ASSET)), read(args.spec))
    for path, digest in inputs.items():
        if sha256(Path(path)) != digest:raise ValueError('Diagnostic input changed')
    result['inputs'] = inputs
    result['implementation'] = {p.name: sha256(p) for p in [Path(__file__), Path(__file__).with_name('contact_pose_reachability.py')]}
    save(args.output, result);print(describe(result))
