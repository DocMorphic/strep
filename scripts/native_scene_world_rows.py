"""Complete read-only Studio world conditions; no optimization or selection.

Reuses the existing SceneProblem arithmetic. Native parameter permissions,
surface geometry, explicit rotation-speed policies and engine/human checks
remain separate mandatory parts of an integrated correction workflow.
"""
import copy
from pathlib import Path
import re
import numpy as np
from native_scene_contacts import SceneContacts
from native_scene_fit import SceneProblem
from engine_contact_sampling import frame_populations
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import sha256

MAXIMUM_TIMES=16384
MAXIMUM_WORLD_BYTES=64*1024**2
MAXIMUM_ROWS=2000000
MAXIMUM_SKIN_BYTES=64*1024**2


class _ReadOnlyEdits:
    size=0
    def __init__(self,caps):
        self.initial=np.empty(0);self.lower=np.empty(0);self.upper=np.empty(0)
        # SceneProblem's advanced joint indexing yields joint-major [J,F]
        # displacement rows. Preserve its ordering and broadcast each joint's
        # explicit cap along time, rather than changing the legacy kernel.
        self.actors={name:dict(tracks=[],displacement=value[:,None].copy()) for name,value in caps.items()}
    @staticmethod
    def controls(value):
        if np.asarray(value).shape!=(0,):raise ValueError('Read-only world evaluator has no optimization variables')
        return np.empty(0)


class _WorldProblem(SceneProblem):
    def skin_points(self,name,ids,worlds,times,reduction):
        actor=self.scene.actors[name];per_frame=worlds[name].shape[1]*16*8+len(ids)*actor['skin'].nodes.shape[1]*12*8
        batch=self.maximum_skin_bytes//per_frame
        if batch<1:raise ValueError('One complete contact frame exceeds the skin working budget')
        result=np.empty((len(times),1 if reduction=='centroid' else len(ids),3))
        for start in range(0,len(times),batch):
            stop=min(start+batch,len(times))
            result[start:stop]=super().skin_points(name,ids,worlds,times[start:stop],reduction)
        return result


class SceneWorldRows:
    def __init__(self,scene,displacement_caps_m,*,maximum_times=MAXIMUM_TIMES,
                 maximum_world_bytes=MAXIMUM_WORLD_BYTES,maximum_rows=MAXIMUM_ROWS,
                 maximum_skin_bytes=8*1024**2):
        if not isinstance(scene,SceneContacts):raise ValueError('Complete source-bound native scene required')
        for value,limit in [(maximum_times,MAXIMUM_TIMES),(maximum_world_bytes,MAXIMUM_WORLD_BYTES),
                            (maximum_rows,MAXIMUM_ROWS),(maximum_skin_bytes,MAXIMUM_SKIN_BYTES)]:
            if type(value) is not int or not 1<=value<=limit:raise ValueError('Explicit bounded complete condition budgets required')
        if not isinstance(displacement_caps_m,dict) or not displacement_caps_m or set(displacement_caps_m)-set(scene.actors):
            raise ValueError('Explicit displacement caps for every proposed edited actor required')
        caps={}
        for name,value in displacement_caps_m.items():
            array=np.asarray(value);count=len(scene.actors[name]['rig'].joints)
            if array.dtype.kind not in 'fiu' or array.shape not in [(),(count,)] or not np.isfinite(array).all() or np.any(array<=0) or np.any(array>10):
                raise ValueError('Positive finite scalar or complete per-joint displacement caps up to10m required')
            caps[name]=np.full(count,float(array)) if array.ndim==0 else array.astype(float,copy=True)
        scene.check_inputs();source=copy.deepcopy(scene)
        uniform=np.arange(int(np.floor(source.duration*120))+1)/120
        if len(uniform)<3:raise ValueError('At least three original uniform source-rate samples required')
        native=[c[2] for actor in source.actors.values() for c in actor['sampler'].channels]+[obj['times'] for obj in source.objects.values()]
        if sum(len(clock) for clock in native)>2000000:raise ValueError('Complete native clock input budget exceeded')
        all_times=[uniform]+native;contacts=[]
        for entry in source.rows:
            row=entry['authored'];a,b=row['interval_s'];populations=frame_populations([a,b]) if row['mode']=='hold' else []
            clock=np.unique(np.concatenate([np.array([a,b])]+native+[p['times_s'] for p in populations]));clock=clock[(clock>=a)&(clock<=b)]
            all_times.append(clock);contacts.append((entry,clock,populations))
            for actor_name,ids in [(row['actor'],entry['ids'])]+([(row['target']['actor'],entry['target_ids'])] if row['target']['space']=='actor' else []):
                actor=source.actors[actor_name];needed=len(actor['rig'].document['nodes'])*16*8+len(ids)*actor['skin'].nodes.shape[1]*12*8
                if needed>maximum_skin_bytes:raise ValueError('One complete contact frame exceeds the skin working budget')
        times=np.unique(np.concatenate(all_times));world_bytes=len(times)*sum(len(a['rig'].document['nodes']) for a in source.actors.values())*16*8
        rows=sum((5*len(uniform)-6)*len(source.actors[name]['rig'].joints) for name in caps)
        for entry,clock,populations in contacts:
            count=1 if entry['authored']['reduction']=='centroid' else len(entry['ids'])
            rows+=len(clock)*count+sum((len(p['times_s'])-1)*count if len(p['times_s'])>=2 else 1 for p in populations)
        if len(times)>maximum_times or world_bytes>maximum_world_bytes or rows>maximum_rows:
            raise ValueError('Complete clock/world/condition budget exceeded; no times or rows discarded')
        self._problem=_WorldProblem(source,_ReadOnlyEdits(caps));self._problem.maximum_skin_bytes=maximum_skin_bytes
        np.testing.assert_array_equal(self._problem.times,times)
        self._times=times.copy();self._times.setflags(write=False);self._rows=rows;self._layout=[];cursor=0
        for name in caps:
            count=len(uniform)*len(source.actors[name]['rig'].joints)
            self._layout.append(('displacement',name,None,cursor,cursor+count));cursor+=count
            for metric,values in zip(['linear_speed','linear_acceleration','angular_speed','angular_acceleration'],self._problem.caps[name].caps):
                count=values.size;self._layout.append(('source_rate',name,metric,cursor,cursor+count));cursor+=count
        for entry,clock,populations in contacts:
            row=entry['authored'];count=1 if row['reduction']=='centroid' else len(entry['ids']);size=len(clock)*count
            self._layout.append(('contact_position',row['id'],row['target']['space'],cursor,cursor+size));cursor+=size
            for population in populations:
                size=(len(population['times_s'])-1)*count if len(population['times_s'])>=2 else 1
                detail=(population['rate_hz'],population['phase_offset_frames'])
                self._layout.append(('contact_speed',row['id'],detail,cursor,cursor+size));cursor+=size
        assert cursor==rows
        self._report=dict(schema='strep-native-scene-world-rows-v1',times=len(times),uniform_rate_samples=len(uniform),
            rows=rows,world_bytes=world_bytes,optimization_variables=0,edited_actors=list(caps),source_rate_tolerance=1e-5,
            maximum_skin_bytes=maximum_skin_bytes,native_parameter_conditions_included=False,surface_geometry_included=False,
            explicit_rotation_speed_policy_included=False,original_selected=True,quality_approved=False,release_approved=False)

    @property
    def times(self):return self._times.copy()
    @property
    def layout(self):return tuple(self._layout)
    @property
    def report(self):return copy.deepcopy(self._report)
    def source_worlds(self):
        self._problem.scene.check_inputs()
        return {name:world.copy() for name,world in self._problem.source_world.items()}

    def violations(self,worlds):
        scene=self._problem.scene;scene.check_inputs()
        if not isinstance(worlds,dict) or set(worlds)!=set(scene.actors):raise ValueError('Every original actor world population required')
        copied={}
        for name,actor in scene.actors.items():
            array=np.asarray(worlds[name]);expected=self._problem.source_world[name]
            if array.dtype.kind not in 'fiu' or array.shape!=expected.shape or not np.isfinite(array).all():raise ValueError('Complete finite matching actor worlds required')
            if name not in self._problem.edits.actors and not np.array_equal(array,expected):raise ValueError('An actor without declared edit caps must remain unchanged')
            copied[name]=array.astype(float,copy=True)
        result=self._problem.constraints(np.empty(0),copied)
        if result.shape!=(self._rows,) or not np.isfinite(result).all():raise ValueError('Incomplete or nonfinite original world conditions')
        scene.check_inputs();return result

    def evaluate_files(self,files):
        scene=self._problem.scene
        if not isinstance(files,dict) or set(files)!=set(self._problem.edits.actors):raise ValueError('One explicit saved candidate for every edited actor required')
        worlds=self.source_worlds();bindings={}
        for name,entry in files.items():
            if not isinstance(entry,dict) or set(entry)!={'path','sha256','animation_index'} or type(entry['animation_index']) is not int or entry['animation_index']<0:
                raise ValueError('Explicit candidate path, digest and animation index required')
            if not isinstance(entry['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',entry['sha256']):raise ValueError('Exact candidate SHA256 required')
            path=Path(entry['path']).resolve();digest=sha256(path)
            if digest!=entry['sha256']:raise ValueError('Saved candidate changed')
            original=scene.actors[name]['rig'];rig=RigAsset.load(path)
            for key in ['nodes','skins','meshes','materials','images','textures','scenes','scene']:
                if rig.document.get(key)!=original.document.get(key):raise ValueError('Candidate static rig or scene changed')
            if rig.binary[:len(original.binary)]!=original.binary:raise ValueError('Source-preserving candidate binary prefix required')
            reader=NativeSupportSampler(rig.document,rig.binary,entry['animation_index'])
            if reader.duration!=scene.duration:raise ValueError('Exact original duration required; retime explicitly outside this evaluator')
            worlds[name]=np.array([reader.sample(float(stamp)) for stamp in self._times]);bindings[str(path)]=digest
        result=self.violations(worlds)
        if any(sha256(path)!=digest for path,digest in bindings.items()):raise ValueError('Saved candidate changed during evaluation')
        return result,dict(candidate_sha256=bindings,world_conditions_pass=bool(np.all(result<=0)),
            failed_rows=int(np.count_nonzero(result>0)),maximum_violation=float(result.max()),
            original_selected=True,quality_approved=False,release_approved=False,
            scope='Complete existing Studio world displacement/source-rate/contact-position/hold-speed conditions only. Native permissions, geometry, explicit speed policies, engine and human acceptance remain separate; no motion selection.')
