"""Compare the complete exported clock of a finished frame-guarded partner trial."""
import argparse
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now
from audit_paired_guides import await_owner
from compare_partner_paths import load,full_curve
from compare_enriched_partner_path import changes


def run(before,study,output):
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    owner=read(study/'request.json');p=psutil.Process()
    names=['verify_frame_guarded_partner.py','audit_paired_guides.py','compare_partner_paths.py',
           'compare_enriched_partner_path.py','contact_witness_clock.py','strep.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),pid=p.pid,created=p.create_time(),before=str(before),study=str(study),
        owner=dict(pid=owner['pid'],created=owner['created']),study_request_sha256=sha256(study/'request.json'),
        before_completion_sha256=sha256(before/'completion.json'),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,**kw));print(status,kw,flush=True)
    try:
        phase('waiting_for_exact_trial_owner')
        await_owner(request['owner'],'pid','created',study,{'complete','complete_no_candidate'})
        assert sha256(study/'request.json')==request['study_request_sha256']
        assert sha256(before/'completion.json')==request['before_completion_sha256']
        for name,h in owner['inputs'].items():assert sha256(name)==h
        for name,h in owner['implementation'].items():assert sha256(study/'implementation'/name)==h
        done=read(study/'completion.json')
        if not done['accepted']:
            save(output/'completion.json',dict(at=now(),exported=False,reason='No locally accepted candidate; all recorded failures retained',study_completion_sha256=sha256(study/'completion.json'),quality_approved=False))
            phase('complete_no_candidate');return
        phase('verifying_full_export')
        a=load(before);export=study/'export';complete=read(export/'completion.json')
        assert sha256(export/'completion.json')==done['export_completion_sha256']
        for name,key in [('manifest.json','manifest_sha256'),('source-evidence.json','source_evidence_sha256'),('engine-audit/verification.json','engine_sha256'),('geometry-summary.json','geometry_summary_sha256')]:assert sha256(export/name)==complete[key]
        assert complete['engine_actor_frames']==600 and complete['samples_per_scene']==299 and complete['scenes']==2
        evidence=read(export/'source-evidence.json')
        for name,key in [('parameters.json','parameters_sha256'),('initial-parameters.json','initial_parameters_sha256'),('history.json','history_sha256')]:assert sha256(study/name)==evidence[key]
        assert a['initial']==read(study/'initial-parameters.json')
        assert Path(owner['source']).resolve()==Path(read(before/'request.json')['study']).resolve()
        manifest=read(export/'manifest.json')
        for name,item in manifest['assets'].items():
            path=(export/name).resolve();assert path.is_relative_to(export) and sha256(path)==item['sha256']
        for actor in ['A','B']:
            for name in ['character.glb','motion.npz']:
                key='assets/'+actor+'/raw/'+name;assert manifest['assets'][key]==a['manifest']['assets'][key]
            bounds=read(export/(actor+'-decoded-bounds.json'))
            assert bounds['bounds']['passed'] and bounds['bounds']['samples']==299
        engine=read(export/'engine-audit/verification.json')['checks']
        assert len(engine)==4 and {(c['scene_id'],c['actor']) for c in engine}=={(v+'-seed-1301',actor) for v in ['raw','candidate'] for actor in ['A','B']}
        for c in engine:
            variant=c['scene_id'].split('-')[0];prefix='assets/'+c['actor']+'/'+variant+'/'
            assert c['frames']==150 and c['glb_sha256']==manifest['assets'][prefix+'character.glb']['sha256'] and c['source_sha256']==manifest['assets'][prefix+'motion.npz']['sha256']
        variants={}
        for row in read(export/'geometry-summary.json')['rows']:
            path=export/'geometry'/row['variant']/'samples.json';assert sha256(path)==row['samples_sha256']
            curve=full_curve(read(path)['rows']);assert curve['max_depth_m']==row['max_depth_m'] and curve['floor_max_m']==row['floor_max_depth_m'] and curve['failed_frames']==row['collision_failed_frames']
            variants[row['variant']]=dict(curve=curve,event=row['event'])
        assert variants['raw']['curve']==a['variants']['raw']['curve']
        old,new=a['variants']['candidate']['curve'],variants['candidate']['curve']
        delta=changes(old,new,owner['frames'])
        cap_pass=all(y<=max(.005,x)+(1e-9 if x>.005 else 0.) for x,y in zip(old['body_depth_m'],new['body_depth_m']))
        save(output/'curves.json',dict(before=old,after=new,raw=variants['raw']['curve']))
        save(output/'summary.json',dict(at=now(),before_peak_m=old['max_depth_m'],after_peak_m=new['max_depth_m'],
            full_clock_cap_pass=cap_pass,full_clock_changes=delta,before_event=a['variants']['candidate']['event'],after_event=variants['candidate']['event'],
            event_preservation=done['event_preservation'],quality_approved=False,
            scope='All299 exported key/midpoint samples against initial edited scene,600engineactorframes, raw identity and hashes. No continuous collision, physical or human approval.'))
        for name,h in request['implementation'].items():assert sha256(ROOT/'scripts'/name)==h and sha256(output/'implementation'/name)==h
        save(output/'completion.json',dict(at=now(),exported=True,summary_sha256=sha256(output/'summary.json'),curves_sha256=sha256(output/'curves.json'),quality_approved=False))
        phase('complete')
    except BaseException as e:phase('failed',error=str(e),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['before','study','output']:p.add_argument(n,type=Path)
    a=p.parse_args();run(a.before.resolve(),a.study.resolve(),a.output.resolve())
