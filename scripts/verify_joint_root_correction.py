"""Independent decoded checks for joint-target root cleanup candidates."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read,save,sha256,now
from verify_authored_root_correction import inspect as root_inspect, samples
from rig_joint_edit import audit_clip
from run_godot_rig_import import run as import_engine
from audit_authoring_intent import check_files


def inspect(folder,candidate,policy, *, source=None, original=None):
    result=read(folder/'result.json');frames=result['frames']
    source=Path(source) if source is not None else folder/'transfer/character.glb'
    original=Path(original) if original is not None else folder/'input/character.glb'
    base=root_inspect(source,candidate,original,folder/'contact-spec.json',frames,policy)
    _,before=samples(source,frames);_,after=samples(candidate,frames);_,raw=samples(original,frames)
    targets=read(folder/'joint-targets.json');spec=read(folder/'joint-spec.json')
    old_audit=audit_clip(source,raw[::2],spec,targets)
    new_audit=audit_clip(candidate,raw[::2],spec,targets)
    eps=policy['position_tolerance_m'];fixed=np.array(targets['envelope'])==0
    goals=[]
    for goal,old,new in zip(targets['goals'],old_audit['target_metrics'],new_audit['target_metrics']):
        n=goal['node']
        a0,a1=[np.linalg.norm(np.diff(w[::2,n,:3,3],n=2,axis=0)*900,axis=1) for w in (before,after)]
        goals.append(dict(node=n,frame=goal['frame'],position_before_m=old['position_error_m'],position_after_m=new['position_error_m'],
            position_cap_excess_m=new['position_error_m']-old['position_error_m'],
            orientation_before_degrees=old['orientation_error_degrees'],orientation_after_degrees=new['orientation_error_degrees'],
            whole_clip_acceleration_cap_excess_m_s2=float((a1-a0).max())))
    context=float(np.max(np.abs(after[::2][fixed]-before[::2][fixed]))) if fixed.any() else 0.
    checks=dict(base=base['all_checks_passed'],original_joint_hard_bounds=new_audit['hard_checks_passed'],
        fixed_context=context<=eps,
        world_goals=all(g['position_cap_excess_m']<=eps for g in goals),
        goal_orientations=all(abs(g['orientation_after_degrees']-g['orientation_before_degrees'])<=1e-9 for g in goals),
        goal_node_acceleration=all(g['whole_clip_acceleration_cap_excess_m_s2']<=policy['acceleration_tolerance_m_s2'] for g in goals))
    return dict(checks=checks,all_checks_passed=all(checks.values()),root=base,goals=goals,
        source_original_hard_checks=old_audit['hard_checks'],candidate_original_hard_checks=new_audit['hard_checks'],
        source_flags=old_audit['flags'],candidate_flags=new_audit['flags'],fixed_context_max_error=context,quality_approved=False)


def run(study,output):
    output.mkdir(parents=True,exist_ok=False)
    protocol,complete=read(study/'protocol.json'),read(study/'completion.json')
    assert sha256(study/'protocol.json')==complete['protocol_sha256']
    cases=[];rows=[]
    with threadpool_limits(limits=1):
        for case,row in zip(protocol['cases'],complete['rows']):
            assert case['id']==row['id']
            folder=study/case['id'];check_files(folder,case['files'])
            selected=Path(row['selected']);assert sha256(selected)==row['selected_sha256']
            audit=inspect(folder,selected,protocol['policy'])
            if row['status']=='improved':assert audit['all_checks_passed']
            else:assert sha256(selected)==sha256(folder/'transfer/character.glb')
            save(output/(case['id']+'.json'),audit);rows.append(dict(id=case['id'],status=row['status'],audit=audit))
            for name,path in [('input',folder/'transfer/character.glb'),('selected',selected)]:
                cases.append(dict(id=case['id']+'-'+name,path=str(path),sha256=sha256(path),frames=read(folder/'result.json')['frames'],fps=30,sample_by_time=True))
    save(output/'manifest.json',dict(cases=cases));import_engine(output,output/'engine')
    save(output/'completion.json',dict(at=now(),rows=rows,engine_actor_frames=sum(c['frames'] for c in cases),
        study_completion_sha256=sha256(study/'completion.json'),engine_verification_sha256=sha256(output/'engine/verification.json'),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.study.resolve(),a.output.resolve())
