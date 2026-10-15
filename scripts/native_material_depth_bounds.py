"""Conditional depth bounds to actual moving partner triangles.

For a tracked point p and a convex material point q on a target triangle,
distance to that surface is <= ||p-q||. A protected distance to q therefore
bounds inside depth for that point. New contacts, volume validity, crossing
counts and complete geometry still require independent observation.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_scene_geometry import faces_for


def require(value,message):
    if not value:raise ValueError(message)


class MaterialDepthBounds:
    def __init__(self,pair,reference_worlds,*,maximum_rows=20000):
        pair.check();pair.validate_worlds(reference_worlds)
        require(type(maximum_rows) is int and 1<=maximum_rows<=100000,'Explicit material-row budget required')
        require(pair.surface is not None,'Explicit partner surface witnesses required')
        self.pair=pair;self.row_ids=[];packed={};faces={n:faces_for(m.rig)[0] for n,m in pair.models.items()}
        for index,row in enumerate(pair.surface.rows):
            if row['kind']!='penetrating-vertex':continue
            require(len(self.row_ids)<maximum_rows,'Complete material rows exceed budget; none discarded')
            left,right=row['left'],row['right'];triangle=row.get('target_triangle')
            require(right is not None and left['actor']!=right['actor'] and len(left['vertices'])==1
                and left['weights']==[1.],'One explicit source vertex and distinct partner required')
            require(type(triangle) is int and 0<=triangle<len(faces[right['actor']])
                and right['vertices']==faces[right['actor']][triangle].tolist(),'Actual canonical target triangle required')
            weights=np.asarray(right['weights'],float)
            require(weights.shape==(3,) and np.isfinite(weights).all() and np.all(weights>=0)
                and abs(weights.sum()-1)<1e-10,'Convex target-triangle material point required')
            key=(row['time_s'],left['actor'],right['actor']);group=packed.setdefault(key,dict(indices=[],left=[],right=[],weights=[]))
            group['indices'].append(len(self.row_ids));group['left'].append(left['vertices'][0]);group['right'].append(right['vertices']);group['weights'].append(weights.copy())
            self.row_ids.append(index)
        require(bool(self.row_ids),'No inside-vertex material witnesses declared')
        self.groups=[];self.labels=[];self.group_ids=np.empty(len(self.row_ids),int)
        for group_id,(key,data) in enumerate(packed.items()):
            time,source,target=key;stamp=int(np.searchsorted(pair.times,time));require(pair.times[stamp]==time,'Existing material sample time required')
            group=dict(time_s=time,source=source,target=target,stamp=stamp,**{k:np.array(v,dtype=float if k=='weights' else int) for k,v in data.items()})
            self.groups.append(group);self.labels.append(key);self.group_ids[group['indices']]=group_id
        self.reference_vectors=self.vectors(reference_worlds);lengths=np.linalg.norm(self.reference_vectors,axis=1)
        self.group_caps=np.array([lengths[g['indices']].max() for g in self.groups])
        self.caps=self.group_caps[self.group_ids].copy();self.scales=np.maximum(self.caps,.001)
        self._caps=self.caps.copy();self._scales=self.scales.copy()

    def check(self):
        self.pair.check()
        require(np.array_equal(self.caps,self._caps) and np.array_equal(self.scales,self._scales),'Original material reference bounds changed')

    def vectors(self,worlds):
        self.pair.validate_worlds(worlds);values=np.empty((len(self.row_ids),3))
        for group in self.groups:
            a,b=group['source'],group['target'];stamp=np.array([group['stamp']])
            left=self.pair.models[a].points(worlds[a],group['left'],stamp)[0]
            right=self.pair.models[b].points(worlds[b],group['right'].ravel(),stamp)[0].reshape(-1,3,3)
            values[group['indices']]=left-np.einsum('nv,nvi->ni',group['weights'],right)
        require(np.isfinite(values).all(),'Finite complete material vectors required')
        return values

    def rows(self,worlds):
        self.check();return NormRows(self.vectors(worlds),self.caps.copy(),self.scales.copy())

    def linearize(self,value,worlds,*,step=.001,maximum_nonzeros=1000000):
        self.check();p=self.pair;value=p.controls(value);base=self.rows(worlds)
        require(type(step) in (int,float) and np.isfinite(step) and 1e-6<=step<=.01,'Explicit finite material difference step required')
        require(type(maximum_nonzeros) is int and maximum_nonzeros>0,'Positive complete material Jacobian budget required')
        proxy_world=p.worlds(value,quantized=False);proxy=self.vectors(proxy_world)
        data=[];indices=[];pointers=[0];steps=[];structural=[]
        for column in range(p.size):
            actor_index=int(np.searchsorted(p.offsets[1:],column,side='right'))
            if actor_index==len(p.names):
                pointers.append(pointers[-1]);steps.append(0.);structural.append(column);continue
            name=p.names[actor_index];m=p.models[name];local=column-int(p.offsets[actor_index])
            key=int(m.active[local//(3*len(m.active_tracks))]);lo=-np.inf if key==0 else m.clock[key-1];hi=np.inf if key==len(m.clock)-1 else m.clock[key+1]
            responds=any(g['source']==name or g['target']==name for g in self.groups if lo<g['time_s']<hi)
            if not responds:
                pointers.append(pointers[-1]);steps.append(0.);structural.append(column);continue
            h=step if p.upper[column]-value[column]>=value[column]-p.lower[column] else -step
            h=np.copysign(min(abs(h),p.upper[column]-value[column] if h>0 else value[column]-p.lower[column]),h)
            require(h!=0,'No finite material difference room');other=value.copy();other[column]+=h
            changed=dict(proxy_world);changed[name]=m.worlds(other[p.offsets[actor_index]:p.offsets[actor_index+1]],quantized=False)
            derivative=((self.vectors(changed)-proxy)/h).ravel();nonzero=np.flatnonzero(derivative)
            require(pointers[-1]+len(nonzero)<=maximum_nonzeros,'Complete material Jacobian exceeds budget; none discarded')
            data.append(derivative[nonzero]);indices.append(nonzero);pointers.append(pointers[-1]+len(nonzero));steps.append(float(h))
        jac=sparse.csc_matrix((np.concatenate(data) if data else np.empty(0),np.concatenate(indices) if indices else np.empty(0,int),pointers),shape=(base.vectors.size,p.size))
        self.check()
        return base,jac,dict(material_rows=len(self.row_ids),groups=[dict(time_s=t,source=a,target=b,reference_distance_m=float(self.group_caps[i])) for i,(t,a,b) in enumerate(self.labels)],
            original_surface_row_ids=self.row_ids,controls=p.size,sparse_nonzeros=jac.nnz,actual_difference_steps=steps,
            structurally_zero_columns=structural,zero_policy='Exact native-key open support intervals and independent plane-offset variables only',
            scope='Decoded material-vector anchor with continuous native differences. Bounds cover tracked vertices only, not new contacts, crossings or complete geometry. Source native motion limits remain separate.',
            quality_approved=False,release_approved=False)


def append_hard(system,jacobian,hard_rows,material,material_jacobian,*,maximum_nonzeros=6000000):
    jacobian,material_jacobian=map(sparse.csc_matrix,(jacobian,material_jacobian))
    require(isinstance(system,NormRows) and isinstance(material,NormRows) and type(hard_rows) is int and 1<=hard_rows<=len(system.caps),
        'Complete parent norms and explicit hard prefix required')
    require(jacobian.shape[0]==system.vectors.size and material_jacobian.shape==(material.vectors.size,jacobian.shape[1])
        and np.isfinite(jacobian.data).all() and np.isfinite(material_jacobian.data).all(),'Matching finite parent/material Jacobians required')
    require(type(maximum_nonzeros) is int and maximum_nonzeros>0 and jacobian.nnz+material_jacobian.nnz<=maximum_nonzeros,
        'Complete combined Jacobian exceeds budget; none discarded')
    result=NormRows(np.r_[system.vectors[:hard_rows],material.vectors,system.vectors[hard_rows:]],
        np.r_[system.caps[:hard_rows],material.caps,system.caps[hard_rows:]],np.r_[system.scales[:hard_rows],material.scales,system.scales[hard_rows:]])
    derivative=sparse.vstack([jacobian[:3*hard_rows],material_jacobian,jacobian[3*hard_rows:]],format='csc')
    return result,derivative,dict(parent_hard_rows=hard_rows,material_hard_rows=len(material.caps),hard_rows=hard_rows+len(material.caps),
        original_parent_rows_caps_scales_retained=True,original_soft_rows_retained=True,quality_approved=False,release_approved=False)
