"""Explicit root references and native-clock contact/gameplay intent tracks.

Root motion stays embedded in the supplied clips. The extracted transforms are
references, never a second placement track to apply to those same clips.
"""
import copy
from pathlib import Path
import numpy as np
from native_scene_contacts import fields,scalar,SceneContacts
from rig_asset import read_asset
from native_engine_clock import clock_wire
from native_scene_engine import POSE_TOLERANCE
from strep import save,read,sha256


def require(condition,message):
    if not condition:raise ValueError(message)


def validate(request,scene,times):
    fields(request,('schema','actors','markers'),'native game tracks')
    require(request['schema']=='strep-native-scene-game-tracks-v1','Native game track schema required')
    times=np.asarray(times,dtype='<f8');clock_wire(times)
    require(times[-1]==scene.duration,'Complete audited scene clock required')
    require(isinstance(request['actors'],dict) and set(request['actors'])==set(scene.actors),'Choose a root joint for every scene actor')
    for name,choice in request['actors'].items():
        fields(choice,('root_node',),'root joint choice');node=choice['root_node']
        require(type(node) is int and node in scene.actors[name]['rig'].joints,'Choose an existing skin joint as root; no anatomy inference')
    require(isinstance(request['markers'],list) and len(request['markers'])<=128,'Use at most 128 explicit gameplay markers')
    seen=set()
    for entry in request['markers']:
        fields(entry,('id','name','actor','time_s','confirmed'),'native gameplay marker');SceneContacts.name(entry['id'])
        require(entry['id'] not in seen,'Unique marker IDs required');seen.add(entry['id'])
        require(isinstance(entry['name'],str) and 1<=len(entry['name'].strip())<=64
            and entry['name']==entry['name'].strip(),'Choose a short explicit marker name')
        require(isinstance(entry['actor'],str) and entry['actor'] in scene.actors,'Marker actor must be selected')
        time=scalar(entry['time_s'],0,scene.duration,'marker time');index=np.searchsorted(times,time)
        require(index<len(times) and times[index]==time,'Choose an exact audited time; declare other times in the scene clock and rebuild first')
        require(type(entry['confirmed']) is bool,'Explicit marker timing confirmation required')
    return times


def event_plan(scene,request,times,report):
    times=validate(request,scene,times)
    require([r['id'] for r in report['contacts']]==[r['authored']['id'] for r in scene.rows],'Complete ordered measured contact report required')
    events=[];contacts=[]
    for entry,measured in zip(scene.rows,report['contacts']):
        row=entry['authored'];require(measured['interval_s']==row['interval_s'] and measured['limits']==row['limits']
            and measured['mode']==row['mode'] and measured['target_space']==row['target']['space'],'Measured contact intent differs')
        contacts.append(dict(intent=copy.deepcopy(row),measurement=copy.deepcopy(measured),runtime_dispatch_allowed=False))
        boundaries=[('touch',row['interval_s'][0])] if row['mode']=='touch' else [('start',row['interval_s'][0]),('end',row['interval_s'][1])]
        for boundary,time in boundaries:
            index=int(np.searchsorted(times,time));require(index<len(times) and times[index]==time,'Complete exact contact boundary clock required')
            events.append(dict(id=f'contact:{row["id"]}:{boundary}',name=boundary,actor=row['actor'],kind='contact_intent',
                contact_id=row['id'],time_s=time,sample_index=index,timing_confirmed=False,runtime_dispatch_allowed=False,
                sampled_contact_conditions_pass=measured['passed']))
    for marker in request['markers']:
        events.append(dict(id='marker:'+marker['id'],name=marker['name'],actor=marker['actor'],kind='gameplay_intent',
            time_s=marker['time_s'],sample_index=int(np.searchsorted(times,marker['time_s'])),timing_confirmed=marker['confirmed'],
            runtime_dispatch_allowed=marker['confirmed']))
    priority=lambda e:0 if e['kind']=='contact_intent' and e['name']=='end' else 1 if e['kind']=='contact_intent' else 2
    events.sort(key=lambda e:(e['sample_index'],priority(e),e['id']))
    return dict(schema='strep-native-scene-game-events-v1',clock=clock_wire(times),duration_s=scene.duration,events=events,
        quality_approved=False,physics_verified=False,release_approved=False,
        scope='Explicit gameplay timing intent only. Contact boundaries never dispatch automatically; sampled contact success does not confirm gameplay, physical attachment or action correctness.'),dict(
        schema='strep-native-scene-contact-tracks-v1',contacts=contacts,continuous_contact_certified=False,
        quality_approved=False,physics_verified=False,release_approved=False)


def crossed(plan,previous,current):
    """Forward finite clock; None starts at zero. Rewind/restart is explicit."""
    duration=plan['duration_s'];current=scalar(current,0,duration,'event clock')
    if previous is not None:
        previous=scalar(previous,0,duration,'previous event clock');require(current>=previous,'Rewind requires an explicit event cursor reset')
    return [copy.deepcopy(e) for e in plan['events'] if e['runtime_dispatch_allowed']
        and (previous is None or e['time_s']>previous) and e['time_s']<=current]


def export(scene,request,times,imported_worlds,report,output,*,source_spec,portable_scene_sha256,contact_report_sha256):
    output=Path(output);require(not output.exists(),'Fresh game track output required')
    times=validate(request,scene,times);require(set(imported_worlds)==set(scene.actors),'Complete imported root observations required')
    scene.check_inputs();roots={};arrays={'times_s':times};checks={}
    require(set(source_spec['actors'])==set(scene.actors),'Complete source actor bindings required')
    for i,(name,actor) in enumerate(scene.actors.items()):
        node=request['actors'][name]['root_node'];joint=actor['rig'].joints.index(node)
        binding=source_spec['actors'][name];path=str(Path(binding['glb']).resolve())
        require(scene.inputs.get(path)==binding['sha256'] and sha256(path)==binding['sha256']
            and binding['animation_index']==actor['animation_index'],'Root source selection differs')
        document,binary=read_asset(path)
        require(document==actor['rig'].document and binary==actor['rig'].binary,'Root source belongs to another actor')
        placement=np.eye(4);placement[:3,:3]=actor['placement'][1];placement[:3,3]=actor['placement'][0]
        native=np.array([placement@actor['sampler'].sample(float(t))[node] for t in times],dtype='<f8')
        observed=np.asarray(imported_worlds[name],dtype='<f8')
        require(observed.shape==(len(times),len(actor['rig'].joints),4,4) and np.isfinite(observed).all(),'Complete finite imported joint matrices required')
        actual=placement@observed[:,joint]
        position_error=float(np.linalg.norm(actual[:,:3,3]-native[:,:3,3],axis=1).max())
        basis_error=float(abs(actual[:,:3,:3]-native[:,:3,:3]).max())
        check=dict(samples=len(times),maximum_position_error_m=position_error,maximum_basis_element_error=basis_error,
            limit=POSE_TOLERANCE,passed=position_error<=POSE_TOLERANCE and basis_error<=POSE_TOLERANCE)
        checks[name]=check
        # Preserve the complete matrices, including any accepted source roundoff.
        # No yaw filter, resampling, projection or decomposition is inferred.
        delta=np.linalg.inv(native[0])@native
        require(np.isfinite(delta).all(),'Finite root reference deltas required')
        require(float(abs(native[0]@delta-native).max())<=1e-9,'Root reference delta reconstruction differs')
        prefix=f'actor_{i}'
        arrays[prefix+'_world_matrices']=native;arrays[prefix+'_initial_local_deltas']=delta;arrays[prefix+'_imported_world_matrices']=actual
        roots[name]=dict(root_node=node,character_glb_sha256=binding['sha256'],
            animation_index=actor['animation_index'],actor_glb=f'actors/{i}.glb',world_matrices=native.tolist(),
            initial_local_deltas=delta.tolist(),array_prefix=prefix,imported_comparison=check)
    events,contacts=event_plan(scene,request,times,report)
    output.mkdir(parents=True)
    save(output/'request.json',request)
    save(output/'root-motion.json',dict(schema='strep-native-scene-root-references-v1',times_s=times.tolist(),actors=roots,
        portable_scene_sha256=portable_scene_sha256,application_mode='reference-only-motion-remains-embedded',
        delta_convention='inverse(world_matrix_at_zero) @ world_matrix_at_time; world_zero @ delta reconstructs world',
        units='Metres, glTF Y-up, authored scene placements included',source_interpolation_preserved_in_glb=True,
        between_reference_samples_certified=False,quality_approved=False,release_approved=False))
    events['portable_scene_sha256']=portable_scene_sha256;contacts.update(portable_scene_sha256=portable_scene_sha256,contact_report_sha256=contact_report_sha256)
    save(output/'events.json',events);save(output/'contacts.json',contacts)
    np.savez_compressed(output/'root-observations.npz',**arrays)
    with np.load(output/'root-observations.npz',allow_pickle=False) as stored:
        require(set(stored.files)==set(arrays),'Complete root array population required')
        for name,values in arrays.items():require(stored[name].dtype==values.dtype and stored[name].shape==values.shape
            and stored[name].tobytes()==values.tobytes(),'Root observation transport changed')
    scene.check_inputs()
    result=dict(status='complete',samples=len(times),root_comparisons=checks,all_root_samples_pass=all(c['passed'] for c in checks.values()),
        contact_conditions_pass=report['passed'],events=len(events['events']),dispatchable_gameplay_markers=sum(e['runtime_dispatch_allowed'] for e in events['events']),
        source_actor_bytes_unchanged=True,root_arrays_roundtrip_exact=True,original_selected=True,
        quality_approved=False,physics_verified=False,training_admitted=False,release_approved=False,
        files_sha256={n:sha256(output/n) for n in ('request.json','root-motion.json','root-observations.npz','contacts.json','events.json')})
    save(output/'result.json',result);return result
