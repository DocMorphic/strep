"""Differentiate exact active dependencies after complete native skin evaluation.

Every original vertex chooses the active maxima/minima. Only backpropagation is
sparse; nonlinear replay and the constraint population remain complete.
"""
import numpy as np
import torch
from grasp_pose_witness import norm_slack_and_jacobian
from scene_pose_restoration import reference_slacks
from support_contact_v8 import torch_primitive_clearance_violation
from pose_row_jacobian import row_jacobian


class SparsePoseJacobian:
    def __init__(self,problem,row_chunk=None):
        if problem.grouping not in ['global','native-joint']:raise ValueError('Known complete constraint grouping required')
        if row_chunk is not None and (type(row_chunk) is not int or not 1<=row_chunk<=32):
            raise ValueError('Explicit bounded derivative-row chunk required')
        self.problem=problem;self.cache=None;self.dependencies=None;self.row_chunk=row_chunk

    def __call__(self,x):
        x=np.asarray(x,dtype=float)
        if x.shape!=(self.problem.dim,) or not np.isfinite(x).all():raise ValueError('Finite complete pose controls required')
        if self.cache is not None and np.array_equal(x,self.cache[0]):return self.cache[1:]
        problem=self.problem
        with torch.no_grad():_,_,_,full=problem.fk(problem.t(x))
        count=len(full);selected={c['vertex'] for c in problem.contacts}
        for _,faces,_ in problem.normals:selected.update(np.asarray(faces).ravel().tolist())
        floor=np.flatnonzero(full[:,1].numpy()==full[:,1].amin().item());selected.update(floor.tolist())
        object_rows=[]
        with torch.no_grad():
            for geometry,name,position,rotation in problem.objects:
                all_values=torch_primitive_clearance_violation(full[None],position,rotation,geometry,problem.t(problem.margins[name][None]))[0]
                groups=problem.vertex_groups if problem.grouping=='native-joint' else [('all',np.arange(count))]
                for group,ids in groups:
                    values=all_values[ids];active=ids[values.numpy()==values.amax().item()]
                    if not len(active):raise ValueError('Every complete object row needs its active dependency')
                    selected.update(active.tolist());object_rows.append((geometry,name,position,rotation,active))
        ids=np.array(sorted(selected),dtype=int)
        if not len(ids) or ids.min()<0 or ids.max()>=count:raise ValueError('Valid complete active skin dependencies required')
        lookup=np.full(count,-1,dtype=int);lookup[ids]=np.arange(len(ids))
        variable=problem.t(x).requires_grad_();rotation,positions=problem.fk(variable)[:2]
        indices=problem.indices[ids]
        vertices=(((rotation[indices]@problem.bind[ids,:,:,None]).squeeze(-1)+positions[indices])*problem.weights[ids,:,None]).sum(1)
        values=[]
        for contact,limit in zip(problem.contacts,problem.point_limits):
            values.append((limit-problem.headroom_m-torch.linalg.vector_norm(vertices[lookup[contact['vertex']]]-problem.t(contact['target'])))/.01)
        chord=2*np.sin(np.deg2rad(problem.config['normal_tolerance_degrees']-.001)/2)
        for _,faces,target in problem.normals:
            triangles=vertices[lookup[faces]]
            normal=torch.linalg.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]).sum(0)
            normal=normal/torch.linalg.vector_norm(normal).clamp_min(1e-12)
            values.append((chord-torch.linalg.vector_norm(normal-target))/chord)
        values.append((vertices[lookup[floor],1].amin()-problem.config['clearance_m']-problem.headroom_m)/.01)
        for geometry,name,position,orientation,active in object_rows:
            violation=torch_primitive_clearance_violation(vertices[lookup[active]][None],position,orientation,geometry,
                problem.t(problem.margins[name][active][None]))
            values.append((-violation.amax()-problem.headroom_m)/.01)
        values.extend(reference_slacks(positions,problem.references,problem.neighbors,problem.frame,.22-problem.headroom_m,
            1.5-30*problem.headroom_m,grouped=problem.grouping=='native-joint'))
        values=torch.stack(values)
        if len(values)!=len(problem.labels):raise ValueError('Complete original constraint rows must remain present')
        jac=(np.array([torch.autograd.grad(value,variable,retain_graph=True)[0].detach().numpy() for value in values])
            if self.row_chunk is None else row_jacobian(values,variable,self.row_chunk))
        slack=values.detach().numpy();bounds,bjac=norm_slack_and_jacobian(x,problem.limits)
        if not np.isfinite(slack).all() or not np.isfinite(jac).all():raise ValueError('Finite exact pose derivatives required')
        self.dependencies=dict(original_vertices=count,active_vertices=len(ids),object_rows=len(object_rows),all_maximum_ties_retained=True,
            nonlinear_population_unchanged=True,row_chunk=self.row_chunk)
        self.cache=(x.copy(),np.r_[slack,bounds],np.concatenate([jac,bjac]))
        return self.cache[1:]
