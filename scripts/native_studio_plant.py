"""Explicit Studio planted-contact choices and bounded joint fit adapter."""
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read,save,sha256,now
from native_support_spec import number,validate
from native_foot_plant import policy_rows,propose
from native_joint_plant_job import run as joint_fit,authored_audit
from native_plant_headroom import reserve_policy
from native_review_support import method_names
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_engine_clock import audit_clock

ITERATIONS=8
TRUST=.001
COORDINATE_TRUST=.000002
MAXIMUM_SPEED_RESERVE=.00001
SPEED_RESERVE_FRACTION=.002


def settings(choice):
    keys={'maximum_patch_anchor_error_m','maximum_patch_speed_m_s'}
    if not isinstance(choice,dict) or set(choice)!=keys:
        raise ValueError('Explicit planting anchor and speed limits required')
    return dict(maximum_patch_anchor_error_m=number(choice['maximum_patch_anchor_error_m'],'planting anchor limit',0,.03),
        maximum_patch_speed_m_s=number(choice['maximum_patch_speed_m_s'],'planting speed limit',0,.1))


def policy(source,draft,choice):
    choice=settings(choice)
    return dict(schema='strep-native-foot-plant-v1',source_sha256=sha256(source),base_sha256=sha256(source),
        draft_sha256=sha256(draft),supports=[dict(id=row['id'],**choice) for row in read(draft)['supports']])


def methods(revision=1):
    if type(revision) is not int or revision not in (1,2):raise ValueError('Known planting revision required')
    names=set(method_names())|{'native_studio_plant.py','native_joint_plant.py','native_joint_plant_job.py',
        'native_foot_plant.py','native_support_rates.py','native_support_feasibility.py','native_support_roundtrip.py',
        'native_support_orientation.py','native_support_swivel.py','native_support_path.py','native_support_coordinates.py'}
    if revision==2:names.add('native_plant_headroom.py')
    return sorted(names)


def speed_reserve(choice):
    choice=settings(choice)
    return min(MAXIMUM_SPEED_RESERVE,choice['maximum_patch_speed_m_s']*SPEED_RESERVE_FRACTION)


def run(source,draft,output,choice,*,headroom=False):
    """Produce the existing Studio manifest contract while preserving phase jobs."""
    if type(headroom) is not bool:raise ValueError('Explicit headroom mode required')
    source,draft,output=map(lambda p:Path(p).resolve(),(source,draft,output));choice=settings(choice)
    if output.exists():raise ValueError('Fresh planted-support output required')
    spec=read(draft);rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    _,rows=validate(spec,rig,reader,sha256(source))
    binding=policy(source,draft,choice);limits=policy_rows(binding,source,source,draft,rows)
    revision=2 if headroom else 1;reserve=speed_reserve(choice) if headroom else 0.
    target=reserve_policy(binding,reserve) if headroom else binding
    inputs={str(p):sha256(p) for p in (source,draft)};directory=Path(__file__).resolve().parent
    hashes={name:sha256(directory/name) for name in methods(revision)}
    output.mkdir();archive=output/'implementation';archive.mkdir()
    for name in hashes:shutil.copyfile(directory/name,archive/name)
    shutil.copyfile(source,output/'input.glb');save(output/'plant-policy.json',binding)
    if headroom:save(output/'proposal-policy.json',target)
    target_path=output/('proposal-policy.json' if headroom else 'plant-policy.json')
    save(output/'request.json',dict(at=now(),inputs=inputs,spec=spec,implementation=hashes,
        proposal_method='joint_native_plant_search',sampled_support_iterations=None,planting=choice,
        planting_iterations=ITERATIONS,planting_trust_radians=TRUST,planting_coordinate_trust_radians=COORDINATE_TRUST,
        planting_revision=revision,proposal_speed_reserve_m_s=reserve,
        native_roundtrip=True,quality_approved=False))
    save(output/'pipeline.json',dict(status='processing'))
    try:
        seed=output/'plant-seed.glb'
        try:
            centering=propose(rig,reader,rig,reader,rows,seed)
            seed_note=dict(status='exported',reports=centering)
        except ValueError as exc:
            # Direct rotations can explore poses an exact ankle target rejected.
            shutil.copyfile(source,seed);seed_note=dict(status='retained_input',reason=str(exc))
        save(output/'plant-seed.json',dict(seed_note,sha256=sha256(seed),quality_approved=False))
        phases=[]
        first=joint_fit(source,source,draft,target_path,output/'joint',seed=seed,iterations=ITERATIONS,trust=TRUST)
        phases.append(('joint',first))
        if first['retained_input'] and not first['baseline']['passed']:
            second=joint_fit(source,source,draft,target_path,output/'coordinates',
                seed=output/'joint/proposal.glb',iterations=ITERATIONS,trust=COORDINATE_TRUST,coordinates=True)
            phases.append(('coordinates',second))
        trials=[]
        for index,(name,result) in enumerate(phases):
            shutil.copyfile(output/name/'proposal.glb',output/f'trial-{index}.glb')
            shutil.copyfile(output/name/'controls.json',output/f'trial-{index}.controls.json')
            save(output/f'trial-{index}-planting.json',result)
            audit=authored_audit(source,output/name/'proposal.glb',spec,limits) if headroom else result['proposal']
            if headroom:
                result=dict(result,public_proposal_audit=audit,public_limits_changed=False,proposal_speed_reserve_m_s=reserve)
                save(output/f'trial-{index}-planting.json',result)
            screens=audit['support_screens']
            trials.append(dict(trial=index,status='complete',sha256=sha256(output/f'trial-{index}.glb'),
                supports=screens['supports'],source_rate_failed_rows=screens['source_rate_failed_rows'],
                source_rates_pass=screens['source_rates_pass'],support_samples_pass=bool(screens['support_samples_pass'] and audit['authored_clearance_pass']),
                planting=dict(audit_file=f'trial-{index}-planting.json',controls_file=f'trial-{index}.controls.json',
                    method=result['optimization']['method'],iterations=result['optimization']['iterations'],
                    contacts=audit['contacts'],contact_samples_pass=audit['contact_samples_pass'],
                    proposal_speed_reserve_m_s=reserve,proposal_target_pass=result['proposal']['passed'],
                    all_selection_gates_pass=not result['retained_input'])))
        final_name,final=phases[-1];shutil.copyfile(output/final_name/'candidate.glb',output/'candidate.glb')
        selected=authored_audit(source,output/'candidate.glb',spec,limits) if headroom else final['selected']
        baseline=authored_audit(source,source,spec,limits) if headroom else final['baseline']
        passed=selected['passed'];selected_index=None if final['retained_input'] else len(phases)-1
        save(output/'support-events.json',dict(source='Explicit authored stance intervals, not measured contact force',
            target_clip_sha256=sha256(output/'candidate.glb'),
            constraint_status='satisfied_at_samples' if passed else 'unverified_on_retained_input',
            intervals=[dict(id=r['id'],foot=r['foot'],start_s=r['stance_s'][0],end_s=r['stance_s'][1]) for r in rows],quality_approved=False))
        times=audit_clock(reader.duration,[c[2] for c in reader.channels],[],rows[0]['stance_s'][0])
        world=np.array([reader.sample(float(t)) for t in times]);root=world[:,spec['root_node']]
        save(output/'root-motion.json',dict(node=spec['root_node'],times_s=times.tolist(),positions_m=root[:,:3,3].tolist(),
            rotations_xyzw=Rotation.from_matrix(root[:,:3,:3]).as_quat().tolist(),source_world_pose_unchanged=True,
            scope='Audit samples from unchanged source root; native source animation tracks remain in GLB'))
        if any(sha256(p)!=digest for p,digest in inputs.items()) or any(sha256(directory/n)!=d for n,d in hashes.items()):
            raise ValueError('Planting source or implementation changed')
        result=dict(status='complete',at=now(),retained_input=final['retained_input'],retention_reason=final['retention_reason'],
            selected_trial=selected_index,input_already_satisfied=baseline['passed'],
            source_supports=baseline['support_screens']['supports'],trials=trials,
            planting=dict(limits=choice,selected_audit=selected,proposal_speed_reserve_m_s=reserve,
                proposal_target_pass=final['selected']['passed'],engine_error_bound_certified=False),candidate_sha256=sha256(output/'candidate.glb'),
            output_support_samples_pass=bool(selected['support_screens']['support_samples_pass'] and selected['authored_clearance_pass']),
            quality_approved=False,training_admitted=False,release_approved=False,continuous_collision_certified=False,
            self_collision_checked=False,engine_import_verified=False,human_review_submitted=False)
        result['outputs']={p.name:sha256(p) for p in output.iterdir() if p.is_file() and p.name!='pipeline.json'}
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete'));return result
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise
