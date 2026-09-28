"""Export original actors and two contact-measurement variants for scene review."""
import copy
import numpy as np
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET,make_preview
from gltf_tools import write_glb,read_glb,sample_animation,accessor
from scene_constraints import evaluate,effector_track
from palm_contacts import calibrate


def run():
    out=ROOT/'reports/scene-preview-v1';out.mkdir(exist_ok=False);(out/'assets').mkdir()
    skin=dict(np.load(ASSET));palms=calibrate(skin);save(out/'palm-calibration.json',dict(asset_sha256=sha256(ASSET),candidates=palms,
        provenance='Geometric selection only, not anatomically or animator validated. Wrist-local offsets approximate a deforming surface vertex.'))
    manifest=dict(created_at=now(),scenes=[],assets={},scope='Raw motions and authored scene fixtures. Palm candidates change contact measurement only, not poses. No attachment, joint generation or successful interaction claim.')
    for trial in read(ROOT/'reports/scene-baseline-v1/summary.json')['trials']:
        folder=ROOT/'reports/scene-baseline-v1'/trial['id'];original=read(folder/'scene.json');variants={}
        motions={}
        for name,entry in original['actors'].items():
            source=ROOT/entry['motion'];digest=sha256(source);motion=dict(np.load(source));motions[name]=motion
            if digest not in manifest['assets']:
                file='assets/'+digest+'.glb';doc,binary,p,r=make_preview(skin,motion,np.zeros(3),repeat=False);write_glb(out/file,doc,binary)
                doc,binary=read_glb(out/file);error=0.
                for f in range(len(p)):
                    actual=sample_animation(doc,binary,0,f)[1:78]
                    error=max(error,float(np.abs(actual[:,:3,3]-p[f]).max()),float(np.abs(actual[:,:3,:3]-r[f]).max()))
                assert error<1e-5
                attributes=doc['meshes'][0]['primitives'][0]['attributes']
                for field,key in [('WEIGHTS','lbs_weights'),('JOINTS','lbs_indices')]:
                    arrays=np.concatenate([accessor(doc,binary,attributes[f'{field}_{g}']) for g in [0,1]],1)
                    assert np.array_equal(arrays,skin[key])
                assert sha256(source)==digest
                manifest['assets'][digest]=dict(file=file,sha256=sha256(out/file),max_transform_error=error,eight_weights_verified=True)
            entry['preview_glb']=manifest['assets'][digest]['file'];entry['source_sha256']=digest
        for variant in ['wrist','palm']:
            scene=copy.deepcopy(original)
            if variant=='palm':
                for contact in scene['contacts']:
                    contact['effector']=copy.deepcopy(palms[contact['effector']['joint']])
                    if contact['target']['space']=='actor':
                        target=contact['target'];target.update(copy.deepcopy(palms[target['joint']]))
                # Initial grasp only. Maintaining contact needs a moving box,
                # which the raw checkpoint does not supply in this baseline.
                if scene['objects']:
                    for contact in scene['contacts']:contact['end_frame']=contact['start_frame']+2
            assessment=evaluate(scene,skin);native={}
            for c in scene['contacts']:
                m=motions[c['actor']];a=dict(positions=m['posed_joints'],rotations=m['global_rot_mats'])
                item=dict(actual=effector_track(a,c['effector'],skin).tolist())
                if c['target']['space']=='actor':
                    m=motions[c['target']['actor']];a=dict(positions=m['posed_joints'],rotations=m['global_rot_mats'])
                    item['target']=effector_track(a,c['target'],skin).tolist()
                native[c['id']]=item
            dest=out/trial['id'];dest.mkdir(exist_ok=True)
            save(dest/(variant+'.json'),dict(scene=scene,evaluation=assessment,native_contact_tracks=native))
            variants[variant]=trial['id']+'/'+variant+'.json'
        manifest['scenes'].append(dict(id=trial['id'],label=trial['id'].replace('-',' '),variants=variants))
        save(out/'manifest.json',manifest);print(trial['id'],flush=True)
    import shutil
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',out/'SOMA-preview-LICENSE.txt')
    save(out/'pipeline.json',dict(status='complete'))


if __name__=='__main__':run()
