"""Opt-in stricter proposal targets; unchanged public contact/support gates.

Headroom is a search target, not a bound on untested import error. Actual
editable-native conversion and engine sampling remain independent checks.
"""
import argparse
import copy
from pathlib import Path
import re
import shutil
from strep import read,save,sha256,now
from native_support_spec import number,validate
from native_foot_plant import policy_rows
from native_joint_plant_job import run as fit,authored_audit
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler


def reserve_policy(policy,reserve):
    reserve=number(reserve,'proposal speed reserve',0,.0001)
    required={'schema','source_sha256','base_sha256','draft_sha256','supports'}
    if (not isinstance(policy,dict) or set(policy)!=required or policy['schema']!='strep-native-foot-plant-v1'
            or any(not isinstance(policy[k],str) or not re.fullmatch('[0-9a-f]{64}',policy[k])
                   for k in ('source_sha256','base_sha256','draft_sha256'))
            or not isinstance(policy['supports'],list) or not policy['supports']):
        raise ValueError('Explicit bound foot-plant policy required')
    target=copy.deepcopy(policy);ids=set()
    for row in target['supports']:
        if (not isinstance(row,dict) or set(row)!={'id','maximum_patch_anchor_error_m','maximum_patch_speed_m_s'}
                or not isinstance(row['id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',row['id']) or row['id'] in ids):
            raise ValueError('Distinct named original support limits required')
        ids.add(row['id'])
        number(row['maximum_patch_anchor_error_m'],'anchor limit',0,.03)
        speed=number(row['maximum_patch_speed_m_s'],'speed limit',0,.1)
        if reserve>0 and reserve>=speed:
            raise ValueError('Positive reserve must be below every supplied speed limit')
        row['maximum_patch_speed_m_s']=speed-reserve
    return target


def run(source,base,draft,policy_path,output,*,seed=None,reserve=.00001,iterations=8,trust=.000002,coordinates=True):
    source,base,draft,policy_path,output=map(lambda p:Path(p).resolve(),(source,base,draft,policy_path,output))
    seed=base if seed is None else Path(seed).resolve()
    paths=(source,base,draft,policy_path,seed)
    inputs={str(p):sha256(p) for p in paths}
    spec=read(draft);original=read(policy_path);target=reserve_policy(original,reserve)
    rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    _,rows=validate(spec,rig,reader,sha256(source))
    limits=policy_rows(original,source,base,draft,rows)
    output.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(policy_path,output/'public-policy.json');save(output/'proposal-policy.json',target)
    shutil.copyfile(__file__,output/'headroom-implementation.py');method=sha256(__file__)
    save(output/'request.json',dict(at=now(),inputs_sha256=inputs,method_sha256=method,
        proposal_speed_reserve_m_s=reserve,public_limits_changed=False,engine_error_bound_certified=False))
    save(output/'pipeline.json',dict(status='processing'))
    try:
        result=fit(source,base,draft,output/'proposal-policy.json',output/'fit',seed=seed,iterations=iterations,
                   trust=trust,coordinates=coordinates)
        public=authored_audit(source,output/'fit/candidate.glb',spec,limits)
        if any(sha256(p)!=h for p,h in inputs.items()) or sha256(__file__)!=method:
            raise ValueError('Headroom inputs or method changed')
        record=dict(status='complete',at=now(),proposal_speed_reserve_m_s=reserve,retained_input=result['retained_input'],
            fit_result_sha256=sha256(output/'fit/result.json'),public_policy_sha256=sha256(policy_path),
            proposal_policy_sha256=sha256(output/'proposal-policy.json'),public_candidate_audit=public,
            public_limits_changed=False,native_npz_conversion_verified=False,engine_contacts_verified=False,
            engine_error_bound_certified=False,quality_approved=False,training_admitted=False,release_approved=False)
        save(output/'result.json',record);save(output/'pipeline.json',dict(status='complete'));return record
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','base','draft','policy','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--seed',type=Path);parser.add_argument('--reserve',type=float,default=.00001)
    parser.add_argument('--iterations',type=int,default=8);parser.add_argument('--trust',type=float,default=.000002)
    parser.add_argument('--joint-directions',action='store_true')
    args=parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=1):
        result=run(args.source,args.base,args.draft,args.policy,args.output,seed=args.seed,reserve=args.reserve,
                   iterations=args.iterations,trust=args.trust,coordinates=not args.joint_directions)
        print(dict(retained_input=result['retained_input'],public_pass=result['public_candidate_audit']['passed']))
