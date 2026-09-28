"""Compile fixed surface normals into sparse skin-to-distance operators.

Only fractional evaluations use this route. Integer frames retain the existing
analytic skin derivative. Correspondences must be rebuilt between outer steps.
"""
import copy
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from paired_hand_trajectory import TemporalSurface


def projection(actor, vertices, coefficients, normals):
    """Map flattened skeleton 3x4 matrices to weighted signed projections."""
    vertices=np.asarray(vertices);coefficients=np.asarray(coefficients,dtype=float);normals=np.asarray(normals,dtype=float)
    if vertices.ndim!=2 or not np.issubdtype(vertices.dtype,np.integer):raise ValueError('Integer vertex rows required')
    count=vertices.shape[0]
    if coefficients.shape!=vertices.shape or normals.shape!=(count,3):raise ValueError('Projection shape mismatch')
    if not np.isfinite(coefficients).all() or not np.isfinite(normals).all():raise ValueError('Finite projection required')
    if np.any(vertices<0) or np.any(vertices>=len(actor.skin_nodes)):raise ValueError('Vertex outside skin')
    nodes=actor.skin_nodes[vertices];points=actor.skin_points[vertices];weights=actor.weights[vertices]
    local_normals=normals@actor.rotation
    values=coefficients[:,:,None,None,None]*weights[:,:,:,None,None]*local_normals[:,None,None,:,None]*points[:,:,:,None,:]
    columns=nodes[:,:,:,None,None]*12+np.arange(12).reshape(3,4)
    rows=np.broadcast_to(np.arange(count)[:,None,None,None,None],values.shape)
    columns=np.broadcast_to(columns,values.shape)
    operator=coo_matrix((values.ravel(),(rows.ravel(),columns.ravel())),shape=(count,len(actor.local[0])*12)).tocsr()
    operator.eliminate_zeros()
    offset=(normals@actor.translation)*coefficients.sum(axis=1)
    return operator,offset


class ProjectedTemporalSurface:
    def __init__(self,fitter,frame,records):
        self.fitter=fitter;self.frame=frame;self.records=copy.deepcopy(records)
        self.reference=TemporalSurface(fitter,frame,self.records)
        if not np.isfinite(frame) or any(not 0<=frame<len(a.local) for a in fitter.actors):raise ValueError('Frame outside clip')
        if len(fitter.actors)!=2:raise ValueError('Two actors required')
        self.count=sum(len(r['points']) for r in self.records);self.operators=[]
        self.offset=np.zeros(self.count)
        for actor_index,actor in enumerate(fitter.actors):
            blocks=[];cursor=0
            for record in self.records:
                source,target=record['source'],record['target']
                if {source,target}!={0,1}:raise ValueError('Distinct actor indices required')
                size=len(record['points'])
                if not size:continue
                ids,triangles,bary,normals=map(np.asarray,zip(*record['points']))
                if actor_index==source:vertices=ids[:,None];coefficients=np.ones((size,1))
                else:vertices=triangles;coefficients=-bary
                operator,offset=projection(actor,vertices,coefficients,normals)
                blocks.append(operator);self.offset[cursor:cursor+size]+=offset;cursor+=size
            if blocks:
                from scipy.sparse import vstack
                self.operators.append(vstack(blocks,format='csr'))
            else:self.operators.append(csr_matrix((0,len(actor.local[0])*12)))

    def clearance(self,x,margin=.001):
        x=np.asarray(x,dtype=float)
        if x.shape!=(sum(self.fitter.sizes),) or not np.isfinite(x).all() or not np.isfinite(margin):raise ValueError('Finite controls/margin required')
        if float(self.frame).is_integer():return self.reference.clearance(x,margin)
        gaps=self.offset.copy()-margin;jac=np.zeros((self.count,len(x)))
        if not self.count:return gaps,jac
        cursor=0
        for actor,size,operator in zip(self.fitter.actors,self.fitter.sizes,self.operators):
            world,derivative=actor.world_pair(self.frame,x[cursor:cursor+size])
            gaps+=operator@world[:,:3,:].reshape(-1)
            jac[:,cursor:cursor+size]=operator@derivative[:,:3,:,:].reshape(-1,size)
            cursor+=size
        return gaps,jac
