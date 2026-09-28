"""Explicit full-weight contact drafts on two previously failed loop candidates."""
import argparse
import numpy as np
from strep import ROOT,read,save
from rig_contact_authoring import empty_spec
from run_event_study import submit


def main(output):
    out=ROOT/output;out.mkdir(exist_ok=False);save(out/'pipeline.json',dict(status='processing'))
    cases={}
    try:
        for name,job in [('turning','20260926-212541-f05dcc66'),('locomotion','20260926-215013-58f47dfd')]:
            source=ROOT/'reports/rig-jobs'/job/'transfer';spec=empty_spec(read(source/'report.json'));review=read(source/'contact-review.json')
            spec['provenance']='Development draft: inherited authored patch targets only at full source weight. Blended partial targets remain in source Contact review and are evaluated separately, not declared solved. No independent support annotations.'
            omitted=0
            for target in review['authored_targets']:
                spec['patches'][target['patch']]=dict(vertices=target['vertices'])
                active=np.zeros(spec['frames'],bool)
                for entry in target['output_frames']:
                    if entry['weight']>=1-1e-9:active[entry['frame']]=True
                    else:omitted+=1
                edges=np.diff(np.r_[False,active,False].astype(int))
                for a,b in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
                    spec['contacts'].append(dict(patch=target['patch'],start_frame=int(a),end_frame_exclusive=int(b),target_position_m=target['target_position_m']))
            save(out/(name+'-draft-scope.json'),dict(source_job=job,partial_target_occurrences_not_fit=omitted,quality_approval=False))
            result=submit('/api/rig-contact-edits',dict(source_job=job,variant='transfer',spec=spec),out,name,timeout=1800)
            cases[name]=result.name;save(out/'cases.json',cases)
        save(out/'pipeline.json',dict(status='complete'))
    except Exception as exc:save(out/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output');main(p.parse_args().output)
