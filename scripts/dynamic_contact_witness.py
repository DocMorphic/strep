"""Recompute signed-distance witnesses at each control evaluation.

Only the retained source vertex identities are fixed. Nearest triangles,
barycentrics and normals are refreshed on the actual skinned target. The
distance derivative differentiates source and target vertices at the current
closest point; ties and degenerate nearest features remain nonsmooth.
"""
import numpy as np
import trimesh


class DynamicWitnessSurface:
    def __init__(self,fitter,frame,keys):
        self.fitter=fitter;self.frame=float(frame);self.keys=[tuple(k) for k in keys]
        if not np.isfinite(self.frame) or len(fitter.actors)!=2:raise ValueError('Finite frame and two actors required')
        if len(set(self.keys))!=len(self.keys):raise ValueError('Duplicate dynamic witness')
        for source,target,vertex in self.keys:
            if {source,target}!={0,1} or type(vertex) is not int or vertex<0:raise ValueError('Invalid witness identity')
        self.count=len(self.keys);self.cache=None;self.cached=None;self.last_records=None

    def clearance(self,x,margin=.001):
        x=np.asarray(x,float);sizes=self.fitter.sizes
        if x.shape!=(sum(sizes),) or not np.isfinite(x).all() or not np.isfinite(margin):raise ValueError('Finite matching controls and margin required')
        if self.cache is not None and np.array_equal(self.cache,x):
            value,jac=self.cached;return value-margin,jac
        if not self.count:
            self.cached=(np.empty(0),np.empty((0,len(x))));self.cache=x.copy();self.last_records=[]
            return self.cached[0]-margin,self.cached[1]
        parts=np.split(x,[sizes[0]]);offset=[0,sizes[0]]
        vertices=[a.rig.vertices(a.pose(self.frame,v))@a.rotation.T+a.translation for a,v in zip(self.fitter.actors,parts)]
        faces=self.fitter.witness_faces
        values=np.empty(self.count);jac=np.zeros((self.count,len(x)));records=[]
        for source,target in [(0,1),(1,0)]:
            indexes=[i for i,key in enumerate(self.keys) if key[:2]==(source,target)]
            if not indexes:continue
            ids=np.array([self.keys[i][2] for i in indexes],dtype=int)
            if np.any(ids>=len(vertices[source])):raise ValueError('Witness vertex outside source')
            mesh=trimesh.Trimesh(vertices[target],faces,process=False)
            if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError('Closed wound target required')
            for start in range(0,len(ids),32):
                selected=ids[start:start+32];positions=np.asarray(indexes[start:start+32],int);points=vertices[source][selected]
                signed=trimesh.proximity.signed_distance(mesh,points)
                closest,_,triangles=trimesh.proximity.closest_point(mesh,points)
                delta=closest-points;length=np.linalg.norm(delta,axis=1)
                normal=np.where((signed>=0)[:,None],1.,-1.)*delta/np.maximum(length[:,None],1e-12)
                normal[length<1e-8]=mesh.face_normals[triangles[length<1e-8]]
                bary=trimesh.triangles.points_to_barycentric(mesh.triangles[triangles],closest)
                tri=np.asarray(faces)[triangles]
                p,jp=self.fitter.actors[source].skin_pair(self.frame,parts[source],selected)
                q,jq=self.fitter.actors[target].skin_pair(self.frame,parts[target],tri.ravel())
                q=np.einsum('ni,nij->nj',bary,q.reshape(-1,3,3))
                jq=np.einsum('ni,nijk->njk',bary,jq.reshape(-1,3,3,sizes[target]))
                gap=np.einsum('ni,ni->n',p-q,normal)
                if not np.isfinite(np.r_[signed,gap,bary.ravel(),jp.ravel(),jq.ravel()]).all():raise ValueError('Nonfinite dynamic witness')
                if np.max(np.abs(gap+signed),initial=0.)>1e-8 or np.max(np.abs(p-points),initial=0.)>1e-10:
                    raise ValueError('Dynamic skin/query projection differs')
                values[positions]=-signed
                jac[positions,offset[source]:offset[source]+sizes[source]]=np.einsum('ni,nij->nj',normal,jp)
                jac[positions,offset[target]:offset[target]+sizes[target]]=-np.einsum('ni,nij->nj',normal,jq)
                records.extend(dict(source=source,target=target,vertex=int(v),triangle=t.tolist(),barycentric=b.tolist(),normal=n.tolist(),signed_depth_m=float(d))
                    for v,t,b,n,d in zip(selected,tri,bary,normal,signed))
        self.cache=x.copy();self.cached=(values,jac);self.last_records=records
        return values-margin,jac
