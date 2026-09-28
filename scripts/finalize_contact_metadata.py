"""Versioned metadata repair for early contact exports; pose files stay unchanged."""
import argparse
import zipfile
import numpy as np
from strep import read,save,sha256,now,ROOT
from export_actions import sequence_diagnostics


def run(folder):
    from pathlib import Path
    folder=Path(folder);summary=read(folder/'summary.json');changes=[]
    for trial in summary['trials']:
        path=folder/'takes'/trial['id'];evidence=read(path/'evidence.json')
        actual=sequence_diagnostics(dict(np.load(path/'motion.npz')),read(path/'timeline.json')['segments'])
        if evidence['sequence']==actual:continue
        before=sha256(path/'evidence.json');pose_hash=sha256(path/'motion.npz')
        save(folder/'metadata-original'/trial['id']/'evidence.json',evidence)
        evidence['sequence']=trial['sequence']=actual;save(path/'evidence.json',evidence)
        with zipfile.ZipFile(path/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as z:
            for file in path.iterdir():
                if file.is_file() and file.suffix!='.zip':z.write(file,file.name)
            z.write(ROOT/'vendor/kimodo/LICENSE','LICENSE.txt')
        trial['hashes']={p.relative_to(path).as_posix():sha256(p) for p in path.rglob('*') if p.is_file()}
        assert sha256(path/'motion.npz')==pose_hash
        changes.append(dict(id=trial['id'],original_evidence_sha256=before,pose_sha256=pose_hash))
    if changes:
        save(folder/'summary.json',summary)
        save(folder/'metadata-amendment.json',dict(at=now(),changes=changes,reason='Recompute sequence diagnostics from edited poses instead of inherited source diagnostics; animation arrays unchanged.',finalizer_sha256=sha256(__file__)))
    print('Metadata records repaired:',len(changes))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');run(p.parse_args().folder)
