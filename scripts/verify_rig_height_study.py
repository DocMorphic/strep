"""Verify constant-height edits, packaged bytes and actual local downloads."""
import argparse
import hashlib
import io
import zipfile
from pathlib import Path
from urllib.request import urlopen
import numpy as np
from rig_asset import RigAsset
from gltf_tools import sample_animation
from strep import ROOT,read,save,sha256,now


def run(baseline,study):
    before={c['id']:c for c in read(baseline/'manifest.json')['cases']};manifest=read(study/'manifest.json')
    calibration=read(study/'request.json')['calibrations'];checks=[]
    for case in manifest['cases']:
        previous=before[case['baseline_id']];a=(baseline/previous['path']).resolve();b=(study/case['path']).resolve()
        if sha256(a)!=previous['sha256'] or sha256(b)!=case['sha256']:raise ValueError('Export changed')
        ra,rb=RigAsset.load(a),RigAsset.load(b);report=read(b.parent/'report.json');root=report['root_node']
        delta=calibration[case['rig']]['added_vertical_offset_m'];moved=[]
        for node in range(len(ra.parents)):
            ancestor=node
            while ancestor>=0 and ancestor!=root:ancestor=ra.parents[ancestor]
            moved.append(ancestor==root)
        expected=np.zeros((len(moved),3));expected[np.array(moved),1]=delta
        matrix_error=skin_error=0.
        for frame in range(case['frames']):
            wa=sample_animation(ra.document,ra.binary,0,frame);wb=sample_animation(rb.document,rb.binary,0,frame)
            matrix_error=max(matrix_error,float(np.abs(wb[:,:3,:3]-wa[:,:3,:3]).max()),float(np.abs(wb[:,:3,3]-wa[:,:3,3]-expected).max()))
            skin_error=max(skin_error,float(np.abs(rb.vertices(wb)-ra.vertices(wa)-[0,delta,0]).max()))
        if max(matrix_error,skin_error)>1e-5:raise ValueError('Calibration changed more than declared height')
        checks.append(dict(id=case['id'],frames=case['frames'],delta_y_m=delta,max_transform_error=matrix_error,max_skin_delta_error_m=skin_error))
    save(study/'preservation-verification.json',dict(checked_at=now(),checks=checks,scope='All-frame GLB reload comparison. Joint rotations and horizontal movement preserved; only declared constant vertical displacement beneath mapped pelvis. Actual target skin checked independently.'))
    for folder in (baseline,study):
        packages=[]
        for case in read(folder/'manifest.json')['cases']:
            job=(folder/case['path']).resolve().parent.parent;result=read(job/'result.json')
            with urlopen('http://127.0.0.1:8768'+result['package']) as response:data=response.read()
            if hashlib.sha256(data).hexdigest()!=result['package_sha256']:raise ValueError('Served package changed')
            entries=0
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if archive.testzip():raise ValueError('Corrupt archive')
                for entry in archive.infolist():
                    if entry.filename=='README.txt':continue
                    if archive.read(entry)!=(job/entry.filename).read_bytes():raise ValueError('Archive differs from saved source/output')
                    entries+=1
            with urlopen('http://127.0.0.1:8768'+result['variants']['transfer']['glb']) as response:data=response.read()
            if hashlib.sha256(data).hexdigest()!=case['sha256']:raise ValueError('Served GLB changed')
            packages.append(dict(id=case['id'],entries_verified=entries,package_sha256=result['package_sha256'],glb_sha256=case['sha256']))
        save(folder/'package-http-verification.json',dict(checked_at=now(),checks=packages))
    print('Verified',len(checks),'paired clips,',sum(c['frames'] for c in checks),'frames and',2*len(checks),'served packages/GLBs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('baseline',type=Path);parser.add_argument('study',type=Path)
    args=parser.parse_args();run(args.baseline.resolve(),args.study.resolve())
