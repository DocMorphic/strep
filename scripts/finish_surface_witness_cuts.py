"""Conditionally export an accepted witness-cut step and audit the whole clip."""
import argparse
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve();recipe=read(study/'request.json')
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    names=['finish_surface_witness_cuts.py','finish_bounded_surface_path.py','audit_paired_guides.py','bounded_pose_ik.py','motion_edit_bounds.py',
        'rig_asset.py','rig_clip_import.py','rig_loop.py','verify_rig_clearance.py','inspect_motion.py','run_godot_scene_import.py',
        'godot_scene_import_audit.gd','convex_partner_surface.py','verify_palm_region.py','strep.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc=psutil.Process();request=dict(at=now(),pid=proc.pid,created=proc.create_time(),study=str(study),study_request_sha256=sha256(study/'request.json'),
        owner=dict(pid=recipe['pid'],created=recipe['created']),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Wait for exact witness-cut trial. Export only a step accepted by its unchanged fitting guard. If none is accepted, record a skipped export without quality approval. Accepted exports receive original/candidate full299-time geometry, decoded limits and600actual engine actor-frames.')
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('waiting_for_exact_witness_trial');await_owner(request['owner'],'pid','created',study,{'complete_pending_export_and_full_geometry','complete_no_accepted_step'})
        if sha256(study/'request.json')!=request['study_request_sha256']:raise ValueError('Witness trial request changed')
        completion=read(study/'completion.json')
        if completion['history_sha256']!=sha256(study/'history.json') or completion['parameters_sha256']!=sha256(study/'parameters.json'):
            raise ValueError('Completed witness trial changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Export implementation changed')
        if not completion['accepted_step']:
            save(output/'completion.json',dict(at=now(),exported=False,reason=completion['reason'],study_completion_sha256=sha256(study/'completion.json'),quality_approved=False))
            phase('complete_no_accepted_step_to_export');return
        if read(study/'parameters.json')['selection']!='accepted_step':raise ValueError('Selected parameters are not an accepted step')
        history=read(study/'history.json')['iterations']
        if not history[-1]['decision']['accepted']:raise ValueError('Final retained step was rejected')
        phase('exporting_and_auditing')
        from finish_bounded_surface_path import run as finish
        finish(study,output/'export')
        if read(output/'export/pipeline.json')['status']!='complete':raise ValueError('Full export audit incomplete')
        save(output/'completion.json',dict(at=now(),exported=True,study_completion_sha256=sha256(study/'completion.json'),
            export_completion_sha256=sha256(output/'export/completion.json'),quality_approved=False))
        phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
