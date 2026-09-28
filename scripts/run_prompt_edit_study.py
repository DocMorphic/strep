"""Fixed-seed real-model dance and jump section replacement on two target rigs."""
from strep import ROOT,read,save,sha256
from run_event_study import submit


def main():
    out=ROOT/'reports/prompt-edit-v1';out.mkdir(exist_ok=False);save(out/'pipeline.json',dict(status='processing'));cases={}
    descriptions={r['id']:r['segments'][0]['prompt'] for r in read(ROOT/'reports/action-coverage-v1/request.json')['requests']}
    save(out/'design.json',dict(cases=['dance in a previously corrected wave clip','jump in an imported locomotion clip'],seeds=[203,204],scope='Engineering pilot using previously encoded descriptions and two existing rigs. Not held-out semantic/animator validation. Exact original clips, bridge, raw model attempts and blended exports retained.'))
    try:
        for action,job,variant,a,b in [('dance','20260926-195412-bf0e8a1d','corrected',10,109),('jump-land','20260926-202128-ecb5f088','transfer',5,55)]:
            for seed in [203,204]:
                name=action+'-'+str(seed);source=ROOT/'reports/rig-jobs'/job/variant/'character.glb'
                payload=dict(source_job=job,variant=variant,edit=dict(schema='strep-rig-prompt-edit-v1',glb_sha256=sha256(source),label=f'{action} section replacement - seed {seed}',prompt=descriptions[action],start_frame=a,last_frame=b,blend_frames=8,seed=seed))
                result=submit('/api/rig-prompt-edits',payload,out,name,timeout=1800);cases[name]=result.name;save(out/'cases.json',cases)
        save(out/'pipeline.json',dict(status='complete'))
    except Exception as exc:save(out/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':main()
