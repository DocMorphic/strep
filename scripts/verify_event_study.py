"""Independent event-clock, runtime eligibility and immutable-package checks."""
import io
import json
import hashlib
import zipfile
from urllib.request import urlopen
import numpy as np
from strep import ROOT,read,save,sha256


def main():
    out=ROOT/'reports/event-authoring-v1';cases=read(out/'cases.json');cases['studio']='20260926-222539-831f5a06';checks=[]
    for name,job in cases.items():
        folder=ROOT/'reports/rig-jobs'/job;result=read(folder/'result.json');events=read(folder/'transfer/events.json')['events']
        if name in ('marked','confirmed','studio'):
            assert sha256(folder/'input/character.glb')==sha256(folder/'transfer/character.glb')
            for file in ('root-motion.json','contacts.json'):
                assert (folder/'input'/file).read_bytes()==(folder/'transfer'/file).read_bytes()
            recipe=read(folder/'event-edit.json');authored={e['id']:e for e in events if e.get('kind')=='authored'}
            assert set(authored)=={m['id'] for m in recipe['markers']}
            for m in recipe['markers']:
                e=authored[m['id']];assert (e['name'],e['frame'],e['requires_review'])==(m['name'],m['frame'],not m['confirmed'])
        if name in ('loop','joined'):
            inputs=[read(folder/'input/events.json')['events']]
            if name=='joined':inputs.append(read(folder/'following/events.json')['events'])
            clock=read(folder/'transfer/timeline.json')['contributors'];expected=[]
            for f,entries in enumerate(clock):
                for c in entries:
                    for e in inputs[c.get('source',0)]:
                        if e['frame']==c['frame'] and c['weight']>0:
                            expected.append((f,e['name'],e.get('origin_id',e['id']),c.get('source',0),e['frame'],c['weight'],e['requires_review'] or c['weight']<1-1e-9))
            observed=[(e['frame'],e['name'],e['origin_id'],e['lineage'][-1]['source'],e['lineage'][-1]['source_frame'],e['lineage'][-1]['weight'],e['requires_review']) for e in events if e.get('kind')=='authored']
            assert sorted(observed)==sorted(expected)
        if name=='retimed':
            source_frames=read(folder/'transfer/timeline.json')['source_frames'];expected=[]
            for e in read(folder/'input/events.json')['events']:
                if source_frames[0]<=e['frame']<=source_frames[-1]:expected.append((e['id'],int(np.floor(np.interp(e['frame'],source_frames,np.arange(len(source_frames)))+.5))))
            assert [(e['id'],e['frame']) for e in events]==expected
        if (folder/'transfer/runtime-cycle.json').exists():
            runtime=read(folder/'transfer/runtime-cycle.json');p=runtime['period_frames'];expected={e['id'] for e in events if e.get('kind')=='authored' and not e['requires_review'] and e['frame']<p}
            assert {e['event_id'] for e in runtime['markers'] if 'event_id' in e}==expected
        data=urlopen('http://127.0.0.1:8768'+result['package']).read();assert hashlib.sha256(data).hexdigest()==result['package_sha256']
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert z.testzip() is None
            for file in z.namelist():
                if file!='README.txt':assert z.read(file)==(folder/file).read_bytes()
            entries=len(z.namelist())
        for variant in result['variants'].values():
            data=urlopen('http://127.0.0.1:8768'+variant['glb']).read();assert hashlib.sha256(data).hexdigest()==variant['sha256']
        checks.append(dict(name=name,job=job,events=len(events),review_required=sum(e.get('requires_review',False) for e in events),package_entries=entries,glb_sha256=result['variants']['transfer']['sha256']))
    save(out/'verification.json',dict(checks=checks,scope='Exact geometry preservation for marker edits, independent contributor and retime clocks, explicit runtime eligibility, all archive entries and HTTP GLB hashes. Event names are development intent cues, not verified semantic/physical actions.'))
    print(json.dumps(checks))


if __name__=='__main__':main()
