"""Independently inspect every checked stationary pin on decoded native exports."""
import numpy as np
from threadpoolctl import threadpool_limits
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from audit_scene_edit_window import summarize
from audit_scene_timing import rates


def audit(source,candidate,spec,window,reference):
    rigs=[RigAsset.load(p) for p in [source,candidate]]
    clocks=[AnimationSampler(r.document,r.binary,0) for r in rigs]
    frames=spec['frame_count'];count=(frames-1)*4+1
    pins=[(name,pin) for name,entry in spec['regions'].items() if entry['mode']=='explicit' for pin in entry['segments']]
    vertices=sorted({p['vertex_id'] for _,p in pins});index={v:i for i,v in enumerate(vertices)}
    points=[[],[]];joints=[[],[]];depths=[[],[]];rows=[]
    with threadpool_limits(limits=1):
        for i in range(count):
            transforms=[c.sample(i/120) for c in clocks]
            meshes=[r.vertices(t) for r,t in zip(rigs,transforms)]
            j=[t[r.joints] for r,t in zip(rigs,transforms)]
            rows.append(dict(frame=i/4,skin_position_error_m=float(np.linalg.norm(meshes[1]-meshes[0],axis=1).max()),
                joint_position_error_m=float(np.linalg.norm(j[1][:,:3,3]-j[0][:,:3,3],axis=1).max()),basis_error=float(np.abs(j[1][:,:3,:3]-j[0][:,:3,:3]).max())))
            for v in range(2):
                points[v].append(meshes[v][vertices]);joints[v].append(j[v]);depths[v].append(max(0.,float(-meshes[v][:,1].min())))
    tracks=[np.array(p) for p in points];contacts=[]
    for name,pin in pins:
        a,b=pin['start_frame']*4,pin['end_frame']*4+1
        error=np.linalg.norm(tracks[1][a:b,index[pin['vertex_id']]]-pin['position_m'],axis=1)
        contacts.append(dict(region=name,vertex_id=pin['vertex_id'],start_frame=pin['start_frame'],end_frame=pin['end_frame'],
            samples=len(error),samples_over_5mm=int((error>.005).sum()),maximum_error_m=float(error.max())))
    phases=[]
    for row in reference['rows']:
        variants={}
        for v,label in enumerate(['source','candidate']):
            peaks=[]
            for order in [1,2]:
                values=np.linalg.norm(np.diff(tracks[v][:,index[row['vertex_id']]],n=order,axis=0)*120**order,axis=1)
                center=(np.arange(len(values))+order/2)/4
                selected=values[(center>=row['first_frame'])&(center<=row['last_frame'])]
                peaks.append(float(selected.max()))
            variants[label]=peaks
        phases.append(dict(region=row['region'],vertex_id=row['vertex_id'],phase=row['phase'],first_frame=row['first_frame'],last_frame=row['last_frame'],
            checked_ceilings=row['reference_ceilings'],variants=variants,
            candidate_excess_over_checked=[max(0.,p-c) for p,c in zip(variants['candidate'],row['reference_ceilings'])]))
    names=[rigs[1].document['nodes'][j].get('name',str(j)) for j in rigs[1].joints]
    preservation=summarize(rows,window,frames)
    return dict(samples=count,contacts=contacts,phase_rates=phases,preservation=preservation,
        variants={label:dict(maximum_floor_depth_m=max(depths[v]),joints=rates(np.array(joints[v]),1/120,names)) for v,label in enumerate(['source','candidate'])},
        all_requested_pin_samples_within_5mm=all(c['samples_over_5mm']==0 for c in contacts),
        outside_preservation_passed=preservation['all_outside_times']['within_numerical_tolerance'],
        quality_approved=False,scope='Every authored interval, full eight-weight GLB skin at 120 Hz; checked speed/acceleration ceilings and raw excesses retained without acceptance padding. Finite sampling is not continuous collision, force, anatomy or naturalness certification.')
