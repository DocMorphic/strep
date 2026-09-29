"""Fresh decoded audit for a source-relative coupled root/leg block."""
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read,sha256
from verify_authored_root_correction import samples
from verify_breadth_contact import verify as original_bounds
from study_breadth_root_cleanup import active_frames
from rig_transition import localize


def audit(folder,source,frames,centers,original_peak):
    spec=read(folder/'spec.json');count=spec['frames'];root=spec['root_node'];proof=original_bounds(folder)
    rig,before=samples(source,count);other,after=samples(folder/'candidate/character.glb',count)
    a,b=[np.array([r.vertices(w) for w in world]) for r,world in [(rig,before),(other,after)]]
    eps=1e-6;acc_eps=.0036;feet=[];annotations=read(folder/'input/contacts.json');guides=read(folder/'request.json')['support']['guides']
    for side,patch in spec['patches'].items():
        ids=patch['vertices'];p,q=[v[::2,ids] for v in [a,b]];c,d=p.mean(1),q.mean(1)
        active=active_frames(annotations,side,count);steps=active[1:]&active[:-1];used=np.asarray(guides[side]['weights'])>0;anchor=np.asarray(guides[side]['anchors_xz_m'])
        acceleration=[np.linalg.norm(np.diff(x,n=2,axis=0)*900,axis=1) for x in [c,d]]
        speeds=[np.linalg.norm(np.diff(x[:,[0,2]],axis=0)*30,axis=1) for x in [c,d]]
        errors=[np.linalg.norm(x[:,[0,2]]-anchor,axis=1) for x in [c,d]]
        hover=[np.maximum(x[:,:,1].min(1),0.) for x in [p,q]]
        feet.append(dict(side=side,acceleration_excess_m_s2=float((acceleration[1]-acceleration[0]).max()),
            support_speed_excess_m_s=float((speeds[1]-speeds[0])[steps].max()) if steps.any() else 0.,
            anchor_excess_m=float((errors[1]-errors[0])[used].max()) if used.any() else 0.,
            hover_excess_m=float((hover[1]-hover[0])[active].max()) if active.any() else 0.))
    root_tracks=[w[::2,root,:3,3] for w in [before,after]]
    root_acc=[np.linalg.norm(np.diff(x,n=2,axis=0)*900,axis=1) for x in root_tracks]
    local=[localize(w[::2],r.parents) for w,r in [(before,rig),(after,other)]]
    angles=[]
    for l in local:
        delta=l[:-1,:,:3,:3].transpose(0,1,3,2)@l[1:,:,:3,:3]
        angles.append(Rotation.from_matrix(delta.reshape(-1,3,3)).magnitude().reshape(count-1,-1))
    untouched=[i for i in range(count) if i not in frames];indices=np.asarray(centers)-1
    objective=[float(np.maximum(v[indices]-original_peak,0.)@np.maximum(v[indices]-original_peak,0.)) for v in root_acc]
    floor=float((np.maximum(0.,-b[:,:,1])-np.maximum(0.,-a[:,:,1])).max())
    peak_change=float((angles[1].max(0)-angles[0].max(0)).max())
    p95_change=float((np.percentile(angles[1],95,axis=0)-np.percentile(angles[0],95,axis=0)).max())
    checks=dict(original_edit_limits=proof['bounds_and_preservation_passed'],full_skin_floor=floor<=eps,
        root_acceleration=bool(np.max(root_acc[1]-root_acc[0])<=acc_eps),
        root_radius=bool(np.linalg.norm(root_tracks[1]-root_tracks[0],axis=1).max()<=.01+eps),
        unchanged_frames=bool(np.abs(after[::2][untouched]-before[::2][untouched]).max()<=eps),
        foot_acceleration=all(f['acceleration_excess_m_s2']<=acc_eps for f in feet),
        foot_speed=all(f['support_speed_excess_m_s']<=60e-6 for f in feet),
        anchors=all(f['anchor_excess_m']<=eps for f in feet),hover=all(f['hover_excess_m']<=eps for f in feet),
        per_joint_peak=peak_change<=1e-6,per_joint_p95=p95_change<=1e-6)
    return dict(source_sha256=sha256(source),candidate_sha256=sha256(folder/'candidate/character.glb'),checks=checks,all_guards_passed=all(checks.values()),
        useful_target_improvement=objective[1]<objective[0]-max(1e-9,.001*objective[0]),objective_before=objective[0],objective_after=objective[1],
        root_peak_before_m_s2=float(root_acc[0].max()),root_peak_after_m_s2=float(root_acc[1].max()),original_peak_m_s2=original_peak,
        remaining_root_failure_centers=(np.flatnonzero(root_acc[1]>original_peak+acc_eps)+1).tolist(),
        full_skin_floor_excess_m=floor,per_joint_peak_excess_radians=peak_change,per_joint_p95_excess_radians=p95_change,feet=feet,original_bounds=proof,quality_approved=False)
