"""Bounded deterministic cycle proposals, with explicit non-semantic ranking."""
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_contact_authoring import source
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_loop import assemble,place
from rig_transition import localize
from rig_contact_tracks import signals,ROLES

SEARCH_LOCK=threading.Lock()
METHOD='strep-cycle-search-v1'
RANKING='step_max_deg/10 + pose_gap_max_deg/45 + velocity_gap_max_deg_s/300 + root_acceleration_max_m_s2/10 + predicted_support_disagreement_fraction (0 when unavailable). Fixed heuristic, not a realism score. Mesh diagnostics do not affect rank.'


def validate(payload):
    keys={'schema','job','variant','glb_sha256','start_min','start_max','period_min','period_max','stride','blend_frames','turn_degrees','root_mode'}
    if not isinstance(payload,dict) or set(payload)!=keys or payload['schema']!=METHOD:raise ValueError('Invalid cycle search request')
    snapshot=source(payload['job'],payload['variant']);report=snapshot[3]
    if sha256(snapshot[4])!=payload['glb_sha256']:raise ValueError('Cycle search source changed')
    a,b,p,q,s,k=(payload[n] for n in ('start_min','start_max','period_min','period_max','stride','blend_frames'))
    if any(type(v) is not int for v in (a,b,p,q,s,k)) or not (0<=a<=b<report['frames'] and 4<=k<p<=q<=900 and 1<=s<=120):raise ValueError('Use integer frame ranges, a positive stride and periods longer than the blend')
    if payload['root_mode'] not in ('travel','in_place'):raise ValueError('Choose traveling or in-place root motion')
    turn=payload['turn_degrees']
    if type(turn) not in (int,float) or not np.isfinite(turn) or abs(turn)>180:raise ValueError('Turn must be within 180 degrees')
    pairs=[(start,period) for start in range(a,b+1,s) for period in range(p,q+1,s) if start+period+k<=report['frames']]
    if not pairs:raise ValueError('No candidates leave enough source continuation')
    if len(pairs)>400 or sum(period+k for _,period in pairs)>40000:raise ValueError('Search too large; increase the frame stride or narrow the ranges (400 candidates / 40,000 candidate frames maximum)')
    return snapshot,pairs


def angular(a,b):
    return np.degrees(Rotation.from_matrix((np.swapaxes(a,-1,-2)@b).reshape(-1,3,3)).magnitude()).reshape(a.shape[:-2])


def measure(rig,root,raw,recipe,masks,origin):
    a,p,k=(recipe[n] for n in ('start_frame','period_frames','blend_frames'))
    single,cycle,w=assemble(raw,rig.parents,root,recipe)
    # Include the first step after wrap as well as the terminal sample.
    continued=np.concatenate([single,place(single[1:2],rig.parents,root,cycle)])
    local=localize(continued,rig.parents);nodes=sorted(set(rig.joints)|{root});rot=local[:,nodes,:3,:3]
    steps=angular(rot[:-1],rot[1:]);step=float(steps.max());peak_frame,peak_joint=np.unravel_index(steps.argmax(),steps.shape)
    source_local=localize(raw,rig.parents)[:,nodes,:3,:3]
    source_step=float(angular(source_local[:-1],source_local[1:]).max())
    head=localize(raw[:k],rig.parents)[:,nodes,:3,:3]
    tail=localize(place(raw[p:p+k],rig.parents,root,np.linalg.inv(cycle)),rig.parents)[:,nodes,:3,:3]
    gap=float(angular(head,tail).max())
    def velocity(r):return Rotation.from_matrix((r[1:]@np.swapaxes(r[:-1],-1,-2)).reshape(-1,3,3)).as_rotvec().reshape(k-1,len(nodes),3)*180/np.pi*30
    velocity_gap=float(np.linalg.norm(velocity(head)-velocity(tail),axis=-1).max())
    root_acc=float(np.linalg.norm(np.diff(continued[:,root,:3,3],n=2,axis=0)*900,axis=-1).max())
    mixed=(w>0)&(w<1)
    disagreements=np.array([masks[r][a:a+k]!=masks[r][a+p:a+p+k] for r in ROLES])[:,mixed]
    support=None if origin in ('none_supplied','partially_unknown') else float(disagreements.mean())
    excursion=float(angular(np.broadcast_to(rot[:1],rot[:-2].shape),rot[:-2]).max())
    metrics=dict(step_max_deg=step,step_peak=dict(node=nodes[peak_joint],from_frame=int(peak_frame),to_frame=int(peak_frame+1),within_return_blend=bool(peak_frame<k or peak_frame>=p)),source_window_step_max_deg=source_step,pose_gap_max_deg=gap,velocity_gap_max_deg_s=velocity_gap,root_acceleration_max_m_s2=root_acc,predicted_support_disagreement_fraction=support,rotation_excursion_from_phase_zero_max_deg=excursion)
    score=step/10+gap/45+velocity_gap/300+root_acc/10+(support or 0)
    return dict(recipe=recipe,metrics=metrics,score=score),single,w


def authored_targets(folder,glb,variant):
    spec=folder/'input/contact-spec.json' if variant=='input' else folder/'contact-spec.json'
    if spec.exists():
        data=read(spec)
        return [dict(vertices=data['patches'][t['patch']]['vertices'],frames=list(range(t['start_frame'],t['end_frame_exclusive']))) for t in data['contacts']]
    review=glb.parent/'contact-review.json'
    if review.exists():return [dict(vertices=t['vertices'],frames=[e['frame'] for e in t['output_frames'] if e['weight']>0]) for t in read(review)['authored_targets']]
    return []


def mesh_diagnostics(rig,single,w,recipe,targets):
    a,p,k=(recipe[n] for n in ('start_frame','period_frames','blend_frames'))
    patches={tuple(t['vertices']):np.zeros(p+1,dtype=bool) for t in targets}
    for t in targets:
        frames=set(t['frames']);active=patches[tuple(t['vertices'])]
        for f in range(p+1):
            phase=f%p
            active[f]|=(a+phase in frames and (phase>=k or w[phase]>0)) or (phase<k and 1-w[phase]>0 and a+p+phase in frames)
    positions={v:[] for v in patches};depth=[]
    for world in single:
        points=rig.vertices(world);depth.append(max(0.,-float(points[:,1].min())))
        for vertices in patches:positions[vertices].append(points[list(vertices)].mean(axis=0))
    speeds=[]
    for vertices,active in patches.items():
        v=np.linalg.norm(np.diff(np.array(positions[vertices])[:,[0,2]],axis=0),axis=1)*30
        speeds.extend(v[active[:-1]&active[1:]].tolist())
    return dict(floor_depth_max_m=max(depth),floor_frames_above_5mm=sum(v>.005 for v in depth),any_weight_authored_patch_speed_p95_m_s=float(np.percentile(speeds,95)) if speeds else None,any_weight_authored_patch_speed_max_m_s=max(speeds) if speeds else None,measured_patch_velocity_steps=len(speeds),scope='Integer-frame mesh only; authored patch horizontal speeds include partial blend support. Missing contact annotations remain unknown. No body/object collision or action correctness test.')


def search(payload):
    if not SEARCH_LOCK.acquire(blocking=False):raise ValueError('A cycle search is already running')
    try:
        started=time.perf_counter();snapshot,pairs=validate(payload);folder,_,_,report,glb=snapshot
        rig=RigAsset.load(glb);sampler=AnimationSampler(rig.document,rig.binary,0);k=payload['blend_frames'];root=report['root_node']
        last=max(a+p+k for a,p in pairs);world=np.array([sampler.sample(float(np.float32(f/30))) for f in range(last)])
        masks,origin=signals(report);rows=[]
        for a,p in pairs:
            recipe=dict(schema='strep-rig-loop-v1',label=f'Cycle proposal · {a} + {p}',**{key:payload[key] for key in ('job','variant','glb_sha256','blend_frames','turn_degrees','root_mode')},start_frame=a,period_frames=p)
            row,_,_=measure(rig,root,world[a:a+p+k],recipe,masks,origin);rows.append(row)
        rows.sort(key=lambda r:(r['score'],r['recipe']['start_frame'],r['recipe']['period_frames']))
        for i,row in enumerate(rows):row['rank']=i+1
        targets=authored_targets(folder,glb,payload['variant'])
        for row in rows[:5]:
            recipe=row['recipe'];a,p=recipe['start_frame'],recipe['period_frames'];single,_,w=assemble(world[a:a+p+k],rig.parents,root,recipe)
            row['mesh']=mesh_diagnostics(rig,single,w,recipe,targets)
        if sha256(glb)!=payload['glb_sha256']:raise ValueError('Source changed during search')
        identity=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];out=ROOT/'reports/rig-loop-searches'/identity;out.mkdir(parents=True,exist_ok=False)
        save(out/'request.json',payload)
        # Keep implementation + annotations with the frozen result, not only a mutable filename.
        import shutil
        for name in ('rig_loop_search.py','rig_loop.py','rig_transition.py','rig_contact_tracks.py','rig_clip_import.py','rig_asset.py','gltf_tools.py'):
            target=out/'implementation'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'scripts'/name,target)
        save(out/'source-report.json',report);save(out/'support-signals.json',dict(origin=origin,masks={r:m.astype(int).tolist() for r,m in masks.items()}));save(out/'authored-patches.json',targets)
        result=dict(schema=METHOD,id=identity,created_at=now(),request=payload,source_glb_sha256=payload['glb_sha256'],source_path=str(glb),contact_origin=origin,candidate_count=len(rows),elapsed_seconds=time.perf_counter()-started,ranking=RANKING,candidates=rows,shortlist=rows[:5],human_approved=False,scope='Proposals from the requested finite frame grid. Ranking rewards low kinematic mismatch and can favor small or incomplete actions. Choose action content and tempo by review. Only top five receive mesh diagnostics; no candidate is automatically accepted.',report_url='/files/rig-loop-searches/'+identity+'/search.json')
        save(out/'search.json',result);return result
    finally:SEARCH_LOCK.release()
