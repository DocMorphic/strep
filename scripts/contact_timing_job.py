"""Read-only stationary-pin timing checks for immutable Studio source snapshots."""
import copy
import shutil
import numpy as np
from strep import ROOT,read,save,sha256
from contact_spec import validate
from support_contact import regions
from build_soma_preview import ASSET


def validate_options(options,spec,frames):
    if type(frames)!=int or not 4<=frames<=901:raise ValueError('Timing checks support 4–901 native frames')
    if not isinstance(options,dict) or set(options)!={'edit_window'}:raise ValueError('Timing check requires an explicit edit window')
    w=options['edit_window']
    if not isinstance(w,list) or len(w)!=2 or any(type(v)!=int for v in w) or not 1<=w[0]<w[1]<=frames-2:
        raise ValueError('Choose held boundary frames between 1 and the penultimate frame')
    count=0
    for entry in spec['regions'].values():
        if entry['mode']!='explicit':continue
        for pin in entry['segments']:
            if pin['space']!='world' or not w[0]<pin['start_frame']<pin['end_frame']<w[1]:
                raise ValueError('Timing check supports stationary world pins with nonempty intervals strictly inside the edit window')
            count+=1
    if not count:raise ValueError('Save at least one stationary world pin before checking timing')
    return copy.deepcopy(options)


def verify_source(path,motion,skin):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from gltf_tools import accessor
    rig=RigAsset.load(path);clock=AnimationSampler(rig.document,rig.binary,0)
    if len(rig.primitives)!=1 or len(rig.joints)!=77:raise ValueError('Native SOMA preview required')
    primitive=rig.primitives[0]
    for key,expected in [('positions',skin['bind_vertices']),('joints',skin['lbs_indices'])]:
        if primitive[key] is None or primitive[key].shape!=expected.shape or not np.allclose(primitive[key],expected,atol=1e-7,rtol=0):
            raise ValueError('Preview skin differs from contact mesh')
    # RigAsset normalizes decoded weights. Compare the actual GLB attributes
    # to the source coefficients instead of rejecting that normalization.
    mesh=rig.document['nodes'][primitive['node']]['mesh']
    attrs=rig.document['meshes'][mesh]['primitives'][primitive['primitive']]['attributes']
    weights=np.concatenate([accessor(rig.document,rig.binary,attrs['WEIGHTS_'+str(i)]) for i in range(2)],axis=1)
    if not np.array_equal(weights,skin['lbs_weights']):raise ValueError('Encoded preview weights differ from contact mesh')
    if not np.allclose(rig.inverse,np.linalg.inv(skin['bind_rig_transform']),atol=1e-6,rtol=0):raise ValueError('Preview inverse binds differ')
    frames=len(motion['root_positions']);peak=0.
    if abs(clock.duration-(frames-1)/30)>1e-5:raise ValueError('Preview duration differs from native motion')
    for f in range(frames):
        matrices=clock.sample(f/30)[rig.joints]
        peak=max(peak,float(np.abs(matrices[:,:3,3]-motion['posed_joints'][f]).max()),
                 float(np.abs(matrices[:,:3,:3]-motion['global_rot_mats'][f]).max()))
    if peak>1e-5:raise ValueError('Preview poses differ from native motion')
    return dict(maximum_pose_component_error=peak,all_eight_weights_verified=True)


def prepare(source,spec,options,folder):
    source,folder=source.resolve(),folder.resolve()
    motion=dict(np.load(source/'motion.npz'));frames=len(motion['root_positions'])
    validate(spec,frames,regions(dict(np.load(ASSET))));validate_options(options,spec,frames)
    reference_files=['motion.npz','soma.glb','raw/motion.npz','limb/motion.npz']
    if any(not (source/name).is_file() for name in reference_files):raise ValueError('Original raw and limb references are required for a contact check')
    folder.mkdir(parents=True,exist_ok=False);snapshot=folder/'source';snapshot.mkdir()
    inputs={}
    for name in reference_files:
        (snapshot/name).parent.mkdir(parents=True,exist_ok=True)
        original=source/name;digest=sha256(original);shutil.copyfile(original,snapshot/name)
        if sha256(snapshot/name)!=digest or sha256(original)!=digest:raise ValueError('Source changed during snapshot')
        inputs[name]=digest
    save(folder/'contact-spec.json',spec)
    save(folder/'edit-request.json',dict(kind='timing_check',source=source.relative_to(ROOT/'reports').as_posix(),options=options))
    methods=['contact_edit_job.py','action_worker_lock.py','strep.py','contact_timing_job.py','contact_spec.py','support_contact.py','floor_contact.py','export_point_rate_objective.py',
        'export_motion_sampling.py','linear_skin_operator.py','plan_point_rate_window.py','point_rate_reachability.py',
        'rig_asset.py','rig_clip_import.py','gltf_tools.py','inspect_motion.py','contact_pose_preflight.py','contact_pose_reachability.py','contact_pose_sphere_bound.py']
    (folder/'implementation').mkdir()
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,folder/'implementation'/name)
    save(folder/'freeze.json',dict(inputs=inputs,mesh_sha256=sha256(ASSET),spec_sha256=sha256(folder/'contact-spec.json'),
        request_sha256=sha256(folder/'edit-request.json'),implementation={name:sha256(ROOT/'scripts'/name) for name in methods}))
    save(folder/'pipeline.json',dict(status='starting'))


def run(folder):
    import torch
    from floor_contact import Surface
    from inspect_motion import skeleton_metadata
    from export_point_rate_objective import ExportPointRateObjective
    from plan_point_rate_window import from_export,describe
    from action_worker_lock import worker_lock
    from contact_pose_preflight import analyze as pose_analyze,describe as pose_describe
    freeze=read(folder/'freeze.json')
    if not {'raw/motion.npz','limb/motion.npz'}<=set(freeze['inputs']):raise ValueError('Saved check lacks pose references; run a new check')
    def check():
        if any(sha256(folder/'source'/name)!=h for name,h in freeze['inputs'].items()):raise ValueError('Frozen clip changed')
        if sha256(ASSET)!=freeze['mesh_sha256'] or sha256(folder/'contact-spec.json')!=freeze['spec_sha256'] or sha256(folder/'edit-request.json')!=freeze['request_sha256']:
            raise ValueError('Frozen check inputs changed')
        if any(sha256(ROOT/'scripts'/n)!=h for n,h in freeze['implementation'].items()):raise ValueError('Check implementation changed')
    check();request=read(folder/'edit-request.json');spec=read(folder/'contact-spec.json')
    skin=dict(np.load(ASSET));motion=dict(np.load(folder/'source/motion.npz'));frames=len(motion['root_positions'])
    validate(spec,frames,regions(skin));options=validate_options(request['options'],spec,frames)
    source_verification=verify_source(folder/'source/soma.glb',motion,skin)
    bound=copy.deepcopy(spec);surface=Surface(skin);groups=regions(skin);bindings=[]
    for name,entry in bound['regions'].items():
        if entry['mode']!='explicit':continue
        for pin in entry['segments']:
            authored='vertex_id' in pin
            if not authored:
                f=pin['start_frame'];ids=groups[name]
                points=surface.vertices(motion['global_rot_mats'][f],motion['posed_joints'][f],ids)
                pin['vertex_id']=int(ids[points[:,1].argmin()])
            bindings.append(dict(region=name,start_frame=pin['start_frame'],end_frame=pin['end_frame'],vertex_id=pin['vertex_id'],
                selection='authored' if authored else 'lowest source region vertex at interval start'))
    with worker_lock():
        torch.set_num_threads(2);_,parents,*_=skeleton_metadata(motion['posed_joints'].shape[1])
        guard=ExportPointRateObjective(torch.tensor(motion['global_rot_mats'],dtype=torch.float64),
            torch.tensor(motion['posed_joints'],dtype=torch.float64),parents,skin,bound,options['edit_window'])
        report=from_export(folder/'source/soma.glb',bound,guard.record(),options['edit_window'],frames,.005)
        pose=pose_analyze({name:dict(np.load(folder/'source'/name/'motion.npz')) for name in ['raw','limb']},skin,bound)
    check();save(folder/'bound-contact-spec.json',bound);save(folder/'point-bindings.json',bindings)
    save(folder/'rate-reference.json',guard.record());save(folder/'window-preflight.json',report)
    save(folder/'pose-preflight.json',pose)
    conflicts=report['requested_conflicts']+pose['conflicting_frame_reference_pairs']
    explanation=describe(report)+'\n\n'+pose_describe(pose)+'\nThis check does not run a correction or enforce these limits in the existing Apply contact edit tool.\n'
    (folder/'window-preflight.txt').write_text(explanation,encoding='utf-8')
    result=dict(status='needs_authoring_change' if conflicts else 'checked',kind='timing_check',check_schema_version=3,
        timing_conflicts=report['requested_conflicts'],pose_conflicts=pose['conflicting_frame_reference_pairs'],pose_screen_status=pose['status'],
        requested_window=options['edit_window'],conflicts=conflicts,proposed_window=report['proposed_window'],
        message=explanation,source=request['source'],bound_points=bindings,quality_approved=False,solver_started=False,
        source_verification=source_verification,
        files={name:sha256(folder/name) for name in ['freeze.json','bound-contact-spec.json','point-bindings.json','rate-reference.json','window-preflight.json','window-preflight.txt','pose-preflight.json']})
    save(folder/'timing-result.json',result);return result


def listing(folder,state):
    if state.get('kind')!='timing_check':return {}
    base='/files/'+folder.relative_to(ROOT/'reports').as_posix()
    return dict(kind='contact_check',check_schema_version=state.get('check_schema_version'),
        pose_report=base+'/pose-preflight.json' if state.get('check_schema_version') in [2,3] else None,
        timing_message=state.get('message','Checking stationary contact timing.'),
        timing_report=base+'/window-preflight.txt',timing_json=base+'/window-preflight.json',
        bound_contacts=base+'/bound-contact-spec.json',source=state.get('source'),
        check_revision=sha256(folder/'timing-result.json') if (folder/'timing-result.json').is_file() else None)
