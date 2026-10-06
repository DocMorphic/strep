"""Bridge-only articulated scene proposals, with original clip libraries retained."""
import argparse,copy,shutil
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
import native_scene_transition as assembly
import native_scene_fit as fitting
from native_scene_edit import SceneEdits
from native_scene_resume import ResumeState
from native_scene_contacts import SceneContacts,fields
from native_scene_geometry import policy_for,evaluate_to_archive
from native_scene_game_tracks import event_plan
from native_support_clock import NativeSupportSampler
from native_transition_curve import localize
from gltf_tools import write_glb
from rig_asset import RigAsset
from strep import read,save,sha256,now

SCHEMA='strep-native-transition-scene-fit-v1'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(tuple(fitting.METHODS)+assembly.METHODS+('native_scene_game_tracks.py','native_transition_scene_fit.py')))
require=assembly.require
equal=assembly.transition.equal


def motion_clock(scene,unit,budget):
    """Preview the exact solver clock before allocating full pose arrays."""
    count=int(np.floor(scene.duration*120))+1
    require(count>=3,'At least three uniform source-rate samples required')
    require(count*unit<=budget,'Complete pose/skin queries exceed the authored budget; no truncation')
    native=[c[2] for a in scene.actors.values() for c in a['sampler'].channels]+[o['times'] for o in scene.objects.values()]
    clocks=[np.arange(count)/120]+native
    for entry in scene.rows:
        row=entry['authored'];a,b=row['interval_s']
        populations=fitting.frame_populations([a,b]) if row['mode']=='hold' else []
        clock=np.unique(np.concatenate([np.array([a,b])]+native+[p['times_s'] for p in populations]))
        clocks.append(clock[(clock>=a)&(clock<=b)])
    result=np.unique(np.concatenate(clocks))
    require(len(result)*unit<=budget,'Complete pose/skin queries exceed the authored budget; no truncation')
    return result


class Problem:
    def __init__(self,recipe,base):
        fields(recipe,('schema','source','label','actors','geometry','iterations','maximum_pose_vertex_queries'),'bridge scene correction')
        require(recipe['schema']==SCHEMA,'Bridge correction schema required')
        fields(recipe['source'],('folder','result_sha256'),'sealed scene transition')
        require(isinstance(recipe['source']['folder'],str) and recipe['source']['folder'],'Source transition folder required')
        require(isinstance(recipe['label'],str) and 1<=len(recipe['label'])<=160,'Explicit variant label required')
        require(type(recipe['iterations']) is int and 1<=recipe['iterations']<=16,'Choose 1-16 bounded correction iterations')
        require(type(recipe['maximum_pose_vertex_queries']) is int and 1<=recipe['maximum_pose_vertex_queries']<=1000000,'Complete query budget required')
        self.folder=(Path(base)/recipe['source']['folder']).resolve();self.recipe=recipe
        require(sha256(self.folder/'result.json')==recipe['source']['result_sha256'],'Selected scene transition result changed')
        self.parent=assembly.verify(self.folder);p=read(self.folder/'prepared.json')
        self.original=assembly.Problem(read(self.folder/'recipe.json'),p['recipe_base'])
        self.spec=read(self.folder/'scene.json')
        for a in self.spec['actors'].values():a['glb']=str((self.folder/a['glb']).resolve())
        self.scene=SceneContacts(self.spec,self.folder)
        fields(recipe['geometry'],('clock','limits','planes'),'explicit complete scene geometry')
        self.policy=dict(schema='strep-native-scene-geometry-v1',contacts_sha256='draft',**copy.deepcopy(recipe['geometry']))
        geometry_times=policy_for(self.policy,self.scene,'draft')[0]
        actors=copy.deepcopy(recipe['actors']);require(isinstance(actors,dict) and actors and not set(actors)-set(self.scene.actors),'Explicit existing correction actors required')
        self.guards={}
        for name,a in actors.items():
            fields(a,('window_s','protected_s','knots_s','tracks','maximum_joint_displacement_m'),'bridge edit permission')
            require(equal(a['window_s'],[self.original.start,self.original.end]),'Edit window must equal the sealed bridge; source phases are protected')
            require(isinstance(a['protected_s'],list),'Explicit additional protected spans required')
            require(isinstance(a['tracks'],list) and a['tracks'],'Explicit native tracks required')
            guards=[]
            for t in a['tracks']:
                fields(t,('node','path','maximum_change'),'native bridge track')
                found=[c for c in self.scene.actors[name]['sampler'].channels if c[:2]==(t['node'],t['path'])]
                require(len(found)==1,'Existing unique bridge track required');clock=found[0][2]
                lo,hi=np.searchsorted(clock,[self.original.start,self.original.end])
                require(hi<len(clock) and clock[lo]==self.original.start and clock[hi]==self.original.end and hi-lo>=4,'Native bridge needs endpoints, tangent guards and interior keys')
                guards.extend([[self.original.start,float(clock[lo+1])],[float(clock[hi-1]),self.original.end]])
            self.guards[name]=guards;a['protected_s']+=guards
        self.permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256='draft',actors=actors)
        self.edits=SceneEdits(self.permissions,self.scene,'draft',rotation_storage_policy='source-scale')
        require(self.edits.size<=96,'At most 96 complete controls; no truncation')
        unit=sum(2*len(a['rig'].parents)+len(a['skin'].nodes) for a in self.scene.actors.values())+2*len(self.scene.objects)
        clock=motion_clock(self.scene,unit,recipe['maximum_pose_vertex_queries'])
        self.times=np.unique(np.concatenate([clock,geometry_times,np.asarray(read(self.folder/'roots.json')['times_s']),self.original.times]))
        self.population=len(self.times)*unit
        require(self.population<=recipe['maximum_pose_vertex_queries'],'Complete pose/skin queries exceed the authored budget; no truncation')
        self.motion=fitting.SceneProblem(self.scene,self.edits)
        require(np.array_equal(clock,self.motion.times),'Preflight and solver clocks differ; no partial population allowed')

    def append(self,name,value,path):
        actor=self.scene.actors[name];rig=actor['rig'];doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
        if name in self.edits.actors:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                fitted=Path(tmp)/'fitted.glb';self.edits.export(name,value,fitted);self.edits.audit(name,fitted,actor['animation_index'])
                candidate=RigAsset.load(fitted);doc=copy.deepcopy(candidate.document);binary=bytearray(candidate.binary)
        variant=copy.deepcopy(doc['animations'][actor['animation_index']]);variant['name']=self.recipe['label']
        doc['animations'][actor['animation_index']]=copy.deepcopy(rig.document['animations'][actor['animation_index']])
        index=len(doc['animations']);doc['animations'].append(variant);write_glb(path,doc,binary)
        return index

    def audit(self,output,value,*,publish=False):
        output=Path(output);spec=read(output/'scene.json');expected=copy.deepcopy(self.spec);checks={};files={};all_worlds={}
        for number,(name,a) in enumerate(self.scene.actors.items()):
            path=output/'actors'/(str(number)+'.glb');index=len(a['rig'].document['animations']);expected['actors'][name].update(glb='actors/'+str(number)+'.glb',sha256=sha256(path),animation_index=index)
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                replay=Path(tmp)/'candidate.glb';require(self.append(name,value,replay)==index and sha256(replay)==sha256(path),'Appended bridge variant does not replay from original controls')
            changed=RigAsset.load(path);require(changed.binary[:len(a['rig'].binary)]==a['rig'].binary,'Original binary payload changed')
            require(equal(changed.document['animations'][:-1],a['rig'].document['animations']),'Original clip library changed')
            reader=NativeSupportSampler(changed.document,changed.binary,index)
            all_worlds[name]=np.array([reader.sample(float(t)) for t in self.times])
            original=copy.copy(self.original.actors[name]['problem']);original.rig=a['rig']
            original.local=lambda times,n=name,actor=a:localize(self.edits.worlds(n,value,times) if n in self.edits.actors else np.array([actor['sampler'].sample(float(t)) for t in times]),actor['rig'].parents)
            checks[name]=original.audit(path)
            if name in self.edits.actors:
                # The independently decoded selected variant supplies every motion/contact row.
                files[name]=path
        require(equal(spec,expected),'Candidate scene changes original intent, object motion, placements or participant selection')
        scene=SceneContacts(spec,output);worlds=dict(self.motion.source_world)
        for name in files:
            actor=scene.actors[name];worlds[name]=np.array([actor['sampler'].sample(float(t)) for t in self.motion.times])
        residual=self.motion.constraints(value,worlds)
        contact,arrays=scene.evaluate()
        policy=dict(schema='strep-native-scene-geometry-v1',contacts_sha256=sha256(output/'scene.json'),**copy.deepcopy(self.recipe['geometry']))
        if publish:geometry,transport=evaluate_to_archive(scene,policy,policy['contacts_sha256'],output/'geometry-observations.npz')
        else:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:geometry,transport=evaluate_to_archive(scene,policy,policy['contacts_sha256'],Path(tmp)/'geometry-observations.npz')
        geometry.update(**transport)
        inherited=shared_floor(scene,all_worlds,self.original.recipe['floor'],self.times)
        if inherited is not None:geometry['inherited_shared_floor']=inherited
        decisions=dict(native_motion_and_contacts=bool(np.all(residual<=0)),
            native_contact_audit=contact['passed'],actor_transition_conditions=all(x['all_declared_samples_pass'] for x in checks.values()),
            whole_scene_geometry=geometry['sampled_conditions_pass'])
        if inherited is not None:decisions['inherited_shared_floor']=inherited['passed']
        return scene,spec,all_worlds,contact,arrays,policy,geometry,decisions,checks


def shared_floor(scene,worlds,floor,times):
    if floor is None:return None
    times=np.asarray(times,float)
    require(times.ndim==1 and len(times)>1 and np.isfinite(times).all() and np.all(np.diff(times)>0)
        and times[0]==0 and times[-1]==scene.duration,'Complete finite full-clip floor clock required')
    require(set(worlds)==set(scene.actors),'Complete floor actor population required')
    depth=0.;peak=None
    for name,a in scene.actors.items():
        values=np.asarray(worlds[name],float)
        require(values.shape==(len(times),len(a['rig'].parents),4,4) and np.isfinite(values).all(),'Complete finite floor pose population required')
        p,r=a['placement']
        for time,world in zip(times,values):
            vertices=a['rig'].vertices(world)@r.T+p;current=max(0.,float(floor['height_m']-vertices[:,1].min()))
            if current>depth:depth=current;peak=dict(actor=name,time_s=float(time))
    return dict(height_m=floor['height_m'],maximum_penetration_m=depth,limit_m=floor['maximum_penetration_m'],
        peak=peak,samples=len(times),full_clip=True,passed=depth<=floor['maximum_penetration_m'])


def write_tracks(problem,scene,spec,request,worlds,contact,folder,scene_digest):
    """Native references only; never substitute these for imported observations."""
    require(all(m['confirmed'] is False for m in request['markers']),'Transferred markers must remain unconfirmed')
    folder=Path(folder);require(not folder.exists(),'Fresh native track folder required');folder.mkdir()
    events,contacts=event_plan(scene,request,problem.times,contact);roots={};arrays={'times_s':problem.times}
    for i,(name,a) in enumerate(scene.actors.items()):
        node=request['actors'][name]['root_node'];p,r=a['placement'];placement=np.eye(4);placement[:3,:3]=r;placement[:3,3]=p
        selected=np.asarray(placement@worlds[name][:,node],dtype='<f8');delta=np.linalg.inv(selected[0])@selected
        require(np.max(abs(selected[0]@delta-selected))<=1e-9,'Root reference reconstruction differs')
        prefix='actor_'+str(i);arrays[prefix+'_world_matrices']=selected;arrays[prefix+'_initial_local_deltas']=delta
        roots[name]=dict(root_node=node,animation_index=a['animation_index'],character_glb_sha256=spec['actors'][name]['sha256'],
            world_matrices=selected.tolist(),initial_local_deltas=delta.tolist())
    root=dict(schema='strep-native-scene-transition-root-references-v1',times_s=problem.times.tolist(),actors=roots,
        application_mode='reference-only-motion-remains-embedded',native_only=True,engine_playback_verified=False,quality_approved=False,release_approved=False)
    events['portable_scene_sha256']=scene_digest;contacts['portable_scene_sha256']=scene_digest
    save(folder/'root-motion.json',root);save(folder/'events.json',events);save(folder/'contacts.json',contacts);save(folder/'request.json',request)
    np.savez_compressed(folder/'root-observations.npz',**arrays);return root


def artifact_names(problem):
    return ['scene.json','game-tracks-request.json','contacts-audit.json','contact-observations.npz','geometry-policy-proposal.json','geometry.json','geometry-observations.npz','geometry-observations.npz.receipt.json']+['actors/'+str(i)+'.glb' for i in range(len(problem.scene.actors))]+['tracks/'+n for n in ('root-motion.json','root-observations.npz','contacts.json','events.json','request.json')]


def decision(problem,output,value,checks,actors):
    return dict(schema=SCHEMA,status='complete',prepared_sha256=sha256(output/'prepared.json'),source_result_sha256=problem.recipe['source']['result_sha256'],
        fit_result_sha256=sha256(output/'fit/result.json'),checks=checks,all_declared_samples_pass=all(checks.values()),actors=actors,
        parent_checks=problem.parent['checks'],parent_decisions_apply_to_original_only=True,bridge_interval_s=[problem.original.start,problem.original.end],tangent_guards=problem.guards,
        controls=value.tolist(),samples=len(problem.times),pose_vertex_population=problem.population,native_root_references_consistent=True,root_observations_are_native_only=True,
        original_clip_libraries_retained=True,source_phases_and_boundary_tangents_protected=True,original_selected=True,
        quality_approved=False,training_admitted=False,release_approved=False,engine_playback_verified=False,
        files_sha256={n:sha256(output/n) for n in artifact_names(problem)},
        scope='Separate bridge-only native TRS proposal under original permissions, source-rate caps, contacts, object paths and parent support/floor/root/boundary limits. Original clips and scene/timing evidence remain. No contact inference, feasibility guarantee, dynamics, live Studio, engine, human motion quality or release approval.')


def run(recipe_path,output,*,resume_from=None):
    recipe_path=Path(recipe_path).resolve();output=Path(output).resolve();require(not output.exists(),'Fresh bridge correction output required')
    problem=Problem(read(recipe_path),recipe_path.parent)
    require(not output.is_relative_to(problem.folder) and not problem.folder.is_relative_to(output),'Output must be separate from the sealed source')
    output.mkdir(parents=True);save(output/'pipeline.json',dict(status='preparing',original_selected=True))
    try:
        with threadpool_limits(limits=1):
            tree={p.relative_to(problem.folder).as_posix():sha256(p) for p in problem.folder.rglob('*') if p.is_file()}
            require(len(tree)<=256 and sum((problem.folder/n).stat().st_size for n in tree)<=1024**3,'Complete source snapshot exceeds its budget')
            shutil.copytree(problem.folder,output/'original-transition');shutil.copyfile(recipe_path,output/'recipe.json')
            methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};(output/'implementation').mkdir()
            for n in methods:shutil.copyfile(SCRIPT_ROOT/n,output/'implementation'/n)
            save(output/'contacts.json',problem.spec);digest=sha256(output/'contacts.json')
            permissions=copy.deepcopy(problem.permissions);permissions['contacts_sha256']=digest;save(output/'permissions.json',permissions)
            policy=copy.deepcopy(problem.policy);policy['contacts_sha256']=digest;save(output/'geometry-policy.json',policy)
            resume=None
            if resume_from is not None:
                resume_from=Path(resume_from).resolve();require(not resume_from.is_relative_to(output),'Resume source must be separate')
                resume=dict(folder=str(resume_from),result_sha256=sha256(resume_from/'result.json'))
            prepared=dict(schema=SCHEMA,at=now(),recipe_original=str(recipe_path),recipe_base=str(recipe_path.parent),recipe_sha256=sha256(recipe_path),resume_source=resume,
                original_files_sha256=tree,implementation_sha256=methods,files_sha256={n:sha256(output/n) for n in ('contacts.json','permissions.json','geometry-policy.json')})
            save(output/'prepared.json',prepared);save(output/'pipeline.json',dict(status='processing',original_selected=True))
            fitting.run(output/'contacts.json',output/'permissions.json',output/'fit',iterations=problem.recipe['iterations'],trust=.02,
                proposal_model='storage-vector',vector_difference_scheme='central',vector_difference_step=.001,restoration_steps=3,
                restoration_model='recentered',serialized_ray_probes=64,rotation_storage_policy='source-scale',geometry_policy=output/'geometry-policy.json',resume_from=resume_from)
            value=np.asarray(read(output/'fit/probes/final/probe.json')['controls'])
            (output/'actors').mkdir();spec=copy.deepcopy(problem.spec)
            for number,(name,a) in enumerate(spec['actors'].items()):
                path=output/'actors'/(str(number)+'.glb');index=problem.append(name,value,path);a.update(glb='actors/'+str(number)+'.glb',sha256=sha256(path),animation_index=index)
            save(output/'scene.json',spec)
            scene,spec,worlds,contact,arrays,policy,geometry,checks,actors=problem.audit(output,value,publish=True)
            save(output/'contacts-audit.json',contact);np.savez_compressed(output/'contact-observations.npz',**arrays);save(output/'geometry-policy-proposal.json',policy);save(output/'geometry.json',geometry)
            request=read(problem.folder/'game-tracks-request.json');require(all(m['confirmed'] is False for m in request['markers']),'Transferred timings must remain unconfirmed')
            save(output/'game-tracks-request.json',request)
            write_tracks(problem,scene,spec,request,worlds,contact,output/'tracks',sha256(output/'scene.json'))
            result=decision(problem,output,value,checks,actors)
            save(output/'result.json',result);save(output/'completion.json',dict(result_sha256=sha256(output/'result.json')));save(output/'pipeline.json',dict(status='complete',original_selected=True));verify(output);return result
    except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


def verify(output):
    output=Path(output).resolve();p=read(output/'prepared.json');require(p['schema']==SCHEMA and set(p['implementation_sha256'])==set(METHODS),'Complete bridge correction methods required')
    for n,h in p['implementation_sha256'].items():require(sha256(SCRIPT_ROOT/n)==sha256(output/'implementation'/n)==h,'Bridge correction implementation changed')
    require(sha256(p['recipe_original'])==sha256(output/'recipe.json')==p['recipe_sha256'],'Bridge correction recipe changed')
    problem=Problem(read(output/'recipe.json'),p['recipe_base'])
    require(p['original_files_sha256']=={v.relative_to(problem.folder).as_posix():sha256(v) for v in problem.folder.rglob('*') if v.is_file()},'Original transition changed')
    require(p['original_files_sha256']=={v.relative_to(output/'original-transition').as_posix():sha256(v) for v in (output/'original-transition').rglob('*') if v.is_file()},'Complete original transition snapshot changed')
    for n,h in p['files_sha256'].items():require(sha256(output/n)==h,'Bridge correction input changed')
    require(set(p['files_sha256'])=={'contacts.json','permissions.json','geometry-policy.json'},'Complete bridge correction inputs required')
    require(equal(read(output/'contacts.json'),problem.spec),'Original scene intent changed')
    permissions=copy.deepcopy(problem.permissions);permissions['contacts_sha256']=sha256(output/'contacts.json');require(equal(read(output/'permissions.json'),permissions),'Bridge correction permissions changed')
    policy=copy.deepcopy(problem.policy);policy['contacts_sha256']=sha256(output/'contacts.json');require(equal(read(output/'geometry-policy.json'),policy),'Bridge correction geometry changed')
    scene=SceneContacts(problem.spec,problem.folder);edits=SceneEdits(permissions,scene,sha256(output/'contacts.json'),rotation_storage_policy='source-scale')
    retained=ResumeState(output/'fit',sha256(output/'contacts.json'),sha256(output/'permissions.json'),edits);retained.check_geometry(policy,sha256(output/'contacts.json'));retained.check_caps(fitting.SceneProblem(scene,edits),__import__('engine_contact_sampling').contract_sha256());retained.check_inputs()
    resume=p.get('resume_source')
    if resume is not None:
        fields(resume,('folder','result_sha256'),'original fit continuation')
        require(sha256(Path(resume['folder'])/'result.json')==resume['result_sha256'],'Original fit continuation changed')
        request=read(output/'fit/request.json');require(request['resume']['source_directory']==resume['folder'],'Continuation source epoch changed')
    else:require(read(output/'fit/request.json')['resume'] is None,'Unrequested continuation changed the source epoch')
    r=read(output/'result.json');require(equal(r['controls'],retained.controls.tolist()),'Final bridge controls changed')
    value=retained.controls;scene,spec,worlds,contact,arrays,policy,geometry,checks,actors=problem.audit(output,value)
    require(equal(read(output/'contacts-audit.json'),contact) and equal(read(output/'geometry-policy-proposal.json'),policy) and equal(read(output/'geometry.json'),geometry),'Bridge correction observations changed')
    with np.load(output/'contact-observations.npz',allow_pickle=False) as stored:require(set(stored.files)==set(arrays) and all(stored[n].dtype==a.dtype and stored[n].shape==a.shape and stored[n].tobytes()==a.tobytes() for n,a in arrays.items()),'Complete contact observation arrays changed')
    require(equal(read(output/'game-tracks-request.json'),read(problem.folder/'game-tracks-request.json')),'Original marker intent changed')
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        write_tracks(problem,scene,spec,read(output/'game-tracks-request.json'),worlds,contact,Path(tmp)/'tracks',sha256(output/'scene.json'))
        for n in ('root-motion.json','root-observations.npz','contacts.json','events.json','request.json'):
            require(sha256(Path(tmp)/'tracks'/n)==sha256(output/'tracks'/n),'Native roots, contact intent or unconfirmed timing changed')
    require(equal(r,decision(problem,output,value,checks,actors)),'Bridge correction decisions or artifact population changed')
    require(equal(read(output/'completion.json'),dict(result_sha256=sha256(output/'result.json'))) and equal(read(output/'pipeline.json'),dict(status='complete',original_selected=True)),'Completed bridge correction required');return r


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--resume-from',type=Path);args=parser.parse_args();print(run(args.recipe,args.output,resume_from=args.resume_from))
