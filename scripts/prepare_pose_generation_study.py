"""Freeze a matched-seed pose-guided vs unchanged-checkpoint pilot."""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from action_encoder import ActionEncoder
from action_requests import request_digest, conditioning_texts
from generation_constraints import compile_guides
from inspect_motion import skeleton_metadata


def prepare(output):
    output = Path(output).resolve()
    source = ROOT / 'reports/action-coverage-v1'
    original = read(source / 'request.json')
    ActionEncoder(source / 'conditioning', original)
    batch = dict(schema_version=1, requests=[])
    fixtures = []
    for action, effector in [('wave', 'RightHand'), ('kick', 'RightFoot')]:
        base = copy.deepcopy(next(r for r in original['requests'] if r['id'] == action))
        base['seeds'] = [77, 88]
        motion_path = source / 'raw' / action / 'seed-11/attempt-001/motion.npz'
        with np.load(motion_path, allow_pickle=False) as data:
            names, _, _ = skeleton_metadata(77)
            source_frame = int(data['posed_joints'][:, names.index(effector), 1].argmax())
        guide = dict(type='end-effector', joint_names=[effector], motion=motion_path.relative_to(ROOT).as_posix(),
            sha256=sha256(motion_path), source_frames=[source_frame], frame_indices=[60])
        target = copy.deepcopy(base); target.update(id=action+'-pose', label=base['label']+' · pose at 2 seconds', generation_constraints=[guide])
        compiled, provenance = compile_guides(target)
        batch['requests'].extend([base, target])
        fixtures.append(dict(action=action, target_frame=60, source_frame=source_frame, compiled=compiled, provenance=provenance))
    output.mkdir(parents=True, exist_ok=False)
    cache = output / 'conditioning'; cache.mkdir()
    manifest = read(source / 'conditioning/manifest.json')
    manifest['entries'] = {text:manifest['entries'][text] for text in conditioning_texts(batch)}
    for item in manifest['entries'].values():
        shutil.copyfile(source / 'conditioning' / item['file'], cache / item['file'])
        assert sha256(cache / item['file']) == item['sha256']
    manifest.update(request_sha256=request_digest(batch), reuse_provenance=dict(source=str(source / 'conditioning'),
        source_manifest_sha256=sha256(source / 'conditioning/manifest.json'), copied_at=now(),
        reason='Exact prompt subset, identical encoder/model revisions and byte-verified tensors. New seeds and optional pose guides do not change text features.'))
    save(cache / 'manifest.json', manifest); save(output / 'request.json', batch); ActionEncoder(cache, batch)
    scripts = ['prepare_pose_generation_study.py', 'generation_constraints.py', 'generate_actions.py', 'audit_generation_guides.py', 'export_actions.py']
    snapshot = output / 'source-snapshot'; snapshot.mkdir()
    for name in scripts: shutil.copyfile(ROOT / 'scripts' / name, snapshot / name)
    save(output / 'freeze.json', dict(created_at=now(), request_sha256=request_digest(batch), fixtures=fixtures,
        script_hashes={n:sha256(snapshot / n) for n in scripts},
        design='Two previously encoded actions, matched seeds 77/88 (77 previously used elsewhere in this project), unchanged checkpoint, raw outputs without postprocessing. Source seed11 peak hand/foot height pose scheduled at frame60. Engineering pilot, not held-out semantic/realism evaluation. No scene collision targets.',
        decision='Report all guides, implicit root constraints and quality regressions; no candidate promotion from target accuracy alone.'))
    print(output)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output', type=Path); prepare(parser.parse_args().output)
