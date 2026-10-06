"""Append a native-clock tangent-matched transition, retaining failed conditions.

Explicit bridge support points and full-mesh horizontal floor screens; no
inferred support, object/partner timeline transfer, physics or quality approval.
"""
import argparse
import copy
from pathlib import Path
import shutil
import tempfile
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from gltf_tools import append_accessor,authored_animation,local_matrix,write_glb
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from native_scene_contacts import fields,scalar,references,points,METHODS as CONTACT_METHODS
from native_rig_transfer import clock,preserves_target,METHODS as TRANSFER_METHODS
from native_transition_curve import LocalBridge,localize,compose,rates
from strep import read,save,sha256,now

SCHEMA='strep-native-rig-transition-v1'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(CONTACT_METHODS+TRANSFER_METHODS+('native_transition_curve.py','native_rig_transition.py')))
FALSE_FLAGS=('quality_approved','release_approved','training_admitted','physics_verified','human_reviewed','engine_import_verified','continuous_collision_certified')


def require(ok,message):
    if not ok:raise ValueError(message)


def equal(a,b):return __import__('json').dumps(a,sort_keys=True,allow_nan=False)==__import__('json').dumps(b,sort_keys=True,allow_nan=False)


class Problem:
    def __init__(self,recipe,base):
        fields(recipe,('schema','source','animation_indices','cuts_s','root_node','bridge_duration_s','rate','label',
            'maximum_pose_vertex_queries','limits','floor','supports'),'native transition recipe')
        require(recipe['schema']==SCHEMA,'Native transition schema required')
        fields(recipe['source'],('path','sha256'),'transition source binding')
        require(isinstance(recipe['source']['path'],str) and recipe['source']['path'],'Source path required')
        self.path=(Path(base)/recipe['source']['path']).resolve()
        require(self.path.is_file() and sha256(self.path)==recipe['source']['sha256'],'Transition source changed')
        self.rig=RigAsset.load(self.path);self.skin=NativeSupportSkin(self.rig);self.recipe=recipe
        indices=recipe['animation_indices'];cuts=recipe['cuts_s'];root=recipe['root_node']
        require(isinstance(indices,list) and len(indices)==2 and all(type(i) is int for i in indices),'Two explicit source indices required')
        require(isinstance(cuts,list) and len(cuts)==2,'Two explicit native cut times required')
        require(type(root) is int and root in self.rig.joints,'Explicit skin-joint root required')
        require(isinstance(recipe['label'],str) and 1<=len(recipe['label'])<=160,'Transition label required')
        require(len(self.rig.parents)<=512,'At most 512 rig nodes supported')
        self.readers=[NativeSupportSampler(self.rig.document,self.rig.binary,i) for i in indices]
        self.clocks=[]
        for reader,cut in zip(self.readers,cuts):
            scalar(cut,0,reader.duration,'native cut')
            original=np.unique(np.concatenate([c[2] for c in reader.channels]))
            require(cut in original and 0<cut<reader.duration,'Cuts need interior native keys and neighboring intervals')
            for node,path,_,values,mode in reader.channels:
                require(mode=='LINEAR' and node in self.rig.joints,'Selected clips require LINEAR skin-joint tracks')
                require(path in ('translation','rotation','scale'),'Morph tracks unsupported')
                if path=='scale':require(np.max(abs(values-1))<1e-7,'Animated scales unsupported')
                if path=='translation' and node!=root:
                    require(np.max(abs(values-local_matrix(self.rig.document['nodes'][node])[:3,3]))<1e-7,'Only the declared root may translate')
            self.clocks.append(clock(reader,recipe['rate']))
        require(np.allclose(self.rig.reference[:,:3,:3].swapaxes(-1,-2)@self.rig.reference[:,:3,:3],np.eye(3),atol=1e-8,rtol=0)
            and np.allclose(np.linalg.det(self.rig.reference[:,:3,:3]),1,atol=1e-8,rtol=0),
            'Proper rigid reference transforms required')
        duration=scalar(recipe['bridge_duration_s'],.01,2,'bridge duration');self.start=float(cuts[0]);self.end=float(np.float32(self.start+duration));self.duration=self.end-self.start
        require(self.duration>0,'Distinct serialized bridge endpoints required')
        first=self.clocks[0][self.clocks[0]<=cuts[0]].astype(float);second=self.clocks[1][self.clocks[1]>=cuts[1]].astype(float)
        middle=np.linspace(self.start,self.end,int(np.ceil(self.duration*recipe['rate']))+1).astype('<f4')
        tail=(second-cuts[1]+self.end).astype('<f4')
        require(len(np.unique(middle))==len(middle) and len(np.unique(tail))==len(tail),'Serialized keys collide; choose a different clock')
        self.times=np.concatenate([first.astype('<f4'),middle[1:-1],tail])
        require(len(self.times)<=8192 and np.all(np.diff(self.times.astype(float))>0) and float(self.times[-1])<=30,'Complete transition needs distinct keys and at most 8192 keys/30 seconds')
        self.tail_source=dict(zip(tail.astype(float),second));self.first_count=len(first);self.tail_count=len(tail)
        self.probes=np.sort(np.concatenate([self.times.astype(float)]+[self.times[:-1].astype(float)+f*np.diff(self.times.astype(float)) for f in (.25,.5,.75)]))
        floor=recipe['floor']
        if floor is not None:
            fields(floor,('height_m','maximum_penetration_m'),'horizontal floor')
            scalar(floor['height_m'],-100,100,'floor height');scalar(floor['maximum_penetration_m'],0,.1,'floor limit')
        require(isinstance(recipe['supports'],list) and len(recipe['supports'])<=8,'Choose up to eight explicit support patches')
        self.supports=[];ids=set()
        for row in recipe['supports']:
            fields(row,('id','vertices','points_m','interval_u','limits'),'explicit bridge support')
            require(isinstance(row['id'],str) and 1<=len(row['id'])<=100 and row['id'] not in ids,'Distinct support IDs required');ids.add(row['id'])
            selected=references(row['vertices'],self.skin);target=points(row['points_m'],len(selected))
            require(isinstance(row['interval_u'],list) and len(row['interval_u'])==2,'Normalized support interval required')
            lo,hi=[scalar(t,0,1,'bridge-relative support fraction') for t in row['interval_u']]
            require(lo<hi,'Support holds need positive-width intervals')
            fields(row['limits'],('position_m','relative_speed_m_s'),'support limits')
            for n in row['limits']:scalar(row['limits'][n],0,10,'support limit')
            lo,hi=self.start+lo*self.duration,self.start+hi*self.duration
            self.probes=np.unique(np.r_[self.probes,lo,hi])
            self.supports.append((row,selected,target,lo,hi))
        self.population=len(self.probes)*(2*len(self.rig.parents)+len(self.skin.nodes))
        require(type(recipe['maximum_pose_vertex_queries']) is int and 1<=recipe['maximum_pose_vertex_queries']<=1000000 and self.population<=recipe['maximum_pose_vertex_queries'],
            'Complete pose/vertex population exceeds its explicit budget; no truncation')
        names=('curve_control_rotation_degrees','bridge_root_excursion_m','linear_boundary_jump_m_s','angular_boundary_jump_degrees_s','root_acceleration_m_s2')
        fields(recipe['limits'],names,'transition limits')
        for n in names:scalar(recipe['limits'][n],0,10000,'transition limit')
        require(0<recipe['limits']['curve_control_rotation_degrees']<=170,'Shortest-arc spherical control limit must be at most 170 degrees')
        endpoints=[]
        for i,(reader,cut) in enumerate(zip(self.readers,cuts)):
            # Native-key tangent, not a 30-FPS frame or inferred support mask.
            original=np.unique(np.concatenate([c[2] for c in reader.channels])).astype(float);at=int(np.searchsorted(original,cut))
            pair=original[at-1:at+1] if i==0 else original[at:at+2]
            local=localize(np.array([reader.sample(t) for t in pair]),self.rig.parents);v,w=rates(local,pair)
            endpoints.append((local[-1 if i==0 else 0],v[0],w[0]))
        a,va,wa=endpoints[0];b,vb,wb=endpoints[1]
        self.curve=LocalBridge(a,b,va,vb,wa,wb,self.duration,recipe['limits']['curve_control_rotation_degrees'])
        self.animated=sorted({root}|{c[0] for r in self.readers for c in r.channels})

    def local(self,times):
        result=[];cuts=self.recipe['cuts_s']
        for t in times:
            if t<self.start:
                world=self.readers[0].sample(float(t));value=localize(world[None],self.rig.parents)[0]
            elif t>self.end:
                source_time=self.tail_source.get(float(t),cuts[1]+float(t)-self.end)
                world=self.readers[1].sample(min(float(source_time),self.readers[1].duration));value=localize(world[None],self.rig.parents)[0]
            else:value=self.curve.sample(np.array([float(t)-self.start]))[0]
            result.append(value)
        return np.array(result)

    def export(self,path):
        local=self.local(self.times);doc=copy.deepcopy(self.rig.document);binary=bytearray(self.rig.binary);animation=authored_animation(self.recipe['label'])
        ti=append_accessor(doc,binary,self.times,'SCALAR')
        for node in self.animated:
            paths={c[1] for reader in self.readers for c in reader.channels if c[0]==node}
            entry=doc['nodes'][node]
            if 'matrix' in entry:
                base=local_matrix(entry);entry.pop('matrix');entry.update(translation=base[:3,3].tolist(),rotation=Rotation.from_matrix(base[:3,:3]).as_quat().tolist(),scale=[1,1,1])
            q=Rotation.from_matrix(local[:,node,:3,:3]).as_quat()
            for i in range(1,len(q)):
                if q[i]@q[i-1]<0:q[i]*=-1
            for name,values,kind in [('rotation',q,'VEC4'),('translation',local[:,node,:3,3],'VEC3')]:
                # Preserve genuinely static paths through their default transforms.
                # Redundant quaternion keys can introduce imported interpolation
                # noise into planted descendants even when local motion is zero.
                if name not in paths:continue
                accessor=append_accessor(doc,binary,values,kind);animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=name)))
                animation['samplers'].append(dict(input=ti,output=accessor,interpolation='LINEAR'))
        index=len(doc.get('animations',[]));doc.setdefault('animations',[]).append(animation);write_glb(path,doc,binary)
        return index

    def audit(self,path):
        rig=RigAsset.load(path);index=len(self.rig.document.get('animations',[]));require(len(rig.document['animations'])==index+1,'One appended transition required')
        require(preserves_target(self.rig,rig,{str(n):n for n in self.animated}),'Original rig, payload or animations changed')
        reader=NativeSupportSampler(rig.document,rig.binary,index);require(reader.duration==float(self.times[-1]),'Transition clock changed')
        worlds=np.array([reader.sample(float(t)) for t in self.probes]);expected=compose(self.local(self.probes),self.rig.parents)
        key=np.isin(self.probes,self.times);key_error=float(abs(worlds[key]-expected[key]).max())
        position_error=float(np.linalg.norm(worlds[:,:,:3,3]-expected[:,:,:3,3],axis=2).max())
        angle_error=float(Rotation.from_matrix((worlds[:,:,:3,:3].swapaxes(-1,-2)@expected[:,:,:3,:3]).reshape(-1,3,3)).magnitude().max())
        vertices=np.array([rig.vertices(w) for w in worlds]);window=(self.probes>=self.start)&(self.probes<=self.end)
        contact_rows=[]
        for row,selected,target,lo,hi in self.supports:
            mask=(self.probes>=lo)&(self.probes<=hi);positions=vertices[mask][:,selected];time=self.probes[mask]
            error=float(np.linalg.norm(positions-target,axis=2).max());slip=float(np.linalg.norm(np.diff(positions,axis=0)/np.diff(time)[:,None,None],axis=2).max())
            contact_rows.append(dict(id=row['id'],samples=len(time),maximum_position_error_m=error,maximum_slip_m_s=slip,
                passed=error<=row['limits']['position_m'] and slip<=row['limits']['relative_speed_m_s']))
        floor=self.recipe['floor'];depth=None if floor is None else float(max(0,floor['height_m']-vertices[window,:,1].min()))
        keys=worlds[np.searchsorted(self.probes,self.times)];v,w=rates(keys,self.times)
        boundaries=[]
        for t in (self.start,self.end):
            i=int(np.searchsorted(self.times,t));require(0<i<len(self.times)-1,'Neighboring transition keys required')
            boundaries.append(dict(time_s=t,linear_jump_m_s=float(np.linalg.norm(v[i,self.rig.joints]-v[i-1,self.rig.joints],axis=1).max()),
                angular_jump_degrees_s=float(np.degrees(np.linalg.norm(w[i,self.rig.joints]-w[i-1,self.rig.joints],axis=1)).max())))
        dt=np.diff(self.times.astype(float));root=self.recipe['root_node'];acceleration=np.diff(v[:,root],axis=0)/((dt[1:]+dt[:-1])/2)[:,None]
        centers=self.times[1:-1].astype(float);active=(centers>=self.start)&(centers<=self.end)
        peak=float(np.linalg.norm(acceleration[active],axis=1).max())
        bridge_positions=worlds[window,root,:3,3];u=(self.probes[window]-self.start)/self.duration
        chord=(1-u[:,None])*bridge_positions[0]+u[:,None]*bridge_positions[-1];excursion=float(np.linalg.norm(bridge_positions-chord,axis=1).max())
        limits=self.recipe['limits'];fidelity=dict(key_matrix_error=key_error,maximum_joint_position_error_m=position_error,maximum_joint_angle_error_rad=angle_error,
            passed=bool(key_error<=1e-5 and position_error<=1e-4 and angle_error<=1e-4))
        checks=dict(fidelity=fidelity['passed'],root_excursion=excursion<=limits['bridge_root_excursion_m'],
            root_acceleration=peak<=limits['root_acceleration_m_s2'],linear_boundaries=all(x['linear_jump_m_s']<=limits['linear_boundary_jump_m_s'] for x in boundaries),
            angular_boundaries=all(x['angular_jump_degrees_s']<=limits['angular_boundary_jump_degrees_s'] for x in boundaries))
        if floor is not None:checks['floor']=depth<=floor['maximum_penetration_m']
        if self.supports:checks['supports']=all(x['passed'] for x in contact_rows)
        return dict(schema=SCHEMA,status='complete',animation_index=index,keys=len(self.times),duration_s=float(self.times[-1]),
            bridge_interval_s=[self.start,self.end],source_animation_indices=self.recipe['animation_indices'],source_cuts_s=self.recipe['cuts_s'],
            queries=len(self.probes),pose_vertex_population=self.population,fidelity=fidelity,boundaries=boundaries,supports=contact_rows,
            floor_maximum_penetration_m=depth,bridge_root_excursion_m=excursion,bridge_root_acceleration_max_m_s2=peak,
            maximum_control_angle_degrees=self.curve.maximum_control_angle_degrees,checks=checks,all_declared_samples_pass=all(checks.values()),
            support_conditions_available=bool(self.supports),floor_conditions_available=floor is not None,
            original_selected=True,**{n:False for n in FALSE_FLAGS},
            scope='Tangent-matched local bridge between explicit native cuts. Complete key/quarter/mid/three-quarter readback, sampled authored bridge supports/floor and neighboring native-key rate limits. No automatic placement, inferred support, object/partner/event timeline, continuous contact/collision or realistic-action approval.')


def run(recipe_path,output):
    recipe_path=Path(recipe_path).resolve();output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        recipe=read(recipe_path);problem=Problem(recipe,recipe_path.parent);require(not output.exists(),'Fresh transition output required')
        require(not recipe_path.is_relative_to(output) and not problem.path.is_relative_to(output),'Output contains an input')
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};inputs={str(recipe_path):sha256(recipe_path),str(problem.path):sha256(problem.path)}
        output.mkdir();(output/'implementation').mkdir();shutil.copyfile(recipe_path,output/'recipe.json');shutil.copyfile(problem.path,output/'source.glb')
        for n in methods:shutil.copyfile(SCRIPT_ROOT/n,output/'implementation'/n)
        save(output/'prepared.json',dict(schema=SCHEMA,at=now(),recipe_base=str(recipe_path.parent),recipe_original_path=str(recipe_path),inputs_sha256=inputs,implementation_sha256=methods,
            recipe_sha256=sha256(output/'recipe.json'),source_sha256=sha256(output/'source.glb')))
        save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            problem.export(output/'character.glb');result=problem.audit(output/'character.glb')
            result.update(prepared_sha256=sha256(output/'prepared.json'),glb_sha256=sha256(output/'character.glb'))
            save(output/'result.json',result);save(output/'completion.json',dict(result_sha256=sha256(output/'result.json')))
            save(output/'pipeline.json',dict(status='complete',original_selected=True));verify(output);return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


def verify(output):
    output=Path(output).resolve();p=read(output/'prepared.json')
    fields(p,('schema','at','recipe_base','recipe_original_path','inputs_sha256','implementation_sha256','recipe_sha256','source_sha256'),'transition preparation')
    require(p['schema']==SCHEMA and set(p['implementation_sha256'])==set(METHODS),'Complete unchanged transition methods required')
    for n,h in p['implementation_sha256'].items():require(sha256(SCRIPT_ROOT/n)==sha256(output/'implementation'/n)==h,'Transition method changed')
    for path,h in p['inputs_sha256'].items():require(sha256(path)==h,'Transition original changed')
    require(sha256(output/'recipe.json')==p['recipe_sha256'] and sha256(output/'source.glb')==p['source_sha256'],'Transition snapshot changed')
    problem=Problem(read(output/'recipe.json'),p['recipe_base']);require(sha256(problem.path)==sha256(output/'source.glb'),'Snapshot uses another source')
    require(set(p['inputs_sha256'])=={str(problem.path),p['recipe_original_path']} and p['inputs_sha256'][str(problem.path)]==p['source_sha256']
        and p['inputs_sha256'][p['recipe_original_path']]==p['recipe_sha256'],'Complete original input bindings required')
    require(read(output/'pipeline.json')==dict(status='complete',original_selected=True),'Completed transition required')
    with tempfile.TemporaryDirectory(prefix='strep-native-transition-replay-') as temporary:
        expected=Path(temporary)/'character.glb';problem.export(expected)
        require(sha256(expected)==sha256(output/'character.glb'),'Transition no longer matches its deterministic construction')
    result=problem.audit(output/'character.glb');result.update(prepared_sha256=sha256(output/'prepared.json'),glb_sha256=sha256(output/'character.glb'))
    require(equal(read(output/'result.json'),result),'Transition measurements or decisions changed')
    require(read(output/'completion.json')==dict(result_sha256=sha256(output/'result.json')),'Transition completion changed')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    print(run(args.recipe,args.output))
