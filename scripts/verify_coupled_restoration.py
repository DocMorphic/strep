"""Replay every saved restoration trial and fresh complete sampled geometry.

Reconstruct raw source-relative keys and native arithmetic, use uncached contact
surfaces, and rerun the unchanged geometry kernel. No engine or human approval.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from native_surface_model import include_times
from native_contact_norms import ContactNorms
from native_geometry_cache import Donor
from native_scene_geometry import evaluate,faces_for
from coupled_restoration_oracles import oracles,rate_values


def score(value):
    value=np.asarray(value,float)
    if value.ndim!=1 or not len(value) or not np.isfinite(value).all():
        raise ValueError('Complete finite replay population required')
    positive=np.maximum(value,0)
    return [float(positive.max()),float(positive@positive)]


def vertices(actor,world):
    """Reconstruct complete placed skin inputs without RigAsset.vertices."""
    rig=actor['rig'];transforms=world[rig.joints]@rig.inverse;parts=[]
    for primitive in rig.primitives:
        if primitive['joints'] is None:raise ValueError('Complete skinned actor geometry required')
        points=np.c_[primitive['positions'],np.ones(len(primitive['positions']))]
        placed=np.einsum('nvij,nj->nvi',transforms[primitive['joints']],points)
        parts.append(np.sum(placed[:,:,:3]*primitive['weights'][:,:,None],axis=1))
    p,r=actor['placement'];return np.concatenate(parts)@r.T+p


def geometry_replay(study,scene,worlds,clock,request,progress):
    donor=Donor(study/'geometry');folder=donor.folder
    policy=read(study/'candidate-geometry-policy.json');digest=sha256(study/'candidate-contacts.json')
    original_policy=read(study/'geometry-policy.json');original_policy['contacts_sha256']=digest
    assert policy==original_policy
    cached=donor.report;times=np.asarray(cached['times_s']);indices=np.searchsorted(clock,times)
    np.testing.assert_array_equal(times,request['geometry_times'])
    np.testing.assert_array_equal(clock[indices],times)
    assert donor.request['limits']==policy['limits'] and donor.request['planes']==policy['planes']
    assert donor.request['actors']==list(scene.actors)
    assert donor.request['objects']=={n:o['geometry'].record() for n,o in scene.objects.items()}
    expected={'times_s'};poses={n:scene.object_poses(n,times) for n in scene.objects}
    with np.load(folder/'observations.npz',allow_pickle=False) as archive:
        np.testing.assert_array_equal(archive['times_s'],times)
        for n,a in scene.actors.items():
            key='topology_'+n+'_faces';expected.add(key)
            np.testing.assert_array_equal(archive[key],faces_for(a['rig'])[0])
        for n,(p,r) in poses.items():
            for key,value in (('object_'+n+'_positions_m',p),('object_'+n+'_rotations',r)):
                expected.add(key);np.testing.assert_array_equal(archive[key],value)
        def placed(name,time):
            index=int(np.searchsorted(times,time));assert times[index]==time
            value=vertices(scene.actors[name],worlds[name][indices[index]])
            key=f'frame_{index}_{name}_vertices_world_m';expected.add(key)
            np.testing.assert_array_equal(archive[key],value);return value
        class Compare:
            def __init__(self):self.seen=set()
            def __setitem__(self,key,value):
                assert key not in self.seen;self.seen.add(key);expected.add(key)
                np.testing.assert_array_equal(archive[key],value)
        fresh,_=evaluate(scene,policy,digest,progress,actor_vertices=placed,observation_sink=Compare())
        assert set(archive.files)==expected and len(archive.files)==len(expected)
    assert fresh==cached
    donor.check()
    return dict(complete_samples=len(times),sampled_conditions_pass=fresh['sampled_conditions_pass'],
        complete_query_vertices_and_topology_exact=True,object_inputs_exact=True,
        all_numeric_geometry_outputs_exact=True,geometry_queries_rerun=True,
        geometry_kernel_shared_with_producer=True,continuous_or_self_collision_checked=False)


def run(study,output,*,progress=None):
    study,output=[Path(p).resolve() for p in (study,output)]
    if output.exists():raise ValueError('Fresh restoration verification output required')
    with worker_lock(),threadpool_limits(limits=1):
        result=read(study/'result.json');request=read(study/'request.json')
        assert result['schema']=='strep-restore-coupled-contacts-result-v1' and result['status']=='complete'
        assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
        assert request['schema']=='strep-restore-coupled-contacts-request-v1'
        assert result['request_sha256']==sha256(study/'request.json') and request['rotation_storage_policy']=='source-scale'
        actual_files={p.relative_to(study).as_posix() for p in study.rglob('*') if p.is_file()
                      and p not in (study/'result.json',study/'pipeline.json',study/'study.json')}
        assert set(result['files_sha256'])==actual_files
        bindings={str(study/'result.json'):sha256(study/'result.json')}
        if (study/'study.json').exists():bindings[str(study/'study.json')]=sha256(study/'study.json')
        bindings.update({str(study/n):d for n,d in result['files_sha256'].items()})
        bindings.update(request['inputs_sha256'])
        for n,d in request['implementation_sha256'].items():
            bindings[str(ROOT/'scripts'/n)]=d;bindings[str(study/'implementation'/n)]=d
        bindings[str(Path(__file__).resolve())]=sha256(__file__)
        helper=ROOT/'scripts/coupled_restoration_oracles.py';bindings[str(helper)]=sha256(helper)
        def check():
            if any(sha256(p)!=d for p,d in bindings.items()):raise ValueError('Restoration source or closed evidence changed')
        check();output.mkdir(parents=True)
        for path in (Path(__file__),helper):
            shutil.copyfile(path,output/path.name);bindings[str(output/path.name)]=sha256(path)
        save(output/'request.json',dict(at=now(),source_bindings_sha256=bindings,
            decoder_shared_with_producer=True,uncached_surface_contact=True,all_derivative_columns_recomputed=False))
        try:
            spec=read(study/'source-contacts.json');permissions=read(study/'permissions.json')
            source=SceneContacts(spec,request['source_base']);digest=sha256(study/'source-contacts.json')
            assert digest==permissions['contacts_sha256']
            problem=SceneProblem(source,SceneEdits(permissions,source,digest,rotation_storage_policy='source-scale'))
            include_times(problem,np.asarray(request['geometry_times']))
            with np.load(study/'source.npz',allow_pickle=False) as archive:saved={n:archive[n] for n in archive.files}
            clock=saved['times_s'];uniform=saved['rate_times_s']
            np.testing.assert_array_equal(clock,problem.times);np.testing.assert_array_equal(uniform,problem.uniform)
            caps={n:v for n,v in saved.items() if '_metric_' in n}
            source_world={n:np.array([a['sampler'].sample(float(t)) for t in clock]) for n,a in source.actors.items()}
            ids=np.searchsorted(clock,uniform);dt=uniform[1]-uniform[0]
            for n in source.actors:np.testing.assert_array_equal(source_world[n],saved['world_'+n])
            for n in permissions['actors']:
                for i,value in enumerate(rate_values(source_world[n][ids],source.actors[n]['rig'].joints,dt)):
                    order=1 if i in (0,2) else 2
                    stamps=uniform[1:-1] if i==3 else (uniform[:-order]+uniform[order:])/2
                    bins=np.searchsorted(np.linspace(0,source.duration,5)[1:-1],stamps,side='right');expected=np.empty_like(value)
                    for b in np.unique(bins):expected[bins==b]=value[bins==b].max(axis=0)
                    np.testing.assert_allclose(expected,caps[f'{n}_metric_{i}'],atol=2e-10,rtol=0)
            native_oracle,key_oracle,vector_oracle=oracles(source,problem,permissions,source_world,clock,uniform,caps)
            contact=ContactNorms(problem,read(study/'surface-policy.json'),digest,maximum_rows=50000)
            original_contact=contact.residual(source_world)
            np.testing.assert_allclose(original_contact,saved['contact'],atol=1e-8,rtol=0)
            np.testing.assert_array_equal(original_contact>0,saved['contact']>0)
            initial_native=native_oracle(problem.initial,source_world)
            np.testing.assert_allclose(initial_native,saved['native'],atol=1e-7,rtol=0)
            np.testing.assert_array_equal(initial_native>0,saved['native']>0)
            assert np.all(initial_native<=0)
            key_count=0;populations=[]
            def population(folder):
                nonlocal key_count
                with np.load(folder/'conditions.npz',allow_pickle=False) as a:obs={n:a[n] for n in a.files}
                value=problem.edits.controls(obs['controls']);assert np.all(value>=problem.lower) and np.all(value<=problem.upper)
                current_spec=copy.deepcopy(spec)
                for n,entry in current_spec['actors'].items():
                    path=folder/(n+'.glb') if n in permissions['actors'] else Path(request['source_base'])/entry['glb']
                    entry['glb']=str(path.resolve());entry['sha256']=sha256(path)
                current=SceneContacts(current_spec,folder)
                worlds={n:np.array([a['sampler'].sample(float(t)) for t in clock]) for n,a in current.actors.items()}
                key_count+=key_oracle(current,value)
                for n,w in worlds.items():
                    np.testing.assert_array_equal(w,obs['world_'+n])
                    old=source.actors[n]['rig'];new=current.actors[n]['rig']
                    for k in ('nodes','skins','meshes','materials','images','textures','scenes','scene'):
                        assert old.document.get(k)==new.document.get(k)
                    assert old.binary==new.binary[:len(old.binary)]
                native=native_oracle(value,worlds)
                np.testing.assert_allclose(native,obs['native'],atol=1e-7,rtol=0)
                np.testing.assert_array_equal(native>0,obs['native']>0)
                computed=contact.residual(worlds)
                np.testing.assert_allclose(computed,obs['contact'],atol=1e-8,rtol=0)
                np.testing.assert_array_equal(computed>0,obs['contact']>0)
                audits={n:problem.edits.audit(n,folder/(n+'.glb'),source.actors[n]['animation_index']) for n in permissions['actors']}
                assert audits==read(folder/'edit-audits.json') and all(a['passed'] for a in audits.values())
                populations.append(folder.relative_to(study).as_posix())
                if progress:progress(dict(stage='closed-population',population=populations[-1],status='processing'))
                return obs,worlds,current,current_spec
            baseline,baseline_worlds,_,_=population(study/'baseline')
            assert np.all(baseline['native']<=0) and np.all(baseline['contact']<=np.maximum(original_contact,0))
            base,worlds,current,current_spec=population(study/'rejected');assert np.any(base['native']>0)
            x=base['controls'];steps=0
            for item in result['history']:
                folder=study/f"iteration-{item['iteration']}";meta=read(folder/'model.json')
                with np.load(folder/'model.npz',allow_pickle=False) as a:
                    vectors=a['vectors'];bounds=a['caps'];scales=a['scales']
                    jac=sparse.csc_matrix((a['jac_data'],a['jac_indices'],a['jac_indptr']),shape=tuple(a['jac_shape']))
                n=len(base['native']);c=len(base['contact']);assert vectors.shape==(n+2*c,3) and jac.shape==(3*(n+2*c),problem.size)
                assert np.isfinite(np.r_[vectors.ravel(),bounds,scales,jac.data]).all()
                v,b,s=vector_oracle(x,worlds)
                np.testing.assert_allclose(vectors[:n],v,atol=1e-12,rtol=0)
                np.testing.assert_array_equal(bounds[:n],b);np.testing.assert_array_equal(scales[:n],s)
                residual=(np.linalg.norm(vectors,axis=1)-bounds)/scales
                np.testing.assert_allclose(residual[:n],base['native'],atol=1e-9,rtol=1e-12)
                np.testing.assert_allclose(residual[n:n+c],base['contact']-np.maximum(baseline['contact'],0),atol=1e-9,rtol=1e-12)
                np.testing.assert_allclose(residual[n+c:],base['contact'],atol=1e-9,rtol=1e-12)
                np.testing.assert_array_equal(vectors[n:n+c],vectors[n+c:])
                np.testing.assert_array_equal(scales[n:n+c],scales[n+c:])
                orientation,gaps,_=contact.sample(worlds)
                previous,previous_gaps,_=contact.sample(baseline_worlds);m=len(orientation.caps)
                assert c==3*m
                np.testing.assert_allclose(vectors[n+c:n+c+m],orientation.vectors,atol=1e-12,rtol=0)
                np.testing.assert_array_equal(bounds[n+c:n+c+m],orientation.caps)
                np.testing.assert_array_equal(scales[n+c:n+c+m],orientation.scales)
                side=jac[3*(n+c+m):][::3];extent=np.maximum(np.minimum(request['trust'],problem.upper-x),np.minimum(request['trust'],x-problem.lower))
                offsets=np.maximum(np.maximum(1.,gaps+np.asarray(abs(side)@extent).ravel()+1.),previous_gaps+1.)
                np.testing.assert_allclose(bounds[n+c+m:],offsets,atol=1e-12,rtol=0)
                np.testing.assert_allclose(vectors[n+c+m:,0],offsets-gaps,atol=1e-12,rtol=0)
                np.testing.assert_array_equal(vectors[n+c+m:,1:],np.zeros((2*m,2)))
                np.testing.assert_array_equal(scales[n+c+m:],np.full(2*m,.005))
                reference=np.r_[previous.vectors,np.c_[offsets-previous_gaps,np.zeros((2*m,2))]]
                np.testing.assert_allclose(bounds[n:n+c],np.maximum(bounds[n+c:],np.linalg.norm(reference,axis=1)),atol=1e-12,rtol=0)
                assert (jac[3*n:3*(n+c)]!=jac[3*(n+c):]).nnz==0 and meta['hard_rows']==n+c
                assert meta['previous_native_feasible'] and not meta['rejected_pose_becomes_new_baseline']
                trials=read(folder/'trials.json');proposal=read(folder/'proposal.json')
                assert len(trials)==item['trials'] and proposal['status']==item['solver_status']
                chosen=None
                if (folder/'direction.npy').exists():
                    delta=np.load(folder/'direction.npy',allow_pickle=False);raw=np.load(folder/'raw-direction.npy',allow_pickle=False)
                    assert delta.shape==raw.shape==x.shape and np.isfinite(np.r_[delta,raw]).all() and trials
                    np.testing.assert_array_equal(delta,np.clip(raw,np.maximum(problem.lower-x,-request['trust']),np.minimum(problem.upper-x,request['trust'])))
                    lo,hi=np.maximum(problem.lower-x,-request['trust']),np.minimum(problem.upper-x,request['trust'])
                    projection=read(folder/'direction-projection.json')
                    assert projection['raw_maximum_control_step']==float(abs(raw).max())
                    assert projection['raw_step_box_excess']==float(np.maximum(np.maximum(lo-raw,raw-hi),0).max())
                    assert projection['projected_maximum_control_step']==float(abs(delta).max())
                    assert projection['changed_components']==int((raw!=delta).sum())
                    assert projection['maximum_projection_change']==float(abs(raw-delta).max())
                    assert projection['exact_step_box_projection'] and not projection['authored_limits_relaxed']
                    assert not projection['projected_affine_feasibility_certified']
                    if 'maximum_control_step' in proposal:assert proposal['maximum_control_step']==float(abs(raw).max())
                else:assert not trials
                for i,trial in enumerate(trials):
                    assert trial['fraction']==.5**i
                    obs,newworlds,newscene,new_spec=population(folder/trial['label'])
                    expected=np.clip(x+trial['fraction']*delta,problem.lower,problem.upper)
                    for _ in range(2):
                        outside=abs(expected-x)>trial['fraction']*request['trust']
                        if not np.any(outside):break
                        expected[outside]=np.nextafter(expected[outside],x[outside])
                    np.testing.assert_array_equal(obs['controls'],expected)
                    before,after=score(base['native']),score(obs['native']);guard=bool(np.all(obs['contact']<=np.maximum(baseline['contact'],0)))
                    original_guard=bool(np.all(obs['contact']<=np.maximum(original_contact,0)))
                    feasible=bool(np.all(obs['native']<=0))
                    improves=bool(after[0]<=before[0] and ((feasible and np.any(base['native']>0)) or after[1]<before[1]-1e-12))
                    okay=bool(guard and original_guard and improves)
                    assert trial['native_pass']==feasible and trial['native_failed_rows']==int((obs['native']>0).sum())
                    assert trial['individual_baseline_contact_guard_pass']==guard and trial['original_contact_guard_pass']==original_guard
                    assert trial['native_merit_improves']==improves and trial['provisional_repair_progress']==okay
                    assert trial['contact_score']==score(obs['contact']) and not trial['retained'] and not trial['full_geometry_checked']
                    if okay:chosen=trial['label'];base,worlds,current,current_spec=obs,newworlds,newscene,new_spec;steps+=1;break
                assert chosen==item['provisional_step'];x=base['controls']
            np.testing.assert_array_equal(np.load(study/'provisional-controls.npy',allow_pickle=False),x)
            assert result['provisional_steps']==steps
            expected_files={n:dict(path=current_spec['actors'][n]['glb'],sha256=current_spec['actors'][n]['sha256']) for n in permissions['actors']}
            assert result['candidate_files']==expected_files
            original_guard=bool(np.all(base['contact']<=np.maximum(original_contact,0)))
            guard=bool(np.all(base['contact']<=np.maximum(baseline['contact'],0)))
            old,new=score(baseline['contact']),score(base['contact'])
            improves=bool(new[0]<=old[0] and new[1]<old[1]-1e-12)
            eligible=bool(np.all(base['native']<=0) and guard and original_guard and improves)
            assert result['geometry_checked']==eligible
            if eligible:assert read(study/'candidate-contacts.json')==current_spec
            geometry=geometry_replay(study,current,worlds,clock,request,progress) if eligible else None
            keep=bool(eligible and geometry['sampled_conditions_pass']) if geometry else False
            assert result['retained_partial_improvement']==keep
            np.testing.assert_array_equal(np.load(study/'retained-controls.npy',allow_pickle=False),x if keep else baseline['controls'])
            check()
            replay=dict(schema='strep-coupled-restoration-replay-v1',at=now(),status='complete',
                study_result_sha256=sha256(study/'result.json'),source_rate_caps_reconstructed=True,
                complete_closed_populations=populations,editable_keys_reconstructed=key_count,
                native_scalar_and_vector_arithmetic_recomputed=True,uncached_full_surface_contact_recomputed=True,
                paired_guard_rows_and_jacobians_checked=True,all_derivative_columns_recomputed=False,
                decoder_shared_with_producer=True,geometry=geometry,retained_claim_reproduced=True,
                engine_or_human_quality_checked=False,quality_approved=False,release_approved=False)
            save(output/'result.json',replay);save(output/'pipeline.json',dict(status='complete'));return replay
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();run(args.study,args.output,progress=lambda r:print(r,flush=True))
