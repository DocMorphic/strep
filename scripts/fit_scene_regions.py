"""V14 experimental clip fitting for explicitly authored hand regions.

Uses source-relative hard edit budgets and witnesses fixed within each stage.
Every output remains a candidate until independent exported geometry review.
"""
import argparse
import copy
import shutil
import time
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET,make_preview
from gltf_tools import write_glb
from compile_scene_regions import compile_regions
from scene_solver_context import compile_context
from region_contact_objective import RegionObjective
from support_contact_v8 import refine,CONFIG
from scene_constraints import evaluate
from action_worker_lock import worker_lock


def run(scene_path,actor,ids,output,stages=3,iterations=40,seconds=600,region_loss='worst',full_object_skin=False,object_constraint_mode='maximum',region_constraint_mode='penalty',initialization=None,witness_mode='frozen',object_clearance_margin_m=0.,contact_gap_margin_m=0.,export_rate_guard=False,export_acceleration_margin_fraction=0.,skin_backend="gather",root_coordinate_mode="legacy"):
    if root_coordinate_mode not in ["legacy","scaled_initial"]:raise ValueError("Unknown root coordinate mode")
    if type(seconds) not in [int,float] or not np.isfinite(seconds) or seconds<=0:
        raise ValueError('Positive finite time budget required')
    scene_path,output=Path(scene_path).resolve(),Path(output).resolve()
    if not output.is_relative_to(ROOT.resolve()):raise ValueError('Fitting output must stay within project for scene asset references')
    data=read(scene_path);scene=data.get('scene',data);skin=dict(np.load(ASSET,allow_pickle=False))
    package=compile_regions(scene,actor,ids,skin)
    source_path=ROOT/scene['actors'][actor]['motion']
    source=dict(np.load(source_path,allow_pickle=False))
    warm_start=None
    if initialization is not None:
        from audit_scene_region_fit import edit_bounds,native_fk_error
        from inspect_motion import skeleton_metadata,validate_motion
        initialization=Path(initialization).resolve()
        warm_start=dict(np.load(initialization,allow_pickle=False))
        validate_motion(warm_start,30)
        names,parents,_=skeleton_metadata(77)
        if not edit_bounds(source,warm_start,names,CONFIG)[0] or native_fk_error(source,warm_start,parents)>3e-6:
            raise ValueError('Initialization violates original clip edit budgets or bone offsets')
    plain=copy.deepcopy(scene)
    for c in plain['contacts']:c.pop('region_contact',None)
    context=compile_context(plain,actor,ids,skin)
    # Regional normals are enforced on the complete authored patch in the new
    # objective. Legacy anchor-adjacent normals represent a different request.
    context['normals']=[]
    implementation=['fit_scene_regions.py','region_contact_objective.py','compile_scene_regions.py',
        'scene_region_contact.py','scene_constraints.py','scene_solver_context.py','support_contact_v8.py',
        'support_contact_v5.py','support_contact_v4.py','support_contact_v3.py','support_contact_v2.py',
        'support_contact.py','floor_contact.py','body_contact.py','contact_spec.py','object_geometry.py',
        'build_soma_preview.py','inspect_motion.py','compile_scene_contacts.py','scene_fit_initialization.py','audit_scene_region_fit.py','export_motion_sampling.py','export_rate_objective.py','linear_skin_operator.py','bounded_root_coordinates.py']
    inputs={str(scene_path):sha256(scene_path),str(ASSET):sha256(ASSET)}
    inputs.update({str(ROOT/r['path']):r['sha256'] for r in package['source_provenance']['sources'].values()})
    if initialization is not None:inputs[str(initialization)]=sha256(initialization)
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    hashes={name:sha256(ROOT/'scripts'/name) for name in implementation}
    for name in implementation:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    shutil.copyfile(source_path,output/'source-motion.npz')
    save(output/'authored-scene.json',scene);save(output/'region-constraints.json',package)
    save(output/'protocol.json',dict(at=now(),solver_version=14,actor=actor,contact_ids=ids,inputs=inputs,
        implementation=hashes,stages=stages,iterations=iterations,seconds_budget=seconds,region_loss=region_loss,full_object_skin=full_object_skin,object_constraint_mode=object_constraint_mode,region_constraint_mode=region_constraint_mode,witness_mode=witness_mode,object_clearance_margin_m=object_clearance_margin_m,contact_gap_margin_m=contact_gap_margin_m,initialization=str(initialization) if initialization is not None else None,
        export_rate_guard=export_rate_guard,export_acceleration_margin_fraction=export_acceleration_margin_fraction,
        skin_backend=skin_backend,root_coordinate_mode=root_coordinate_mode,source_relative_bounds=True,config=CONFIG,quality_approved=False,
        scope='Whole-clip source-relative bounded edits. Region witnesses fixed per stage; optional reselection logged. No release guard added implicitly, no partner solve or feasibility guarantee.'))
    started=time.monotonic();history=[]
    def progress(row):
        history.append(dict(seconds=time.monotonic()-started,**row))
        save(output/'progress.json',dict(status='running',history=history))
        print(dict(seconds=round(time.monotonic()-started,2),**row),flush=True)
        if time.monotonic()-started>seconds:raise TimeoutError('Declared fitting time budget exceeded')
    try:
        with worker_lock():
            objective=RegionObjective(package,source,skin,region_loss,region_constraint_mode,witness_mode,contact_gap_margin_m)
            result,recipe=refine(source,source,skin,progress,source,package['anchor_subproblem'],context,
                finger_edits=True,physical_finger_parameters=True,object_inequalities=True,
                outer_stage_count=stages,region_fitting=objective,iteration_count=iterations,full_object_skin=full_object_skin,object_constraint_mode=object_constraint_mode,warm_start=warm_start,object_clearance_margin_m=object_clearance_margin_m,export_rate_guard=export_rate_guard,export_acceleration_margin_fraction=export_acceleration_margin_fraction,skin_backend=skin_backend,root_coordinate_mode=root_coordinate_mode)
        for path,digest in inputs.items():
            if sha256(path)!=digest:raise ValueError('Fitting input changed')
        for name,digest in hashes.items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Fitting implementation changed')
        np.savez(output/'motion.npz',**result);save(output/'recipe.json',recipe)
        for label,motion in [('source',source),('candidate',result)]:
            doc,binary,_,_=make_preview(skin,motion,np.zeros(3),repeat=False)
            write_glb(output/(label+'.glb'),doc,binary)
        candidate=copy.deepcopy(scene)
        candidate['actors'][actor]['motion']=(output/'motion.npz').relative_to(ROOT).as_posix()
        candidate['actors'][actor]['source_sha256']=sha256(output/'motion.npz')
        save(output/'candidate-scene.json',candidate)
        save(output/'source-evaluation.json',evaluate(scene,skin))
        assessment=evaluate(candidate,skin);save(output/'candidate-evaluation.json',assessment)
        save(output/'result.json',dict(at=now(),status='complete',seconds=time.monotonic()-started,
            candidate_sha256=sha256(output/'motion.npz'),candidate_glb_sha256=sha256(output/'candidate.glb'),
            source_glb_sha256=sha256(output/'source.glb'),recipe_sha256=sha256(output/'recipe.json'),
            authored_scene_sha256=sha256(output/'authored-scene.json'),
            protocol_sha256=sha256(output/'protocol.json'),quality_approved=False,
            contact_passes={c['id']:c['all_requested_frames_within_tolerance'] for c in assessment['contacts']}))
        print(dict(status='complete',contacts=[(c['id'],c['all_requested_frames_within_tolerance']) for c in assessment['contacts']]),flush=True)
    except Exception as exc:
        save(output/'result.json',dict(at=now(),status='failed',error=str(exc),seconds=time.monotonic()-started,quality_approved=False))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('--actor',required=True)
    p.add_argument('--contact',action='append',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stages',type=int,default=3);p.add_argument('--iterations',type=int,default=40);p.add_argument('--seconds',type=float,default=600)
    p.add_argument('--region-loss',choices=['worst','balanced'],default='worst')
    p.add_argument('--full-object-skin',action='store_true')
    p.add_argument('--object-constraint-mode',choices=['maximum','per_vertex'],default='maximum')
    p.add_argument('--region-constraint-mode',choices=['penalty','augmented'],default='penalty')
    p.add_argument('--initialization',type=Path)
    p.add_argument('--witness-mode',choices=['frozen','stage_refresh'],default='frozen')
    p.add_argument('--object-clearance-margin-m',type=float,default=0.)
    p.add_argument('--contact-gap-margin-m',type=float,default=0.)
    p.add_argument('--export-rate-guard',action='store_true')
    p.add_argument('--export-acceleration-margin-fraction',type=float,default=0.)
    p.add_argument('--skin-backend',choices=['gather','sparse'],default='gather')
    p.add_argument('--root-coordinate-mode',choices=['legacy','scaled_initial'],default='legacy')
    a=p.parse_args();run(a.scene,a.actor,a.contact,a.output,a.stages,a.iterations,a.seconds,a.region_loss,a.full_object_skin,a.object_constraint_mode,a.region_constraint_mode,a.initialization,a.witness_mode,a.object_clearance_margin_m,a.contact_gap_margin_m,a.export_rate_guard,a.export_acceleration_margin_fraction,a.skin_backend,a.root_coordinate_mode)
