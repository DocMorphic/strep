"""Real Studio marker authoring, looping, confirmation, trim and transition study."""
import json
import time
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from strep import ROOT,read,save,sha256


def submit(route,payload,out,name,timeout=240):
    if (out/(name+'-job.json')).exists():
        assert read(out/(name+'-request.json'))==payload
        folder=ROOT/'reports/rig-jobs'/read(out/(name+'-job.json'))['id']
        if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Existing job is not complete; inspect its actual worker before resuming')
        return folder
    save(out/(name+'-request.json'),payload)
    for attempt in range(60):
        try:
            response=json.load(urlopen(Request('http://127.0.0.1:8768'+route,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8768'})));break
        except HTTPError as e:
            if e.code!=409 or attempt==59:raise
            # Pipeline completion precedes process exit; wait for the server's actual Popen/lock state.
            state=json.load(urlopen('http://127.0.0.1:8768/api/studies'))
            save(out/(name+'-busy-retry.json'),dict(attempt=attempt+1,busy=state['busy']));time.sleep(.5)
    save(out/(name+'-job.json'),response);folder=ROOT/'reports/rig-jobs'/response['id'];deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        state=read(folder/'pipeline.json')
        if state['status'] in ('failed','complete'):break
        time.sleep(1)
    if state['status']!='complete':raise ValueError(state)
    print(name,response['id'],flush=True);return folder


def main(resume=False):
    out=ROOT/'reports/event-authoring-v1';out.mkdir(exist_ok=resume)
    if resume and (out/'pipeline.json').exists():save(out/'previous-attempt.json',read(out/'pipeline.json'))
    save(out/'pipeline.json',dict(status='processing'))
    try:
        source=ROOT/'reports/rig-jobs/20260926-195412-bf0e8a1d';points=[('outside',2),('zero_weight',25),('blend_head',28),('accent',40),('sound_cue',40),('wrist_cue',58),('cycle_start_cue',70),('blend_tail',73)]
        marked=submit('/api/rig-events',dict(schema='strep-rig-events-v1',job=source.name,variant='corrected',glb_sha256=sha256(source/'corrected/character.glb'),label='Wave with authored intent cues',markers=[dict(id=n,name=n,frame=f,confirmed=True) for n,f in points]),out,'marked')
        assert sha256(marked/'transfer/character.glb')==sha256(source/'corrected/character.glb')
        loop=submit('/api/rig-loops',dict(schema='strep-rig-loop-v1',job=marked.name,variant='transfer',glb_sha256=sha256(marked/'transfer/character.glb'),label='Wave loop with mapped cues',start_frame=25,period_frames=45,blend_frames=8,turn_degrees=0,root_mode='in_place'),out,'loop')
        events=read(loop/'transfer/events.json')['events'];authored=[e for e in events if e.get('kind')=='authored']
        assert [(e['name'],e['frame'],e['requires_review']) for e in authored if e['frame']<45]==[('cycle_start_cue',0,False),('blend_tail',3,True),('blend_head',3,True),('accent',15,False),('sound_cue',15,False),('wrist_cue',33,False)]
        assert {e['name'] for e in read(loop/'transfer/runtime-cycle.json')['markers']}=={'cycle_boundary','cycle_start_cue','accent','sound_cue','wrist_cue'}
        confirmed=submit('/api/rig-events',dict(schema='strep-rig-events-v1',job=loop.name,variant='transfer',glb_sha256=sha256(loop/'transfer/character.glb'),label='Wave loop with reviewed event timing',markers=[dict(id=e['id'],name=e['name'],frame=e['frame'],confirmed=not e['requires_review'] or e['name']=='blend_head') for e in authored]),out,'confirmed')
        assert sha256(confirmed/'transfer/character.glb')==sha256(loop/'transfer/character.glb')
        assert 'blend_head' in {e['name'] for e in read(confirmed/'transfer/runtime-cycle.json')['markers']}
        trimmed=submit('/api/rig-clip-edits',dict(source_job=marked.name,variant='transfer',edit=dict(schema='strep-rig-clip-edit-v1',glb_sha256=sha256(marked/'transfer/character.glb'),label='Wave cues trimmed and retimed',start_frame=25,last_frame=80,speed=2,poses=[])),out,'retimed')
        events=read(trimmed/'transfer/events.json')['events'];assert 'outside' not in {e['name'] for e in events};assert next(e for e in events if e['name']=='accent')['frame']==8
        joined=submit('/api/rig-transitions',dict(schema='strep-rig-transition-v1',label='Two marked wave excerpts',clips=[dict(job=marked.name,variant='transfer',glb_sha256=sha256(marked/'transfer/character.glb'),first_frame=25,last_frame=45),dict(job=marked.name,variant='transfer',glb_sha256=sha256(marked/'transfer/character.glb'),first_frame=35,last_frame=80)],blend_frames=8,yaw_degrees=0),out,'joined')
        save(out/'cases.json',dict(marked=marked.name,loop=loop.name,confirmed=confirmed.name,retimed=trimmed.name,joined=joined.name))
        save(out/'pipeline.json',dict(status='complete'))
    except Exception as e:save(out/'pipeline.json',dict(status='failed',error=str(e)));raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');main(p.parse_args().resume)
