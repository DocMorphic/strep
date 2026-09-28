"""Exploratory palm-region fitting with explicit full-surface inequalities.

Contact correspondences may move within declared patches. Old center vertices
are not equality constraints. Independent decoded geometry remains authoritative.
"""
import numpy as np
import trimesh
from scipy.optimize import minimize
from paired_hand_fit import HandActor,PairFitter
from paired_hand_clearance import SkinPoints,correspondences
from target_rig_contact import SkinEvaluator


def region(skin,hand,radius=.045,normal_degrees=60.):
    from palm_contacts import calibrate
    from floor_contact import Surface
    surface=Surface(skin);calibration=calibrate(skin)[hand]
    joint=surface.names.index(hand);bind=skin['bind_rig_transform'][joint]
    points=np.asarray(skin['bind_vertices']);faces=np.asarray(skin['faces']);triangles=points[faces]
    normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);length=np.linalg.norm(normal,axis=1)
    hint=bind[:3,:3]@np.asarray(calibration['palm_normal_local'])
    local=(points-bind[:3,3])@bind[:3,:3]
    central=np.linalg.norm(local-np.asarray(calibration['center_local_m']),axis=1)<=radius
    mask=central&np.isin(np.arange(len(points)),surface.regions[hand])
    aligned=normal@hint>=np.cos(np.radians(normal_degrees))*length
    selected=np.flatnonzero(mask[faces].all(axis=1)&aligned&(length>1e-12))
    if len(selected)<3:raise ValueError('Palm region has too few triangles')
    return dict(hand=hand,vertices=np.unique(faces[selected]).tolist(),face_ids=selected.tolist(),
        criteria=dict(radius_m=radius,normal_degrees=normal_degrees),anatomical_review=False)


def install_region(actor,patch,faces):
    faces=np.asarray(faces)[patch['face_ids']]
    actor.vertices,remap=np.unique(faces,return_inverse=True);actor.triangles=remap.reshape(-1,3);actor.palm=0
    nodes,points,weights=SkinEvaluator(actor.rig).parts[0]
    actor.skin_nodes=nodes[actor.vertices];actor.skin_points=points[actor.vertices];actor.weights=weights[actor.vertices]
    actor.patch=patch


class RegionActor(HandActor):
    def __init__(self,*args,patch,**kwargs):
        super().__init__(*args,**kwargs)
        install_region(self,patch,args[4])


class RegionFitter(PairFitter):
    def objective_pair(self,x):
        n=self.sizes[0];a=self.actors[0].frame_pair(self.event,x[:n]);b=self.actors[1].frame_pair(self.event,x[n:])
        # Region normals and finger direction regularize orientation; no fixed
        # center-point residual is present. Surface pairs supply the contact.
        return (np.r_[(a[1]+b[1])*.8,(a[2]-b[2])*.5,x*.2],
            np.vstack([np.c_[a[4],b[4]]*.8,np.c_[a[5],-b[5]]*.5,np.eye(len(x))*.2]))


def contact_records(actors,frame,x,faces,count=3,spacing=.006):
    parts=np.split(x,[actors[0].dim]);records=[];metrics=[]
    points=[a.rig.vertices(a.pose(frame,v))@a.rotation.T+a.translation for a,v in zip(actors,parts)]
    for source,target in [(0,1),(1,0)]:
        ids=np.array(actors[source].patch['vertices']);triangles=np.asarray(faces)[actors[target].patch['face_ids']]
        mesh=trimesh.Trimesh(points[target],triangles,process=False)
        closest=[];distances=[];which=[]
        for start in range(0,len(ids),32):
            p,d,t=trimesh.proximity.closest_point(mesh,points[source][ids[start:start+32]])
            closest.extend(p);distances.extend(d);which.extend(t)
        closest=np.array(closest);distances=np.array(distances);which=np.array(which);chosen=[]
        for index in np.argsort(distances,kind='stable'):
            # Distant patches can initially project onto one target edge. Allow
            # that initialization; target coverage is measured independently
            # and must spread before the final contact-area screen can pass.
            if all(np.linalg.norm(points[source][ids[index]]-points[source][ids[j]])>=spacing for j in chosen):chosen.append(int(index))
            if len(chosen)==count:break
        if len(chosen)<count:raise ValueError('Insufficient separated palm contacts')
        face=which[chosen];bary=trimesh.triangles.points_to_barycentric(mesh.triangles[face],closest[chosen]);normal=mesh.face_normals[face]
        records.append(dict(source=source,target=target,points=list(zip(ids[chosen].tolist(),triangles[face].tolist(),bary.tolist(),normal.tolist()))))
        sample=points[source][ids[chosen]]
        area=float(np.linalg.norm(np.cross(sample[1]-sample[0],sample[2]-sample[0]))/2)
        q=closest[chosen];target_area=float(np.linalg.norm(np.cross(q[1]-q[0],q[2]-q[0]))/2)
        metrics.append(dict(source=source,target=target,source_vertices=ids[chosen].tolist(),distances_m=distances[chosen].tolist(),triangle_area_m2=area,target_triangle_area_m2=target_area))
    return records,metrics


class CorrespondenceEvaluator:
    def __init__(self,fitter,records):
        self.fitter=fitter;self.skin=[SkinPoints(a) for a in fitter.actors];self.records=[]
        for r in records:
            if r['points']:
                ids,triangles,bary,normals=zip(*r['points'])
                self.records.append((r['source'],r['target'],np.array(ids),np.array(triangles),np.array(bary),np.array(normals)))

    def pairs(self,x):
        n=self.fitter.sizes[0];parts=[x[:n],x[n:]];offset=[0,n];result=[]
        for source,target,ids,triangles,bary,normals in self.records:
            p,jp=self.skin[source].evaluate(self.fitter.event,parts[source],ids)
            q,jq=self.skin[target].evaluate(self.fitter.event,parts[target],triangles.ravel())
            q=np.einsum('ni,nij->nj',bary,q.reshape(-1,3,3));jq=np.einsum('ni,nijk->njk',bary,jq.reshape(-1,3,3,self.fitter.sizes[target]))
            jac=np.zeros((len(ids),3,len(x)));jac[:,:,offset[source]:offset[source]+self.fitter.sizes[source]]=jp
            jac[:,:,offset[target]:offset[target]+self.fitter.sizes[target]]=-jq
            result.append((p-q,jac,normals))
        return result

    def clearance(self,x,margin=.001):
        result=self.pairs(x)
        if not result:return np.empty(0),np.empty((0,len(x)))
        return (np.concatenate([np.einsum('ni,ni->n',d,n)-margin for d,j,n in result]),
            np.vstack([np.einsum('ni,nij->nj',n,j) for d,j,n in result]))

    def contact(self,x,gap=.001,weight=100.):
        result=self.pairs(x);scale=weight/np.sqrt(sum(len(d) for d,j,n in result))
        return (np.concatenate([(d-n*gap).ravel() for d,j,n in result])*scale,
            np.vstack([j.reshape(-1,len(x)) for d,j,n in result])*scale)


def refine(fitter,initial,faces,progress=None,iterations=4,safeguard=False):
    x=np.asarray(initial,dtype=float).copy();history=[]
    if x.shape!=fitter.bounds.shape or not np.isfinite(x).all() or np.any(np.abs(x)>fitter.bounds+1e-10):raise ValueError('Invalid initial correction')
    for step in range(iterations+1):
        collision,diagnostics=correspondences(fitter.actors,fitter.event,x,faces,margin=.003)
        contact,metrics=contact_records(fitter.actors,fitter.event,x,faces)
        history.append(dict(iteration=step,parameters=x.tolist(),collision=diagnostics,contact=metrics))
        if step:history[-1].update(solver_success=bool(result.success),solver_message=str(result.message),solver_iterations=int(result.nit),frozen_constraint_min_m=float(clearance.clearance(x)[0].min()) if clearance.records else None,step_trials=trials)
        if progress:progress(history)
        if step==iterations:break
        clearance=CorrespondenceEvaluator(fitter,collision);surface=CorrespondenceEvaluator(fitter,contact)
        def objective(v):
            r,j=fitter.objective_pair(v);cr,cj=surface.contact(v);r=np.r_[r,cr];j=np.vstack([j,cj])
            return .5*float(r@r),j.T@r
        lower=np.maximum(-fitter.bounds,x-np.radians(5));upper=np.minimum(fitter.bounds,x+np.radians(5))
        constraints=[]
        if clearance.records:constraints=[dict(type='ineq',fun=lambda v:clearance.clearance(v)[0],jac=lambda v:clearance.clearance(v)[1])]
        result=minimize(objective,x,jac=True,method='SLSQP',bounds=list(zip(lower,upper)),constraints=constraints,options=dict(maxiter=100,ftol=1e-10))
        proposed=np.clip(result.x,lower,upper);trials=[]
        if not np.isfinite(proposed).all():raise ValueError('Nonfinite region solution')
        if not safeguard:x=proposed;continue
        # Frozen linearized surface constraints cannot prevent a new collision
        # outside their active set. Check each proposed step against the full
        # nonlinear mesh query, retaining the current feasible pose on failure.
        allowed=max(1e-6,max(d['max_depth_m'] for d in diagnostics))
        old_energy=objective(x)[0]
        for backtrack in range(8):
            alpha=2.**(-backtrack);candidate=x+alpha*(proposed-x)
            _,actual=correspondences(fitter.actors,fitter.event,candidate,faces,margin=.003)
            depth=max(d['max_depth_m'] for d in actual);energy=objective(candidate)[0]
            accepted=depth<=allowed and energy<=old_energy+1e-10
            trials.append(dict(alpha=alpha,max_depth_m=depth,energy=energy,accepted=bool(accepted),parameters=candidate.tolist()))
            if accepted:x=candidate;break
    return x,history
