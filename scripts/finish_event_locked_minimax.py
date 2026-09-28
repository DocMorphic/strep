"""Conditionally export a completed minimax study and independently audit it."""
import argparse
from pathlib import Path
import shutil
import time
import traceback
import psutil
from strep import ROOT,read,save,sha256,now


def run(study, output):
    study,output=study.resolve(),output.resolve()
    if output.exists():raise ValueError('Preserve prior export attempt')
    owner=read(study/'request.json');source=Path(owner['study'])
    names=set(owner['implementation'])|{'finish_event_locked_minimax.py','finish_bounded_surface_path.py',
        'audit_paired_guides.py','bounded_pose_ik.py','motion_edit_bounds.py','rig_asset.py','rig_clip_import.py',
        'rig_loop.py','verify_rig_clearance.py','inspect_motion.py','run_godot_scene_import.py',
        'godot_scene_import_audit.gd','convex_partner_surface.py','verify_palm_region.py'}
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in sorted(names):shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    proc=psutil.Process()
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),study=str(study),
        study_request_sha256=sha256(study/'request.json'),wait_pid=owner['pid'],wait_created=owner['created'],
        frames=[i*.5 for i in range(299)],planned_engine_actor_frames=600,
        implementation={n:sha256(output/'implementation'/n) for n in sorted(names)},quality_approved=False,
        scope='Conditional export of a finite minimax development study with locally accepted steps. '
        'Raw and candidate, decoded hard bounds, actual engine import and full integer/half-frame vertex geometry. '
        'No selection for product use, new inference or motion-quality approval.')
    save(output/'request.json',request)
    def phase(status,**details):
        save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    def implementation_check():
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:
                raise ValueError('Implementation changed: '+name)
    try:
        phase('waiting_for_exact_minimax_owner')
        while True:
            try:
                p=psutil.Process(owner['pid'])
                if p.create_time()!=owner['created']:raise ValueError('Minimax PID reused')
            except psutil.NoSuchProcess:break
            time.sleep(5)
        if read(study/'pipeline.json')['status']!='complete':raise ValueError('Minimax study incomplete')
        if sha256(study/'request.json')!=request['study_request_sha256']:raise ValueError('Minimax request changed')
        for path,digest in owner['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Minimax input changed')
        implementation_check()
        done=read(study/'completion.json')
        for name in ['summary','parameters','history']:
            if sha256(study/(name+'.json'))!=done[name+'_sha256']:raise ValueError('Completed study changed')
        if done['accepted_rounds']==0:
            save(output/'completion.json',dict(at=now(),exported=False,reason='no_locally_accepted_step',quality_approved=False))
            phase('complete_no_export');return
        # Prepare explicit inputs for the unchanged full exporter. No synthetic
        # process/pipeline state is created for this data-only adapter directory.
        phase('preparing_export_inputs')
        adapter=output/'export-input';adapter.mkdir()
        for name in ['initial-parameters.json','palm-region.json','A-source-local.npz','B-source-local.npz']:
            shutil.copyfile(source/name,adapter/name)
        for name in ['parameters.json','history.json']:shutil.copyfile(study/name,adapter/name)
        recipe=read(source/'request.json')
        save(adapter/'source-recipe.json',recipe)
        save(adapter/'provenance.json',dict(minimax_request_sha256=sha256(study/'request.json'),
             minimax_completion_sha256=sha256(study/'completion.json'),original_recipe_sha256=sha256(source/'request.json'),
             selection='Final locally accepted minimax study step; independent export evaluation only.',quality_approved=False))
        export=output/'export';export.mkdir()
        validation=dict(frames=request['frames'],quality_approved=False,parent_request_sha256=sha256(output/'request.json'))
        save(export/'request.json',validation)
        from threadpoolctl import threadpool_limits
        from finish_bounded_surface_path import complete
        with threadpool_limits(limits=1):
            complete(adapter,export,recipe,validation,lambda status,**details:phase('export_'+status,**details))
        # Recheck the claimed event lock after glTF serialization/decoding.
        from rig_asset import RigAsset
        from rig_clip_import import AnimationSampler
        import numpy as np
        component=read(Path(owner['component_audit'])/'summary.json')
        original_export=Path(read(Path(component['study'])/'request.json')['audit'])
        locked=[]
        for label in ['A','B']:
            paths=[original_export/'assets'/label/'candidate/character.glb',export/'assets'/label/'candidate/character.glb']
            vertices=[]
            for path in paths:
                rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
                vertices.append(rig.vertices(sampler.sample(float(np.float32(75/30)))))
            error=float(np.abs(vertices[1]-vertices[0]).max())
            if error>1e-6:raise ValueError('Decoded event geometry changed')
            locked.append(dict(actor=label,source_sha256=sha256(paths[0]),candidate_sha256=sha256(paths[1]),max_vertex_error_m=error))
        save(output/'event-preservation.json',dict(rows=locked,tolerance_m=1e-6,quality_approved=False))
        implementation_check()
        save(output/'completion.json',dict(at=now(),exported=True,engine_actor_frames=600,samples_per_scene=299,
             export_completion_sha256=sha256(export/'completion.json'),event_preservation_sha256=sha256(output/'event-preservation.json'),
             minimax_completion_sha256=sha256(study/'completion.json'),quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.study,args.output)
