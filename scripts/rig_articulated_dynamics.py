"""Immutable baked-GLB body-demand diagnostic under explicit physical inputs."""
import argparse
from pathlib import Path
import shutil
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256
from rig_asset import RigAsset
from rig_body_tracks import sample
from articulated_motion_dynamics import diagnose

SCHEMA = 'strep-rig-articulated-dynamics-v1'
FIELDS = {'schema', 'glb', 'animation_index', 'bindings', 'profile', 'sample_count', 'placement',
          'rigid_tolerance', 'external_forces_world_N', 'external_torques_about_com_world_Nm',
          'gravity_world_m_s2', 'phases', 'anchor_tolerance_m', 'force_tolerance_N', 'torque_tolerance_Nm',
          'assumption_notes'}
METHODS = ('rig_articulated_dynamics.py', 'rig_body_tracks.py', 'articulated_motion_dynamics.py',
           'object_dynamics.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py',
           'native_support_clock.py', 'strep.py', 'action_worker_lock.py')


def run(request_path, output):
    root = ROOT.resolve(); request_path = Path(request_path).resolve(); output = Path(output).resolve()
    if (not request_path.is_relative_to(root) or not request_path.is_file()
            or request_path.stat().st_size > 64*1024*1024):
        raise ValueError('Bounded in-project physical request required')
    digest = sha256(request_path); request = read(request_path)
    if sha256(request_path) != digest:
        raise ValueError('Physical request changed while reading')
    if not isinstance(request, dict) or set(request) != FIELDS or request['schema'] != SCHEMA:
        raise ValueError('Complete explicit baked-rig physical request required')
    asset = request['glb']
    if (not isinstance(asset, dict) or set(asset) != {'path', 'sha256'}
            or not isinstance(asset['path'], str) or not asset['path']):
        raise ValueError('Explicit hash-bound supplied GLB required')
    glb = (request_path.parent / asset['path']).resolve()
    if (not glb.is_relative_to(root) or not glb.is_file() or glb.suffix.lower() != '.glb'
            or glb.stat().st_size > 256*1024*1024 or sha256(glb) != asset['sha256']):
        raise ValueError('Bounded unchanged in-project GLB required')
    notes = request['assumption_notes']
    if (not isinstance(notes, dict) or set(notes) != {'body_model', 'external_wrenches', 'support', 'capacity'}
            or any(not isinstance(v, str) or not 1 <= len(v) <= 2000 for v in notes.values())):
        raise ValueError('Explicit body/reaction/support/capacity assumptions required')
    if (not output.is_relative_to(root/'reports') or output == root/'reports'
            or request_path.is_relative_to(output) or glb.is_relative_to(output)):
        raise ValueError('Fresh ignored output separate from immutable inputs required')
    if output.exists():
        raise FileExistsError(output)
    with worker_lock(), threadpool_limits(limits=1):
        output.mkdir(parents=True); save(output/'pipeline.json', dict(status='processing', quality_approved=False, release_approved=False))
        try:
            inputs = {str(request_path): digest, str(glb): asset['sha256']}
            snapshots = {str(request_path): 'inputs/request.json', str(glb): 'inputs/character.glb'}
            for p, name in snapshots.items():
                dest = output/name; dest.parent.mkdir(exist_ok=True); shutil.copyfile(p, dest)
                if sha256(dest) != inputs[p]:
                    raise ValueError('Original body-dynamics input changed while freezing')
            methods = {}; source_folder = Path(__file__).resolve().parent
            (output/'implementation').mkdir()
            for name in METHODS:
                p = source_folder/name; methods[name] = sha256(p); shutil.copyfile(p, output/'implementation'/name)
                if sha256(output/'implementation'/name) != methods[name]:
                    raise ValueError('Body-dynamics method changed while freezing')
            save(output/'protocol.json', dict(schema=SCHEMA, inputs_sha256=inputs, input_snapshots=snapshots,
                 methods_sha256=methods, uniform_clock_includes_original_clip_endpoints=True,
                 quality_approved=False, release_approved=False, training_admitted=False))
            rig = RigAsset.load(output/'inputs/character.glb')
            tracks = sample(rig, request['animation_index'], request['bindings'], request['sample_count'],
                            request['placement'], rigid_tolerance=request['rigid_tolerance'])
            profile = request['profile']
            if not isinstance(profile, list) or [r.get('id') if isinstance(r, dict) else None for r in profile] != tracks['body_ids']:
                raise ValueError('Explicit physical body order must match the node/COM bindings')
            save(output/'body-tracks.json', tracks)
            demand = diagnose(profile, tracks['world_com_positions_m'], tracks['body_rotations_xyzw'],
                              request['external_forces_world_N'], request['external_torques_about_com_world_Nm'],
                              fps=tracks['fps'], gravity_world_m_s2=request['gravity_world_m_s2'], phases=request['phases'],
                              anchor_tolerance_m=request['anchor_tolerance_m'], force_tolerance_N=request['force_tolerance_N'],
                              torque_tolerance_Nm=request['torque_tolerance_Nm'])
            save(output/'demands.json', demand)
            if any(sha256(p) != h or sha256(output/snapshots[p]) != h for p, h in inputs.items()):
                raise ValueError('Original or copied physical input changed during measurement')
            if any(sha256(source_folder/name) != h or sha256(output/'implementation'/name) != h for name, h in methods.items()):
                raise ValueError('Original or copied physical method changed during measurement')
            result = dict(status='complete', protocol_sha256=sha256(output/'protocol.json'),
                          files_sha256={n: sha256(output/n) for n in ['body-tracks.json', 'demands.json']},
                          body_ids=tracks['body_ids'], samples=tracks['sample_count'], fps=tracks['fps'],
                          assessed_samples=demand['assessed_samples'],
                          floating_root_wrench_consistent_samples=demand['floating_root_wrench_consistent_samples'],
                          input_glb_unchanged=True, assumption_notes=notes, physical_approval=None,
                          quality_approved=False, release_approved=False, training_admitted=False,
                          scope='Original supplied GLB motion sampled with explicit rigid-body/node/COM/axis, mass/inertia, joint-anchor, gravity, phase and complete external-wrench declarations. Internal joint demands and necessary floating-root balance only. No inferred anatomy/mass/strength, contact allocation, joint-axis restrictions, calibrated capacity, continuous/impact/skin collision, engine playback, human or release approval.')
            save(output/'result.json', result)
            save(output/'pipeline.json', dict(status='complete', result_sha256=sha256(output/'result.json'), quality_approved=False, release_approved=False))
            return result
        except BaseException as exc:
            save(output/'pipeline.json', dict(status='failed', error=repr(exc), quality_approved=False, release_approved=False))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); print(run(args.request, args.output))
