"""Bind paired floor-valid fits and independently check exported finger budgets."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from inspect_motion import skeleton_metadata


def angular_steps(local):
    delta=local[:-1].transpose(0,1,3,2)@local[1:]
    return np.rad2deg(Rotation.from_matrix(delta.reshape(-1,3,3)).magnitude()).reshape(delta.shape[:2])*30


def export_budget(study):
    fit=study/'fit';summary=read(fit/'summary.json');trial=summary['trials'][0];scene=read(fit/trial['id']/'candidate.json')['scene']
    if set(scene['actors'])!={'A'}:raise ValueError('One native actor expected')
    entry=scene['actors']['A'];asset=fit/entry['preview_glb'];doc,binary=read_glb(asset);sampler=AnimationSampler(doc,binary,0)
    nodes=doc['skins'][0]['joints'];names,parents,_=skeleton_metadata(77)
    if [doc['nodes'][j]['name'] for j in nodes]!=names:raise ValueError('Bone mapping mismatch')
    worlds=np.array([sampler.sample(float(np.float32(f/30)))[nodes] for f in range(scene['frame_count'])])
    local=worlds[:,:,:3,:3].copy()
    for j,p in enumerate(parents):
        if p>=0:local[:,j]=worlds[:,p,:3,:3].transpose(0,2,1)@worlds[:,j,:3,:3]
    folder=fit/'assets'/trial['id']/'A';previous=dict(np.load(folder/'previous-motion.npz',allow_pickle=False))
    recipe=read(folder/'recipe.json')['contact'];relative=previous['local_rot_mats'].transpose(0,1,3,2)@local
    angles=np.rad2deg(Rotation.from_matrix(relative.reshape(-1,3,3)).magnitude()).reshape(relative.shape[:2])
    fingers=[i for i,n in enumerate(names) if any(n.startswith(side+'Hand'+finger) for side in ['Left','Right'] for finger in ['Thumb','Index','Middle','Ring','Pinky'])]
    declared=recipe.get('finger_edits',{}).get('budgets_degrees',{})
    controlled={names[j] for j in fingers if not names[j].endswith('End')}
    if declared and set(declared)!=controlled:raise ValueError('Incomplete finger budget declaration')
    rows=[dict(joint=names[j],limit_degrees=declared.get(names[j],0.),maximum_edit_degrees=float(angles[:,j].max())) for j in fingers]
    for row in rows:
        if row['maximum_edit_degrees']>row['limit_degrees']+1e-4:raise ValueError('Exported finger edit budget exceeded')
    before=angular_steps(previous['local_rot_mats']);after=angular_steps(local)
    return dict(glb_sha256=sha256(asset),previous_motion_sha256=sha256(folder/'previous-motion.npz'),finger_joints=rows,all_finger_budgets_passed=True,
        maximum_finger_angular_speed_before_degrees_s=float(before[:,fingers].max()),maximum_finger_angular_speed_after_degrees_s=float(after[:,fingers].max()),
        scope='Independent exported local rotations versus the body-preprocessed input. Edit budgets only; anatomical validity, self-collision and allowable angular speeds are not established.')


def compare(control,candidate,output):
    control=Path(control).resolve();candidate=Path(candidate).resolve();output=Path(output).resolve()
    protocols=[read(p/'protocol.json') for p in [control,candidate]]
    versions=[p['solver_version'] for p in protocols]
    if versions not in [[8,9],[9,10],[10,11],[11,12]]:raise ValueError('Expected adjacent V8 through V12 fits')
    sources=[read(p/'source.json')['scene'] for p in [control,candidate]]
    if sources[0]!=sources[1]:raise ValueError('Fits do not share the exact source scene')
    if versions in [[9,10],[10,11],[11,12]]:
        folders=[]
        for study in [control,candidate]:
            trial=read(study/'fit/summary.json')['trials'][0]['id'];folders.append(study/'fit/assets'/trial/'A')
        for filename in ['limb-motion.npz','previous-motion.npz']:
            a=dict(np.load(folders[0]/filename,allow_pickle=False));b=dict(np.load(folders[1]/filename,allow_pickle=False))
            if set(a)!=set(b) or any(not np.array_equal(a[k],b[k]) for k in a):raise ValueError('Preprocessed input differs: '+filename)
        specs=[read(folder/'contact-spec.json') for folder in folders]
        if specs[0]!=specs[1]:raise ValueError('Authored contact specifications differ')
        contexts=[read(folder/'scene-context.json') for folder in folders]
        recipes=[read(folder/'recipe.json')['contact'] for folder in folders]
        configs=[recipe['config'].copy() for recipe in recipes]
        if versions==[9,10]:configs[1].pop('finger_parameter_units')
        elif versions==[10,11]:
            from scene_release_guards import compile_release_guards,extend_solver_spec
            if configs[1].pop('release_endpoint_guards') is not True:raise ValueError('Release guards not enabled')
            ids=[c['id'] for c in sources[1]['contacts'] if c['actor']=='A']
            expected=compile_release_guards(sources[1],'A',ids)
            if contexts[1].pop('release_guards')!=expected:raise ValueError('Release targets do not match authored scene')
            guard_recipe=recipes[1]['release_endpoint_guards']
            if guard_recipe['guards']!=expected or guard_recipe['solver_contact_spec']!=extend_solver_spec(specs[1],expected):raise ValueError('Effective solver track mismatch')
        else:
            if configs[1].pop('object_collision_mode')!='per_frame_max_inequality':raise ValueError('Expected signed object inequalities')
            for field in ['selected_vertices','release_endpoint_guards','finger_edits']:
                a=recipes[0][field];b=recipes[1][field]
                if field=='finger_edits':
                    a={k:v for k,v in a.items() if k!='measured_max_degrees'};b={k:v for k,v in b.items() if k!='measured_max_degrees'}
                if a!=b:raise ValueError('Object comparison changed '+field)
        if contexts[0]!=contexts[1]:raise ValueError('Base scene context differs')
        if configs[0]!=configs[1]:raise ValueError('Comparison changes unrelated objective or budget settings')
    output.mkdir(parents=True,exist_ok=False);rows=[]
    for study,protocol in zip([control,candidate],protocols):
        if read(study/'pipeline.json')['status']!='complete':raise ValueError('Fit incomplete')
        audit=Path(str(study)+'-audit');engine=Path(str(study)+'-engine')
        verification=read(audit/'verification.json');imported=read(engine/'verification.json')
        if verification['study_protocol_sha256']!=sha256(study/'protocol.json'):raise ValueError('Dense audit belongs to a different fit')
        if verification['fit_summary_sha256']!=sha256(study/'fit/summary.json'):raise ValueError('Dense fit summary binding mismatch')
        budget=export_budget(study)
        checks=[c for c in imported['checks'] if c['scene_id'].endswith('-candidate')]
        if len(checks)!=1 or checks[0]['glb_sha256']!=budget['glb_sha256']:raise ValueError('Candidate engine proof mismatch')
        a=verification['variants']['candidate']['A']
        if a['glb_sha256']!=budget['glb_sha256']:raise ValueError('Dense audit candidate differs from current export')
        failures=[]
        if any(c['samples_within_30mm']!=c['samples'] for c in a['contacts']):failures.append('scene_contact')
        if any(c['samples_within_5mm']!=c['samples'] for c in a['contacts']):failures.append('solver_contact')
        if any(c['samples_within_15degrees']!=c['samples'] for c in a['contacts']):failures.append('palm_orientation')
        if any(o['maximum_skin_vertex_depth_m']>.01 for o in a['objects'].values()):failures.append('skin_object_depth')
        if a['maximum_floor_depth_m']>.01:failures.append('skin_floor_depth')
        if any(o['maximum_depth_m']>.01 for o in verification['authored_object_floor'].values()):failures.append('authored_object_floor')
        rows.append(dict(solver_version=protocol['solver_version'],study=study.relative_to(ROOT).as_posix(),audit_sha256=sha256(audit/'verification.json'),engine_sha256=sha256(engine/'verification.json'),
            failed_screens=failures,dense_candidate=a,finger_budget=budget,quality_approved=False))
    before,after=[r['dense_candidate'] for r in rows]
    changes=dict(maximum_joint_acceleration_m_s2=after['maximum_joint_acceleration_m_s2']-before['maximum_joint_acceleration_m_s2'],
        object_depth_m={name:after['objects'][name]['maximum_skin_vertex_depth_m']-obj['maximum_skin_vertex_depth_m'] for name,obj in before['objects'].items()},contacts=[])
    for a,b in zip(before['contacts'],after['contacts']):
        if a['id']!=b['id']:raise ValueError('Contact comparison order differs')
        changes['contacts'].append(dict(id=a['id'],maximum_error_m=b['maximum_error_m']-a['maximum_error_m'],
            peak_release_palm_speed_m_s=b['boundary']['release']['peak_palm_speed_m_s']-a['boundary']['release']['peak_palm_speed_m_s']))
    factor={(8,9):'Finger degrees of freedom and separate pose regularizer',(9,10):'Finger parameter scaling only, with the same objective and reachable edits',(10,11):'Additional solver point and surface-frame key at release; fade follows the extended track. Authored events and edit budgets unchanged.',(11,12):'Sampled object clearance uses per-frame signed max-vertex inequalities and multiplier updates; initial merit equals V11 fixed penalty.'}[tuple(versions)]
    save(output/'comparison.json',dict(at=now(),rows=rows,candidate_minus_control=changes,changed_factor=factor,exact_source_scene_matched=True,preprocessing_and_constraints_matched=versions in [[9,10],[11,12]],preprocessing_and_authored_constraints_matched=versions in [[9,10],[10,11],[11,12]],quality_approved=False,
        scope='One paired development scene with floor-valid object placement; no new semantic coverage, training, held-out or animator approval. Temporal measurements remain descriptive and must not be hidden by numerical contact passes.',method_sha256=sha256(__file__)))
    print([dict(solver=r['solver_version'],failed=r['failed_screens'],grip_mm=[c['maximum_error_m']*1000 for c in r['dense_candidate']['contacts']],depth_mm=max(o['maximum_skin_vertex_depth_m'] for o in r['dense_candidate']['objects'].values())*1000) for r in rows],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('control',type=Path);parser.add_argument('candidate',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();compare(args.control,args.candidate,args.output)
