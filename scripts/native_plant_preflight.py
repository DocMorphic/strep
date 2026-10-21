"""Necessary planted-patch checks at native keys, never motion acceptance.

An ankle limit is not a mesh limit. For fully foot-owned points, combine the
accepted ankle and local-key angle budgets through the rigid-point bound.
Unsupported applicability or an oversized check falls back to ordinary fitting.
Between-key motion, rates, maximum gaps and feasibility remain unproved.
"""
import numpy as np
from elbow_swivel import descendants
from native_foot_plant import patch_geometry
from native_support_skin import NativeSupportSkin
from root_plane_contact_bounds import translation_coefficients
from rigid_support_point_bounds import composed_angle_bound,rigid_point_movement
from support_centroid_bounds import bound
from native_support_spec import number

SCHEMA='strep-native-plant-preflight-v1'
MAX_POINT_OBSERVATIONS=200000
# Existing serialized_screens/authored_audit acceptance tolerances, not new slack.
ANKLE_TOLERANCE_M=1e-7
ANGLE_TOLERANCE_DEGREES=1e-4
CLEARANCE_TOLERANCE_M=1e-8


def _rigid_ancestry(rig,reader,foot):
    ancestors=set();node=foot
    while node>=0:
        if node in ancestors:return False
        ancestors.add(node);item=rig.document['nodes'][node]
        if 'matrix' in item or item.get('scale',[1,1,1])!=[1,1,1]:return False
        node=rig.parents[node]
    return not any(n in ancestors and path=='scale' for n,path,*_ in reader.channels)


def analyze(rig,reader,rows,limits):
    """Use rows from native_support_spec.validate and the authored plant limits."""
    if not isinstance(rows,list) or not 1<=len(rows)<=64:raise ValueError('Validated nonempty support rows required')
    if not isinstance(limits,dict) or set(limits)!={r['id'] for r in rows}:raise ValueError('Matching planting limits required')
    for value in limits.values():
        if not isinstance(value,dict) or set(value)!={'anchor','speed'}:raise ValueError('Explicit planting limits required')
        number(value['anchor'],'anchor tolerance',0,.03);number(value['speed'],'speed tolerance',0,.1)
    skin=NativeSupportSkin(rig);reference_ids={tuple(ref):i for i,ref in enumerate(skin.vertex_references)}
    if len(reference_ids)!=len(skin.vertex_references):raise ValueError('Distinct skin vertex references required')
    reports=[];plans=[];total=0
    for row in rows:
        report=dict(id=row['id'],foot=row['foot'],status='not_applicable',reason=None,
            native_keys_checked=0,point_observations=0,incompatible_points=0,worst_conflict=None)
        reports.append(report);foot=row['chain'][-1]
        if not _rigid_ancestry(rig,reader,foot):
            report['reason']='Rigid TRS ancestry without scale channels required';continue
        try:
            points,anchor,patch,refs=patch_geometry(rig,reader,row)
        except ValueError:
            report['reason']='A fully foot-owned source patch is unavailable';continue
        ids=np.array([reference_ids[tuple(ref)] for ref in refs],dtype=int)
        if not len(ids) or np.any((skin.weights[ids]>0)&~descendants(rig.parents,foot)[skin.nodes[ids]]):
            report['reason']='Every positive patch influence must belong to the foot subtree';continue
        coefficients,_=translation_coefficients(rig,foot)
        keys=[(i,float(t)) for i,t in enumerate(row['clock']) if row['stance_s'][0]<=float(t)<=row['stance_s'][1]]
        total+=len(ids)*len(keys)
        plans.append((row,report,points,anchor[patch],patch,ids,coefficients[ids],keys))
        report.update(source_patch_vertex_references=refs,planned_native_keys=[t for _,t in keys])
    if total>MAX_POINT_OBSERVATIONS:
        for _,report,*_ in plans:report['reason']='Necessary precheck exceeds its point/key budget; ordinary fitting remains available'
        plans=[]
    for row,report,points,anchor,patch,ids,coefficients,keys in plans:
        foot=row['chain'][-1];normal=row['up'];length=float(np.linalg.norm(normal));normal=normal/length
        clearance=max(0.,row['clearance']-CLEARANCE_TOLERANCE_M)/length;offset=-row['offset']/length
        report['status']='not_ruled_out'
        for index,time in keys:
            world=reader.sample(time);rotation=world[foot,:3,:3];current=points(world[None])[0,patch]
            if not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-12,rtol=0) or abs(np.linalg.det(rotation)-1)>1e-12:
                report.update(status='not_applicable',reason='Source pivot is not sufficiently rigid',native_keys_checked=0,point_observations=0,incompatible_points=0,worst_conflict=None);break
            frozen=index in row['edit_keys']
            translation=0. if frozen else row['displacement']+ANKLE_TOLERANCE_M
            angle=0. if frozen else composed_angle_bound([row['angle']+ANGLE_TOLERANCE_DEGREES]*len(row['chain']))
            observations=[]
            try:
                for ref,point,target,response in zip(report['source_patch_vertex_references'],current,anchor,coefficients):
                    allowance=rigid_point_movement(point.tolist(),world[foot,:3,3].tolist(),float(response),translation,angle)
                    result=bound([point.tolist()],target.tolist(),normal.tolist(),offset,clearance,limits[row['id']]['anchor'],allowance['maximum_point_displacement_m'])
                    observations.append((ref,point,target,float(response),allowance,result))
            except ValueError:
                report.update(status='not_applicable',reason='Source geometry exceeds the necessary-check range',native_keys_checked=0,point_observations=0,incompatible_points=0,worst_conflict=None);break
            report['native_keys_checked']+=1;report['point_observations']+=len(observations)
            for ref,point,target,response,allowance,result in observations:
                if result['status']!='incompatible_support_target':continue
                report['status']='incompatible_support_target';report['incompatible_points']+=1
                deficit=result['minimum_required_vertex_max_displacement_m']-result['maximum_vertex_displacement_m']-result['comparison_reserve_m']
                if report['worst_conflict'] is None or deficit>report['worst_conflict']['deficit_m']:
                    report['worst_conflict']=dict(time_s=time,native_key=index,vertex_reference=ref,
                        source_point_m=point.tolist(),target_point_m=target.tolist(),translation_response=response,
                        frozen_key=frozen,pivot_translation_allowance_m=translation,world_angle_allowance_degrees=angle,
                        point_displacement_allowance_m=allowance['maximum_point_displacement_m'],
                        required_point_displacement_m=result['minimum_required_vertex_max_displacement_m'],
                        comparison_reserve_m=result['comparison_reserve_m'],deficit_m=deficit)
    conflicts=sum(r['incompatible_points'] for r in reports)
    checked=sum(r['native_keys_checked'] for r in reports)
    return dict(schema=SCHEMA,status='incompatible_support_target' if conflicts else 'not_ruled_out' if checked else 'not_applicable',
        supports=reports,limits={k:dict(v) for k,v in limits.items()},native_keys_checked=checked,
        point_observations=sum(r['point_observations'] for r in reports),incompatible_points=conflicts,
        complete_native_key_coverage=all(r['status']!='not_applicable' for r in reports),interpolated_times_checked=False,
        scope='Necessary source-bound patch/clearance check at native keys only. No conflict found is not a feasible correction; ordinary contact/rate/export gates remain required.',
        feasibility_proven=False,formal_interval_certificate=False,quality_approved=False)


def conflict_message(report):
    rows=[r for r in report['supports'] if r['worst_conflict'] is not None]
    row=max(rows,key=lambda r:r['worst_conflict']['deficit_m']);w=row['worst_conflict']
    return (f"Stance '{row['id']}' cannot hold its foot patch at {w['time_s']:.6g} s within the edit limits: "
        f"a point needs at least {w['required_point_displacement_m']*1000:.6g} mm of movement, "
        f"but the ankle and rotation limits allow at most {w['point_displacement_allowance_m']*1000:.6g} mm. "
        "Shorten or reposition the stance, or revise the edit limits. The original clip is preserved.")
