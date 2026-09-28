"""Check object transforms from the actual Godot import and served deliverables."""
import hashlib
import urllib.request
import numpy as np
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def verify():
    out=ROOT/'reports/object-release-v2';engine=ROOT/'reports/godot-object-release-v2'
    report=read(engine/'engine-output.json');manifest=read(out/'manifest.json');checks=[]
    assert read(engine/'pipeline.json')['status']=='complete'
    for case,observed in zip(manifest['cases'],report['cases']):
        assert case['id']==observed['id'] and len(observed['frames'])==case['frames']
        path=out/case['path'];assert sha256(path)==case['sha256']
        doc,binary=read_glb(path);sampler=AnimationSampler(doc,binary,0)
        node=next(i for i,n in enumerate(doc['nodes']) if n.get('name')=='Interaction_box')
        position_error=0.;rotation_error=0.
        for i,frame in enumerate(observed['frames']):
            assert frame['object'] is not None
            actual=np.asarray(frame['object']);expected=sampler.sample(float(np.float32(i/30)))[node]
            position_error=max(position_error,float(np.max(np.abs(actual[3]-expected[:3,3]))))
            rotation_error=max(rotation_error,float(np.max(np.abs(actual[:3].T-expected[:3,:3]))))
        checks.append(dict(id=case['id'],frames=case['frames'],max_object_position_error_m=position_error,max_object_rotation_element_error=rotation_error,
            position_screen_passed=position_error<1e-5,rotation_screen_passed=rotation_error<1e-5,
            precision_screen=1e-5))
    served=[]
    for item in manifest['scenes']:
        for download in item['downloads']:
            if download['path']=='engine-http-verification.json':continue
            path=out/download['path'];url='http://127.0.0.1:8768/files/object-release-v2/'+download['path']
            with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
            assert hashlib.sha256(data).hexdigest()==sha256(path)
            served.append(dict(path=download['path'],sha256=sha256(path),bytes=len(data)))
    save(out/'engine-http-verification.json',dict(at=now(),engine=report['engine'],objects=checks,
        all_object_precision_screens_passed=all(c['position_screen_passed'] and c['rotation_screen_passed'] for c in checks),
        note='Initial verifier aborted on seed-22 dynamic rotation; preserved engine-object-initial-failure.json. Full reporting now retains this failure without relaxing the 1e-5 precision screen. Imported rotation keys match source; playback discrepancy remains unresolved.',
        actor_evidence='reports/godot-object-release-v2/verification.json',served=served,
        scope='Actual Godot scene import, all 720 object poses plus separate 77-bone checks, and served GLB/ZIP/event/audit bytes. No GPU rendering, actor-collider simulation or independent human approval.'))
    for item,check in zip(manifest['scenes'],checks):
        if not check['rotation_screen_passed']:
            note=' Engine playback rotation precision check failed; see engine audit. Export remains experimental.'
            if note not in item['review_note']:item['review_note']+=note
        link=dict(label='Engine audit',path='engine-http-verification.json')
        if link not in item['downloads']:item['downloads'].append(link)
    save(out/'manifest.json',manifest)
    print(checks)


if __name__=='__main__':verify()
