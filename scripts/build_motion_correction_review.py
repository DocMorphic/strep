"""Review raw, contact-only and two pose-guided native correction paths."""
import os
import shutil
from strep import ROOT,read,save,sha256


def build():
    out=ROOT/'reports/motion-correction-v2';old=ROOT/'reports/motion-correction-v1'
    metrics={(row['case'],row['mode']):row['metrics'] for folder in (old,out) for row in read(folder/'verification.json')['cases']}
    cases=[]
    for case in read(out/'design.json')['cases']:
        variants={}
        for mode,label,folder in [('raw','Raw generation',old),('contact_only','Contact cleanup only',old),('guided','Pose + predicted contacts',out),('guided_pose_only','Pose fitting only',out)]:
            path=folder/case/mode/'soma.glb'
            variants[mode]=dict(label=label,path=os.path.relpath(path,out).replace('\\','/'),sha256=sha256(path),metrics=metrics[case,mode])
        record=read(out/case/'guided/record.json')
        note='Both guided versions fit the SOMA30 boundary poses within 0.004 mm. All corrected variants still fail the 5 mm native-skin floor screen; no quality approval or default change.'
        if case.startswith('dance'):note+=' These exact boundary poses themselves penetrate the native skin floor by about 7.3 mm.'
        cases.append(dict(id=case,label=case,frames=record['frames'],root_node=1,camera_height_m=.9,variants=variants,status=note,audit='verification.json',package='design.json',studio='http://127.0.0.1:8768/studio?rig_job='+record['source_job']))
    save(out/'review.json',dict(cases=cases,quality_approved=False))
    page=(ROOT/'scripts/clearance-review.html').read_text(encoding='utf8')
    page=page.replace('Strep · Surface clearance study','Strep · Native motion correction')
    page=page.replace('Surface clearance on your character','Exact poses do not guarantee clean contact')
    page=page.replace('Same generated motion, different correction objectives. Compare foot clearance and sliding together. Failed raw pose guides and original frames outside the editable section remain unchanged.','Unchanged saved model outputs, processed with NVIDIA’s official correction code. Compare pose fitting, floor penetration and sliding at the same frame. No training or new inference.')
    page=page.replace("key==='candidate'","key==='guided_pose_only'")
    page=page.replace("['Editable-section floor depth',v=>mm(v.metrics.editable_floor_depth_max_m)]","['Boundary pose error (SOMA30)',v=>(v.metrics.anchor_max_position_error_m*1000).toFixed(3)+' mm']")
    page=page.replace("['Largest adjacent joint rotation',v=>v.metrics.local_rotation_step_max_degrees.toFixed(2)+'°']","['Largest adjacent joint rotation',v=>v.metrics.local_rotation_step_max_degrees.toFixed(2)+'°'],['Largest boundary joint step',v=>v.metrics.boundary_eight_frame_step_max_degrees.toFixed(2)+'°']")
    page=page.replace('Case package','Experiment design')
    page=page.replace('<a href="../godot-rig-clearance-v3/verification.json">Godot verification</a>','<a href="rebuild-provenance.json">Native build provenance</a><a href="../motion-correction-v1/verification.json">Contact-only audit</a>')
    page=page.replace('Original character licenses and source files are retained in each case package. Grey material is preview-only. No independent animator approval.','Native preview: NVIDIA Kimodo, Apache-2.0. <a href="SOMA-preview-LICENSE.txt">Preview license</a> · <a href="Kimodo-model-LICENSE.txt">Checkpoint license</a>. Predicted contact labels are unconfirmed; “Pose fitting only” suppresses them inside the solver. No independent animator approval.')
    (out/'viewer.html').write_text(page,encoding='utf8')
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',out/'SOMA-preview-LICENSE.txt')
    shutil.copyfile(ROOT/'models/checkpoints/Kimodo-SOMA-RP-v1.1/LICENSE',out/'Kimodo-model-LICENSE.txt')
    save(out/'decision.json',dict(production_changed=False,quality_approved=False,exact_boundary_component_verified=True,contact_cleanup_not_approved=True,next='Combine exact pose fitting with geometry-aware contact correction and retain boundary feasibility checks; retarget the exact-pose candidates and compare splice derivatives. Broaden held-out actions after measured regressions are addressed.'))


if __name__=='__main__':build()
