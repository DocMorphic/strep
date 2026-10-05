"""Retain explicit scene contact intent across native rig transfers.

Vertex correspondence is authored, never inferred from joint names. This
creates a separate portable scene and measures failures; it does not solve them.
"""
import argparse
import copy
from pathlib import Path
import shutil

import numpy as np
from threadpoolctl import threadpool_limits

import audit_native_rig_transfer as transfer_audit
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts, fields, METHODS as CONTACT_METHODS
from engine_contact_sampling import frame_populations
from strep import read, save, sha256, now

SCHEMA='strep-native-transfer-scene-v1'
METHODS=tuple(dict.fromkeys(CONTACT_METHODS+transfer_audit.METHODS+('native_transfer_scene.py',)))
SCRIPT_ROOT=Path(__file__).resolve().parent
POSITION_QUERY_LIMIT=262144
POINT_OBSERVATION_LIMIT=1000000


def require(value,message):
    if not value:raise ValueError(message)


def binding(entry,base,directory=False):
    fields(entry,('path','sha256'),'transfer scene input binding')
    require(isinstance(entry['path'],str) and bool(entry['path']),'Explicit input path required')
    path=(Path(base)/entry['path']).resolve()
    hashed=path/'report.json' if directory else path
    require(isinstance(entry['sha256'],str) and len(entry['sha256'])==64
        and sha256(hashed)==entry['sha256'],'Transfer scene input changed')
    return path


def vertex_key(ref):
    require(isinstance(ref,list) and len(ref)==3 and all(type(v) is int and v>=0 for v in ref),
        'Exact [mesh node, primitive, vertex] correspondence required')
    return tuple(ref)


def used_vertices(spec,name):
    used=set()
    for row in spec['contacts']:
        if row['actor']==name:used.update(vertex_key(r) for r in row['vertices'])
        target=row['target']
        if target['space']=='actor' and target['actor']==name:used.update(vertex_key(r) for r in target['vertices'])
    return used


def remap(spec,replacements):
    """Change only bound actor clips and explicitly corresponding vertex IDs."""
    result=copy.deepcopy(spec)
    for name,entry in replacements.items():
        fields(entry,('glb','sha256','animation_index','vertex_map'),'bound actor replacement')
        require(name in spec['actors'],'Existing scene actor required')
        table=entry['vertex_map'];required=used_vertices(spec,name)
        require(isinstance(table,list) and 1<=len(table)<=16384,'Complete explicit used-vertex correspondence required')
        mapping={};targets=set()
        for pair in table:
            fields(pair,('source','target'),'vertex correspondence')
            source=vertex_key(pair['source']);target=vertex_key(pair['target'])
            require(source not in mapping and target not in targets,'Distinct one-to-one vertex correspondence required')
            mapping[source]=list(target);targets.add(target)
        require(set(mapping)==required,'Correspondence must cover every used source/partner vertex exactly; no extra or omitted vertices')
        result['actors'][name].update(**{k:entry[k] for k in ('glb','sha256','animation_index')})
        for row in result['contacts']:
            if row['actor']==name:row['vertices']=[mapping[vertex_key(r)] for r in row['vertices']]
            target=row['target']
            if target['space']=='actor' and target['actor']==name:
                target['vertices']=[mapping[vertex_key(r)] for r in target['vertices']]
    return result


def validated(recipe_path):
    recipe_path=Path(recipe_path).resolve();recipe=read(recipe_path)
    fields(recipe,('schema','contacts','transfers'),'transfer scene recipe')
    require(recipe['schema']==SCHEMA,'Native transfer scene recipe required')
    contacts=binding(recipe['contacts'],recipe_path.parent);spec=read(contacts)
    scene=SceneContacts(spec,contacts.parent);transfers=recipe['transfers']
    require(isinstance(transfers,dict) and 1<=len(transfers)<=8 and set(transfers)<=set(scene.actors),
        'Choose 1-8 existing actors with native rig transfers')
    sources={str(recipe_path):sha256(recipe_path),str(contacts):sha256(contacts),**scene.inputs}
    replacements={};folders={}
    for name,entry in transfers.items():
        fields(entry,('candidate','vertex_map'),'actor transfer')
        folder=binding(entry['candidate'],recipe_path.parent,directory=True)
        bound=transfer_audit.bound_candidate(folder);report=bound[1];original=spec['actors'][name]
        require(original['sha256']==report['input_snapshots_sha256']['source.glb']
            and original['animation_index']==report['source_animation_index'],'Transfer belongs to another scene actor or source clip')
        require(report['source_duration_s']==scene.duration,'Transfer duration differs from scene')
        replacements[name]=dict(glb=str(folder/'character.glb'),sha256=report['glb_sha256'],
            animation_index=report['output_animation_index'],vertex_map=copy.deepcopy(entry['vertex_map']))
        folders[name]=folder
        for p in folder.rglob('*'):
            if p.is_file():sources[str(p.resolve())]=sha256(p)
    changed=remap(spec,replacements);candidate=SceneContacts(changed,contacts.parent)
    planned_clocks(scene,candidate)
    scene.check_inputs();candidate.check_inputs()
    return recipe,contacts,scene,changed,candidate,folders,sources


def contact_points(scene,entry,times):
    row=entry['authored'];target=row['target'];effector=scene.actor_points(row['actor'],entry['ids'],times)
    if row['reduction']=='centroid':effector=effector.mean(axis=1,keepdims=True)
    if target['space']=='actor':
        goal=scene.actor_points(target['actor'],entry['target_ids'],times)
        if target['reduction']=='centroid':goal=goal.mean(axis=1,keepdims=True)
    elif target['space']=='world':goal=np.repeat(entry['target_ids'][None],len(times),axis=0)
    else:
        p,r=scene.object_poses(target['object'],times);goal=np.einsum('fij,vj->fvi',r,entry['target_ids'])+p[:,None]
    return effector,goal


def planned_clocks(original,candidate):
    """Budget the whole common population before any animated skin query."""
    require(len(original.rows)==len(candidate.rows),'Complete unchanged contact population required')
    native=np.unique(np.concatenate([c[2] for scene in (original,candidate) for actor in scene.actors.values() for c in actor['sampler'].channels]
        +[o['times'] for scene in (original,candidate) for o in scene.objects.values()]))
    clocks=[];queries=points=0
    for left,right in zip(original.rows,candidate.rows):
        row=left['authored'];other=right['authored']
        require(row['id']==other['id'] and row['interval_s']==other['interval_s'] and row['limits']==other['limits']
            and row['mode']==other['mode'] and row['reduction']==other['reduction'],'Contact timing/limits/reduction changed')
        start,end=row['interval_s'];populations=frame_populations([start,end]) if row['mode']=='hold' else []
        keys=np.unique(np.concatenate([np.array([start,end]),native]+[p['times_s'] for p in populations]));keys=keys[(keys>=start)&(keys<=end)]
        times=np.unique(np.concatenate([keys]+[keys[:-1]+f*np.diff(keys) for f in (.25,.5,.75)]))
        count=1 if row['reduction']=='centroid' else len(left['ids'])
        require(count==(1 if other['reduction']=='centroid' else len(right['ids'])),'Complete one-to-one measured point population required')
        queries+=len(times);points+=len(times)*count
        require(queries<=POSITION_QUERY_LIMIT and points<=POINT_OBSERVATION_LIMIT,
            'Complete common-clock comparison exceeds fixed query/point budget; no partial sampling or truncation')
        clocks.append(times)
    return clocks


def evaluate(original,candidate):
    """Existing full frame-speed audit plus common native/quarter position probes."""
    clocks=planned_clocks(original,candidate)
    before,b_arrays=original.evaluate();after,a_arrays=candidate.evaluate();rows=[];arrays={}
    for i,(left,right) in enumerate(zip(original.rows,candidate.rows)):
        row=left['authored'];other=right['authored'];prefix='contact_'+str(i)
        require(row['id']==other['id'] and row['interval_s']==other['interval_s'] and row['limits']==other['limits'],
            'Contact timing/limits changed')
        times=clocks[i]
        require(np.isin(b_arrays[prefix+'_times_s'],times).all() and np.isin(a_arrays[prefix+'_times_s'],times).all(),'Complete original/candidate audit clocks required')
        maximum={};passed={}
        for label,scene,entry,baseline in [('source',original,left,before),('candidate',candidate,right,after)]:
            effector,goal=contact_points(scene,entry,times);error=effector-goal;distance=np.linalg.norm(error,axis=2)
            maximum[label]=float(distance.max());passed[label]=bool(baseline['contacts'][i]['passed'] and maximum[label]<=row['limits']['position_m'])
            for suffix,value in [('effector_world_m',effector),('target_world_m',goal),('error_world_m',error)]:
                arrays[prefix+'_'+label+'_'+suffix]=value
        arrays[prefix+'_times_s']=times
        state=('preserved' if passed['candidate'] else 'regressed') if passed['source'] else ('source_failed_candidate_passed' if passed['candidate'] else 'source_and_candidate_failed')
        rows.append(dict(id=row['id'],target_space=row['target']['space'],mode=row['mode'],interval_s=row['interval_s'],limits=row['limits'],
            common_position_samples=len(times),maximum_source_position_error_m=maximum['source'],maximum_candidate_position_error_m=maximum['candidate'],
            source_samples_pass=passed['source'],candidate_samples_pass=passed['candidate'],retention_status=state))
    original.check_inputs();candidate.check_inputs()
    source_pass=all(r['source_samples_pass'] for r in rows);candidate_pass=all(r['candidate_samples_pass'] for r in rows)
    result=dict(schema='strep-native-transfer-scene-comparison-v1',contacts=rows,source_contacts_pass=source_pass,
        candidate_contact_samples_pass=candidate_pass,retention_samples_pass=source_pass and candidate_pass,
        common_position_queries=sum(r['common_position_samples'] for r in rows),
        position_query_limit=POSITION_QUERY_LIMIT,point_observation_limit=POINT_OBSERVATION_LIMIT,
        continuous_contact_certified=False,anatomical_reviewed=False,surface_orientation_verified=False,
        collision_verified=False,engine_playback_verified=False,quality_approved=False,release_approved=False,
        scope='Explicit corresponding skin points/centroids against unchanged world/object/partner targets. Both sides use the union of source/candidate/native/frame times plus quarter/midpoint/three-quarter positions; relative-speed gates retain every existing frame population. No contact correction, anatomy, normals, collision or realism inference.')
    return result,arrays,before,after


def verify(output,expected_result_sha256=None):
    """Replay a completed portable comparison from its complete snapshots."""
    output=Path(output).resolve();result=read(output/'result.json')
    if expected_result_sha256 is not None:require(sha256(output/'result.json')==expected_result_sha256,'Selected transfer scene result changed')
    require(result['schema']=='strep-native-transfer-scene-comparison-v1' and result['status']=='complete'
        and result['original_selected'] is True and result['source_bytes_unchanged'] is True
        and result['contact_intent_revised'] is False,'Transfer scene scope changed')
    actual={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p!=output/'result.json' and p.name!='pipeline.json'}
    require(actual==set(result['files_sha256']) and all(sha256(output/n)==h for n,h in result['files_sha256'].items()),'Complete transfer scene payload changed')
    request=read(output/'request.json');require(request['schema']==SCHEMA and set(request['implementation_sha256'])==set(METHODS),'Complete transfer scene methods required')
    for name,digest in request['implementation_sha256'].items():
        require(sha256(SCRIPT_ROOT/name)==digest==sha256(output/'implementation'/name),'Transfer scene method binding changed')
    recipe=read(output/'input/recipe.json');fields(recipe,('schema','contacts','transfers'),'snapshotted transfer scene recipe')
    require(recipe['schema']==SCHEMA and sha256(output/'input/recipe.json')==result['recipe_sha256']
        and recipe['contacts']['sha256']==sha256(output/'input/contacts.json'),'Original contact intent binding changed')
    spec=read(output/'input/contacts.json');source=copy.deepcopy(spec);replacements={}
    require(isinstance(recipe['transfers'],dict) and 1<=len(recipe['transfers'])<=8 and set(recipe['transfers'])<=set(spec['actors'])
        and list(recipe['transfers'])==result['transfer_actors'],'Complete transfer actor population required')
    for i,(name,actor) in enumerate(source['actors'].items()):actor['glb']='input/actor-'+str(i)+'.glb'
    for name,entry in recipe['transfers'].items():
        fields(entry,('candidate','vertex_map'),'snapshotted actor transfer');folder=output/'input/transfers'/name
        require(sha256(folder/'report.json')==entry['candidate']['sha256'],'Snapshotted transfer report changed')
        report=transfer_audit.bound_candidate(folder)[1];actor=spec['actors'][name]
        require(report['input_snapshots_sha256']['source.glb']==actor['sha256']
            and report['source_animation_index']==actor['animation_index'] and report['source_duration_s']==spec['duration_s'],
            'Snapshotted transfer belongs to another actor/clip')
        replacements[name]=dict(glb='actors/actor-'+str(list(spec['actors']).index(name))+'.glb',sha256=report['glb_sha256'],
            animation_index=report['output_animation_index'],vertex_map=entry['vertex_map'])
    candidate=remap(source,replacements)
    for i,(name,actor) in enumerate(candidate['actors'].items()):actor['glb']='actors/actor-'+str(i)+'.glb'
    require(read(output/'source-contacts.json')==source and read(output/'contacts.json')==candidate,'Contact intent/placement/timing/limits or correspondence changed')
    measured,arrays,before,after=evaluate(SceneContacts(source,output),SceneContacts(candidate,output))
    require(all(result.get(k) is False for k in ('continuous_contact_certified','anatomical_reviewed','surface_orientation_verified',
        'collision_verified','engine_playback_verified','quality_approved','release_approved'))
        and all(type(result.get(k)) is bool for k in ('source_contacts_pass','candidate_contact_samples_pass','retention_samples_pass')),
        'Typed unapproved transfer scene scope required')
    require(all(result.get(k)==v for k,v in measured.items()),'Transfer scene measurements or scope disagree with source replay')
    for label,audit in [('source',before),('candidate',after)]:
        stored=read(output/(label+'-audit.json'))
        require({k:v for k,v in stored.items() if k!='inputs_sha256'}=={k:v for k,v in audit.items() if k!='inputs_sha256'},'Transfer scene frame audit changed')
        canonical=lambda values:{Path(*Path(p).parts[-2:]).as_posix():h for p,h in values.items()}
        require(len(stored['inputs_sha256'])==len(audit['inputs_sha256']) and canonical(stored['inputs_sha256'])==canonical(audit['inputs_sha256']),
            'Transfer scene frame audit actor binding changed')
    with np.load(output/'observations.npz',allow_pickle=False) as stored:
        require(set(stored.files)==set(arrays) and all(stored[k].dtype==v.dtype and stored[k].shape==v.shape and stored[k].tobytes()==v.tobytes() for k,v in arrays.items()),
            'Transfer scene complete common-clock observations changed')
    return result


def run(recipe_path,output):
    recipe_path=Path(recipe_path).resolve();output=Path(output).resolve()
    require(not output.exists(),'Fresh transfer scene output required')
    with worker_lock(),threadpool_limits(limits=1):
        recipe,contacts,original,changed,candidate,folders,sources=validated(recipe_path)
        require(all(not output.is_relative_to(p) for p in folders.values()),'Output cannot be inside a transfer input')
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};output.mkdir(parents=True)
        save(output/'pipeline.json',dict(status='processing',original_selected=True,quality_approved=False))
        try:
            save(output/'request.json',dict(schema=SCHEMA,at=now(),inputs_sha256=sources,implementation_sha256=methods))
            archive=output/'implementation';archive.mkdir()
            for n in METHODS:shutil.copyfile(SCRIPT_ROOT/n,archive/n)
            inputs=output/'input';inputs.mkdir();shutil.copyfile(recipe_path,inputs/'recipe.json');shutil.copyfile(contacts,inputs/'contacts.json')
            source_spec=read(contacts);candidate_spec=copy.deepcopy(changed)
            for i,(name,actor) in enumerate(source_spec['actors'].items()):
                path=(contacts.parent/actor['glb']).resolve();dest=inputs/('actor-'+str(i)+'.glb');shutil.copyfile(path,dest)
                actor['glb']=dest.relative_to(output).as_posix()
                dest=output/'actors'/('actor-'+str(i)+'.glb');dest.parent.mkdir(exist_ok=True)
                source=(Path(changed['actors'][name]['glb']) if name in folders else path)
                shutil.copyfile(source,dest);candidate_spec['actors'][name]['glb']=dest.relative_to(output).as_posix()
            for name,folder in folders.items():shutil.copytree(folder,inputs/'transfers'/name)
            save(output/'source-contacts.json',source_spec);save(output/'contacts.json',candidate_spec)
            result,arrays,before,after=evaluate(SceneContacts(source_spec,output),SceneContacts(candidate_spec,output))
            save(output/'source-audit.json',before);save(output/'candidate-audit.json',after)
            np.savez_compressed(output/'observations.npz',**arrays)
            with np.load(output/'observations.npz',allow_pickle=False) as stored:
                require(set(stored.files)==set(arrays) and all(stored[k].dtype==v.dtype and stored[k].shape==v.shape and stored[k].tobytes()==v.tobytes() for k,v in arrays.items()),'Complete contact observations changed')
            require(all(sha256(p)==h for p,h in sources.items()),'Transfer scene input changed during comparison')
            require(all(sha256(SCRIPT_ROOT/n)==h==sha256(archive/n) for n,h in methods.items()),'Transfer scene implementation changed')
            files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file() and p.name!='pipeline.json'}
            result.update(status='complete',at=now(),original_selected=True,source_bytes_unchanged=True,contact_intent_revised=False,
                transfer_actors=list(folders),recipe_sha256=sha256(recipe_path),files_sha256=files)
            save(output/'result.json',result)
            verify(output,sha256(output/'result.json'))
            save(output/'pipeline.json',dict(status='complete',retention_samples_pass=result['retention_samples_pass'],original_selected=True,quality_approved=False))
            return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(run(args.recipe,args.output))
