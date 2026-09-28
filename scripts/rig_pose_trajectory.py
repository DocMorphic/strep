"""Sparse joint goals on the existing bounded surface/support trajectory solver."""
import copy
import numpy as np
from rig_trajectory_fit import TrajectoryFitter,skew
from rig_clearance_fit import right_jacobian

class PoseTrajectoryFitter(TrajectoryFitter):
    def __init__(self,rig,spec,local,targets,envelope,supports,goals,settings=None):
        super().__init__(rig,spec,local,targets,envelope,supports,settings)
        if not isinstance(goals,list) or not 1<=len(goals)<=64:raise ValueError('Use1–64 sparse joint goals')
        self.goals=copy.deepcopy(goals);occupied=set()
        for goal in self.goals:
            if not isinstance(goal,dict) or set(goal)!={'frame','node','position_m','rotation_matrix','position_weight','rotation_weight','provenance'}:raise ValueError('Invalid joint goal fields')
            f,n=goal['frame'],goal['node']
            if type(f)is not int or not 0<=f<len(local) or self.envelope[f]<=0:raise ValueError('Joint goal must lie in editable frames')
            if type(n)is not int or n not in rig.joints or (f,n) in occupied:raise ValueError('Invalid or duplicate joint goal')
            if not self.descendants[spec['root_node']][n]:raise ValueError('Goal must descend from editable root')
            occupied.add((f,n));p=np.asarray(goal['position_m'],float);r=np.asarray(goal['rotation_matrix'],float)
            if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Finite XYZ goal required')
            if r.shape!=(3,3) or not np.isfinite(r).all() or not np.allclose(r.T@r,np.eye(3),atol=1e-5) or abs(np.linalg.det(r)-1)>1e-5:raise ValueError('Proper target orientation required')
            if any(type(goal[k])not in (int,float) or not np.isfinite(goal[k]) or not 0<goal[k]<=1000 for k in ['position_weight','rotation_weight']):raise ValueError('Positive finite goal weights required')
            if not isinstance(goal['provenance'],str) or not goal['provenance'].strip():raise ValueError('Target provenance required')
            goal['position_m']=p;goal['rotation_matrix']=r

    def joint_pair(self,frame,x,node):
        world,_=self.pose(frame,x);position=world[node,:3,3];rotation=world[node,:3,:3]
        jp=np.zeros((3,len(x)));jr=np.zeros((3,3,len(x)))
        if self.descendants[self.spec['root_node']][node]:jp[:,:3]=np.eye(3)
        for i,(edited,vector) in enumerate(zip(self.nodes,x[3:].reshape(-1,3))):
            if not self.descendants[edited][node]:continue
            axes=world[edited,:3,:3]@right_jacobian(vector);delta=position-world[edited,:3,3]
            for axis in range(3):
                column=3+3*i+axis;jp[:,column]=np.cross(axes[:,axis],delta);jr[:,:,column]=skew(axes[:,axis])@rotation
        return position,rotation,jp,jr

    def goal_pair(self,frame,x):
        residual=[];jacobian=[]
        for goal in self.goals:
            if goal['frame']!=frame:continue
            p,r,jp,jr=self.joint_pair(frame,x,goal['node'])
            residual.extend([(p-goal['position_m'])*goal['position_weight'],((r-goal['rotation_matrix'])*goal['rotation_weight']).ravel()])
            jacobian.extend([jp*goal['position_weight'],(jr*goal['rotation_weight']).reshape(9,len(x))])
        if not residual:return np.empty(0),np.empty((0,len(x)))
        return np.concatenate(residual),np.vstack(jacobian)

    def trajectory_pair(self,frame,x):
        r,j=super().trajectory_pair(frame,x);gr,gj=self.goal_pair(frame,x)
        return np.r_[r,gr],np.vstack([j,gj])
