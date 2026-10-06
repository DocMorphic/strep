"""Assemble verified actor transitions, rigid props and remapped scene intent.

Source scenes remain immutable. Contacts in the bridge must be authored;
retimed gameplay confirmations are reset. No attachment or realism inference.
"""
import argparse,copy,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts,fields,scalar
from native_scene_game_tracks import validate,event_plan
from native_scene_engine import METHODS as ENGINE_METHODS
from native_transition_curve import LocalBridge,rates,mix
import native_rig_transition as transition
import native_transition_root_support as root_support
from strep import read,save,sha256,now

SCHEMA='strep-native-scene-transition-v1'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(root_support.METHODS+ENGINE_METHODS+('native_scene_game_tracks.py','native_scene_transition.py')))
require=transition.require


def matrices(p,r):
    result=np.tile(np.eye(4),(len(p),1,1));result[:,:3,3]=p;result[:,:3,:3]=r;return result


class Problem:
    def __init__(self,recipe,base):
        fields(recipe,('schema','sources','actors','bridge','object_limits','floor','maximum_timestamp_rounding_s','maximum_pose_vertex_queries'),'scene transition')
        require(recipe['schema']==SCHEMA,'Scene transition schema required')
        self.recipe=recipe;self.base=Path(base);self.inputs={};self.actors={};self.scenes=[];self.requests=[]
        self.rounding=scalar(recipe['maximum_timestamp_rounding_s'],0,1e-4,'timestamp rounding permission')
        require(type(recipe['maximum_pose_vertex_queries']) is int and 1<=recipe['maximum_pose_vertex_queries']<=1000000,'Complete population permission required')
        fields(recipe['object_limits'],('curve_control_rotation_degrees','position_error_m','basis_error','linear_boundary_jump_m_s','angular_boundary_jump_degrees_s','acceleration_m_s2'),'object bridge limits')
        for name,value in recipe['object_limits'].items():scalar(value,0,10000,'object limit')
        require(0<recipe['object_limits']['curve_control_rotation_degrees']<=170,'Shortest-arc object controls required')
        if recipe['floor'] is not None:
            fields(recipe['floor'],('height_m','maximum_penetration_m'),'whole scene floor')
            scalar(recipe['floor']['height_m'],-100,100,'floor height');scalar(recipe['floor']['maximum_penetration_m'],0,.1,'floor limit')
        fields(recipe['bridge'],('contacts','markers'),'explicit bridge intent')
        require(isinstance(recipe['sources'],list) and len(recipe['sources'])==2,'Two source scenes required')
        for binding in recipe['sources']:
            fields(binding,('scene','game_tracks'),'scene and game track bindings')
            spec=read(self.bound(binding['scene']));request=read(self.bound(binding['game_tracks']))
            scene=SceneContacts(spec,self.bound(binding['scene']).parent);self.inputs.update(scene.inputs)
            fields(request,('schema','actors','markers'),'source game tracks')
            require(isinstance(request['markers'],list) and len(request['markers'])<=128,'Bounded source marker population required')
            times=[0.,scene.duration]+[float(t) for a in scene.actors.values() for c in a['sampler'].channels for t in c[2]]
            for m in request['markers']:
                fields(m,('id','name','actor','time_s','confirmed'),'source gameplay marker')
                times.append(scalar(m['time_s'],0,scene.duration,'source marker time'))
            validate(request,scene,np.unique(times));self.scenes.append(scene);self.requests.append(request)
        a,b=self.scenes
        require(set(a.actors)==set(b.actors)==set(recipe['actors']),'Every source participant needs a transition')
        require(set(a.objects)==set(b.objects),'Source object populations must match')
        cache={};probes=[];signature=None
        for name,binding in recipe['actors'].items():
            fields(binding,('kind','folder','result_sha256'),'verified actor transition')
            require(binding['kind'] in ('transition','root-support') and isinstance(binding['folder'],str) and binding['folder'],'Supported completed actor variant required')
            folder=(self.base/binding['folder']).resolve();require(sha256(folder/'result.json')==binding['result_sha256'],'Actor result binding changed')
            key=(binding['kind'],str(folder))
            if key not in cache:
                if binding['kind']=='transition':
                    r=transition.verify(folder);p=transition.Problem(read(folder/'recipe.json'),read(folder/'prepared.json')['recipe_base'])
                else:
                    r=root_support.verify(folder);require(r['candidate_available'],'Root-support conflict has no actor candidate')
                    p=root_support.Problem(read(folder/'recipe.json'),read(folder/'prepared.json')['recipe_base']).original
                cache[key]=(r,p)
            r,p=cache[key];clock=(tuple(p.recipe['cuts_s']),p.start,p.end,float(p.times[-1]))
            if signature is None:signature=clock
            require(clock==signature,'All actor transitions must share exact cuts, bridge and output duration')
            for side,scene in enumerate(self.scenes):
                actor=scene.actors[name]
                require(sha256(p.path)==sha256((self.bound(recipe['sources'][side]['scene']).parent/read(self.bound(recipe['sources'][side]['scene']))['actors'][name]['glb']).resolve()),'Transition belongs to another source actor library')
                require(actor['animation_index']==p.recipe['animation_indices'][side],'Transition selected different source clips')
                require(self.requests[side]['actors'][name]['root_node']==p.recipe['root_node'],'Source root choices must agree with the transition')
            require(transition.equal(read(self.bound(recipe['sources'][0]['scene']))['actors'][name]['placement'],read(self.bound(recipe['sources'][1]['scene']))['actors'][name]['placement']),'Source actor placements must match; align explicitly first')
            self.inputs[str(folder/'result.json')]=binding['result_sha256'];self.inputs[str(folder/'character.glb')]=sha256(folder/'character.glb')
            self.actors[name]=dict(folder=folder,result=r,problem=p);probes.append(p.probes)
        self.cut_a,self.cut_b=signature[0];self.start,self.end,self.duration=signature[1:];self.bridge_duration=self.end-self.start
        self.rounding_rows=[];self.mapping=[]
        self.spec=dict(schema='strep-native-scene-contacts-v1',duration_s=self.duration,actors={},objects={},contacts=[])
        for name,value in self.actors.items():
            entry=copy.deepcopy(read(self.bound(recipe['sources'][0]['scene']))['actors'][name])
            entry.update(glb='actors/'+name+'.glb',sha256=sha256(value['folder']/'character.glb'),animation_index=value['result']['animation_index']);self.spec['actors'][name]=entry
        self.game=dict(schema='strep-native-scene-game-tracks-v1',actors=copy.deepcopy(self.requests[0]['actors']),markers=[])
        for side,scene in enumerate(self.scenes):
            low,high=(0,self.cut_a) if side==0 else (self.cut_b,scene.duration)
            for row in scene.rows:
                source=row['authored'];lo,hi=source['interval_s'];left,right=max(lo,low),min(hi,high)
                keep=left<=right if source['mode']=='touch' else left<right
                record=dict(kind='contact',side=side,source_id=source['id'],source_interval_s=[lo,hi],disposition='dropped')
                if keep:
                    mapped=copy.deepcopy(source);mapped['id']=self.identifier(side,source['id']);mapped['interval_s']=[self.map_time(side,t) for t in (left,right)]
                    require(mapped['mode']=='touch' or mapped['interval_s'][0]<mapped['interval_s'][1],'A retained hold collapses under the shared clock')
                    self.spec['contacts'].append(mapped);record.update(output_id=mapped['id'],output_interval_s=mapped['interval_s'],disposition='retained' if (left,right)==(lo,hi) else 'clipped')
                self.mapping.append(record)
            for marker in self.requests[side]['markers']:
                record=dict(kind='marker',side=side,source_id=marker['id'],source_time_s=marker['time_s'],disposition='dropped')
                if low<=marker['time_s']<=high:
                    mapped=copy.deepcopy(marker);mapped.update(id=self.identifier(side,marker['id']),time_s=self.map_time(side,marker['time_s']),confirmed=False)
                    self.game['markers'].append(mapped);record.update(output_id=mapped['id'],output_time_s=mapped['time_s'],source_confirmed=marker['confirmed'],disposition='retained-confirmation-reset')
                self.mapping.append(record)
        require(isinstance(recipe['bridge']['contacts'],list) and isinstance(recipe['bridge']['markers'],list),'Explicit bridge arrays required')
        for kind,rows in recipe['bridge'].items():
            require(len(rows)<=64 if kind=='contacts' else len(rows)<=128,'Bounded bridge intent required')
            for row in rows:
                value=copy.deepcopy(row);SceneContacts.name(value.get('id'));value['id']='bridge_'+value['id'];SceneContacts.name(value['id'])
                ts=value.get('interval_s') if kind=='contacts' else [value.get('time_s')]
                require(isinstance(ts,list) and len(ts)==(2 if kind=='contacts' else 1),'Explicit bridge intent time required')
                for t in ts:scalar(t,self.start,self.end,'bridge intent time')
                if kind=='markers':require(value.get('confirmed') is False,'New transition markers need timing review before dispatch')
                (self.spec['contacts'] if kind=='contacts' else self.game['markers']).append(value)
        require(1<=len(self.spec['contacts'])<=64 and len(self.game['markers'])<=128,'Complete mapped contact/marker population exceeds schema limits; no truncation')
        self.object_curves={};self.object_clocks={};self.tail_maps={};self.refinement={}
        for name in a.objects:
            require(a.objects[name]['geometry'].record()==b.objects[name]['geometry'].record(),'Source object geometry changed')
            curve=self.object_curve(name);self.object_curves[name]=curve
            prefix=a.objects[name]['times'];prefix=prefix[prefix<self.cut_a]
            tail=b.objects[name]['times'];tail=tail[tail>self.cut_b]
            mapped=np.array([self.map_time(1,float(t)) for t in tail]);require(np.all(np.diff(mapped)>0) and np.all(mapped>self.end),'Object tail keys collide after timestamp encoding')
            self.tail_maps[name]=dict(zip(mapped,tail))
            bridge=np.unique(np.concatenate([np.array([self.start,self.end])]+[v['problem'].times[(v['problem'].times>self.start)&(v['problem'].times<self.end)] for v in self.actors.values()]))
            clock=np.unique(np.r_[0.,prefix,bridge,mapped,self.duration]);clock=self.refine_object(name,clock)
            self.object_clocks[name]=clock
            world=self.expected_object(name,clock);q=Rotation.from_matrix(world[:,:3,:3]).as_quat();keys=[]
            for t,p,r in zip(clock,world[:,:3,3],q):keys.append(dict(time_s=float(t),translation_m=p.tolist(),rotation_xyzw=r.tolist()))
            self.spec['objects'][name]=dict(geometry=a.objects[name]['geometry'].record(),keyframes=keys)
            probes.append(clock);probes.extend([clock[:-1]+f*np.diff(clock) for f in (.25,.5,.75)])
        probes.extend([np.array([0.,self.duration])]+[np.array(c['interval_s']) for c in self.spec['contacts']]+[np.array([m['time_s']]) for m in self.game['markers']])
        from engine_contact_sampling import frame_populations
        for c in self.spec['contacts']:
            if c['mode']=='hold':probes.extend([p['times_s'] for p in frame_populations(c['interval_s'])])
        self.times=np.unique(np.concatenate(probes));self.population=len(self.times)*(sum(2*len(a.actors[n]['rig'].parents)+len(a.actors[n]['skin'].nodes) for n in self.actors)+2*len(a.objects))
        require(self.population<=recipe['maximum_pose_vertex_queries'],'Complete scene population exceeds its budget; no truncation')
        resolved=copy.deepcopy(self.spec)
        for name in self.actors:resolved['actors'][name]['glb']=str(self.actors[name]['folder']/'character.glb')
        self.scene=SceneContacts(resolved,self.base);validate(self.game,self.scene,self.times)

    def bound(self,binding):
        fields(binding,('path','sha256'),'file binding');require(isinstance(binding['path'],str) and binding['path'],'Bound file path required')
        path=(self.base/binding['path']).resolve();require(sha256(path)==binding['sha256'],'Scene or track source changed')
        self.inputs[str(path)]=binding['sha256'];return path

    @staticmethod
    def identifier(side,name):
        result=('first_' if side==0 else 'second_')+name;SceneContacts.name(result);return result

    def map_time(self,side,time):
        ideal=float(time) if side==0 else float(time)-self.cut_b+self.end
        mapped=ideal if side==0 else float(np.float32(ideal));error=abs(mapped-ideal)
        require(error<=self.rounding,'Remapped timestamp exceeds its authored rounding permission')
        self.rounding_rows.append(dict(side=side,source_time_s=float(time),output_time_s=mapped,rounding_s=error));return mapped

    def object_curve(self,name):
        endpoints=[]
        for side,(scene,cut) in enumerate(zip(self.scenes,(self.cut_a,self.cut_b))):
            obj=scene.objects[name];times=obj['times']
            if len(times)==1:va=wa=np.zeros((1,3))
            else:
                i=int(np.searchsorted(times,cut,side='left'))
                if side==0:left=max(0,i-1)
                else:left=i if i<len(times) and times[i]==cut else max(0,i-1)
                left=min(left,len(times)-2);pair=(left,left+1)
                clock=times[list(pair)];p,r=scene.object_poses(name,clock);v,w=rates(matrices(p,r)[:,None],clock);va,wa=v[0],w[0]
            p,r=scene.object_poses(name,[cut]);endpoints.append((matrices(p,r),va,wa))
        a,va,wa=endpoints[0];b,vb,wb=endpoints[1]
        return LocalBridge(a,b,va,vb,wa,wb,self.bridge_duration,self.recipe['object_limits']['curve_control_rotation_degrees'])

    def refine_object(self,name,clock):
        limits=self.recipe['object_limits'];curve=self.object_curves[name];initial=len(clock);rounds=0
        # Refine only failing bridge intervals. Acceptance remains independent
        # readback on every declared scene/contact probe, not a continuous proof.
        for iteration in range(9):
            require(len(clock)<=3601,'Complete refined object clock exceeds 3601 keys; no truncation')
            inside=clock[(clock>=self.start)&(clock<=self.end)];values=curve.sample(inside-self.start)[:,0];bad=np.zeros(len(inside)-1,dtype=bool)
            for f in (.25,.5,.75):
                query=inside[:-1]+f*np.diff(inside);expected=curve.sample(query-self.start)[:,0]
                position=(1-f)*values[:-1,:3,3]+f*values[1:,:3,3];rotation=mix(values[:-1,:3,:3],values[1:,:3,:3],f)
                bad|=(np.linalg.norm(position-expected[:,:3,3],axis=1)>limits['position_error_m'])|(abs(rotation-expected[:,:3,:3]).max(axis=(1,2))>limits['basis_error'])
            if not bad.any():break
            if iteration==8:break  # Retain a failed candidate after the bounded proposal.
            additions=(inside[:-1]+.5*np.diff(inside))[bad];new=np.unique(np.r_[clock,additions]);require(len(new)>len(clock),'Object refinement clock collapsed')
            clock=new;rounds+=1
        self.refinement[name]=dict(initial_keys=initial,final_keys=len(clock),rounds=rounds,proposal_samples_pass=not bool(bad.any()))
        return clock

    def expected_object(self,name,times):
        values=[]
        for t in times:
            if t<self.start:p,r=self.scenes[0].object_poses(name,[float(t)]);world=matrices(p,r)[0]
            elif t>self.end:
                source=self.tail_maps[name].get(float(t),float(t)-self.end+self.cut_b);source=min(source,self.scenes[1].duration)
                p,r=self.scenes[1].object_poses(name,[source]);world=matrices(p,r)[0]
            else:world=self.object_curves[name].sample([float(t)-self.start])[0,0]
            values.append(world)
        return np.array(values)

    def write(self,output):
        output=Path(output);(output/'actors').mkdir()
        for name,value in self.actors.items():shutil.copyfile(value['folder']/'character.glb',output/'actors'/(name+'.glb'))
        save(output/'scene.json',self.spec);save(output/'game-tracks-request.json',self.game)

    def audit(self,output):
        output=Path(output);require(transition.equal(read(output/'scene.json'),self.spec) and transition.equal(read(output/'game-tracks-request.json'),self.game),'Assembled scene or game intent changed')
        scene=SceneContacts(self.spec,output);objects={};roots={};floor_depth=0.;all_times=[self.times]
        # Include every predeclared contact velocity population in the complete cap.
        from engine_contact_sampling import frame_populations
        for c in self.spec['contacts']:
            if c['mode']=='hold':all_times.extend([p['times_s'] for p in frame_populations(c['interval_s'])])
        times=np.unique(np.concatenate(all_times));population=len(times)*(sum(2*len(a['rig'].parents)+len(a['skin'].nodes) for a in scene.actors.values())+2*len(scene.objects))
        require(population<=self.recipe['maximum_pose_vertex_queries'],'Complete contact clock exceeds the scene population budget; no truncation')
        contact,arrays=scene.evaluate();events,tracks=event_plan(scene,self.game,times,contact)
        for name,actor in scene.actors.items():
            require(sha256(output/'actors'/(name+'.glb'))==sha256(self.actors[name]['folder']/'character.glb'),'Actor variant payload changed')
            node=self.game['actors'][name]['root_node'];p,r=actor['placement'];placement=np.eye(4);placement[:3,:3]=r;placement[:3,3]=p
            world=np.array([placement@actor['sampler'].sample(float(t)) for t in times]);selected=world[:,node]
            roots[name]=dict(root_node=node,animation_index=actor['animation_index'],character_glb_sha256=self.spec['actors'][name]['sha256'],world_matrices=selected.tolist(),initial_local_deltas=(np.linalg.inv(selected[0])@selected).tolist())
            if self.recipe['floor'] is not None:
                floor_depth=max(floor_depth,max(0,float(self.recipe['floor']['height_m']-min(actor['rig'].vertices(w)[:,1].min() for w in world))))
        limits=self.recipe['object_limits']
        for name in scene.objects:
            p,r=scene.object_poses(name,times);actual=matrices(p,r);expected=self.expected_object(name,times)
            position=float(np.linalg.norm(actual[:,:3,3]-expected[:,:3,3],axis=1).max());basis=float(abs(actual[:,:3,:3]-expected[:,:3,:3]).max())
            clock=self.object_clocks[name];p,r=scene.object_poses(name,clock);v,w=rates(matrices(p,r)[:,None],clock);boundaries=[]
            for t in (self.start,self.end):
                i=int(np.searchsorted(clock,t));boundaries.append(dict(time_s=t,linear_jump_m_s=float(np.linalg.norm(v[i]-v[i-1])),angular_jump_degrees_s=float(np.degrees(np.linalg.norm(w[i]-w[i-1])))))
            dt=np.diff(clock);acc=np.diff(v[:,0],axis=0)/((dt[1:]+dt[:-1])/2)[:,None];mask=(clock[1:-1]>=self.start)&(clock[1:-1]<=self.end);peak=float(np.linalg.norm(acc[mask],axis=1).max())
            objects[name]=dict(keys=len(clock),maximum_position_error_m=position,maximum_basis_error=basis,boundaries=boundaries,maximum_bridge_acceleration_m_s2=peak,
                passed=position<=limits['position_error_m'] and basis<=limits['basis_error'] and peak<=limits['acceleration_m_s2'] and all(c['linear_jump_m_s']<=limits['linear_boundary_jump_m_s'] and c['angular_jump_degrees_s']<=limits['angular_boundary_jump_degrees_s'] for c in boundaries))
        checks=dict(actor_transition_conditions=all(v['result']['all_declared_samples_pass'] for v in self.actors.values()),objects=all(o['passed'] for o in objects.values()),contacts=contact['passed'])
        if self.recipe['floor'] is not None:checks['floor']=floor_depth<=self.recipe['floor']['maximum_penetration_m']
        root_track=dict(schema='strep-native-scene-transition-root-references-v1',times_s=times.tolist(),actors=roots,application_mode='reference-only-motion-remains-embedded',quality_approved=False,release_approved=False)
        value=dict(schema=SCHEMA,status='complete',duration_s=self.duration,bridge_interval_s=[self.start,self.end],source_cuts_s=[self.cut_a,self.cut_b],
            queries=len(times),pose_vertex_population=population,objects=objects,checks=checks,all_declared_samples_pass=all(checks.values()),floor_maximum_penetration_m=None if self.recipe['floor'] is None else floor_depth,
            actor_results={n:dict(result_sha256=self.recipe['actors'][n]['result_sha256'],animation_index=v['result']['animation_index'],source_checks=v['result']['checks']) for n,v in self.actors.items()},
            timeline_mapping=self.mapping,timestamp_mapping=self.rounding_rows,object_refinement=self.refinement,
            floor_conditions_available=self.recipe['floor'] is not None,full_scene_collision_verified=False,gameplay_event_playback_verified=False,
            all_transferred_gameplay_confirmations_reset=True,original_selected=True,
            **{n:False for n in transition.FALSE_FLAGS},
            scope='Verified actor variants, tangent-bridged rigid objects, clipped/remapped source contact and marker intent, explicit bridge intent, sampled whole-scene contacts/floor and embedded root references. No attachment, full scene collision, continuous contact, runtime dispatch, production action or release approval.')
        return value,dict(events=events,contacts=tracks,roots=root_track),arrays


def run(recipe_path,output):
    recipe_path=Path(recipe_path).resolve();output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        recipe=read(recipe_path);problem=Problem(recipe,recipe_path.parent);require(not output.exists(),'Fresh scene transition output required')
        require(not recipe_path.is_relative_to(output) and not any(Path(p).is_relative_to(output) for p in problem.inputs),'Output contains a bound input')
        output.mkdir();shutil.copyfile(recipe_path,output/'recipe.json');(output/'implementation').mkdir();(output/'input').mkdir()
        snapshots={}
        for i,(p,h) in enumerate(problem.inputs.items()):
            name=str(i)+Path(p).suffix;shutil.copyfile(p,output/'input'/name);snapshots[p]=dict(path='input/'+name,sha256=h)
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS}
        for n in methods:shutil.copyfile(SCRIPT_ROOT/n,output/'implementation'/n)
        save(output/'prepared.json',dict(schema=SCHEMA,at=now(),recipe_original_path=str(recipe_path),recipe_base=str(recipe_path.parent),recipe_sha256=sha256(recipe_path),inputs=snapshots,implementation_sha256=methods))
        save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            problem.write(output);value,tracks,arrays=problem.audit(output)
            for name,data in tracks.items():save(output/(name+'.json'),data)
            np.savez_compressed(output/'contact-observations.npz',**arrays)
            value.update(prepared_sha256=sha256(output/'prepared.json'),files_sha256={n:sha256(output/n) for n in ['scene.json','game-tracks-request.json','events.json','contacts.json','roots.json','contact-observations.npz']+['actors/'+n+'.glb' for n in problem.actors]})
            save(output/'result.json',value);save(output/'completion.json',dict(result_sha256=sha256(output/'result.json')));save(output/'pipeline.json',dict(status='complete',original_selected=True));verify(output);return value
        except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


def verify(output):
    output=Path(output).resolve();p=read(output/'prepared.json')
    fields(p,('schema','at','recipe_original_path','recipe_base','recipe_sha256','inputs','implementation_sha256'),'scene transition preparation')
    require(p['schema']==SCHEMA and set(p['implementation_sha256'])==set(METHODS),'Complete scene transition methods required')
    for n,h in p['implementation_sha256'].items():require(sha256(SCRIPT_ROOT/n)==sha256(output/'implementation'/n)==h,'Scene transition methods changed')
    require(sha256(p['recipe_original_path'])==sha256(output/'recipe.json')==p['recipe_sha256'],'Scene transition recipe changed')
    problem=Problem(read(output/'recipe.json'),p['recipe_base']);require(set(p['inputs'])==set(problem.inputs),'Complete original scene inputs required')
    for i,(path,h) in enumerate(problem.inputs.items()):
        snapshot=p['inputs'][path];require(snapshot==dict(path='input/'+str(i)+Path(path).suffix,sha256=h),'Canonical complete scene snapshots required')
        require(sha256(path)==sha256(output/snapshot['path'])==h,'Scene transition source snapshot changed')
    require(read(output/'pipeline.json')==dict(status='complete',original_selected=True),'Completed scene transition required')
    value,tracks,arrays=problem.audit(output)
    for name,data in tracks.items():require(transition.equal(read(output/(name+'.json')),data),'Scene transition track changed')
    with np.load(output/'contact-observations.npz',allow_pickle=False) as stored:
        require(set(stored.files)==set(arrays),'Complete scene contact observation population required')
        for n,a in arrays.items():require(stored[n].dtype==a.dtype and stored[n].shape==a.shape and stored[n].tobytes()==a.tobytes(),'Scene contact observations changed')
    value.update(prepared_sha256=sha256(output/'prepared.json'),files_sha256={n:sha256(output/n) for n in ['scene.json','game-tracks-request.json','events.json','contacts.json','roots.json','contact-observations.npz']+['actors/'+n+'.glb' for n in problem.actors]})
    require(transition.equal(read(output/'result.json'),value),'Scene transition decisions changed')
    require(read(output/'completion.json')==dict(result_sha256=sha256(output/'result.json')),'Scene transition completion changed');return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();print(run(args.recipe,args.output))
