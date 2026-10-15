"""Joint native-key approach proposals with original motion bounds held hard.

Guides are explicit sampled surface-region halfspaces, not collision acceptance.
Contacts and floor retain separate original-authority results; a failed source
condition may be protected against worsening without becoming a passing one.
"""
import copy
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_surface_lift import lift


def require(value,message):
    if not value:raise ValueError(message)


class PairKeyGuides:
    def __init__(self,models,guides,*,surface_rows=None):
        require(isinstance(models,dict) and len(models)==2,'Two explicit actor interval models required')
        self.models=dict(models);self.names=list(models);first=models[self.names[0]]
        require(set(first.scene.actors)==set(models),'Complete two-actor scene required')
        for name,model in models.items():
            model.check()
            require(model.name==name and model.digest==first.digest and model.policy==first.policy
                and np.array_equal(model.times,first.times),'Same original scene, policy and complete clock required')
            require(not np.any(model.seed),'Original zero-key source epoch required; no inherited correction seed')
        self.times=first.times.copy();self.scene=first.scene
        self.sizes=[models[n].size for n in self.names];self.offsets=np.r_[0,np.cumsum(self.sizes)]
        require(isinstance(guides,list),'Explicit complete regional guide list required')
        self.guides=copy.deepcopy(guides)
        self.surface=None
        from native_scene_geometry import faces_for
        used={n:set(np.unique(faces_for(m.rig)[0]).tolist()) for n,m in models.items()}
        if surface_rows is not None:
            from native_partner_surface_rows import SurfaceRows
            require(isinstance(surface_rows,SurfaceRows) and surface_rows.scene is self.scene,
                'Surface rows must bind the exact original interval scene instance')
            require(isinstance(surface_rows.rows,list) and bool(surface_rows.rows),'Explicit nonempty surface population required')
            for row in surface_rows.rows:
                require(isinstance(row,dict),'Explicit surface row object required')
                require(row.get('kind') in ('world-plane','triangle-separation','penetrating-vertex','primitive-triangle','primitive-center-enclosure'),
                    'Explicit supported surface row kind required')
                require(type(row.get('time_s')) in (int,float) and np.isfinite(row['time_s'])
                    and np.count_nonzero(self.times==row['time_s'])==1,'Existing complete-clock surface time required')
                normal=np.asarray(row.get('normal_world'))
                require(normal.dtype.kind in 'fiu' and normal.shape==(3,) and np.isfinite(normal).all()
                    and abs(np.linalg.norm(normal)-1)<1e-8,'Finite unit surface normal required')
                for key in ('constant_m','clearance_m'):
                    require(type(row.get(key)) in (int,float) and np.isfinite(row[key]),'Finite surface constants required')
                require(0<=row['clearance_m']<=.005,'Explicit surface clearance inside original guide budget required')
                for side in ('left','right'):
                    entry=row.get(side)
                    if side=='right' and entry is None:continue
                    require(isinstance(entry,dict) and entry.get('actor') in self.models,'Existing surface actor required')
                    ids=entry.get('vertices');weights=np.asarray(entry.get('weights'))
                    require(isinstance(ids,list) and bool(ids) and all(type(v) is int and v in used[entry['actor']] for v in ids)
                        and len(ids)==len(set(ids)),'Distinct existing surface vertices required')
                    require(weights.dtype.kind in 'fiu' and weights.shape==(len(ids),) and np.isfinite(weights).all()
                        and np.all(weights>=0) and abs(weights.sum()-1)<1e-10,'Complete convex surface weights required')
            self.surface=SurfaceRows(self.scene,copy.deepcopy(surface_rows.rows),copy.deepcopy(surface_rows.report))
        require(bool(guides) or self.surface is not None,'Nonempty regional or local surface guidance required')
        expected={'time_s','left_actor','right_actor','axis_world','vertices','midpoint_m','maximum_shift_m','clearance_m','reserve_m'}
        for guide in self.guides:
            require(isinstance(guide,dict) and set(guide)==expected,'Exact explicit guide fields required')
            require({guide['left_actor'],guide['right_actor']}==set(models),'Both distinct guide actors required')
            for key in ('time_s','midpoint_m','maximum_shift_m','clearance_m','reserve_m'):
                require(type(guide[key]) in (int,float) and np.isfinite(guide[key]),'Finite numeric guide settings required')
            require(guide['maximum_shift_m']>0 and guide['clearance_m']>=0 and guide['reserve_m']>=0,'Positive shift and nonnegative clearance/reserve required')
            axis=np.asarray(guide['axis_world'])
            require(axis.dtype.kind in 'fiu' and axis.shape==(3,) and np.isfinite(axis).all()
                and abs(np.linalg.norm(axis)-1)<1e-10,'Explicit finite unit guide axis required')
            require(np.count_nonzero(self.times==guide['time_s'])==1,'Guide must use an existing complete-clock time')
            require(isinstance(guide['vertices'],dict) and set(guide['vertices'])==set(models),'Both complete explicit vertex regions required')
            for name,ids in guide['vertices'].items():
                require(isinstance(ids,list) and bool(ids) and all(type(i) is int and i in used[name] for i in ids)
                    and len(ids)==len(set(ids)),'Distinct existing triangle-referenced region vertices required')
        self.size=int(sum(self.sizes)+len(guides));require(self.size<=768,'Joint proposal exceeds explicit 768-component budget')
        self.lower=np.full(self.size,-1.);self.upper=np.full(self.size,1.);self.initial=np.zeros(self.size)
        self.source_worlds={n:m.source_world for n,m in models.items()}
        native,contacts=self.norms(self.initial,self.source_worlds)
        require(np.all(native.residual()<=0),'Original native motion must satisfy its unchanged bounds')
        self.native_caps=native.caps.copy();self.native_scales=native.scales.copy()
        self.contact_caps=np.empty(0) if contacts is None else contacts.caps.copy()
        self.contact_scales=np.empty(0) if contacts is None else contacts.scales.copy()
        self.protected_contact_caps=np.empty(0) if contacts is None else np.maximum(contacts.caps,np.linalg.norm(contacts.vectors,axis=1))
        self.source_floor={n:m.floor(m.source_world)[0] for n,m in models.items()}

    def check(self):
        for model in self.models.values():model.check()

    def controls(self,value):
        value=np.asarray(value)
        require(value.dtype.kind in 'fiu' and value.shape==(self.size,) and np.isfinite(value).all()
            and np.all(value>=self.lower) and np.all(value<=self.upper),'Complete finite joint controls inside original boxes required')
        return value.astype(float,copy=True)

    def worlds(self,value,*,quantized=True):
        value=self.controls(value)
        return {n:self.models[n].worlds(value[self.offsets[i]:self.offsets[i+1]],quantized=quantized) for i,n in enumerate(self.names)}

    def validate_worlds(self,worlds):
        require(isinstance(worlds,dict) and set(worlds)==set(self.models),'Complete observed actor population required')
        for n,m in self.models.items():
            require(np.shape(worlds[n])==m.source_world.shape and np.isfinite(worlds[n]).all(),'Complete finite actor worlds required')

    def norms(self,value,worlds):
        value=self.controls(value);self.validate_worlds(worlds);native=[]
        for i,n in enumerate(self.names):
            m=self.models[n];rows=m.rows(value[self.offsets[i]:self.offsets[i+1]],worlds[n])
            independent=len(m.times)*(len(m.nodes)+len(m.rig.joints))
            ids=np.r_[np.arange(independent),np.arange(m.edit_count,len(rows.caps))]
            native.append(NormRows(rows.vectors[ids],rows.caps[ids],rows.scales[ids]))
        vectors=[];caps=[];scales=[]
        def add(v,cap,scale):
            v=np.asarray(v).reshape(-1,3);vectors.append(v);caps.append(np.full(len(v),cap));scales.append(np.full(len(v),scale))
        # Rebuild contact errors from BOTH edited actors, rather than keeping the
        # other actor at its original pose as a single-actor interval does.
        for data in self.models[self.names[0]].contact_rows:
            entry=data['entry'];row=entry['authored'];target=row['target'];clock=data['times'];ids=np.searchsorted(self.times,clock)
            def points(name,refs,reduction):
                p=self.models[name].points(worlds[name],refs,ids)
                return p.mean(1,keepdims=True) if reduction=='centroid' else p
            left=points(row['actor'],entry['ids'],row['reduction'])
            if target['space']=='actor':right=points(target['actor'],entry['target_ids'],target['reduction'])
            elif target['space']=='world':right=np.repeat(entry['target_ids'][None],len(ids),axis=0)
            else:
                p,r=self.scene.object_poses(target['object'],clock);right=np.einsum('fij,vj->fvi',r,entry['target_ids'])+p[:,None]
            error=left-right
            if target['space']=='object':error=np.einsum('fvi,fij->fvj',error,r)
            limit=row['limits']['position_m'];add(error,limit,max(limit,.0001))
            for pop in data['populations']:
                if len(pop['times_s'])<2:add(np.zeros((1,3)),-1.,1.);continue
                stamps=np.searchsorted(clock,pop['times_s']);limit=row['limits']['relative_speed_m_s']
                add(np.diff(error[stamps],axis=0)*pop['rate_hz'],limit,max(limit,.001))
        native=NormRows(np.concatenate([r.vectors for r in native]),np.concatenate([r.caps for r in native]),np.concatenate([r.scales for r in native]))
        contacts=NormRows(np.concatenate(vectors),np.concatenate(caps),np.concatenate(scales)) if vectors else None
        if hasattr(self,'native_caps'):
            require(np.array_equal(native.caps,self.native_caps) and np.array_equal(native.scales,self.native_scales)
                and np.array_equal(np.empty(0) if contacts is None else contacts.caps,self.contact_caps)
                and np.array_equal(np.empty(0) if contacts is None else contacts.scales,self.contact_scales),'Original joint native/contact caps, scales or populations changed')
        return native,contacts

    def guide_gaps(self,value,worlds):
        value=self.controls(value);self.validate_worlds(worlds);gaps=[]
        for i,guide in enumerate(self.guides):
            stamp=int(np.searchsorted(self.times,guide['time_s']));axis=np.asarray(guide['axis_world']);mid=guide['midpoint_m']+guide['maximum_shift_m']*value[sum(self.sizes)+i]
            for name,sign in ((guide['left_actor'],-1),(guide['right_actor'],1)):
                points=self.models[name].points(worlds[name],np.array(guide['vertices'][name]),np.array([stamp]))[0]
                gaps.append(sign*(points@axis-mid)-guide['clearance_m']/2-guide['reserve_m'])
        if self.surface is not None:
            def posed(name,time):
                model=self.models[name];stamp=int(np.searchsorted(self.times,time))
                return model.points(worlds[name],np.arange(len(model.skin.nodes)),np.array([stamp]))[0]
            gaps.append(self.surface.gaps(posed)-np.array([row['clearance_m'] for row in self.surface.rows]))
        return np.concatenate(gaps)

    def linearize(self,value,worlds,trust,*,step=.001,maximum_nonzeros=3_000_000):
        self.check();value=self.controls(value);self.validate_worlds(worlds)
        require(type(step) in (int,float) and np.isfinite(step) and 1e-6<=step<=.01,'Explicit finite difference step required')
        require(type(maximum_nonzeros) is int and maximum_nonzeros>0,'Positive complete Jacobian budget required')
        base,contact=self.norms(value,worlds);guide=self.guide_gaps(value,worlds)
        floor={n:self.models[n].floor(worlds[n]) for n in self.names}
        floor_gaps=np.concatenate([floor[n][0]-np.minimum(0,self.source_floor[n]) for n in self.names])
        smooth_world=self.worlds(value,quantized=False);smooth,smooth_contact=self.norms(value,smooth_world)
        smooth_guide=self.guide_gaps(value,smooth_world)
        def witnesses(other):return np.concatenate([self.models[n].witness_gaps(other[n],floor[n][1]) for n in self.names])
        smooth_floor=witnesses(smooth_world)
        base_vectors=base.vectors if contact is None else np.r_[base.vectors,contact.vectors]
        smooth_vectors=smooth.vectors if smooth_contact is None else np.r_[smooth.vectors,smooth_contact.vectors]
        data=[];indices=[];pointers=[0];gdata=[];gindices=[];gpointers=[0];actual_steps=[];count=0
        for column in range(self.size):
            h=step if self.upper[column]-value[column]>=value[column]-self.lower[column] else -step
            h=np.copysign(min(abs(h),self.upper[column]-value[column] if h>0 else value[column]-self.lower[column]),h)
            require(h!=0,'No finite difference room');other=value.copy();other[column]+=h
            changed=self.worlds(other,quantized=False);n,c=self.norms(other,changed)
            vectors=n.vectors if c is None else np.r_[n.vectors,c.vectors]
            derivative=((vectors-smooth_vectors)/h).ravel()
            gd=np.r_[(witnesses(changed)-smooth_floor)/h,(self.guide_gaps(other,changed)-smooth_guide)/h]
            ids=np.flatnonzero(derivative);gids=np.flatnonzero(gd);count+=len(ids)+len(gids)
            require(count<=maximum_nonzeros,f'Complete joint Jacobian has {count} entries at column {column}, exceeding budget {maximum_nonzeros}; no entries discarded')
            data.append(derivative[ids]);indices.append(ids);pointers.append(pointers[-1]+len(ids))
            gdata.append(gd[gids]);gindices.append(gids);gpointers.append(gpointers[-1]+len(gids));actual_steps.append(float(h))
        jac=sparse.csc_matrix((np.concatenate(data),np.concatenate(indices),pointers),shape=(base_vectors.size,self.size))
        gjac=sparse.csc_matrix((np.concatenate(gdata),np.concatenate(gindices),gpointers),shape=(len(floor_gaps)+len(guide),self.size))
        scalar=np.r_[floor_gaps,guide];lifted,ljac,identity=lift(scalar,gjac,value,self.lower,self.upper,trust,clearance=0.,scale=.001)
        f=len(floor_gaps);contact_count=len(self.contact_caps);hard=len(base.caps)+contact_count+f
        system=NormRows(np.r_[base_vectors,lifted.vectors],np.r_[base.caps,self.protected_contact_caps,lifted.caps],np.r_[base.scales,self.contact_scales,lifted.scales])
        derivative=sparse.vstack([jac,ljac],format='csc');self.check()
        return system,derivative,dict(hard_rows=hard,native_rows=len(base.caps),contact_rows=contact_count,floor_rows=f,guide_rows=len(guide),
            local_surface_rows=0 if self.surface is None else len(self.surface.rows),
            controls=self.size,nonzero_entries=derivative.nnz,actual_difference_steps=actual_steps,conversion=identity,
            original_native_caps_scales_unchanged=True,contact_and_floor_protection='No worsening of original failures; authored acceptance unchanged',
            scope='Joint sampled affine proposal only. Independent native export, full floor/contact/geometry and engine/human checks remain required.')
