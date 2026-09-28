"""Draft, fit and retain every target-rig contact candidate in a transfer study."""
import argparse
import shutil
from pathlib import Path
from strep import read, save, sha256, now, ROOT
from target_rig_contact import draft, run


def study(source, output, rotation_prior=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    manifest = read(source / 'manifest.json')
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'pipeline.json').exists():
        raise ValueError('Study already started; inspect recorded process/output before rerunning')
    for case in manifest['cases']:
        if sha256(source / case['path']) != case['sha256']:
            raise ValueError('Transfer GLB changed')
    save(output / 'pipeline.json', dict(status='fitting', completed_cases=0))
    save(output / 'input-manifest.json', manifest)
    frozen = output / 'authoring-source'; frozen.mkdir(exist_ok=False)
    for name in ['run_target_rig_study.py', 'target_rig_contact.py', 'retarget_rig.py', 'rig_asset.py', 'gltf_tools.py']:
        shutil.copyfile(ROOT / 'scripts' / name, frozen / name)
    cases, comparison = [], []
    for case in manifest['cases']:
        folder = source / Path(case['path']).parent
        spec_path = output / 'specs' / (case['id'] + '.json')
        spec = draft(folder, spec_path)
        if rotation_prior is not None:
            spec['objective']['rotation_prior_m_per_radian'] = rotation_prior
            save(spec_path, spec)
        evidence = run(folder, spec_path, output / case['id'])
        cases.append(dict(id=case['id'], path=case['id']+'/character.glb', frames=case['frames'], fps=case['fps'],
                          sha256=evidence['glb_sha256'], audit=case['id']+'/audit.json'))
        comparison.append(dict(id=case['id'], **evidence))
        save(output / 'pipeline.json', dict(status='fitting', completed_cases=len(cases), cases=len(manifest['cases'])))
    for name in ['LICENSE.md', 'Cesium-logo-terms.txt', 'UPSTREAM-README.md', 'provenance.json']:
        shutil.copyfile(ROOT / 'assets/characters/cesium-man' / name, output / name)
    save(output / 'manifest.json', dict(cases=cases, source_study=str(source),
        scope='Calibration-aware deterministic target contact fitting on reused development clips, no independent animator review or release approval'))
    save(output / 'comparison.json', dict(created_at=now(), cases=comparison))
    save(output / 'pipeline.json', dict(status='complete', completed_cases=len(cases)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--rotation-prior',type=float)
    args=parser.parse_args();study(args.study,args.output,args.rotation_prior)
