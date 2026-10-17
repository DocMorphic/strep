"""Original world rows plus all evaluated-time displacement derivatives.

Native parameter permissions/balls, geometry and explicit rotation-speed policies
remain separate required conditions. This evaluator never selects an animation.
"""
import copy
from collections import OrderedDict
import numpy as np
from native_evaluated_world_rows import EvaluatedWorldRows
from native_complete_max_rows import CompleteMaxRows
from native_motion_rate_stencil import motion_rate_stencil,METRICS
from native_skin_frame_map import skin_frame_map

MAXIMUM_BYTES=64*1024**2


def _real(value):
    array=np.asarray(value)
    if array.dtype.kind not in 'fiu' or array.dtype.itemsize>8 or not np.isfinite(array).all():raise ValueError('Complete finite real arrays required')
    return array.astype(float,copy=True)


def _norm(vectors,derivative,cap,scale):
    norms=np.linalg.norm(vectors,axis=1);unit=np.divide(vectors,norms[:,None],out=np.zeros_like(vectors),where=norms[:,None]>0)
    return (norms-cap)/scale,np.einsum('vi,vic->vc',unit,derivative)/np.asarray(scale)[...,None]


class EvaluatedWorldDerivatives:
    def __init__(self,world_rows,columns,*,temperature=1e-5,maximum_jacobian_bytes=MAXIMUM_BYTES,
                 maximum_world_cache_bytes=MAXIMUM_BYTES,maximum_contact_cache_bytes=MAXIMUM_BYTES,maximum_skin_bytes=8*1024**2):
        if type(world_rows) is not EvaluatedWorldRows or type(columns) is not int or not 1<=columns<=768:
            raise ValueError('Complete evaluated-time world evaluator and explicit full derivative count required')
        for budget in [maximum_jacobian_bytes,maximum_world_cache_bytes,maximum_contact_cache_bytes,maximum_skin_bytes]:
            if type(budget) is not int or not 1<=budget<=MAXIMUM_BYTES:raise ValueError('Explicit complete bounded storage budgets required')
        self._oracle=copy.deepcopy(world_rows);self._p=self._oracle._problem;self._columns=columns
        self._p.scene.check_inputs();self._groups=[];self._blocks={};self._limits=(maximum_jacobian_bytes,maximum_world_cache_bytes,maximum_contact_cache_bytes,maximum_skin_bytes)
        for kind,name,detail,first,last in self._oracle.layout:
            frames=len(self._oracle._extra) if kind=='evaluated_displacement' else len(self._p.uniform)
            ranges=[(first+j*frames,first+(j+1)*frames) for j in range(len(self._p.scene.actors[name]['rig'].joints))] if kind in ('displacement','evaluated_displacement') else [(first,last)]
            numbers=[]
            for start,stop in ranges:
                index=len(self._groups);numbers.append(index);self._groups.append(dict(id='g'+str(index),rows=stop-start,first=start,last=stop,kind=kind,name=name,detail=detail))
            self._blocks[(kind,name,detail)]=numbers
        assert self._groups[0]['first']==0 and self._groups[-1]['last']==self._oracle.report['rows'] and all(a['last']==b['first'] for a,b in zip(self._groups,self._groups[1:]))
        self._partition=[dict(id=g['id'],rows=g['rows']) for g in self._groups]
        CompleteMaxRows(self._partition,derivative_columns=columns,temperature=temperature,maximum_jacobian_bytes=maximum_jacobian_bytes)
        self._temperature=temperature
        largest=max(len(a['rig'].document['nodes'])*16*8*(1+columns) for a in self._p.scene.actors.values())
        stencil=max(3*len(a['rig'].joints)*16*8*columns for a in self._p.scene.actors.values())
        if 3*largest>maximum_world_cache_bytes or stencil>maximum_jacobian_bytes:raise ValueError('Complete three-frame world/derivative stencil exceeds budget')
        for data in self._p.rows:
            entry=data['entry'];row=entry['authored'];points=1 if row['reduction']=='centroid' else len(entry['ids'])
            if 2*points*3*8*(1+columns)>maximum_contact_cache_bytes:raise ValueError('Complete two-frame contact cache exceeds budget')
            names=[row['actor']]+([row['target']['actor']] if row['target']['space']=='actor' else [])
            if any(self._p.scene.actors[name]['skin'].nodes.shape[1]*3*4*8*(1+columns)>maximum_skin_bytes for name in names):
                raise ValueError('One complete skin vertex/influence/column batch exceeds budget')
        self._report=dict(schema='strep-native-evaluated-world-derivatives-v1',rows=self._oracle.report['rows'],groups=len(self._groups),columns=columns,
            original_rows=self._oracle.report['original_rows'],appended_rows=self._oracle.report['appended_rows'],
            original_groups=sum(g['kind']!='evaluated_displacement' for g in self._groups),
            additional_displacement_times=len(self._oracle._extra),
            times=len(self._oracle.times),original_scalar_anchor='unchanged EvaluatedWorldRows.violations with byte-identical original prefix',
            group_order='Original groups first unchanged, then complete evaluated-time displacement refined per joint in joint-major time order',
            grouped_jacobian_bytes=len(self._groups)*columns*8,maximum_jacobian_bytes=maximum_jacobian_bytes,
            maximum_world_cache_bytes=maximum_world_cache_bytes,maximum_contact_cache_bytes=maximum_contact_cache_bytes,maximum_skin_bytes=maximum_skin_bytes,
            native_parameter_conditions_included=False,surface_geometry_included=False,explicit_rotation_speed_policy_included=False,
            zero_norm_derivative='zero symmetric subgradient; not structural infeasibility',original_selected=True,quality_approved=False,release_approved=False)

    @property
    def report(self):return copy.deepcopy(self._report)
    @property
    def columns(self):return self._columns
    @property
    def partition(self):return copy.deepcopy(self._groups)
    @property
    def times(self):return self._oracle.times

    def _callbacks(self,callbacks):
        if not isinstance(callbacks,dict) or set(callbacks)!=set(self._p.edits.actors) or any(not callable(c) for c in callbacks.values()):
            raise ValueError('One explicit pose callback for every edited actor required')

    def _call(self,callbacks,name,index,derivatives):
        actor=self._p.scene.actors[name];expected=self._p.source_world[name][index]
        if name not in callbacks:return expected.copy(),np.zeros(expected.shape+(self.columns,)) if derivatives else None
        result=callbacks[name](float(self._p.times[index]),derivatives)
        if not isinstance(result,tuple) or len(result)!=2:raise ValueError('Callback must return the complete world and explicit derivative/None pair')
        world=_real(result[0]);matrix=None
        if world.shape!=expected.shape or not np.array_equal(world[:,3,:],expected[:,3,:]):raise ValueError('Matching complete affine hierarchy required')
        if derivatives:
            raw=np.asarray(result[1])
            if raw.shape!=world.shape+(self.columns,) or raw.size*8>self._limits[0]:raise ValueError('Complete callback world Jacobian must fit every declared column')
            matrix=_real(raw)
            if np.any(matrix[:,3,:]):raise ValueError('Homogeneous world derivatives must be zero')
        elif result[1] is not None:raise ValueError('Value-only callback must return explicit None derivatives')
        return world,matrix

    def _anchor(self,callbacks):
        self._callbacks(callbacks);self._p.scene.check_inputs();worlds=self._oracle.source_worlds()
        for name in callbacks:
            for index in range(len(self._p.times)):worlds[name][index]=self._call(callbacks,name,index,False)[0]
        values=self._oracle.violations(worlds);return worlds,values

    def values(self,callbacks):
        worlds,anchor=self._anchor(callbacks);aggregate=CompleteMaxRows(self._partition,temperature=self._temperature)
        for group,g in enumerate(self._groups):
            for start in range(0,g['rows'],4096):aggregate.append(group,start,anchor[g['first']+start:min(g['last'],g['first']+start+4096)])
        result=aggregate.finalize();self._p.scene.check_inputs()
        return dict(result,original_violations=anchor,composition=copy.deepcopy(self._report))

    def evaluate(self,callbacks):
        worlds,anchor=self._anchor(callbacks);p=self._p;maximum_bytes,cache_budget,contact_budget,skin_budget=self._limits
        aggregate=CompleteMaxRows(self._partition,derivative_columns=self.columns,temperature=self._temperature,maximum_jacobian_bytes=maximum_bytes)
        cache=OrderedDict();cache_bytes=0;peak=0;calls=0;local_difference=0.
        def pose(name,index):
            nonlocal cache_bytes,peak,calls
            key=(name,int(index))
            if key in cache:cache.move_to_end(key);return cache[key]
            world,matrix=self._call(callbacks,name,index,True);calls+=1
            if world.tobytes()!=worlds[name][index].tobytes():raise ValueError('Derivative callback pose differs from the original value-pass anchor')
            size=world.nbytes+matrix.nbytes
            while cache and cache_bytes+size>cache_budget:
                _,old=cache.popitem(last=False);cache_bytes-=old[0].nbytes+old[1].nbytes
            if size>cache_budget:raise ValueError('One complete derivative pose exceeds the cache budget')
            cache[key]=(world,matrix);cache_bytes+=size;peak=max(peak,cache_bytes);return world,matrix
        def feed(group,start,values,matrix):
            nonlocal local_difference
            g=self._groups[group];values=np.asarray(values).ravel();matrix=np.asarray(matrix);exact=anchor[g['first']+start:g['first']+start+len(values)]
            if matrix.shape!=(len(values),self.columns) or exact.shape!=values.shape or not np.isfinite(values).all():raise ValueError('Complete matching local derivative row population required')
            difference=np.abs(values-exact);local_difference=max(local_difference,float(difference.max()))
            if np.any(difference>1e-10*(1+np.abs(exact))):raise ValueError('Local derivative arithmetic is inconsistent with the unchanged scalar anchor')
            for offset in range(0,len(values),4096):aggregate.append(group,start+offset,exact[offset:offset+4096],jacobian=matrix[offset:offset+4096])
        for name in p.edits.actors:
            actor=p.scene.actors[name];joints=actor['rig'].joints;cap=p.caps[name];bounds=p.edits.actors[name]['displacement'].ravel();groups=self._blocks[('displacement',name,None)]
            for index in range(len(p.uniform)):
                world,matrix=pose(name,int(p.rate_ids[index]));delta=world[joints,:3,3]-p.source_world[name][p.rate_ids[index]][joints,:3,3]
                rows,jac=_norm(delta,matrix[joints,:3,3,:],bounds,bounds)
                for joint,group in enumerate(groups):feed(group,index,rows[joint:joint+1],jac[joint:joint+1])
                for metric_index,metric in enumerate(METRICS):
                    order=2 if metric_index in (1,3) else 1
                    if index<order:continue
                    samples=[pose(name,int(p.rate_ids[at])) for at in range(index-order,index+1)]
                    sampled_world=np.stack([w[joints] for w,j in samples]);sampled_jac=np.stack([j[joints] for w,j in samples]);start=index-order
                    rows,jac,_=motion_rate_stencil(metric,sampled_world,cap.caps[metric_index][start],cap.dt,jacobian=sampled_jac,tolerance=cap.tolerance,maximum_jacobian_bytes=maximum_bytes)
                    feed(self._blocks[('source_rate',name,metric)][0],start*len(joints),rows,jac)
        for data in p.rows:
            entry=data['entry'];row=entry['authored'];target=row['target'];errors=OrderedDict()
            def error(index):
                if index in errors:errors.move_to_end(index);return errors[index]
                global_index=int(data['ids'][index]);world,matrix=pose(row['actor'],global_index)
                effector,ej,_=skin_frame_map(p.scene.actors[row['actor']]['skin'],world,p.scene.actors[row['actor']]['placement'],entry['ids'],'centroid' if row['reduction']=='centroid' else 'vertices',jacobian=matrix,maximum_jacobian_bytes=maximum_bytes,maximum_working_bytes=skin_budget)
                if target['space']=='actor':
                    world,matrix=pose(target['actor'],global_index)
                    goal,gj,_=skin_frame_map(p.scene.actors[target['actor']]['skin'],world,p.scene.actors[target['actor']]['placement'],entry['target_ids'],'centroid' if target['reduction']=='centroid' else 'vertices',jacobian=matrix,maximum_jacobian_bytes=maximum_bytes,maximum_working_bytes=skin_budget)
                elif target['space']=='world':goal=entry['target_ids'];gj=np.zeros(goal.shape+(self.columns,))
                else:
                    position,rotation=data['object_pose'];goal=entry['target_ids']@rotation[index].T+position[index];gj=np.zeros(goal.shape+(self.columns,))
                vector=effector-goal;jac=ej-gj
                if target['space']=='object':vector=vector@rotation[index];jac=np.einsum('vic,ij->vjc',jac,rotation[index])
                if 2*(vector.nbytes+jac.nbytes)>contact_budget:raise ValueError('Complete contact error pair exceeds cache budget')
                if len(errors)==2:errors.popitem(last=False)
                errors[index]=(vector,jac);return vector,jac
            group=self._blocks[('contact_position',row['id'],target['space'])][0];limit=row['limits']['position_m'];points=self._groups[group]['rows']//len(data['times'])
            for index in range(len(data['times'])):
                vector,jac=error(index);rows,matrix=_norm(vector,jac,limit,max(limit,.0001));feed(group,index*points,rows,matrix)
            for population in data['populations']:
                detail=(population['rate_hz'],population['phase_offset_frames']);group=self._blocks[('contact_speed',row['id'],detail)][0];clock=population['times_s']
                if len(clock)<2:feed(group,0,[1.],np.zeros((1,self.columns)));continue
                ids=np.searchsorted(data['times'],clock);np.testing.assert_array_equal(data['times'][ids],clock);limit=row['limits']['relative_speed_m_s']
                for index in range(len(clock)-1):
                    left,lj=error(int(ids[index]));right,rj=error(int(ids[index+1]));rate=population['rate_hz']
                    rows,matrix=_norm((right-left)*rate,(rj-lj)*rate,limit,max(limit,.001));feed(group,index*points,rows,matrix)
        # Stream the appended exact-time bands through the same bounded pose
        # cache. Never allocate [times,joints,xyz,columns] for the whole clip.
        for name in p.edits.actors:
            groups=self._blocks.get(('evaluated_displacement',name,None),[])
            if not groups:continue
            joints=p.scene.actors[name]['rig'].joints;bounds=p.edits.actors[name]['displacement'].ravel()
            for local,index in enumerate(self._oracle._extra):
                world,matrix=pose(name,int(index));delta=world[joints,:3,3]-p.source_world[name][index][joints,:3,3]
                rows,jac=_norm(delta,matrix[joints,:3,3,:],bounds,bounds)
                for joint,group in enumerate(groups):feed(group,local,rows[joint:joint+1],jac[joint:joint+1])
        result=aggregate.finalize();p.scene.check_inputs()
        composition=dict(self._report,derivative_pose_queries=calls,peak_world_cache_bytes=peak,maximum_local_value_comparison_difference=local_difference,
            scope='Every original anchored world scalar plus joint displacement at every already-evaluated exact time, with every supplied derivative column. Original groups/rows remain an unchanged prefix. Exact groups preserve physical verdicts; smooth guidance is stronger, not infeasibility. Native permissions/balls, geometry, explicit speed policies, encoded output, engine and human acceptance remain separate. No optimization or selection.')
        return dict(result,original_violations=anchor,composition=composition)
