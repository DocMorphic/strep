"""Package edited rig clips with source transfer, contact spec and failure evidence."""
import argparse
import hashlib
from pathlib import Path
import zipfile
from strep import read,save,sha256,now


def run(study):
    study=Path(study).resolve();manifest=read(study/'manifest.json');source=Path(manifest['source_study'])
    imported=read((study/manifest['engine_verification']).resolve());preserved=read(study/'preservation-verification.json');packages=[]
    for item in manifest['cases']:
        folder=study/item['id'];audit=read(folder/'audit.json')
        verified=next((c for c in imported['checks'] if c['source_sha256']==item['sha256']),None)
        preservation=next((c for c in preserved['checks'] if c['glb_sha256']==item['sha256']),None)
        if verified is None or preservation is None or sha256(folder/'character.glb')!=item['sha256']:
            raise ValueError('Matching engine/preservation evidence required')
        save(folder/'engine-verification.json',dict(engine=imported['engine'],check=verified,source_report_sha256=sha256((study/manifest['engine_verification']).resolve())))
        save(folder/'preservation-verification.json',preservation)
        note=('Strep target-rig contact candidate\n\n'
            f'Provisional numerical screen: {"passed" if audit["numerical_screen_passed"] else "FAILED"}. Flags: {audit["flags"]}. No independent animator approval.\n\n'
            'character.glb contains the finite corrected clip; root-motion.json is the corrected mapped pelvis world track, not engine root extraction. '
            'contact-spec.json contains explicit vertex patch sets, world targets and half-open support intervals. These intervals were drafted from model predictions and are not confirmed gameplay events. '
            'source/character.glb is the unchanged input transfer for this correction. source/report.json and source/rig-profile.json preserve calibration/source hashes; absolute paths in that report are provenance, not bundled dependencies. '
            'The original raw SOMA generation and original unanimated character are not bundled. The package supports editing/import and repeating this deterministic fit with the project scripts, not regenerating the model output.\n\n'
            'Reproduce with the matching scripts and Python dependencies: python scripts/target_rig_contact.py fit --transfer <unpacked>/source --spec <unpacked>/contact-spec.json --output <new-output>. '
            'Inspect audit.json, solver.json, preservation-verification.json and engine-verification.json before use. Engine evidence checks sampled bone playback, not GPU skin/physics/contact realism.\n\n'
            'CesiumMan copyright 2017 Cesium, CC BY 4.0; animation modified by Strep. Read LICENSE.md and the separate Cesium-logo-terms.txt.\n')
        (folder/'README.txt').write_text(note,encoding='utf8')
        files={name:folder/name for name in ['character.glb','root-motion.json','contact-spec.json','audit.json','solver.json','engine-verification.json','preservation-verification.json','README.txt']}
        files.update({name:study/name for name in ['LICENSE.md','Cesium-logo-terms.txt','UPSTREAM-README.md','provenance.json']})
        files.update({'source/'+name:source/item['id']/name for name in ['character.glb','report.json','rig-profile.json']})
        for file in (folder/'source-snapshot').iterdir():files['source-snapshot/'+file.name]=file
        path=folder/'animation.zip'
        if path.exists():raise ValueError('Refusing to overwrite an existing archive')
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,file in files.items():archive.write(file,name)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None or set(archive.namelist())!=set(files):raise ValueError('Invalid package')
            for name,file in files.items():
                if hashlib.sha256(archive.read(name)).hexdigest()!=sha256(file):raise ValueError('Package byte mismatch')
        packages.append(dict(id=item['id'],file=item['id']+'/animation.zip',sha256=sha256(path),files=len(files),bytes=path.stat().st_size,numerical_screen_passed=audit['numerical_screen_passed']))
    save(study/'package-verification.json',dict(created_at=now(),packages=packages,implementation_sha256=sha256(__file__)))
    print(packages)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True)
    run(parser.parse_args().study)
