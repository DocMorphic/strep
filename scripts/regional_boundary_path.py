"""Joint boundary-path objective with native budgets and subframe skin checks.

Geometry and temporal terms are soft optimization objectives. Serialized export
checks, not optimizer termination, decide acceptance. Grasp keys stay fixed.
"""
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from angular_join import rotation_log
from support_contact_v5 import rodrigues, bounded_rotation


def interpolate_rotations(left, right, weight):
    return left @ rodrigues(rotation_log(left.transpose(-1, -2) @ right) * weight[..., None])


def cylinder_distance(points, center, rotation, dimensions):
    local = (points-center[..., None, :]) @ rotation
    radial = torch.linalg.vector_norm(local[..., [0, 2]], dim=-1)-dimensions[0]
    height = local[..., 1].abs()-dimensions[1]/2
    q = torch.stack([radial, height], -1)
    return torch.linalg.vector_norm(torch.relu(q), dim=-1)+q.amax(-1).clamp_max(0)


def kinematics(local, offsets, parents):
    rotations, positions = [], []
    for joint, parent in enumerate(parents):
        if parent < 0:
            rotations.append(local[:, joint]); positions.append(offsets[:, joint])
        else:
            rotations.append(rotations[parent] @ local[:, joint])
            positions.append(positions[parent]+(rotations[parent] @ offsets[:, joint, :, None]).squeeze(-1))
    return torch.stack(rotations, 1), torch.stack(positions, 1)


def assemble(source, local, frames, parents):
    """Rebuild selected FK without normalizing or changing frozen local keys."""
    result={k:v.copy() for k,v in source.items()}
    offsets=np.zeros_like(source['posed_joints'][frames],dtype=float)
    for j,parent in enumerate(parents):
        if parent<0:offsets[:,j]=source['root_positions'][frames]
        else:offsets[:,j]=np.einsum('fji,fj->fi',source['global_rot_mats'][frames,parent],
                                   source['posed_joints'][frames,j]-source['posed_joints'][frames,parent])
    # Quantize once into the stored local format before FK. Frozen local values
    # retain their exact input bits; orthogonality drift is measured on export.
    result['local_rot_mats'][frames]=local[frames]
    r,p=kinematics(torch.as_tensor(result['local_rot_mats'][frames],dtype=torch.float64),
                   torch.as_tensor(offsets,dtype=torch.float64),parents)
    result['global_rot_mats'][frames]=r.numpy();result['posed_joints'][frames]=p.numpy()
    return result


class BoundaryPath:
    def __init__(self, problem, source, frames, object_track, settings):
        self.problem, self.source, self.frames, self.settings = problem, source, frames, settings
        if frames != list(range(frames[0], frames[-1]+1)) or frames[0]<2 or frames[-1]+2>=len(source['root_positions']):
            raise ValueError('Contiguous interior window with two fixed keys on each side required')
        self.support = list(range(frames[0]-2, frames[-1]+3))
        self.arms = [problem.names.index(side+part) for side in ['Left','Right'] for part in ['Shoulder','Arm','ForeArm','Hand']]
        self.limits = problem.limits[[problem.lookup[j] for j in self.arms]]
        relative = problem.base['local_rot_mats'][frames][:,self.arms].transpose(0,1,3,2) @ source['local_rot_mats'][frames][:,self.arms]
        theta = Rotation.from_matrix(relative.reshape(-1,3,3)).as_rotvec().reshape(len(frames),8,3)
        scaled = theta/self.limits[None,:,None]
        if np.any(np.sum(scaled**2,-1)>=1): raise ValueError('Interior arm edit seed required')
        self.initial = (scaled/np.sqrt(1-np.sum(scaled**2,-1))[...,None]).ravel()
        self.local = problem.t(source['local_rot_mats'][self.support])
        self.base_arm = problem.t(problem.base['local_rot_mats'][frames][:,self.arms])
        offsets = np.zeros_like(source['posed_joints'][self.support],dtype=float)
        for j,parent in enumerate(problem.parents):
            if parent<0: offsets[:,j]=source['posed_joints'][self.support,j]
            else:
                offsets[:,j]=np.einsum('fji,fj->fi',source['global_rot_mats'][self.support,parent],
                                     source['posed_joints'][self.support,j]-source['posed_joints'][self.support,parent])
        self.offsets = problem.t(offsets)
        self.native_positions = problem.t(source['posed_joints'][self.support][:,self.arms])
        # Four samples per edge plus the final key, including both protected joins.
        self.times = np.arange(frames[0]-1,frames[-1]+1.001,.25)
        self.left = np.minimum(np.floor(self.times).astype(int),frames[-1])-self.support[0]
        self.fractions = problem.t(self.times-(self.left+self.support[0]))
        self.object_geometry, positions, rotations = object_track
        if self.object_geometry.shape!='cylinder': raise ValueError('Cylinder path study required')
        from scipy.spatial.transform import Slerp
        clock=np.arange(len(positions))
        self.centers=problem.t(np.stack([np.interp(self.times,clock,positions[:,i]) for i in range(3)],1))
        self.object_rotations=problem.t(Slerp(clock,Rotation.from_matrix(rotations))(self.times).as_matrix())

    def locals(self, raw):
        angles=bounded_rotation(raw.reshape(len(self.frames),8,3),self.problem.t(self.limits)[None,:,None])
        local=self.local.clone()
        indices=torch.as_tensor(np.array(self.frames)-self.support[0])
        updated=local[indices].index_copy(1,torch.as_tensor(self.arms),self.base_arm@rodrigues(angles))
        return local.index_copy(0,indices,updated)

    def terms(self, raw):
        local=self.locals(raw); _,position=kinematics(local,self.offsets,self.problem.parents)
        arm=local[:,self.arms]; points=position[:,self.arms]
        angular=(arm[2:]-2*arm[1:-1]+arm[:-2])/self.settings['rotation_curvature_scale']
        cartesian=(points[2:]-2*points[1:-1]+points[:-2])/self.settings['position_curvature_scale_m']
        fidelity=(points-self.native_positions)/self.settings['position_reference_scale_m']
        sampled=interpolate_rotations(local[self.left],local[self.left+1],self.fractions[:,None])
        offsets=(1-self.fractions[:,None,None])*self.offsets[self.left]+self.fractions[:,None,None]*self.offsets[self.left+1]
        r,p=kinematics(sampled,offsets,self.problem.parents)
        # All vertices and eight skin influences; never just hand guide points.
        vertices=(((r[:,self.problem.indices]@self.problem.bind[None,:,:,:,None]).squeeze(-1)+p[:,self.problem.indices])*self.problem.weights[None,:,:,None]).sum(2)
        gaps=cylinder_distance(vertices,self.centers,self.object_rotations,self.object_geometry.dimensions)
        collision=torch.relu(self.problem.config['object_clearance_m']+self.settings['clearance_reserve_m']-gaps.amin(1))/self.settings['geometry_scale_m']
        floor=torch.relu(self.problem.config['clearance_m']-vertices[:,:,1].amin(1))/self.settings['geometry_scale_m']
        return dict(rotation_curvature=angular.square().sum(),position_curvature=cartesian.square().sum(),
                    position_reference=fidelity.square().sum(),object_clearance=collision.square().sum(),floor=floor.square().sum())

    def pair(self, raw):
        variable=self.problem.t(raw).requires_grad_(); terms=self.terms(variable); loss=sum(terms.values())
        gradient=torch.autograd.grad(loss,variable)[0]
        return float(loss.detach()),gradient.detach().numpy(),{k:float(v.detach()) for k,v in terms.items()}
