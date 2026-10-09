"""Complete adjacent-key pose constraints with coupled temporal derivatives.

An experimental contact-window problem, not a full-clip quality certificate.
"""
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scene_pose_restoration import RestorationProblem
from sparse_pose_jacobian import SparsePoseJacobian
from pose_row_jacobian import row_jacobian


class CoupledPoseWindow:
    def __init__(self,folder,skin,frames,*,row_chunk=16):
        if (not isinstance(frames,list) or not 2<=len(frames)<=5
                or any(type(frame) is not int or frame<0 for frame in frames)
                or frames!=list(range(frames[0],frames[0]+len(frames)))
                or type(row_chunk) is not int or not 1<=row_chunk<=32):
            raise ValueError('Two to five consecutive native frames and bounded derivative chunk required')
        self.frames=frames.copy();self.row_chunk=row_chunk
        self.problems=[RestorationProblem(folder,skin,frame,grouping='native-joint') for frame in frames]
        self.lookup={frame:i for i,frame in enumerate(frames)}
        first=self.problems[0];self.pose_dim=first.dim;self.dim=self.pose_dim*len(frames)
        if any(p.dim!=first.dim or p.names!=first.names or p.editable!=first.editable
               or not np.array_equal(p.limits,first.limits) or p.config['fps']!=30 for p in self.problems):
            raise ValueError('Identical native rig/control budgets and original 30 Hz clock required')
        self.scale=np.concatenate([np.r_[np.repeat(p.limits,3),p.config['max_root_lift_m']] for p in self.problems])
        self.seed=np.concatenate([p.seed for p in self.problems])
        self.labels=[];self.row_starts=[]
        for p in self.problems:
            self.row_starts.append(len(self.labels))
            names=p.labels+['rotation-budget:'+p.names[j] for j in p.editable]
            self.labels.extend([name+':frame-'+str(p.frame) for name in names])
        if len(set(self.labels))!=len(self.labels):raise ValueError('Unique complete window row identities required')
        self.sparse=[SparsePoseJacobian(p,row_chunk=row_chunk) for p in self.problems]
        self.cache=None
        self.representation_cache=None
        self.representation_labels=self.labels+[name+':frame-'+str(p.frame) for p in self.problems
            for name in ['saved-root-lower','saved-root-upper','saved-fixed-rotation']]

    def controls(self,x):
        x=np.asarray(x,dtype=float)
        if x.shape!=(self.dim,) or not np.isfinite(x).all():raise ValueError('Complete finite window controls required')
        return x

    def set_fixed_neighbors(self,positions):
        """Bind an explicit interval state's exterior keys; never rebase references."""
        expected={f for p in self.problems for f in p.neighbors if f not in self.frames}
        if not isinstance(positions,dict) or set(positions)!=expected or any(type(f) is not int for f in positions):
            raise ValueError('Every exterior neighbor and no internal/unknown frame required')
        arrays={f:np.asarray(value) for f,value in positions.items()}
        shape=(len(self.problems[0].names),3)
        if any(a.shape!=shape or a.dtype.kind!='f' or not np.isfinite(a).all() for a in arrays.values()):
            raise ValueError('Complete finite exterior native joint positions required')
        for p in self.problems:
            for frame in p.neighbors:
                if frame in arrays:p.neighbors[frame]=p.t(arrays[frame].copy())
            p.cache=None
        for sparse in self.sparse:sparse.cache=None;sparse.dependencies=None
        self.cache=None;self.representation_cache=None

    def geometry_slack(self,x):
        if (not isinstance(x,torch.Tensor) or x.shape!=(self.dim,) or x.dtype!=torch.float64
                or not torch.isfinite(x).all()):raise ValueError('Complete double-precision window controls required')
        positions={p.frame:p.fk(x[i*self.pose_dim:(i+1)*self.pose_dim])[1] for i,p in enumerate(self.problems)}
        values=[]
        for i,p in enumerate(self.problems):
            part=x[i*self.pose_dim:(i+1)*self.pose_dim]
            neighbors={frame:positions.get(frame,fixed) for frame,fixed in p.neighbors.items()}
            values.append(p.geometry_slack(part,neighbors=neighbors))
            angles=part[:-1].reshape(-1,3)
            values.append(1-(angles**2).sum(-1)/p.t(p.limits)**2)
        return torch.cat(values)

    def dense_pair(self,x):
        x=self.controls(x);variable=torch.as_tensor(x,dtype=torch.float64).requires_grad_()
        values=self.geometry_slack(variable)
        return values.detach().numpy(),row_jacobian(values,variable,self.row_chunk)

    def _build(self,x):
        x=self.controls(x)
        if self.cache is not None and np.array_equal(x,self.cache[0]):return self.cache[1:]
        parts=[x[i*self.pose_dim:(i+1)*self.pose_dim] for i in range(len(self.frames))]
        pairs=[sparse(part) for sparse,part in zip(self.sparse,parts)]
        local=[sparse.vector_linearization(part) for sparse,part in zip(self.sparse,parts)]
        positions={};derivatives={}
        for i,(p,v) in enumerate(zip(self.problems,local)):
            joints=len(p.names);start=len(p.contacts)+len(p.normals)
            body_start=len(p.labels)-(1+len(p.neighbors))*joints
            np.testing.assert_array_equal(v['rows'][start:start+joints],body_start+np.arange(joints))
            positions[p.frame]=v['offsets'][start:start+joints]+p.references['raw'].numpy()[p.frame]
            derivative=np.zeros((joints,3,self.dim))
            derivative[:,:,i*self.pose_dim:(i+1)*self.pose_dim]=v['jacobian'][start:start+joints]
            derivatives[p.frame]=derivative
        values=np.concatenate([pair[0] for pair in pairs]);jac=np.zeros((len(values),self.dim))
        records=[]
        for i,(p,v,pair) in enumerate(zip(self.problems,local,pairs)):
            row_start=self.row_starts[i];row_end=row_start+len(pair[0]);control_start=i*self.pose_dim
            jac[row_start:row_end,control_start:control_start+self.pose_dim]=pair[1]
            coupled={key:np.array(value,copy=True) for key,value in v.items()}
            coupled['jacobian']=np.zeros((len(v['rows']),3,self.dim))
            coupled['jacobian'][:,:,control_start:control_start+self.pose_dim]=v['jacobian']
            joints=len(p.names);start=len(p.contacts)+len(p.normals)
            body_start=len(p.labels)-(1+len(p.neighbors))*joints
            stride=(1+len(p.neighbors))*joints
            for reference_index,reference in enumerate(p.references.values()):
                ref=reference.numpy()
                for neighbor_index,(frame,fixed) in enumerate(sorted(p.neighbors.items())):
                    offset=start+reference_index*stride+(1+neighbor_index)*joints
                    ids=slice(offset,offset+joints)
                    np.testing.assert_array_equal(v['rows'][ids],body_start+(1+neighbor_index)*joints+np.arange(joints))
                    neighbor=positions.get(frame,fixed.numpy())
                    coupled['offsets'][ids]=((positions[p.frame]-ref[p.frame])-(neighbor-ref[frame]))*30
                    coupled['jacobian'][ids]=(derivatives[p.frame]-derivatives.get(frame,np.zeros_like(derivatives[p.frame])))*30
            speed_rows=range(body_start+joints,body_start+stride)
            for row in speed_rows:
                selected=coupled['rows']==row
                offsets=coupled['offsets'][selected];radii=coupled['limits'][selected]
                np.testing.assert_array_equal(radii,np.full(len(radii),radii[0]))
                squared=(offsets**2).sum(-1);active=squared==squared.max()
                gradients=-2*np.einsum('rk,rkd->rd',offsets,coupled['jacobian'][selected])/radii[:,None]**2
                values[row_start+row]=1-squared.max()/radii[0]**2;jac[row_start+row]=gradients[active].mean(0)
            coupled['rows']+=row_start;records.append(coupled)
        vectors={key:np.concatenate([record[key] for record in records]) for key in records[0]}
        if not np.isfinite(values).all() or not np.isfinite(jac).all():raise ValueError('Complete finite coupled derivatives required')
        self.cache=(x.copy(),values,jac,vectors)
        return values,jac,vectors

    def pair(self,x):return self._build(x)[:2]

    def vector_linearization(self,x):
        # The caller scales proposal derivatives; do not expose cached arrays.
        return {key:value.copy() for key,value in self._build(x)[2].items()}

    def independent(self,x):
        x=self.controls(x);motions=[]
        for i,p in enumerate(self.problems):
            motions.append(p.independent(x[i*self.pose_dim:(i+1)*self.pose_dim])[1])
        positions={p.frame:motion['posed_joints'][0] for p,motion in zip(self.problems,motions)}
        audits=[]
        for i,p in enumerate(self.problems):
            neighbors={frame:p.t(positions.get(frame,fixed.numpy())) for frame,fixed in p.neighbors.items()}
            audit,motion=p.independent(x[i*self.pose_dim:(i+1)*self.pose_dim],neighbors=neighbors)
            audits.append(dict(frame=p.frame,**audit))
            for key in motion:np.testing.assert_array_equal(motion[key],motions[i][key])
        motion={key:np.concatenate([item[key] for item in motions]) for key in motions[0]}
        return dict(frames=audits,window_checks_passed=all(a['pose_checks_passed'] for a in audits),
            scope='Complete keyed native window with coupled adjacent speeds and fixed exterior keys; no between-key, self-collision, anatomy, dynamics, engine or human certificate.',
            quality_approved=False,release_approved=False),motion

    def saved_representation(self,x,*,motion=None):
        """Complete rows from the same float32/projected arrays written to disk."""
        x=self.controls(x)
        cached=motion is None
        if cached and self.representation_cache is not None and np.array_equal(x,self.representation_cache[0]):
            return self.representation_cache[1].copy()
        if motion is None:_,motion=self.independent(x)
        positions={p.frame:p.t(motion['posed_joints'][i]) for i,p in enumerate(self.problems)}
        values=[];extra=[]
        for i,p in enumerate(self.problems):
            vertices=p.t(p.surface.vertices(motion['global_rot_mats'][i],motion['posed_joints'][i]))
            neighbors={f:positions.get(f,fixed) for f,fixed in p.neighbors.items()}
            values.extend(p.geometry_rows(positions[p.frame],vertices,neighbors=neighbors).detach().numpy())
            angles=Rotation.from_matrix(p.previous['local_rot_mats'][p.frame].transpose(0,2,1)@motion['local_rot_mats'][i]).magnitude()
            parameters=x[i*self.pose_dim:(i+1)*self.pose_dim][:-1].reshape(-1,3)
            values.extend(1-np.maximum((parameters**2).sum(-1),angles[p.editable]**2)/p.limits**2)
            lift=float(motion['root_positions'][i,1])-float(p.base['root_positions'][p.frame,1])
            fixed=[j for j in range(len(p.names)) if j not in p.editable]
            extra.extend([lift/p.config['max_root_lift_m'],1-lift/p.config['max_root_lift_m'],
                1-float(angles[fixed].max(initial=0))/1e-6])
        result=np.r_[values,extra]
        if result.shape!=(len(self.representation_labels),) or not np.isfinite(result).all():
            raise ValueError('Complete finite saved geometry and original rig/root bounds required')
        if cached:self.representation_cache=(x.copy(),result.copy())
        return result
