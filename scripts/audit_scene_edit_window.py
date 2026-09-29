"""Verify native-window preservation on decoded SOMA exports, without approval."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256
from build_soma_preview import ASSET, make_preview
from floor_contact import Surface
from gltf_tools import read_glb, write_glb
from rig_clip_import import AnimationSampler

POSITION_TOLERANCE_M = 1e-6
BASIS_TOLERANCE = 1e-6


def summarize(rows, window, frames):
    if type(frames) is not int or frames < 2:
        raise ValueError('At least two native frames required')
    if not isinstance(window, (list, tuple)) or len(window) != 2 or any(type(x) is not int for x in window):
        raise ValueError('Two integer edit-window endpoints required')
    start, end = window
    if not 0 <= start <= end < frames:
        raise ValueError('Edit window outside clip')
    expected = np.arange((frames-1)*4+1)/4
    if len(rows) != len(expected) or not np.array_equal([r['frame'] for r in rows], expected):
        raise ValueError('Complete ordered quarter-frame clock required')
    fields = ['joint_position_error_m', 'basis_error', 'skin_position_error_m']
    for row in rows:
        if any(type(row.get(k)) not in (int, float) or not np.isfinite(row[k]) or row[k] < 0 for k in fields):
            raise ValueError('Finite nonnegative preservation errors required')
    groups = dict(locked_segments=[], boundary_segments=[], edited_window=[])
    for row in rows:
        f = row['frame']
        if start <= f <= end:
            group = 'edited_window'
        elif np.ceil(f) < start or np.floor(f) > end:
            group = 'locked_segments'
        else:
            group = 'boundary_segments'
        groups[group].append(row)
    groups['all_outside_times'] = groups['locked_segments']+groups['boundary_segments']
    output = {}
    for name, selected in groups.items():
        peaks = {k: max((r[k] for r in selected), default=None) for k in fields}
        passed = (peaks['joint_position_error_m'] <= POSITION_TOLERANCE_M
                  and peaks['skin_position_error_m'] <= POSITION_TOLERANCE_M
                  and peaks['basis_error'] <= BASIS_TOLERANCE) if selected else None
        output[name] = dict(samples=len(selected), maximum_errors=peaks,
                            within_numerical_tolerance=passed)
    return output


def run(study, output, seed_path=None):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'reports'):
        raise ValueError('Fresh local audit directory required')
    result, protocol, scene = [read(study/n) for n in ['result.json', 'protocol.json', 'authored-scene.json']]
    if result.get('status') != 'complete':
        raise ValueError('Completed fitting result required')
    for name, key in [('protocol.json', 'protocol_sha256'), ('authored-scene.json', 'authored_scene_sha256'),
                      ('candidate.glb', 'candidate_glb_sha256'), ('motion.npz', 'candidate_sha256')]:
        if sha256(study/name) != result[key]:
            raise ValueError('Changed fitting artifact: '+name)
    if scene['fps'] != 30:
        raise ValueError('Current SOMA export audit requires 30 fps')
    frames, window = scene['frame_count'], protocol.get('edit_window')
    # Validate the window before writing artifacts, without inventing coverage.
    dummy = [dict(frame=float(f), joint_position_error_m=0., basis_error=0., skin_position_error_m=0.)
             for f in np.arange((frames-1)*4+1)/4]
    summarize(dummy, window, frames)
    declared = protocol.get('initialization')
    if seed_path is None:
        if 'initialization' not in protocol:
            raise ValueError('Explicit seed path required when protocol does not identify initialization')
        seed_path = declared or study/'source-motion.npz'
    seed_path = Path(seed_path).resolve()
    if declared is not None and seed_path != Path(declared).resolve():
        raise ValueError('Seed differs from declared initialization')
    if protocol['inputs'].get(str(seed_path)) != sha256(seed_path):
        # Source copies have a different path but must be byte-identical to the
        # original source explicitly bound in the input protocol.
        original = ROOT/scene['actors'][protocol['actor']]['motion']
        if declared is not None or seed_path != study/'source-motion.npz' or protocol['inputs'].get(str(original)) != sha256(seed_path):
            raise ValueError('Seed is not bound by the fitting protocol')
    if protocol['inputs'].get(str(ASSET)) != sha256(ASSET):
        raise ValueError('Preview mesh differs from fitting input')
    seed = dict(np.load(seed_path, allow_pickle=False))
    if len(seed['root_positions']) != frames:
        raise ValueError('Seed clock differs from candidate')
    skin = dict(np.load(ASSET, allow_pickle=False))
    doc, binary, _, _ = make_preview(skin, seed, np.zeros(3), repeat=False)
    candidate_doc, candidate_binary = read_glb(study/'candidate.glb')
    samplers = [AnimationSampler(doc, binary, 0), AnimationSampler(candidate_doc, candidate_binary, 0)]
    layouts = [d['skins'][0]['joints'] for d in [doc, candidate_doc]]
    names = [[d['nodes'][j]['name'] for j in ids] for d, ids in zip([doc, candidate_doc], layouts)]
    if names[0] != names[1] or names[0] != list(map(str, skin['rig_joint_names'])):
        raise ValueError('Rig identities differ')
    if any(abs(s.duration-(frames-1)/30) > 1e-5 for s in samplers):
        raise ValueError('Export duration differs')
    output.mkdir(parents=True)
    reference = output/'seed-reference.glb'
    write_glb(reference, doc, binary)
    surface, rows = Surface(skin), []
    for frame in np.arange((frames-1)*4+1)/4:
        a, b = [sampler.sample(frame/30)[ids] for sampler, ids in zip(samplers, layouts)]
        av, bv = [surface.vertices(m[:, :3, :3], m[:, :3, 3]) for m in [a, b]]
        rows.append(dict(frame=float(frame),
                         joint_position_error_m=float(np.linalg.norm(a[:, :3, 3]-b[:, :3, 3], axis=1).max()),
                         basis_error=float(np.abs(a[:, :3, :3]-b[:, :3, :3]).max()),
                         skin_position_error_m=float(np.linalg.norm(av-bv, axis=1).max())))
    report = dict(result_sha256=sha256(study/'result.json'), window=window, frames=frames,
                  position_tolerance_m=POSITION_TOLERANCE_M, basis_tolerance=BASIS_TOLERANCE,
                  groups=summarize(rows, window, frames), rows=rows,
                  inputs={str(p): sha256(p) for p in [seed_path, ASSET, reference, study/'candidate.glb', study/'protocol.json']},
                  auditor_sha256=sha256(__file__), quality_approved=False,
                  scope='120 Hz decoded seed/candidate joint and full-skin comparison. Locked-key segments and boundary-straddling segments reported separately. Numerical preservation is not contact, dynamics or animation-quality approval.')
    save(output/'verification.json', report)
    print(report['groups'], flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('study', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--seed', type=Path)
    a = p.parse_args(); run(a.study, a.output, a.seed)
