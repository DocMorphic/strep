"""Compare body cleanup with both raw and limb-only motion, including support costs."""
import numpy as np
from scipy.spatial.transform import Rotation
from floor_contact import Surface,reconstruct
from evaluate_floor_contact import compare,stats
from inspect_motion import skeleton_metadata
from audit_body_ground import measure


def midpoints(motion):
    local=motion['local_rot_mats'].astype(float)
    relative=local[:-1].transpose(0,1,3,2)@local[1:]
    half=Rotation.from_rotvec(Rotation.from_matrix(relative.reshape(-1,3,3)).as_rotvec()*.5).as_matrix().reshape(relative.shape)
    source={k:v[:-1].copy() for k,v in motion.items()}
    source['root_positions']=(motion['root_positions'][:-1]+motion['root_positions'][1:])/2
    return reconstruct(source,local[:-1]@half,skeleton_metadata(77)[1])


def body_support(base,candidate,skin):
    surface=Surface(skin);names=surface.names
    dominant=surface.indices[np.arange(len(surface.indices)),surface.weights.argmax(1)]
    regions={'Torso':['Hips','Spine1','Spine2','Chest'],'Head':['Head','Neck1','Neck2']}
    indices={name:np.flatnonzero(np.isin(dominant,[names.index(j) for j in bones])) for name,bones in regions.items()}
    for side in ['Left','Right']:
        for region,bone in [('Knee','Shin'),('Elbow','ForeArm')]:
            joint=names.index(side+bone)
            near=np.linalg.norm(skin['bind_vertices']-skin['bind_rig_transform'][joint,:3,3],axis=1)<.13
            indices[side+region]=np.flatnonzero((dominant==joint)&near)
    report={};flags=[]
    for name,idx in indices.items():
        a=np.array([surface.vertices(r,p,idx) for r,p in zip(base['global_rot_mats'],base['posed_joints'])])
        b=np.array([surface.vertices(r,p,idx) for r,p in zip(candidate['global_rot_mats'],candidate['posed_joints'])])
        minimum=a[:,:,1].min(1);speed=np.linalg.norm(np.diff(a.mean(1)[:,[0,2]],axis=0),axis=1)*30
        mask=(minimum[:-1]<.025)&(minimum[1:]<.025)&(speed<.2)
        gaps=[[],[]];slides=[[],[]]
        for f in np.flatnonzero(mask):
            patch=a[f,:,1]<minimum[f]+.01
            for n,v in enumerate([a,b]):
                gaps[n].append(max(0,float(v[f,patch,1].min())))
                slides[n].append(float(np.linalg.norm((v[f+1,patch]-v[f,patch])[:,[0,2]],axis=1).mean()*30))
        report[name]=dict(intervals=int(mask.sum()),before_gap_m=stats(gaps[0]),after_gap_m=stats(gaps[1]),
                         before_slide_m_s=stats(slides[0]),after_slide_m_s=stats(slides[1]))
        if mask.sum()>=3:
            if report[name]['after_gap_m']['p95']>report[name]['before_gap_m']['p95']+.02:flags.append(name+'_body_support_gap_regression')
            if report[name]['after_slide_m_s']['p95']>report[name]['before_slide_m_s']['p95']+.05:flags.append(name+'_body_support_slide_regression')
    return dict(regions=report,flags=flags,scope='Fixed low/slow limb-baseline surface patches; geometric contact candidates, not annotated weight-bearing contacts. Knee/elbow patches lie within 13 cm of the bind joint.')


def evaluate(raw,base,candidate,skin,recipe):
    raw_comparison=compare(raw,candidate,skin);baseline_comparison=compare(base,candidate,skin)
    support=body_support(base,candidate,skin)
    midpoint_before=measure(midpoints(base),skin);midpoint_after=measure(midpoints(candidate),skin)
    flags=list(dict.fromkeys(raw_comparison['flags']+baseline_comparison['flags']+support['flags']))
    if midpoint_after['mesh_max_depth_m']>.01:flags.append('intermediate_surface_penetration_above_1cm')
    lift=candidate['root_positions'][:,1]-raw['root_positions'][:,1]
    if lift.max()>.22001:flags.append('root_lift_budget')
    if not np.array_equal(candidate['root_positions'][:,[0,2]],raw['root_positions'][:,[0,2]]):flags.append('horizontal_root_changed')
    raw_comparison['flags']=flags;raw_comparison['screen_status']='flagged' if flags else 'within_provisional_screen'
    raw_comparison['scope']='Raw-to-body candidate comparison plus limb-baseline and body-contact regression gates. No animator, dynamics or engine-import claim.'
    return raw_comparison,dict(relative_to_limb=baseline_comparison,body_support=support,
        midpoint_depth_before_m=midpoint_before['mesh_max_depth_m'],midpoint_depth_after_m=midpoint_after['mesh_max_depth_m'],
        max_root_lift_m=float(lift.max()),min_root_lift_m=float(lift.min()),
        applied=recipe['applied'],flags=flags,scope='30 fps keys and halfway samples (60 Hz coverage); not a continuous-time collision proof.')
