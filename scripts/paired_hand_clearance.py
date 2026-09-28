"""Exploratory coupled contact refinement with frozen surface correspondences.

Correspondences are rebuilt between bounded inner solves. The independent full
surface audit remains authoritative; this local objective is not a certificate.
"""
import numpy as np
import trimesh
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from target_rig_contact import SkinEvaluator
from rig_clearance_fit import right_jacobian


class SkinPoints:
    def __init__(self,actor):
        self.actor=actor
        self.nodes,self.points,self.weights=SkinEvaluator(actor.rig).parts[0]

    def evaluate(self,frame,x,vertices):
        a=self.actor;world=a.pose(frame,x)
        nodes=self.nodes[vertices];weights=self.weights[vertices]
        components=np.einsum('vkij,vkj->vki',world[nodes,:3,:],self.points[vertices])
        points=np.sum(components*weights[:,:,None],axis=1)
        jac=np.zeros((len(vertices),3,a.dim))
        for i,(node,v) in enumerate(zip(a.nodes,np.asarray(x).reshape(-1,3))):
            axis=world[node,:3,:3]@right_jacobian(v)
            influence=weights*a.descendants[node][nodes]
            delta=np.sum((components-world[node,:3,3])*influence[:,:,None],axis=1)
            jac[:,:,i*3:i*3+3]=np.cross(axis.T[None,:,:],delta[:,None,:]).transpose(0,2,1)
        return points@a.rotation.T+a.translation,np.einsum('ij,vjk->vik',a.rotation,jac)


def correspondences(actors,frame,x,faces,margin=.002):
    sizes=[a.dim for a in actors];parts=np.split(x,[sizes[0]])
    vertices=[a.rig.vertices(a.pose(frame,v))@a.rotation.T+a.translation for a,v in zip(actors,parts)]
    records=[];diagnostics=[]
    for source,target in [(0,1),(1,0)]:
        points=vertices[source];mesh=trimesh.Trimesh(vertices[target],faces,process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError('Closed wound target required')
        ids=np.flatnonzero(np.all((points>=vertices[target].min(0)-margin)&(points<=vertices[target].max(0)+margin),axis=1))
        active=[];max_depth=0.;over=0
        for start in range(0,len(ids),32):
            chunk=ids[start:start+32];signed=trimesh.proximity.signed_distance(mesh,points[chunk])
            if not np.isfinite(signed).all():raise ValueError('Nonfinite signed distance')
            max_depth=max(max_depth,float(np.maximum(signed,0).max()));over+=int((signed>.005).sum())
            near=signed>=-margin
            if not near.any():continue
            selected=chunk[near];distance=signed[near]
            closest,_,triangles=trimesh.proximity.closest_point(mesh,points[selected])
            delta=closest-points[selected];length=np.linalg.norm(delta,axis=1)
            normal=np.where((distance>=0)[:,None],1.,-1.)*delta/np.maximum(length[:,None],1e-12)
            normal[length<1e-8]=mesh.face_normals[triangles[length<1e-8]]
            bary=trimesh.triangles.points_to_barycentric(mesh.triangles[triangles],closest)
            if not np.isfinite(bary).all():raise ValueError('Degenerate contact triangle')
            active.extend(zip(selected.tolist(),np.asarray(faces)[triangles].tolist(),bary.tolist(),normal.tolist()))
        records.append(dict(source=source,target=target,points=active))
        diagnostics.append(dict(source=source,target=target,vertices_checked=len(points),max_depth_m=max_depth,vertices_over_5mm=over,active_constraints=len(active)))
    return records,diagnostics


class SurfaceObjective:
    def __init__(self,fitter,records,margin=.002,weight=1000.):
        self.fitter=fitter;self.margin=margin;self.skin=[SkinPoints(a) for a in fitter.actors];self.records=[]
        self.scale=weight/np.sqrt(max(1,sum(len(r['points']) for r in records)))
        for r in records:
            if not r['points']:continue
            source_ids,triangles,bary,normals=zip(*r['points'])
            self.records.append((r['source'],r['target'],np.array(source_ids),np.array(triangles),np.array(bary),np.array(normals)))

    def pair(self,x):
        residual,jac=self.fitter.objective_pair(x);residual=[residual];jac=[jac]
        n=self.fitter.sizes[0];parts=[x[:n],x[n:]];offset=[0,n]
        for source,target,ids,triangles,bary,normals in self.records:
            p,jp=self.skin[source].evaluate(self.fitter.event,parts[source],ids)
            q,jq=self.skin[target].evaluate(self.fitter.event,parts[target],triangles.ravel())
            q=np.einsum('ni,nij->nj',bary,q.reshape(-1,3,3))
            jq=np.einsum('ni,nijk->njk',bary,jq.reshape(-1,3,3,self.fitter.sizes[target]))
            gap=np.einsum('ni,ni->n',p-q,normals);active=gap<self.margin
            residual.append(np.maximum(0,self.margin-gap)*self.scale)
            block=np.zeros((len(ids),len(x)))
            block[:,offset[source]:offset[source]+self.fitter.sizes[source]]=-np.einsum('ni,nij->nj',normals,jp)
            block[:,offset[target]:offset[target]+self.fitter.sizes[target]]=np.einsum('ni,nij->nj',normals,jq)
            jac.append(block*active[:,None]*self.scale)
        return np.concatenate(residual),np.vstack(jac)


def refine(fitter,initial,faces,progress=None,iterations=4):
    x=np.asarray(initial,dtype=float).copy();history=[]
    if x.shape!=fitter.bounds.shape or not np.isfinite(x).all() or np.any(np.abs(x)>fitter.bounds+1e-10):raise ValueError('Invalid initial correction')
    records,diagnostics=correspondences(fitter.actors,fitter.event,x,faces)
    history.append(dict(iteration=0,collision=diagnostics,parameters=x.tolist()))
    if progress:progress(history)
    for iteration in range(1,iterations+1):
        objective=SurfaceObjective(fitter,records)
        lower=np.maximum(-fitter.bounds,x-np.radians(5));upper=np.minimum(fitter.bounds,x+np.radians(5))
        result=least_squares(lambda v:objective.pair(v)[0],x,jac=lambda v:objective.pair(v)[1],
            bounds=(lower,upper),max_nfev=60,ftol=1e-8,xtol=1e-8,gtol=1e-8)
        candidate=np.clip(result.x,lower,upper)
        if not np.isfinite(candidate).all():raise ValueError('Nonfinite candidate')
        records,diagnostics=correspondences(fitter.actors,fitter.event,candidate,faces)
        a=fitter.actors[0].frame_pair(fitter.event,candidate[:fitter.sizes[0]])
        b=fitter.actors[1].frame_pair(fitter.event,candidate[fitter.sizes[0]:])
        history.append(dict(iteration=iteration,collision=diagnostics,parameters=candidate.tolist(),evaluations=int(result.nfev),
            solver_success=bool(result.success),palm_gap_m=float(np.linalg.norm(a[0]-b[0])),
            opposing_normal_degrees=float(np.degrees(np.arccos(np.clip(-a[1]@b[1],-1,1)))),
            tangent_difference_degrees=float(np.degrees(np.arccos(np.clip(a[2]@b[2],-1,1))))))
        if progress:progress(history)
        x=candidate
    # All iterations are retained, including regressions. No quality promotion
    # and no selection of the best seed/frame based on these diagnostics.
    return x,history
