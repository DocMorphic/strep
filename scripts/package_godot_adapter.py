"""Package the audited adapter separately from immutable motion scene packs."""
import argparse
import zipfile
from pathlib import Path
from strep import ROOT,read,save,sha256,now


def package(output):
    output=Path(output).resolve()
    verification=ROOT/'reports/godot-playback-v3/verification.json'
    audit=read(verification)
    adapter=ROOT/'scripts/godot_clip_adapter.gd'
    if audit['implementation']['godot_clip_adapter.gd']!=sha256(adapter):raise ValueError('Adapter changed since engine verification')
    files={'godot_clip_adapter.gd':adapter,'README.md':ROOT/'integrations/godot/README.md','verification.json':verification}
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as archive:
        for name,path in files.items():archive.write(path,name)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name,path in files.items():assert archive.read(name)==path.read_bytes()
    save(output.with_suffix('.json'),dict(created_at=now(),sha256=sha256(output),files={n:sha256(p) for n,p in files.items()},
        scope='Godot forward playback marker/root adapter. Motion quality and physical attachment are not approved.'))
    print(output)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);args=p.parse_args();package(args.output)
