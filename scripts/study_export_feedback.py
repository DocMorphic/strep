"""Experimental three-case export-feedback study; retains every failed proposal.

Requires the completed local contact-breadth-v1 archive and acquired assets/Godot.
This research runner does not change Studio defaults or approve motion quality.
"""
import sys, shutil, traceback
from pathlib import Path
import psutil
import numpy as np
import torch
from threadpoolctl import threadpool_limits
sys.path.insert(0,str(Path.cwd()/'scripts'))
from strep import ROOT,read,save,sha256,now
from verify_contact_archive import verify_archive
from root_height_feasibility import RootHeightProblem
from linear_feasibility_restore import linear_step
from build_soma_preview import ASSET
from inspect_motion import skeleton_metadata,validate_motion
from evaluate_body_contact import evaluate
from run_body_contact import export_motion
from kimodo.skeleton import SOMASkeleton77
from audit_checked_contact import audit
from scene_runtime import write
from study_scene_runtime import verify as verify_engine
from probe_godot_render import run_engine
from held_pose_preservation import restore_locked_pose

def phase(status,**kw):
    save(output/'pipeline.json',dict(status=status,at=now(),**kw));print(status,kw,flush=True)
def verify_methods():
    assert sha256(Path(__file__))==protocol['script_sha256']
    for name,h in methods.items():assert sha256(ROOT/'scripts'/name)==sha256(output/'implementation'/name)==h,name


def rate_layout(p):
    blocks={};offset=sum((r['last_frame']-r['first_frame'])*4+1 for r in p.position.rows)
    for order in [1,2]:
        for i,(row,masks,caps,scales) in enumerate(zip(p.point_rate.rows,p.masks,p.point_rate.ceilings,p.point_rate.scales)):
            n=int(masks[order-1].sum());rate=np.diff(p.rate_points[:,row['point']],n=order,axis=0)*120**order
            horizontal=float(np.linalg.norm(rate[masks[order-1]][:,[0,2]],axis=1).max())
            blocks[f'point_rate:{i}:{order}']=dict(bounds=[offset,offset+n],cap=float(caps[order-1]),scale=float(scales[order-1]),horizontal=horizontal,index=i,order=order)
            offset+=n
        n=len(p.joints)-order;rate=np.diff(p.joints,n=order,axis=0)*120**order
        blocks[f'global_rate:{order}']=dict(bounds=[offset,offset+n],cap=float(p.global_rate.ceilings[order-1]),scale=float(p.global_rate.scales[order-1]),horizontal=float(np.linalg.norm(rate[...,[0,2]],axis=-1).max()),order=order)
        offset+=n
    assert offset+len(p.heights)==len(p.evaluate(p.start,False)[0])
    return blocks


def exported_measurements(audit_result,blocks):
    peaks={};slacks={}
    for key,g in blocks.items():
        peak=(audit_result['phase_rates'][g['index']]['variants']['candidate'][g['order']-1] if 'index' in g else
          max(r[['peak_speed_m_s','peak_acceleration_m_s2'][g['order']-1]] for r in audit_result['variants']['candidate']['joints']))
        peaks[key]=peak;slacks[key]=(g['cap']-peak)/g['scale']
    for i,row in enumerate(audit_result['contacts']):slacks['pin:'+str(i)]=(.005-row['maximum_error_m'])/.005
    slacks['floor']=-audit_result['floor_nonregression']['maximum_added_depth_m']/.001
    errors=audit_result['preservation']['all_outside_times']['maximum_errors']
    slacks['outside']=-max(errors.values())
    return peaks,slacks


def strengthen(target,values,blocks,peaks,slacks,requirements,margin_fraction):
    updated=target.copy();notes=[]
    for key,g in blocks.items():
        if slacks[key]>=0:continue
        a,b=g['bounds'];proxy=g['cap']-g['scale']*float(values[a:b].min())
        discrepancy=max(requirements.get(key,{}).get('discrepancy',0.),(peaks[key]-proxy)/g['scale']);capacity=(g['cap']-g['horizontal'])/g['scale']
        if capacity<=discrepancy:
            notes.append(dict(group=key,changed=False,reason='No horizontal room beyond observed discrepancy',capacity=capacity,discrepancy=discrepancy));continue
        requirements[key]=dict(discrepancy=discrepancy,optional=min(1e-4,.5*(capacity-discrepancy)))
        margin=discrepancy+margin_fraction*requirements[key]['optional']
        prior=float(target[a:b].max());updated[a:b]=max(prior,margin)
        notes.append(dict(group=key,changed=margin>prior,previous_target=prior,target=float(updated[a:b].max()),proxy_peak=proxy,export_peak=peaks[key],capacity=capacity,discrepancy=discrepancy))
    return updated,notes


def engine_check(folder,id,take):
    scene=folder/'scene';(scene/'actors/0').mkdir(parents=True)
    shutil.copyfile(take/'motion.npz',scene/'actors/0/motion.npz');shutil.copyfile(take/'soma.glb',scene/'actors/0/actor.glb')
    save(scene/'portable-scene.json',dict(schema_version=1,id=id,fps=30,frame_count=120,actors={'A':dict(motion='actors/0/motion.npz',preview_glb='actors/0/actor.glb',source_sha256=sha256(take/'motion.npz'),transform=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1]))},objects={},contacts=[]))
    save(scene/'events.json',dict(fps=30,events=[dict(type='requested_pin_start',actor='A',frame=50,time_s=50/30),dict(type='requested_pin_end',actor='A',frame=70,time_s=70/30)]));write(scene)
    project=folder/'project';project.mkdir();(project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Targeted export headroom diagnostic"\n')
    for name in ['godot_scene_clock.gd','godot_scene_clock_audit.gd']:shutil.copyfile(ROOT/'scripts'/name,project/name)
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    assert sha256(engine)==read(engine.parent/'acquisition.json')['executables'][engine.name]
    engine_output=folder/'engine';engine_output.mkdir()
    command=[str(engine),'--headless','--path',str(project),'--fixed-fps','60','--script','godot_scene_clock_audit.gd','--',str(engine_output/'request.json'),str(engine_output/'engine-output.json')]
    request=dict(cases=[dict(id=id,folder=str(scene),frames=120,metadata_sha256=sha256(scene/'scene-runtime.json'))],controls=[],command=command)
    save(engine_output/'request.json',request);run_engine(command,engine_output/'engine.log',timeout=150)
    passed,checks=verify_engine(request,read(engine_output/'engine-output.json'),engine_output)
    return passed,checks


def run():
    phase('verifying_archive')
    save(output/'historical-verification.json',verify_archive(suite,suite/'batch-engine-followup-v2'))
    skin=dict(np.load(ASSET));_,parents,_=skeleton_metadata(77);results=[]
    with threadpool_limits(limits=1):
      torch.set_num_threads(2)
      for id in protocol['cases']:
        phase('case_start',case=id);folder=output/id;folder.mkdir()
        job=ROOT/'reports/contact-jobs'/('contact-breadth-v1-'+id+'-repair')
        paths=[job/'source-take/motion.npz',job/'source-take/soma.glb',job/'source-take/raw/motion.npz',job/'source-take/limb/motion.npz',job/'candidate/motion.npz',job/'candidate/soma.glb',job/'checked-plan/bound-contact-spec.json',job/'checked-plan/rate-reference.json',job/'checked-plan/edit-request.json',job/'protocol.json',ASSET]
        inputs={str(path):sha256(path) for path in paths};save(folder/'inputs.json',inputs)
        source=dict(np.load(job/'source-take/motion.npz'));seed=dict(np.load(job/'candidate/motion.npz'))
        raw=dict(np.load(job/'source-take/raw/motion.npz'));limb=dict(np.load(job/'source-take/limb/motion.npz'))
        spec=read(job/'checked-plan/bound-contact-spec.json');reference=read(job/'checked-plan/rate-reference.json')
        window=read(job/'checked-plan/edit-request.json')['options']['edit_window'];held=np.ones(len(seed['root_positions']),bool)
        held[window[0]+int(window[0]>0):window[1]+int(window[1]==len(held)-1)]=False
        seed=restore_locked_pose(source,seed,held)
        p=RootHeightProblem(source,seed,parents,skin,spec,window,read(job/'protocol.json')['original_max_root_lift_m'])
        blocks=rate_layout(p);x=p.start.copy();values,j,_=p.evaluate(x);target=np.zeros_like(values)
        def inspect(coordinates,destination):
            candidate={k:v.astype(seed[k].dtype) for k,v in p.motion(coordinates).items()}
            validate_motion(candidate,30)
            for key in ['local_rot_mats','global_rot_mats']:assert candidate[key].tobytes()==seed[key].tobytes()
            for key in ['root_positions','posed_joints']:assert candidate[key][held].tobytes()==source[key][held].tobytes()
            assert candidate['root_positions'][:,[0,2]].tobytes()==seed['root_positions'][:,[0,2]].tobytes()
            lift=candidate['root_positions'][:,1].astype(float)-source['root_positions'][:,1]
            assert lift.min()>=0 and lift.max()<=p.max_lift
            serial=p.reference_residuals(candidate)
            evaluation,body=evaluate(raw,limb,candidate,skin,dict(applied=True))
            validation=export_motion(destination,candidate,skin,SOMASkeleton77(),evaluation['after']['per_frame_max_depth_m'])
            a=audit(job/'source-take/soma.glb',destination/'soma.glb',spec,window,reference)
            peaks,slacks=exported_measurements(a,blocks)
            save(destination/'checked-export-audit.json',a);save(destination/'body-evaluation.json',dict(evaluation=evaluation,body=body))
            save(destination/'serialized-proxy.json',dict(minimum_slack=float(serial.min()),violations=int((serial<0).sum())))
            save(destination/'validation.json',validation)
            return dict(path=destination,peaks=peaks,slacks=slacks,serial=serial,flags=evaluation['flags'],validation=validation,audit=a)
        current=inspect(x,folder/'restored-seed');initial=current
        requirements={};margin_index=0
        target,notes=strengthen(target,values,blocks,current['peaks'],current['slacks'],requirements,protocol['optional_margin_fractions'][margin_index])
        history=[];save(folder/'initial-targets.json',notes)
        for iteration in range(protocol['attempts']):
            if min(current['slacks'].values())>=0 and current['serial'].min()>=0:break
            values,j,_=p.evaluate(x);residual=values-target
            margin_trials=[]
            while True:
                delta,info=linear_step(x,residual,j,p.bounds,trust=1e-5,margin=0.)
                margin_trials.append(dict(optional_fraction=protocol['optional_margin_fractions'][margin_index],result=dict(info)))
                if delta is not None or margin_index==len(protocol['optional_margin_fractions'])-1:break
                margin_index+=1;target=np.zeros_like(target)
                for key,need in requirements.items():
                    a,b=blocks[key]['bounds'];target[a:b]=need['discrepancy']+protocol['optional_margin_fractions'][margin_index]*need['optional']
                residual=values-target
            info['optional_margin_trials']=margin_trials
            info.update(iteration=iteration+1,source_export=str(current['path']),trials=[])
            accepted=False;changed=False
            if delta is not None:
                for backtrack in range(protocol['backtracks']):
                    fraction=.5**backtrack;trial=x+fraction*delta;c,_,_=p.evaluate(trial,False)
                    native_ok=bool(np.isfinite(c).all() and (c[values>=0]>=0).all() and np.all(np.abs(trial)<=p.bounds) and (c-target).min()>residual.min())
                    record=dict(fraction=fraction,native_proposal_passed=native_ok,minimum_original_slack=float(c.min()),minimum_target_slack=float((c-target).min()),accepted=False)
                    if native_ok:
                        phase('export_trial',case=id,iteration=iteration+1,backtrack=backtrack)
                        inspected=inspect(trial,folder/f'trial-{iteration+1}-{backtrack}')
                        regressions=[k for k,v in current['slacks'].items() if v>=0 and inspected['slacks'][k]<0]
                        serial_ok=bool((inspected['serial'][current['serial']>=0]>=0).all())
                        body_ok=not(set(inspected['flags'])-set(current['flags']))
                        improves=min(inspected['slacks'].values())>min(current['slacks'].values())
                        if min(current['slacks'].values())>=0:improves=bool(min(inspected['slacks'].values())>=0 and inspected['serial'].min()>current['serial'].min())
                        good=bool(not regressions and serial_ok and body_ok and improves)
                        record.update(path=str(inspected['path']),export_regressions=regressions,serialized_passing_rows_preserved=serial_ok,
                            body_flags_preserved=body_ok,export_slacks=inspected['slacks'],export_worst_strictly_improved=bool(improves),accepted=good)
                        new_target,notes=strengthen(target,c,blocks,inspected['peaks'],inspected['slacks'],requirements,protocol['optional_margin_fractions'][margin_index]);record['feedback']=notes
                        changed=bool(np.any(new_target>target));target=new_target
                        if good:x=trial;current=inspected;accepted=True
                        # New export feedback means relinearize at last accepted x.
                        info['trials'].append(record)
                        if good or changed:break
                    else:info['trials'].append(record)
            info.update(accepted=accepted,targets_strengthened=changed);history.append(info)
            save(folder/'history.json',history)
            phase('proposal_result',case=id,iteration=iteration+1,accepted=accepted,targets_strengthened=changed)
            if not accepted and not changed:break
        values,_,_=p.evaluate(x,False);full=p.reference_residuals(p.motion(x));np.testing.assert_allclose(values,full,atol=1e-8,rtol=1e-8)
        take=folder/'candidate';shutil.copytree(current['path'],take)
        save(folder/'solver.json',dict(history=history,final_coordinates=x.tolist(),maximum_root_step_m=float(np.abs(x-p.start).max()),
             original_minimum_slack=float(values.min()),serialized_minimum_slack=float(current['serial'].min()),
             selected_export=str(current['path']),final_export_slacks=current['slacks'],requirements=requirements,optional_margin_fraction=protocol['optional_margin_fractions'][margin_index],quality_approved=False))
        phase('engine_check',case=id);passed,checks=engine_check(folder,id,take);assert passed
        for path,h in inputs.items():assert sha256(Path(path))==h,path
        verify_methods()
        screen=bool(min(current['slacks'].values())>=0 and current['serial'].min()>=0)
        record=dict(case=id,export_and_native_screen=screen,flags=current['flags'],engine_passed=passed,engine_checks=checks,
            initial_slacks=initial['slacks'],final_slacks=current['slacks'],serialized_minimum_slack=float(current['serial'].min()),quality_approved=False,
            files={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()})
        save(folder/'completion.json',record);results.append(record)
        phase('case_complete',case=id,screen=screen)
    save(output/'completion.json',dict(cases=[dict(case=r['case'],screen=r['export_and_native_screen'],engine_passed=r['engine_passed']) for r in results],
        inputs={str(p):sha256(p) for p in [output/'protocol.json',output/'historical-verification.json']},quality_approved=False))
    phase('complete')
def main():
    import argparse
    global suite, output, protocol, methods
    parser=argparse.ArgumentParser(description='Experimental export-feedback repair on the three declared contact-breadth cases. Creates a new output; never promotes motion quality.')
    parser.add_argument('--suite',type=Path,required=True,help='Completed contact-breadth-v1 study including batch-engine-followup-v2')
    parser.add_argument('--output',type=Path,required=True,help='New output directory under local reports; must not exist')
    args=parser.parse_args()
    destination=args.output.resolve()
    if not destination.is_relative_to((ROOT/'reports').resolve()):
        parser.error('Store generated study output under reports/')
    suite=args.suite.resolve()
    output=args.output.resolve();output.mkdir(exist_ok=False)
    worker=psutil.Process();save(output/'worker.json',dict(pid=worker.pid,created=worker.create_time()))
    methods={}
    (output/'implementation').mkdir()
    for path in (ROOT/'scripts').iterdir():
        if path.suffix not in ['.py','.gd']:continue
        shutil.copyfile(path,output/'implementation'/path.name);methods[path.name]=sha256(path)
    protocol=dict(cases=['wave-11','wave-22','crawl-22'],attempts=8,backtracks=4,trust_m=1e-5,
        maximum_optional_normalized_headroom=1e-4,geometric_room_fraction=.5,optional_margin_fractions=[1.,.1,.01,.001,0.],
        method='Actual NPZ/BVH/GLB export and full pin/floor/point/global/outside checks before accepting every proposal. '
          'Retain every previously passing native row and exported group, reject new body flags, strictly lower maximum '
          'normalized exported violation. Rejected exports can add or strengthen rate-group search targets from their '
          'measured proxy discrepancy, bounded by horizontal capacity; retry from last accepted state. '
          'On LP infeasibility reduce optional headroom along [1,.1,.01,.001,0], retaining the maximum observed discrepancy for every learned group. Original budgets and zero-slack acceptance remain unchanged. No quality approval.',
        script_sha256=sha256(Path(__file__)),implementation=methods,created_at=now(),quality_approved=False)
    save(output/'protocol.json',protocol)
    try:run()
    except BaseException as e:
        phase('failed',error=str(e),traceback=traceback.format_exc());raise


if __name__=="__main__":main()
