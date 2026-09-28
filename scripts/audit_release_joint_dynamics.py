"""Per-edited-joint rotation tails hidden by a single whole-body maximum."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize


def run(studies, output):
    if output.exists(): raise ValueError('Preserve prior diagnostic')
    cases = []
    for study in studies:
        if read(study/'pipeline.json')['status'] != 'complete': raise ValueError('Completed study required')
        request = read(study/'request.json'); completion = read(study/'completion.json')
        for name, digest in completion['files'].items():
            if sha256(study/name) != digest: raise ValueError('Completed artifact changed')
        spec = read(study/'take/spec.json'); variants = []
        paths = [('raw', study/'take/input/character.glb'), ('prior', Path(request['prior'])/'candidate/character.glb'),
                 ('held', Path(request['held'])/'candidate/character.glb'), ('candidate', study/'take/candidate/character.glb')]
        bindings = {str(path): sha256(path) for _, path in paths}
        for label, path in paths:
            rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
            world = np.array([sampler.sample(float(np.float32(f/spec['fps']))) for f in range(spec['frames'])])
            local = localize(world, rig.parents); joints = {}
            for role, joint in spec['edit_joints'].items():
                node = joint['node']; matrices = local[:, node, :3, :3]
                steps = np.degrees(Rotation.from_matrix(matrices[:-1].transpose(0, 2, 1)@matrices[1:]).magnitude())
                joints[role] = dict(node=node, name=rig.document['nodes'][node].get('name'),
                    max_degrees_per_frame=float(steps.max()), p95_degrees_per_frame=float(np.percentile(steps, 95)),
                    peak_step_end_frame=int(steps.argmax()+1))
            variants.append(dict(variant=label, source_sha256=sha256(path), joints=joints))
        differences = []
        for role in spec['edit_joints']:
            raw, prior, held, candidate = [v['joints'][role] for v in variants]
            delta = candidate['max_degrees_per_frame']-max(raw['max_degrees_per_frame'], prior['max_degrees_per_frame'])
            p95_delta = candidate['p95_degrees_per_frame']-max(raw['p95_degrees_per_frame'], prior['p95_degrees_per_frame'])
            differences.append(dict(role=role, peak_increase_over_raw_prior_degrees=delta,
                p95_increase_over_raw_prior_degrees=p95_delta, candidate_peak_step_end_frame=candidate['peak_step_end_frame']))
        for path, digest in bindings.items():
            if sha256(path) != digest: raise ValueError('Motion changed during audit')
        cases.append(dict(study=str(study), completion_sha256=sha256(study/'completion.json'), frames=spec['frames'], fps=spec['fps'],
            variants=variants, differences=differences, files=bindings))
    save(output, dict(at=now(), implementation_sha256=sha256(__file__), cases=cases, quality_approved=False,
        scope='Fresh decoded rotation step maxima and95th percentiles for every edited leg joint. Diagnostic differences only: no new post-hoc acceptance threshold, physical angular-speed limit or animator judgement. Original full-screen decisions unchanged.'))
    for case in cases:
        print(dict(study=case['study'], positive_peak_differences=[d for d in case['differences'] if d['peak_increase_over_raw_prior_degrees'] > 1e-5]))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('output', type=Path); p.add_argument('studies', nargs='+', type=Path); a = p.parse_args(); run([s.resolve() for s in a.studies], a.output.resolve())
