"""First-order point/triangle-mesh penetration with gradients to both bodies.

Uses the same Trimesh signed-distance observation as the existing partner
auditor, including its near-surface convention. This is a discrete vertex
term, not edge-only/continuous/self collision, physics or quality approval.
"""
import copy
import hashlib
import numpy as np
import torch
import trimesh
from torch.autograd.function import once_differentiable
from convex_partner_surface import candidates


def _digest(value):
    value=np.ascontiguousarray(value)
    return hashlib.sha256(str((value.shape,value.dtype.str)).encode()+value.tobytes()).hexdigest()


def _vertices(value):
    result=np.array(value,dtype=np.float64,copy=True)
    if result.ndim!=2 or result.shape[1:]!=(3,) or not 1<=len(result)<=32768 or not np.isfinite(result).all() or np.any(abs(result)>1e4):
        raise ValueError('Complete finite bounded vertex array N by3 required')
    return result


class _Penetration(torch.autograd.Function):
    @staticmethod
    def forward(ctx,source,target,operator):
        depth,derivative,triangles,barycentric,report=operator._query(
            source.detach().cpu().numpy(),target.detach().cpu().numpy())
        tensor=lambda v:torch.as_tensor(v,device=source.device)
        # Saving original inputs also enforces normal PyTorch version checks;
        # a target edited in-place before backward cannot reuse stale features.
        ctx.save_for_backward(source,target,tensor(derivative).to(source.dtype),tensor(triangles),tensor(barycentric).to(source.dtype))
        ctx.target_shape=target.shape
        operator._records.append(report)
        return tensor(depth).to(source.dtype)

    @staticmethod
    @once_differentiable
    def backward(ctx,incoming):
        source,target,derivative,triangles,barycentric=ctx.saved_tensors
        weighted=incoming[:,None]*derivative
        target_gradient=weighted.new_zeros(ctx.target_shape)
        contributions=-(weighted[:,None,:]*barycentric[:,:,None]).reshape(-1,3)
        target_gradient.index_add_(0,triangles.reshape(-1),contributions)
        return weighted,target_gradient,None


class MeshPenetration:
    """Caller-supplied complete source points and closed target triangle mesh.

Every call rebuilds current target geometry. Convex hulls only reject outside
points; retained points query the original mesh, never a hull substitute.
The first derivative uses the returned closest triangle and barycentric point.
Nearest-feature/inside changes are nonsmooth; verify proposed edits separately.
No gradient of topology or second derivative is provided.
    """
    def __init__(self,target_faces,*,query_batch_size=32,maximum_records=2048):
        raw=np.asarray(target_faces)
        if (raw.dtype.kind not in 'iu' or raw.ndim!=2 or raw.shape[1:]!=(3,)
                or not 4<=len(raw)<=65536 or raw.min()<0 or raw.max()>=32768):
            raise ValueError('Complete bounded integer triangle topology required')
        if type(query_batch_size) is not int or not 1<=query_batch_size<=32:
            raise ValueError('Explicit query batches of1-32 points required')
        if type(maximum_records) is not int or not 1<=maximum_records<=4096:
            raise ValueError('Explicit bounded complete observation receipt budget required')
        self._faces=raw.astype(np.int64,copy=True);self._faces.setflags(write=False)
        self._faces_sha256=_digest(self._faces);self.query_batch_size=query_batch_size
        self.maximum_records=maximum_records;self._records=[]

    @property
    def records(self):return copy.deepcopy(self._records)

    def __call__(self,source_vertices,target_vertices):
        if (not isinstance(source_vertices,torch.Tensor) or not isinstance(target_vertices,torch.Tensor)
                or source_vertices.dtype not in (torch.float32,torch.float64)
                or target_vertices.dtype!=source_vertices.dtype or target_vertices.device!=source_vertices.device):
            raise ValueError('Floating source/target tensors on the same device and dtype required')
        if len(self._records)>=self.maximum_records:raise ValueError('Complete mesh observation receipt budget exhausted')
        return _Penetration.apply(source_vertices,target_vertices,self)

    def _query(self,source,target):
        source,target=_vertices(source),_vertices(target)
        if len(target)<4 or self._faces.max()>=len(target):raise ValueError('Every target face index must exist in the supplied mesh')
        mesh=trimesh.Trimesh(vertices=target,faces=self._faces.copy(),process=False)
        if (not mesh.is_watertight or not mesh.is_winding_consistent or not np.isfinite(mesh.volume)
                or mesh.volume<=0 or not np.isfinite(mesh.area_faces).all() or np.any(mesh.area_faces<=0)):
            raise ValueError('Closed outward consistently wound nondegenerate target required; no automatic repair')
        selected,broadphase=candidates(source,target)
        depth=np.zeros(len(source));derivative=np.zeros_like(source)
        triangles=np.zeros((len(source),3),dtype=np.int64);barycentric=np.zeros((len(source),3));queries=0;reconstruction=0.
        for start in range(0,len(selected),self.query_batch_size):
            ids=selected[start:start+self.query_batch_size];queries+=1
            signed=trimesh.proximity.signed_distance(mesh,source[ids])
            if signed.shape!=(len(ids),) or not np.isfinite(signed).all():raise ValueError('Finite complete signed-distance observations required')
            depth[ids]=np.maximum(signed,0.);positive=ids[signed>0]
            if not len(positive):continue
            nearest,distance,faces=trimesh.proximity.closest_point(mesh,source[positive])
            actual=mesh.triangles[faces];bary=trimesh.triangles.points_to_barycentric(actual,nearest)
            delta=source[positive]-nearest;length=np.linalg.norm(delta,axis=1);nonzero=length>0
            gradient=np.zeros_like(delta);gradient[nonzero]=delta[nonzero]/length[nonzero,None]
            if not all(np.isfinite(v).all() for v in [nearest,distance,bary,gradient]):raise ValueError('Finite nearest-point derivative required')
            derivative[positive]=gradient;triangles[positive]=self._faces[faces];barycentric[positive]=bary
            reconstruction=max(reconstruction,float(np.linalg.norm(np.einsum('ij,ijk->ik',bary,actual)-nearest,axis=1).max()))
        report=dict(schema='strep-mesh-penetration-gradient-v1',source_vertices=len(source),target_vertices=len(target),target_faces=len(self._faces),
            source_sha256=_digest(source),target_sha256=_digest(target),target_faces_sha256=self._faces_sha256,
            all_source_vertices_considered=True,original_triangle_mesh_queried=True,convex_hull_is_only_broadphase=True,
            query_batch_size=self.query_batch_size,signed_query_batches=queries,positive_depth_vertices=int(np.count_nonzero(depth)),maximum_depth_m=float(depth.max()),squared_depth_sum_m2=float(depth@depth),
            broadphase=broadphase,maximum_barycentric_reconstruction_error_m=reconstruction,
            trimesh_version=trimesh.__version__,inherited_trimesh_near_surface_tolerance_m=float(trimesh.constants.tol.merge),added_physical_tolerance_m=0.,
            source_and_target_gradients=True,second_derivatives_supported=False,nearest_feature_switches_nonsmooth=True,
            edge_only_continuous_and_self_collision_unchecked=True,quality_approved=False,release_approved=False)
        return depth,derivative,triangles,barycentric,report
