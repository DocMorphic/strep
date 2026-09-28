"""Acquire the pinned official portable engine for local import verification."""
import hashlib
import urllib.request
import zipfile
from strep import ROOT,save,sha256,now

VERSION='4.7.2-stable'
NAME='Godot_v4.7.2-stable_win64.exe.zip'
DIGEST='731980f9608d61333e5baf54a2ef17210acc7a538446c0cb9969f002aca1e953'
URL='https://github.com/godotengine/godot-builds/releases/download/'+VERSION+'/'+NAME


def main():
    out=ROOT/'.cache/godot'/VERSION;out.mkdir(parents=True,exist_ok=True);archive=out/NAME
    if not archive.exists():
        request=urllib.request.Request(URL,headers={'User-Agent':'strep-local-engine-audit'})
        with urllib.request.urlopen(request,timeout=60) as response,archive.open('wb') as stream:
            while chunk:=response.read(1024*1024):stream.write(chunk)
    if sha256(archive)!=DIGEST:raise ValueError('Godot archive hash mismatch')
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            target=(out/member.filename).resolve()
            if not target.is_relative_to(out.resolve()):raise ValueError('Archive path escapes engine folder')
        package.extractall(out)
    executables={p.name:sha256(p) for p in out.glob('*.exe')}
    save(out/'acquisition.json',dict(acquired_at=now(),version=VERSION,url=URL,archive_sha256=DIGEST,executables=executables,
        checksum_source='Official godotengine/godot-builds GitHub release API asset digest',purpose='Portable reference engine for local Strep import audit; no system installation.'))
    print(out)


if __name__=='__main__':main()
