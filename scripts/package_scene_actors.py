"""Downloadable editable actor clips, with placement and unreviewed evidence."""
import argparse
import json
import zipfile
from pathlib import Path
from strep import ROOT,read,save,sha256,now


def package(report):
    report=Path(report).resolve();summary=read(report/'summary.json');checks=[]
    if read(report/'pipeline.json')['status']!='complete':raise ValueError('Finish the fitting job before packaging')
    files=['soma.glb','motion.bvh','motion.npz','root-motion.json','contacts.json','contact-spec.json','recipe.json','evaluation.json','compilation.json']
    for trial in summary['trials']:
        scene=read(report/trial['id']/'candidate.json')['scene']
        for actor,entry in scene['actors'].items():
            folder=(ROOT/entry['motion']).resolve().parent
            if not folder.is_relative_to(report):raise ValueError('Actor artifact outside this report')
            record=dict(schema_version=1,scene=scene['id'],actor=actor,source_motion_sha256=trial['actors'][actor]['source_sha256'],
                candidate_sha256=sha256(folder/'motion.npz'),files={n:sha256(folder/n) for n in files},human_approved=False,
                scope='Individual SOMA actor candidate in native coordinates; scene placement is separate. No retargeting, collision-free or release certification.')
            extras={'actor-placement.json':json.dumps(dict(actor=actor,transform=entry['transform'],units='metres, Y-up'),indent=2)+'\n',
                'manifest.json':json.dumps(record,indent=2)+'\n',
                'README.txt':'Experimental Strep animation candidate; NOT release-approved.\n\nGLB includes the grey SOMA body and animation. BVH/NPZ provide editable motion.\nRoot-motion.json describes the native actor track; apply actor-placement.json separately for this scene.\nContacts.json contains model-predicted foot contacts, not validated grasp/release events.\nContact-spec.json and recipe.json describe requested corrections, not proof of success.\nRead evaluation.json and the Studio scene diagnostics; partner/object quality is assessed separately.\nThe pack contains this actor only, not partner geometry, an attached object, or a complete game scene.\n'}
            archive_path=folder/'actor-animation.zip'
            with zipfile.ZipFile(archive_path,'x',zipfile.ZIP_DEFLATED) as archive:
                for name in files:archive.write(folder/name,name)
                for name,content in extras.items():archive.writestr(name,content)
                archive.write(ROOT/'vendor/kimodo/LICENSE','SOMA-LICENSE.txt')
            with zipfile.ZipFile(archive_path) as archive:
                assert archive.testzip() is None
                for name in files:assert archive.read(name)==(folder/name).read_bytes()
                assert json.loads(archive.read('actor-placement.json'))['transform']==entry['transform']
            checks.append(dict(scene=scene['id'],actor=actor,path=archive_path.relative_to(report).as_posix(),sha256=sha256(archive_path),candidate_sha256=record['candidate_sha256']))
    save(report/'actor-package-verification.json',dict(created_at=now(),packages=checks,packager_sha256=sha256(__file__),scope='Archive byte/provenance verification, not animation quality approval.'))
    print('Packaged',len(checks),'actor candidates')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report');a=p.parse_args();package(a.report)
