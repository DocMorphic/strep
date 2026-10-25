"""Rig-independent native clip context for bounded rolling surface correction.

Explicit node IDs, static world contact phases and limits replace study-specific
role names and report paths. Only shared LINEAR clocks are supported by the
current exporter. This prepares/audits windows; it does not authorize motion,
run the rolling coordinator or replace scene/partner collision checking.
"""
import copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from surface_pose_model import SurfacePoseModel
from surface_pose_working_floor import WorkingFloorConstraints
from surface_pose_window import CoupledPoseWindow
from surface_pose_interpolation import InterpolatedPoseMap
from surface_pose_key_export import validate_layout
from strep import sha256


class SurfaceClip:
    def __init__(self, rig, *, animation_index, root, rotations, angles_degrees,
                 contacts, limits, fitting, sampling):
        if not isinstance(rig, RigAsset):
            raise ValueError('A decoded source rig is required')
        if (type(root) is not int or root not in rig.joints or not isinstance(rotations,list) or not 1<=len(rotations)<=20
                or any(type(n) is not int or n not in rig.joints for n in rotations) or len(set(rotations))!=len(rotations)
                or not isinstance(angles_degrees,list) or len(rotations)!=len(angles_degrees)):
            raise ValueError('One explicit angular limit per editable rotation is required')
        def number(value):
            return type(value) in (int,float) and np.isfinite(value)
        if any(not number(a) or not 0<a<=180 for a in angles_degrees):
            raise ValueError('Finite positive angular limits up to 180 degrees required')
        required={'root_horizontal_m','root_vertical_m','floor_depth_m','contact_error_m','root_step_m','rotation_step_degrees'}
        if not isinstance(limits,dict) or set(limits)!=required or any(not number(v) or v<=0 for v in limits.values()) or limits['rotation_step_degrees']>180:
            raise ValueError('Complete finite positive acceptance limits required')
        reserves={'root_reserve_m','angle_reserve_radians','step_reserve_m','step_reserve_radians','floor_reserve_m','contact_reserve_m'}
        if not isinstance(fitting,dict) or set(fitting)!=reserves or any(not number(v) or v<0 for v in fitting.values()):
            raise ValueError('Complete finite nonnegative fitting reserves required')
        if (fitting['root_reserve_m']>=min(limits['root_horizontal_m'],limits['root_vertical_m']/2)
                or fitting['angle_reserve_radians']>=np.deg2rad(min(angles_degrees))
                or fitting['step_reserve_m']>=limits['root_step_m']
                or fitting['step_reserve_radians']>=np.deg2rad(limits['rotation_step_degrees'])
                or fitting['floor_reserve_m']>=limits['floor_depth_m']
                or fitting['contact_reserve_m']>=limits['contact_error_m']):
            raise ValueError('Fitting reserves must remain inside the original limits')
        if (not isinstance(sampling,dict) or set(sampling)!={'dense_hz','initial_fractions','maximum_samples'}
                or type(sampling['dense_hz']) is not int or not 1<=sampling['dense_hz']<=1920
                or type(sampling['maximum_samples']) is not int or not 2<=sampling['maximum_samples']<=100000
                or not isinstance(sampling['initial_fractions'],list) or not sampling['initial_fractions']
                or any(not number(f) or f not in [i/8 for i in range(1,8)] for f in sampling['initial_fractions'])
                or len(set(sampling['initial_fractions']))!=len(sampling['initial_fractions'])):
            raise ValueError('Explicit bounded dense clock and distinct interior eighths required')
        self.reader,_,_=validate_layout(rig,rig,root=root,rotations=rotations,animation_index=animation_index)
        self.rig=rig;self.animation_index=animation_index;self.root=root;self.nodes=rotations.copy()
        self.keys=self.reader.channels[0][2].astype(float)
        if len(self.keys)<2 or self.keys[0]!=0 or np.any(np.diff(self.keys)<=0):
            raise ValueError('At least two increasing native keys starting at zero required')
        bound=len(self.keys)+7*(len(self.keys)-1)+int(np.floor(self.keys[-1]*sampling['dense_hz']))+1
        if bound>sampling['maximum_samples']:
            raise ValueError('Complete sampling population exceeds its declared budget; no samples dropped')
        model=SurfacePoseModel(rig,self.reader.sample(0.),root,rotations)
        if not isinstance(contacts,list):raise ValueError('Explicit contact phases required')
        for index,phase in enumerate(contacts):
            if (not isinstance(phase,dict) or set(phase)!={'vertex','target_m','start_time_s','end_time_s'}
                    or type(phase['vertex']) is not int or not 0<=phase['vertex']<model.skin.count
                    or not isinstance(phase['target_m'],list) or len(phase['target_m'])!=3 or not all(number(v) for v in phase['target_m'])
                    or not number(phase['start_time_s']) or not number(phase['end_time_s'])
                    or not 0<=phase['start_time_s']<=phase['end_time_s']<=self.reader.duration):
                raise ValueError('Exact in-range material vertices, world targets and closed contact intervals required')
            if any(p['vertex']==phase['vertex'] and max(p['start_time_s'],phase['start_time_s'])<=min(p['end_time_s'],phase['end_time_s']) for p in contacts[:index]):
                raise ValueError('Overlapping phases for the same material vertex are ambiguous')
        self.phases=copy.deepcopy(contacts);self.angles=np.asarray(angles_degrees,float).copy()
        self.width=model.size;self.vertex_count=model.skin.count
        self.settings={**copy.deepcopy(limits),**{k:fitting[k] for k in ('floor_reserve_m','contact_reserve_m')}}
        self.request={**copy.deepcopy(sampling),**{'fit_'+k:fitting[k] for k in ('root_reserve_m','angle_reserve_radians','step_reserve_m','step_reserve_radians')},'fit_geometry_reserve_scale':1.}

    def frames(self,frames,*,window=False):
        if (not isinstance(frames,list) or not frames or any(type(f) is not int or not 0<=f<len(self.keys) for f in frames)
                or frames!=list(range(frames[0],frames[-1]+1)) or window and not 2<=len(frames)<=8):
            raise ValueError('Explicit consecutive in-range native frames required (2-8 per window)')
        return frames

    def controls(self,rig,frames):
        self.frames(frames)
        _,reader,_=validate_layout(self.rig,rig,root=self.root,rotations=self.nodes,animation_index=self.animation_index)
        values=[]
        for frame in frames:
            before=self.reader.sample(float(self.keys[frame]));after=reader.sample(float(self.keys[frame]));a=before.copy();b=after.copy()
            for n,parent in enumerate(self.rig.parents):
                if parent>=0:a[n]=np.linalg.solve(before[parent],before[n]);b[n]=np.linalg.solve(after[parent],after[n])
            angles=Rotation.from_matrix(np.linalg.solve(a[self.nodes,:3,:3],b[self.nodes,:3,:3])).as_rotvec()
            values.append(np.r_[after[self.root,:3,3]-before[self.root,:3,3],angles.reshape(-1)])
        return np.asarray(values)

    def clock(self,frames):
        self.frames(frames)
        groups=[self.keys[frames]]
        for a,b in zip(self.keys[frames][:-1],self.keys[frames][1:]):
            groups.extend([np.linspace(a,b,9),np.arange(np.ceil(a*self.request['dense_hz']),np.floor(b*self.request['dense_hz'])+1)/self.request['dense_hz']])
        return np.unique(np.concatenate(groups))

    def measure(self,points,controls,t):
        points=np.asarray(points,float);controls=np.asarray(controls,float)
        if (points.shape!=(self.vertex_count,3) or controls.shape!=(self.width,)
                or not np.isfinite(points).all() or not np.isfinite(controls).all()
                or type(t) not in (int,float) or not np.isfinite(t) or not 0<=t<=self.reader.duration):
            raise ValueError('Complete finite mesh, controls and in-range sample time required')
        floor=max(0.,-float(points[:,1].min()));active=[p for p in self.phases if p['start_time_s']<=t<=p['end_time_s']]
        contact=max((float(np.linalg.norm(points[p['vertex']]-p['target_m'])) for p in active),default=0.)
        angles=np.rad2deg(np.linalg.norm(controls[3:].reshape(-1,3),axis=1));horizontal=float(np.linalg.norm(controls[[0,2]]))
        s=self.settings;violations=[(floor-s['floor_depth_m'])/.1,(contact/s['contact_error_m'])**2-1,horizontal/s['root_horizontal_m']-1,-controls[1],controls[1]-s['root_vertical_m'],float(np.max(angles-self.angles))]
        return dict(time_s=float(t),floor_depth_m=floor,contact_error_m=contact,numerical_pose_pass=bool(max(violations)<=0),violation=max(0.,float(max(violations))))

    def step_check(self,controls):
        controls=np.asarray(controls,float)
        if controls.ndim!=2 or controls.shape[1]!=self.width or not 1<=len(controls)<=len(self.keys) or not np.isfinite(controls).all():
            raise ValueError('Complete finite consecutive key controls required')
        if len(controls)<2:return dict(step_pass=True,maximum_root_step_m=0.,maximum_rotation_step_degrees=0.)
        delta=np.linalg.norm(np.diff(controls,axis=0).reshape(len(controls)-1,-1,3),axis=2)
        return dict(step_pass=bool(np.all(delta[:,0]<=self.settings['root_step_m']) and np.all(np.rad2deg(delta[:,1:])<=self.settings['rotation_step_degrees'])),
            maximum_root_step_m=float(delta[:,0].max()),maximum_rotation_step_degrees=float(np.rad2deg(delta[:,1:]).max()))

    def audit(self,path,frames):
        self.frames(frames)
        rig=RigAsset.load(path)
        _,reader,_=validate_layout(self.rig,rig,root=self.root,rotations=self.nodes,animation_index=self.animation_index)
        rows=[];controls=[]
        for t in self.clock(frames):
            original=self.reader.sample(float(t));world=reader.sample(float(t));a=original.copy();b=world.copy()
            for n,parent in enumerate(self.rig.parents):
                if parent>=0:a[n]=np.linalg.solve(original[parent],original[n]);b[n]=np.linalg.solve(world[parent],world[n])
            angles=Rotation.from_matrix(np.linalg.solve(a[self.nodes,:3,:3],b[self.nodes,:3,:3])).as_rotvec();x=np.r_[world[self.root,:3,3]-original[self.root,:3,3],angles.reshape(-1)]
            rows.append(self.measure(rig.vertices(world),x,float(t)))
            if t in self.keys[frames]:controls.append(x)
        assert len(controls)==len(frames);steps=self.step_check(controls)
        return dict(frames=frames,samples=rows,**steps,passed=bool(steps['step_pass'] and all(r['numerical_pose_pass'] for r in rows)),
            failed_samples=sum(not r['numerical_pose_pass'] for r in rows),maximum_floor_depth_m=max(r['floor_depth_m'] for r in rows),maximum_contact_error_m=max(r['contact_error_m'] for r in rows),
            clip_sha256=sha256(path),quality_approved=False,release_approved=False)

    def build_window(self,frames,seed,*,preserve_last=False):
        self.frames(frames,window=True)
        if type(preserve_last) is not bool or preserve_last and frames[-1]!=len(self.keys)-1:
            raise ValueError('Explicit preservation applies only to the final native key')
        seed=np.asarray(seed,float)
        if seed.shape!=(len(frames),self.width) or not np.isfinite(seed).all():
            raise ValueError('Complete finite window seed required')
        models=[SurfacePoseModel(self.rig,self.reader.sample(float(self.keys[f])),self.root,self.nodes) for f in frames]
        for model in models[1:]:model.skin=models[0].skin
        def problem(model,t,*,reserve=1.,key_budget=False):
            root_reserve=self.request['fit_root_reserve_m'] if key_budget else 0.
            angle_reserve=np.rad2deg(self.request['fit_angle_reserve_radians']) if key_budget else 0.
            s=self.settings
            p=WorkingFloorConstraints(model,angles_degrees=(self.angles-angle_reserve).tolist(),root_horizontal_m=s['root_horizontal_m']-root_reserve,
                root_vertical_m=s['root_vertical_m']-root_reserve,floor_depth_m=s['floor_depth_m'],contact_error_m=s['contact_error_m'],
                floor_reserve_m=s['floor_reserve_m']*reserve*self.request['fit_geometry_reserve_scale'],contact_reserve_m=s['contact_reserve_m']*reserve*self.request['fit_geometry_reserve_scale'],
                contacts=[p for p in self.phases if p['start_time_s']<=t<=p['end_time_s']])
            assert p.floor==s['floor_depth_m'] and p.contact==s['contact_error_m']
            if key_budget:p.bounds[1]=(root_reserve,p.vertical)
            return p
        fixed={0,len(frames)-1} if preserve_last else {0}
        keys=[problem(m,float(self.keys[f]),reserve=0. if i in fixed else 1.,key_budget=i not in fixed) for i,(m,f) in enumerate(zip(models,frames))]
        keys[0].bounds=[(float(v),float(v)) for v in seed[0]]
        if preserve_last:keys[-1].bounds=[(float(v),float(v)) for v in seed[-1]]
        native=CoupledPoseWindow(keys,root_step_m=self.settings['root_step_m']-self.request['fit_step_reserve_m'],rotation_step_degrees=self.settings['rotation_step_degrees']-np.rad2deg(self.request['fit_step_reserve_radians']))
        checks={};samples={};clock=self.clock(frames)
        for i in range(len(frames)-1):
            a,b=map(float,self.keys[frames[i:i+2]])
            for t in clock:
                if not a<t<b:continue
                fraction=float((t-a)/(b-a));model=SurfacePoseModel(self.rig,self.reader.sample(float(t)),self.root,self.nodes);model.skin=models[0].skin
                mapper=InterpolatedPoseMap(models[i],models[i+1],model,fraction)
                reserve=(fraction if i==0 else 1.)*(1-fraction if preserve_last and i==len(frames)-2 else 1.)
                checks[float(t)]=(i,mapper,problem(model,float(t),reserve=reserve))
            for fraction in self.request['initial_fractions']:
                t=float(np.linspace(a,b,9)[int(fraction*8)]);samples[t]=checks[t]
        return native,checks,samples,clock

    def dense_check(self,native,checks,clock,frames,x):
        self.frames(frames,window=True)
        if (not np.array_equal(np.asarray(clock),self.clock(frames))
                or set(checks)!=set(clock)-set(self.keys[frames])
                or native.size!=len(frames)*self.width):
            raise ValueError('Complete native window and declared dense sample population required')
        poses=native.unpack(x);rows=[]
        for t in clock:
            where=np.flatnonzero(self.keys[frames]==t)
            if len(where):index=int(where[0]);p=native.problems[index];z=poses[index]
            else:i,m,p=checks[float(t)];z=m.parameters(poses[i:i+2].reshape(-1),derivatives=False)[0]
            rows.append(self.measure(p.pose(z,derivatives=False)[2],z,float(t)))
        steps=self.step_check(poses)
        return rows,steps,bool(steps['step_pass'] and all(r['numerical_pose_pass'] for r in rows))
