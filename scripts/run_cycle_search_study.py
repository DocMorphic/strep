"""Run fixed cycle-search comparisons through the real Studio API."""
import json
import time
from urllib.request import Request,urlopen
from strep import ROOT,read,save


def post(route,data):
    return json.load(urlopen(Request('http://127.0.0.1:8768'+route,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8768'}),timeout=240))


def main():
    out=ROOT/'reports/cycle-selection-v1';out.mkdir(exist_ok=False)
    cases=[];save(out/'pipeline.json',dict(status='running'))
    try:
        for name,baseline,bounds in [('wave','20260926-213335-362828ae',(0,30,30,90)),('locomotion','20260926-212922-5f10b11e',(0,15,20,45))]:
            frozen=read(ROOT/'reports/rig-jobs'/baseline/'loop.json')
            request=dict(schema='strep-cycle-search-v1',**{k:frozen.get(k,'travel') for k in ('job','variant','glb_sha256','root_mode','blend_frames','turn_degrees')},start_min=bounds[0],start_max=bounds[1],period_min=bounds[2],period_max=bounds[3],stride=5)
            save(out/(name+'-request.json'),request);result=post('/api/rig-loop-search',request);save(out/(name+'-search.json'),result)
            winner=result['shortlist'][0];recipe={**winner['recipe'],'label':name.title()+' cycle proposal 1'};save(out/(name+'-loop.json'),recipe)
            job=post('/api/rig-loops',recipe);print(name,'search',result['id'],'candidates',result['candidate_count'],'job',job['id'],flush=True)
            deadline=time.monotonic()+240
            while time.monotonic()<deadline:
                state=read(ROOT/'reports/rig-jobs'/job['id']/'pipeline.json')
                if state['status'] in ('complete','failed'):break
                time.sleep(1)
            if state['status']!='complete':raise RuntimeError(str(state))
            audit=read(ROOT/'reports/rig-jobs'/job['id']/'transfer/loop-audit.json')
            case=dict(name=name,baseline_job=baseline,search_id=result['id'],candidate_job=job['id'],proposal=winner,audit=audit)
            cases.append(case);save(out/'cases.json',dict(cases=cases));print(json.dumps(case),flush=True)
        save(out/'pipeline.json',dict(status='complete'))
    except Exception as e:
        save(out/'pipeline.json',dict(status='failed',error=str(e)));raise


if __name__=='__main__':main()
