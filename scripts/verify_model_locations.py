"""Read-only check that runtime weights resolve under the current pinned checkout."""
import argparse
from pathlib import Path
from strep import ROOT,read,save,sha256,model_directory,now

def run(output):
    manifest=ROOT/'models/manifest.json';before=sha256(manifest);rows=[]
    for repo,entry in read(manifest)['models'].items():
        if entry['repo_id']!=repo:raise ValueError('Acquisition repository mismatch')
        directory=model_directory(entry);files=[]
        for name,expected in entry['files_sha256'].items():
            path=(directory/name).resolve()
            if not path.is_relative_to(ROOT.resolve()):raise ValueError('Model asset escaped project')
            if sha256(path)!=expected:raise ValueError('Pinned weight checksum mismatch: '+repo+'/'+name)
            files.append(dict(file=name,sha256=expected,bytes=path.stat().st_size))
        rows.append(dict(repo_id=repo,revision=entry['revision'],directory=directory.relative_to(ROOT).as_posix(),files=files))
    if sha256(manifest)!=before:raise ValueError('Acquisition manifest changed during audit')
    result=dict(created_at=now(),current_files_verified=True,acquisition_manifest_unchanged=True,manifest_sha256=before,resolver_sha256=sha256(ROOT/'scripts/strep.py'),models=rows,
        scope='Current local pinned bytes and relative runtime resolution. Relocation behavior is separately covered by synthetic filesystem tests. This does not establish a portable virtualenv, offline installer or full relocated inference.')
    save(output,result);print(dict(models=len(rows),files=sum(len(r['files']) for r in rows),bytes=sum(f['bytes'] for r in rows for f in r['files'])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
