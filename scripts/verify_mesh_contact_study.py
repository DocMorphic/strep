"""Reload actual contact exports and verify bounds, preservation and downloads."""
import argparse
import hashlib
import io
import zipfile
from pathlib import Path
from urllib.request import urlopen
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from target_rig_contact import baseline,audit


def run(study,jobs):
    study=Path(study).resolve();checks=[];cases=[]
    for identifier in jobs:
        folder=ROOT/'reports/rig-jobs'/identifier
        if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Job not complete')
        result=read(folder/'result.json');request=read(folder/'request.json');spec=read(folder/'contact-spec.json')
        parent=ROOT/'reports/rig-jobs'/request['source_job']/request['input_variant']/'character.glb'
        if sha256(parent)!=sha256(folder/'transfer/character.glb') or sha256(parent)!=request['input_glb_sha256']:
            raise ValueError('Input is not the exact chosen parent version')
        if sha256(folder/'contact-spec.json')!=request['authored_spec_sha256']:raise ValueError('Authored request changed')
        a=RigAsset.load(folder/'transfer/character.glb');before,local_before=baseline(a,spec['frames'])
        check=dict(id=identifier,source_job=request['source_job'],input_sha256=sha256(parent),frames=spec['frames'])
        if 'corrected' in result['variants']:
            b=RigAsset.load(folder/'corrected/character.glb');after,local_after=baseline(b,spec['frames'])
            evidence=read(folder/'corrected/audit.json')
            verified=audit(b,spec,before,after,None,read(folder/'corrected/solver.json'))
            for stage in ('before','after'):
                for key,value in evidence[stage].items():
                    if value is not None and abs(value-verified[stage][key])>1e-5:raise ValueError('Exported metric differs: '+key)
            if verified['flags']!=evidence['flags']:raise ValueError('Export changed acceptance flags')
            edited={v['node'] for v in spec['edit_joints'].values()};root=spec['root_node']
            untouched=[n for n in range(len(a.parents)) if n not in edited]
            rotations=float(np.abs(local_after[:,untouched,:3,:3]-local_before[:,untouched,:3,:3]).max())
            nonroot=[n for n in range(len(a.parents)) if n!=root]
            translations=float(np.abs(local_after[:,nonroot,:3,3]-local_before[:,nonroot,:3,3]).max())
            track=read(folder/'corrected/root-motion.json')
            root_error=float(np.abs(after[:,root,:3,3]-track['positions_m']).max())
            track_rotation=Rotation.from_quat(track['rotations_xyzw']).as_matrix()
            root_rotation_error=float(np.abs(after[:,root,:3,:3]-track_rotation).max())
            if max(rotations,translations,root_error,root_rotation_error)>1e-5:raise ValueError('Untouched pose or root track changed')
            check.update(exported_audit=verified,max_untouched_rotation_error=rotations,max_nonroot_translation_error_m=translations,
                         max_root_track_position_error_m=root_error,max_root_track_rotation_error=root_rotation_error)
        with urlopen('http://127.0.0.1:8768'+result['package']) as response:data=response.read()
        if hashlib.sha256(data).hexdigest()!=result['package_sha256']:raise ValueError('Downloaded package changed')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip():raise ValueError('Bad ZIP')
            entries=0
            for entry in archive.infolist():
                if entry.filename=='README.txt':continue
                if archive.read(entry)!=(folder/entry.filename).read_bytes():raise ValueError('Packaged file changed')
                entries+=1
        check.update(package_sha256=result['package_sha256'],verified_package_entries=entries)
        for variant,version in result['variants'].items():
            path=folder/variant/'character.glb'
            with urlopen('http://127.0.0.1:8768'+version['glb']) as response:data=response.read()
            if hashlib.sha256(data).hexdigest()!=version['sha256'] or sha256(path)!=version['sha256']:raise ValueError('Downloaded GLB changed')
            cases.append(dict(id=identifier+'-'+variant,path='../rig-jobs/'+identifier+'/'+variant+'/character.glb',sha256=version['sha256'],frames=spec['frames'],fps=spec['fps']))
        checks.append(check)
    save(study/'manifest.json',dict(cases=cases,jobs=jobs))
    save(study/'verification.json',dict(checked_at=now(),checks=checks,scope='Actual exported GLBs, all-frame authored patch/floor metrics and edit bounds; untouched local rotations/nonroot translations and root tracks; local HTTP GLBs and every ZIP entry. No independent animator or continuous collision approval.'))
    print('Verified',len(checks),'jobs and',len(cases),'served GLBs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('jobs',nargs='+')
    args=parser.parse_args();run(args.study,args.jobs)
