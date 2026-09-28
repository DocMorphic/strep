"""Compare complete exported motion after changing distance evaluation only."""
import argparse
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now
from compare_partner_paths import load
from compare_enriched_partner_path import FIXED,changes


def matching_protocol(a,b):
    for key in FIXED+['frames','sampling_plan','selection_screen','restoration','restoration_slack_is_acceptance_tolerance']:
        if a['request'][key]!=b['request'][key]:raise ValueError('Matched protocol differs: '+key)
    if a['initial']!=b['initial']:raise ValueError('Initial parameters differ')
    if a['request']['method']!='audit_enriched_screen_preserving_steps' or b['request']['method']!='projected_fractional_surface_distances':raise ValueError('Unexpected comparison methods')
    if a['variants']['raw']['curve']!=b['variants']['raw']['curve']:raise ValueError('Raw full-clock geometry differs')
    for actor in ['A','B']:
        for name in ['character.glb','motion.npz']:
            key='assets/'+actor+'/raw/'+name
            if a['manifest']['assets'][key]!=b['manifest']['assets'][key]:raise ValueError('Raw assets differ')


def compare(before,after,output):
    a,b=load(before),load(after);matching_protocol(a,b)
    parent=Path(read(Path(before)/'request.json')['study']);candidate=Path(read(Path(after)/'request.json')['study'])
    if Path(b['request']['matched_study']).resolve()!=parent.resolve() or b['request']['matched_request_sha256']!=sha256(parent/'request.json') or b['request']['matched_initial_parameters_sha256']!=sha256(parent/'initial-parameters.json'):raise ValueError('Projection trial parent differs')
    benchmark=Path(b['request']['projection_benchmark']);consumed=read(candidate/'projection-proof.json')
    if b['request']['projection_request_sha256']!=sha256(benchmark/'request.json') or consumed['completion_sha256']!=sha256(benchmark/'completion.json') or consumed['results_sha256']!=sha256(benchmark/'results.json'):raise ValueError('Consumed derivative proof differs')
    curves={'raw':a['variants']['raw']['curve'],'enriched':a['variants']['candidate']['curve'],'projected':b['variants']['candidate']['curve']}
    rows=[]
    for name,item in [('raw',a['variants']['raw']),('enriched',a['variants']['candidate']),('projected',b['variants']['candidate'])]:
        curve,event=item['curve'],item['event']
        rows.append(dict(method=name,max_body_depth_m=curve['max_depth_m'],peak_frame=curve['peak_frame'],failed_samples=len(curve['failed_frames']),floor_max_m=curve['floor_max_m'],event_gap_m=event['gap_m'],opposing_normal_degrees=event['region']['opposing_normal_degrees']))
    save(output/'curves.json',curves)
    save(output/'summary.json',dict(at=now(),rows=rows,full_clock_changes=changes(curves['enriched'],curves['projected'],a['request']['frames']),curves_sha256=sha256(output/'curves.json'),completions={name:dict(folder=item['folder'],sha256=item['completion_sha256']) for name,item in [('enriched',a),('projected',b)]},quality_approved=False,
        scope='Same initial motion, fitting clock, objectives, bounds and iteration limits; projected fractional distance evaluation. Every integer/half-frame exported sample and engine actor retained. Numerical derivative agreement need not produce bitwise-identical nonlinear optimization. No continuous collision, physical, semantic or human quality approval.'))


def run(before,after,output):
    before,after,output=[Path(p).resolve() for p in [before,after,output]]
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    names=['compare_projected_partner_path.py','compare_enriched_partner_path.py','compare_partner_paths.py','contact_witness_clock.py','audit_paired_guides.py','strep.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc=psutil.Process();owner=read(after/'request.json')
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),before=str(before),after=str(after),before_request_sha256=sha256(before/'request.json'),after_request_sha256=sha256(after/'request.json'),owner=dict(pid=owner['pid'],created=owner['created']),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('waiting_for_exact_projected_geometry_owner');await_owner(request['owner'],'pid','created',after,{'complete'})
        if sha256(before/'request.json')!=request['before_request_sha256'] or sha256(after/'request.json')!=request['after_request_sha256']:raise ValueError('Completion request changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Frozen comparison changed')
        phase('comparing');compare(before,after,output)
        save(output/'completion.json',dict(at=now(),summary_sha256=sha256(output/'summary.json'),quality_approved=False));phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['before','after','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.before,a.after,a.output)
