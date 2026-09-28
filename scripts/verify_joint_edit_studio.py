"""Verify actual API/UI joint-edit jobs and prepare independent engine fixtures."""
import copy
import hashlib
import shutil
import urllib.request
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_joint_edit import audit_clip

OUT=ROOT/'reports/rig-joint-studio-v1'


def verify():
    manifest=[];rows=[]
    for case in read(OUT/'observed-requests.json')['cases']:
        folder=ROOT/'reports/rig-jobs'/case['job']
        assert read(folder/'pipeline.json')['status']=='complete'
        request=read(folder/'request.json');recipe=read(folder/'joint-edit.json')
        assert all(sha256(folder/name)==digest for name,digest in request['input_files'].items())
        assert sha256(folder/'input/character.glb')==request['input_glb_sha256']
        rig=RigAsset.load(folder/'input/character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
        goal=recipe['goals'][0];world=sampler.sample(float(np.float32(goal['frame']/30)))[goal['node']]
        delta=np.array(goal['position_m'])-world[:3,3]
        np.testing.assert_allclose(delta,case['offset_m'],atol=1e-6,rtol=0)
        orientation=float(np.degrees(Rotation.from_matrix(world[:3,:3].T@Rotation.from_quat(goal['rotation_xyzw']).as_matrix()).magnitude()))
        assert orientation<1e-4
        data=dict(np.load(folder/'joint-input.npz',allow_pickle=False));spec=read(folder/'joint-spec.json');targets=read(folder/'joint-targets.json')
        guards=read(folder/'quality-fit/guards.json') if (folder/'quality-fit/guards.json').exists() else None
        independent=audit_clip(folder/'transfer/character.glb',data['before'],spec,targets,guards)
        reported=read(folder/'transfer/joint-edit-audit.json')
        for key,value in independent.items():assert reported[key]==value
        assert independent['hard_checks_passed']
        expected_status='numerical_screens_met' if independent['numerical_screen_passed'] else 'rejected'
        result=read(folder/'result.json');assert result['joint_edit_status']==expected_status
        before_contacts=read(folder/'input/contacts.json');after_contacts=read(folder/'transfer/contacts.json')
        assert all(after_contacts[k]==v for k,v in before_contacts.items())
        if (folder/'input/events.json').exists():assert sha256(folder/'input/events.json')==sha256(folder/'transfer/events.json')
        assert read(folder/'contact-spec.json')['contacts']==read(folder/'input/contact-spec.json')['contacts']
        with zipfile.ZipFile(folder/'character-animation.zip') as archive:
            assert archive.testzip() is None
            for entry in archive.namelist():
                if entry!='README.txt':assert hashlib.sha256(archive.read(entry)).hexdigest()==sha256(folder/entry)
        served=[]
        for label,directory in [('input','input'),('target-fit','target-fit'),('candidate','transfer')]:
            source=folder/directory/'character.glb';name=case['id']+'-'+label+'.glb';destination=OUT/name
            if destination.exists():assert sha256(destination)==sha256(source)
            else:shutil.copyfile(source,destination)
            url='http://127.0.0.1:8768/files/rig-jobs/'+folder.name+'/'+directory+'/character.glb'
            with urllib.request.urlopen(url,timeout=30) as response:content=response.read()
            assert hashlib.sha256(content).hexdigest()==sha256(source)
            manifest.append(dict(id=case['id']+'-'+label,path=name,frames=len(data['before']),fps=30,sha256=sha256(source)))
            served.append(dict(stage=label,bytes=len(content),sha256=sha256(source)))
        rows.append(dict(id=case['id'],job=folder.name,requested_offset_m=delta.tolist(),
            sampled_orientation_error_degrees=orientation,audit=independent,served=served,
            package_sha256=sha256(folder/'character-animation.zip'),annotations_preserved=True,quality_approved=False))
    save(OUT/'manifest.json',dict(cases=manifest))
    save(OUT/'verification.json',dict(checked_at=now(),checks_passed=True,cases=rows,
        scope='Actual API/UI requests, original-rig world-space correspondence, decoded motion, unchanged input/annotations, packages and HTTP bytes. Not held-out quality or animator review.'))


if __name__=='__main__':verify()
