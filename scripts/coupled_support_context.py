"""Bind coupled leg/root correction to immutable raw and selected motion."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, sha256
from profile_support_surface import load
from sparse_support_surface import SparseSupportReferenceFitter
from serialized_pose import SerializedPose
from authored_root_correction import load_motion
from rig_clip_import import AnimationSampler
from rig_transition import localize
from angular_release_block import chord_cap
from support_temporal_cleanup import support_mask, guarded_edges
from coupled_support_block import CoupledBlock


def context(whole_folder, selected):
    fitter, initial = load(whole_folder, SparseSupportReferenceFitter)
    spec, request = fitter.spec, read(whole_folder/'request.json')
    frames, root = spec['frames'], spec['root_node']
    source_rig, clock = load_motion(selected, frames)
    source_world = clock[::2]
    world = np.array([fitter.pose(f, v)[0] for f, v in enumerate(initial)])
    # Earlier root cleanup preserves rotations and changes only translation.
    initial[:, :3] += source_world[:, root, :3, 3]-world[:, root, :3, 3]
    animated = {c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
    oracle = SerializedPose(fitter.rig, animated, root, frames)
    reconstructed = np.array([oracle.pose(fitter.pose(f, v)[0]) for f, v in enumerate(initial)])
    if np.abs(reconstructed-source_world).max() > 1e-6:
        raise ValueError('Selected source cannot be reproduced by original correction coordinates')
    points = np.array([source_rig.vertices(w) for w in source_world])
    reconstruction_error = max(float(np.linalg.norm(fitter.rig.vertices(w)-p, axis=1).max()) for w, p in zip(reconstructed, points))
    if reconstruction_error > 1e-6:
        raise ValueError('Source skin reconstruction exceeds one micrometre')
    sides = list(spec['patches']); patches = [p['vertices'] for p in spec['patches'].values()]
    centers = np.array([[p[ids].mean(axis=0) for ids in patches] for p in points])
    annotations = read(whole_folder/'input/contacts.json')
    active = np.array([support_mask(annotations, side, frames) for side in sides]).T
    steps = active[:-1]&active[1:]
    guarded = np.array([guarded_edges(active[:, i]) for i in range(len(sides))]).T
    anchors = np.array([request['support']['guides'][side]['anchors_xz_m'] for side in sides]).transpose(1, 0, 2)
    used = np.array([request['support']['guides'][side]['weights'] for side in sides]).T > 0
    speed = np.linalg.norm(np.diff(centers[:, :, [0, 2]], axis=0), axis=2)*30
    local = localize(source_world, fitter.rig.parents)
    q = local[:, fitter.nodes, :3, :3]
    angles = Rotation.from_matrix((q[:-1].swapaxes(-1, -2)@q[1:]).reshape(-1, 3, 3)).magnitude().reshape(frames-1, len(fitter.nodes))
    sampler = AnimationSampler(source_rig.document, source_rig.binary, 0)
    half_depths = np.array([np.maximum(-source_rig.vertices(sampler.sample((f+.5)/30))[:, 1], 0) for f in range(frames-1)])
    step_norms = np.linalg.norm(np.diff(initial.reshape(frames, -1, 3), axis=0), axis=2)
    nominal = np.r_[spec['limits']['root_step_m'], np.full(len(fitter.nodes), np.radians(spec['limits']['joint_step_degrees']))]
    allowance = np.r_[1e-6, np.full(len(fitter.nodes), np.radians(1e-4))]
    if np.max(step_norms-nominal-allowance) > 0:
        raise ValueError('Source exceeds original root/joint step envelope')
    envelope = dict(active=active, support_steps=steps, guarded=guarded, anchors=anchors, used=used,
        anchor_caps=np.linalg.norm(centers[:, :, [0, 2]]-anchors, axis=2), speed_caps=speed,
        foot_acc_caps=np.linalg.norm(np.diff(centers, n=2, axis=0)*900, axis=2),
        root_acc_caps=np.linalg.norm(np.diff(source_world[:, root, :3, 3], n=2, axis=0)*900, axis=1),
        rotation_chord_caps=chord_cap(np.minimum(np.pi, angles+np.radians(1e-4))), half_depths=half_depths,
        edit_step_caps=np.maximum(nominal, step_norms), position_epsilon_m=1e-6,
        speed_epsilon_m_s=.00006, acc_epsilon_m_s2=.0036)
    trace = read(whole_folder/'traces.json')
    raw = next(v for v in trace['variants'] if v['variant'] == 'input')
    if raw['source_sha256'] != sha256(whole_folder/'input/character.glb'):
        raise ValueError('Raw target trace no longer matches source')
    targets = np.array([raw['feet'][side]['predicted_support_max_m_s'] if raw['feet'][side]['predicted_support_max_m_s'] is not None else 0. for side in sides])
    excess = np.maximum(speed-targets, 0)*steps
    selection = []
    # At most two non-overlapping twelve-frame blocks, selected by worst
    # remaining supported speed excess across either foot, not by action label.
    for flat in np.argsort(excess.ravel())[::-1]:
        edge, side = np.unravel_index(flat, excess.shape)
        if excess[edge, side] <= .001: break
        start = max(2, min(int(edge)-5, frames-14)); end = min(frames-2, start+12)
        block = list(range(start, end))
        if any(set(block)&set(item['frames']) for item in selection): continue
        selection.append(dict(frames=block, side=sides[side], step_end_frame=int(edge+1),
            speed_m_s=float(speed[edge, side]), raw_peak_target_m_s=float(targets[side]), excess_m_s=float(excess[edge, side])))
        if len(selection) == 2: break
    return dict(fitter=fitter, oracle=oracle, initial=initial, source_world=source_world,
                source_points=points, envelope=envelope, targets=targets,
                selection=selection, reconstruction_error_m=reconstruction_error)


def block(ctx, frames, initial=None):
    return CoupledBlock(ctx['fitter'], ctx['oracle'], ctx['initial'] if initial is None else initial,
        ctx['source_world'], ctx['source_points'], frames, ctx['envelope'], ctx['targets'])


def derivative_proof(problem, seed=963):
    x = problem.initial[problem.frames].ravel(); rng = np.random.default_rng(seed)
    direction = rng.normal(size=len(x)); direction /= np.linalg.norm(direction)
    base = problem.pair(x, quantized=False); step = 1e-6
    plus, minus = [problem.pair(x+sign*step*direction, quantized=False) for sign in (1, -1)]
    error = abs((plus[0]-minus[0])/(2*step)-base[1]@direction)
    linear_errors, norm_errors = {}, {}
    for (v, j, kind), (vp, _, _), (vm, _, _) in zip(base[2].linear, plus[2].linear, minus[2].linear):
        value = float(np.abs((vp-vm)/(2*step)-j@direction).max())
        linear_errors[kind] = max(linear_errors.get(kind, 0.), value)
    for (v, j, _, kind), (vp, _, _, _), (vm, _, _, _) in zip(base[2].norms, plus[2].norms, minus[2].norms):
        value = float(np.abs((vp-vm)/(2*step)-j@direction).max())
        norm_errors[kind] = max(norm_errors.get(kind, 0.), value)
    maximum = max([error, *linear_errors.values(), *norm_errors.values()])
    return dict(passed=bool(np.isfinite(maximum) and maximum < 2e-4), objective_error=float(error),
        linear_errors=linear_errors, norm_vector_errors=norm_errors, tolerance=2e-4,
        initial_margins=problem.pair(x)[2].margins(), scope='Smooth proposal derivative; quantized geometry checked separately.')
