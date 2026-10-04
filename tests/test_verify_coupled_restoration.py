"""Whole exported populations and fresh scene queries detect forged saved evidence."""
from pathlib import Path
import sys,copy
import os,subprocess,shutil
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import restore_coupled_contacts as flow
import verify_coupled_restoration as replay
from coupled_restoration_oracles import oracles
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from native_scene_norms import rows
from test_restore_coupled_contacts import rejected_file,to_value
from test_cumulative_coupled_contacts import fixture
from test_native_scene_fit import prepare
from test_native_contact_norms import prepared
from test_native_scene_geometry import policy as geometry_policy
from strep import read,save,sha256


def study(tmp_path,monkeypatch,*,unsafe_floor=False,timeout=False):
    paths=fixture(tmp_path,monkeypatch,unsafe_floor=unsafe_floor);rejected=rejected_file(tmp_path)
    monkeypatch.setattr(flow,'direction',lambda *a,**k:(None,dict(status='MaxTime')) if timeout else to_value(1e-7)(*a,**k))
    out=tmp_path/'study';result=flow.run(*paths,out,rejected_controls=rejected,iterations=1,backoffs=1)
    return out,result


@pytest.mark.parametrize('unsafe_floor',[False,True])
def test_replay_recomputes_every_closed_population_and_complete_geometry(tmp_path,monkeypatch,unsafe_floor):
    out,original=study(tmp_path,monkeypatch,unsafe_floor=unsafe_floor)
    proof=replay.run(out,tmp_path/'replay')
    assert proof['status']=='complete' and proof['retained_claim_reproduced']
    assert proof['complete_closed_populations']==['baseline','rejected','iteration-1/backoff-0']
    assert proof['editable_keys_reconstructed']==27
    assert proof['native_scalar_and_vector_arithmetic_recomputed'] and proof['uncached_full_surface_contact_recomputed']
    assert proof['geometry']['geometry_queries_rerun'] and proof['geometry']['complete_samples']==3
    assert proof['geometry']['sampled_conditions_pass']==original['complete_geometry_pass']==(not unsafe_floor)
    assert proof['decoder_shared_with_producer'] and not proof['all_derivative_columns_recomputed']
    assert proof['condition_summaries_and_closed_decisions_reduced']
    assert not proof['quality_approved'] and not proof['release_approved']


def test_timeout_replay_verifies_non_retention_without_inventing_geometry(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch,timeout=True);proof=replay.run(out,tmp_path/'replay')
    assert proof['complete_closed_populations']==['baseline','rejected'] and proof['geometry'] is None
    assert proof['retained_claim_reproduced'] and proof['editable_keys_reconstructed']==18


@pytest.mark.parametrize('population',['original','baseline','rejected','final'])
def test_contradictory_final_summary_rejects_even_when_motion_and_hashes_are_valid(tmp_path,monkeypatch,population):
    out,_=study(tmp_path,monkeypatch);result=read(out/'result.json')
    result[population]['surface_failed_rows']+=1;save(out/'result.json',result)
    with pytest.raises(ValueError,match='summary'):
        replay.run(out,tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


@pytest.mark.parametrize('field',['native_maximum_excess','contact_score','feasible_improved_motion','static_edit_audit_pass'])
def test_forged_closed_decision_summary_rejects_with_rebound_inventory(tmp_path,monkeypatch,field):
    out,_=study(tmp_path,monkeypatch);path=out/'iteration-1/trials.json';trials=read(path)
    if field=='contact_score':trials[0][field][1]+=.1
    elif field=='native_maximum_excess':trials[0][field]+=.1
    else:trials[0][field]=not trials[0][field]
    decision=out/'iteration-1/backoff-0/decision.json';save(path,trials);save(decision,trials[0]);rebind(out,path,decision)
    with pytest.raises(ValueError,match='summary'):
        replay.run(out,tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


@pytest.mark.parametrize('field',['baseline_fallback_preserved','original_contact_guard_pass','complete_geometry_pass'])
def test_contradictory_final_retention_flags_reject(tmp_path,monkeypatch,field):
    out,_=study(tmp_path,monkeypatch);result=read(out/'result.json');result[field]=not result[field];save(out/'result.json',result)
    with pytest.raises(AssertionError):replay.run(out,tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


@pytest.mark.parametrize('kind',['partner','object'])
@pytest.mark.parametrize('hold',[False,True])
def test_complete_partner_and_moving_object_geometry_replayed_without_approving_open_meshes(tmp_path,monkeypatch,kind,hold):
    paths=fixture(tmp_path,monkeypatch);source,p,s,g=paths
    _,surface,digest=prepared(tmp_path,partner=kind=='partner',hold=hold)
    spec=read(source)
    if kind=='object':
        row=spec['contacts'][0];normal=np.asarray(surface['contacts'][row['id']]['target_normal']['normals'][0])
        point=.2*normal;center=np.asarray(row['target']['points_m'][0])-point
        spec['objects']['grip']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.2),
            keyframes=[dict(time_s=t,translation_m=(center+shift).tolist(),rotation_xyzw=[0,0,0,1])
                for t,shift in [(0.,np.array([.5,0,0])),(.8,np.zeros(3)),(1.2,np.zeros(3)),(2.,np.array([-.5,0,0]))]])
        row['target']=dict(space='object',object='grip',points_m=[point.tolist()])
        surface['contacts'][row['id']]['target_normal']['space']='object'
        save(source,spec);digest=sha256(source);surface['contacts_sha256']=digest
    permissions=read(p);permissions['contacts_sha256']=digest;save(p,permissions);save(s,surface)
    save(g,geometry_policy(source,planes=dict(floor=dict(normal_world=[0.,1.,0.],offset_m=-10.))))
    value=[0.,0.,-.001] if kind=='partner' else [.001,0.,0.]
    target=np.asarray(value)*1e-4;rejected=tmp_path/'rejected.npy';np.save(rejected,value)
    monkeypatch.setattr(flow,'direction',lambda system,jac,x,*a,**k:(target-x,dict(status='test-external-proposal')))
    out=tmp_path/'study';original=flow.run(*paths,out,rejected_controls=rejected,iterations=1,backoffs=1)
    assert original['geometry_checked'] and original['final']['native_pass'] and not original['retained_partial_improvement']
    proof=replay.run(out,tmp_path/'replay')
    assert proof['retained_claim_reproduced'] and proof['geometry']['all_numeric_geometry_outputs_exact']
    assert proof['geometry']['geometry_queries_rerun'] and not proof['geometry']['sampled_conditions_pass']
    assert proof['geometry']['complete_query_vertices_and_topology_exact'] and proof['geometry']['object_inputs_exact']


def rebind(out,*paths):
    result=read(out/'result.json')
    for path in paths:result['files_sha256'][path.relative_to(out).as_posix()]=sha256(path)
    save(out/'result.json',result)


@pytest.mark.parametrize('fault',['world','native','contact','controls','source-cap','model-vector','model-cap','guard','retained'])
def test_rebound_hashes_do_not_hide_altered_physical_populations(tmp_path,monkeypatch,fault):
    out,_=study(tmp_path,monkeypatch)
    path=out/'iteration-1/backoff-0/conditions.npz'
    if fault=='source-cap':path=out/'source.npz'
    if fault in ('model-vector','model-cap','guard'):path=out/'iteration-1/model.npz'
    if fault=='retained':
        path=out/'retained-controls.npy';value=np.load(path);value[0]+=.001;np.save(path,value)
    else:
        with np.load(path,allow_pickle=False) as archive:arrays={n:archive[n] for n in archive.files}
        if fault=='world':arrays['world_A'][0,0,0,3]+=.001
        if fault=='native':arrays['native'][0]+=.001
        if fault=='contact':arrays['contact'][0]+=.001
        if fault=='controls':arrays['controls'][0]+=.001
        if fault=='source-cap':arrays['A_metric_0'][0,0]+=.001
        if fault=='model-vector':arrays['vectors'][0,0]+=.001
        if fault=='model-cap':arrays['caps'][0]+=.001
        if fault=='guard':arrays['vectors'][-1,0]+=.001
        np.savez_compressed(path,**arrays)
    rebind(out,path)
    with pytest.raises((AssertionError,ValueError)):replay.run(out,tmp_path/'replay')
    assert read(tmp_path/'replay/pipeline.json')['status']=='failed' and not (tmp_path/'replay/result.json').exists()


def test_rebound_wrong_retention_metadata_is_not_an_animation_certificate(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch);result=read(out/'result.json');result['retained_partial_improvement']=False;save(out/'result.json',result)
    with pytest.raises(AssertionError):replay.run(out,tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


def test_omitted_closed_file_cannot_hide_from_the_binding_inventory(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch);result=read(out/'result.json')
    del result['files_sha256']['baseline/conditions.npz'];save(out/'result.json',result)
    with pytest.raises(AssertionError):replay.run(out,tmp_path/'replay')
    assert not (tmp_path/'replay').exists()


def test_forged_projection_record_rejected_after_hashes_rebound(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch);path=out/'iteration-1/direction-projection.json'
    metadata=read(path);metadata['changed_components']+=1;save(path,metadata);rebind(out,path)
    with pytest.raises(AssertionError):replay.run(out,tmp_path/'replay')
    assert read(tmp_path/'replay/pipeline.json')['status']=='failed'


def test_candidate_file_metadata_must_identify_the_actual_selected_export(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch);result=read(out/'result.json')
    result['candidate_files']['A']['path']=str(out/'rejected/A.glb');save(out/'result.json',result)
    with pytest.raises(AssertionError):replay.run(out,tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


def test_mutated_verifier_method_snapshot_is_detected_before_completion(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch);output=tmp_path/'replay';changed=[]
    def mutate(record):
        if not changed:
            path=output/'coupled_restoration_oracles.py';path.write_bytes(path.read_bytes()+b' ');changed.append(path)
    with pytest.raises(ValueError,match='changed'):replay.run(out,output,progress=mutate)
    assert read(output/'pipeline.json')['status']=='failed' and not (output/'result.json').exists()


def test_existing_verification_output_is_never_overwritten(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch);output=tmp_path/'replay';output.mkdir();sentinel=output/'sentinel'
    sentinel.write_text('keep',encoding='utf-8')
    with pytest.raises(ValueError,match='Fresh'):replay.run(out,output)
    assert sentinel.read_text(encoding='utf-8')=='keep'


def test_public_replay_command_runs_in_a_separate_source_checkout(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch);scripts=tmp_path/'command-source/scripts';scripts.mkdir(parents=True)
    for path in Path(replay.__file__).parent.glob('*.py'):shutil.copyfile(path,scripts/path.name)
    output=tmp_path/'replay';env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
    command=[sys.executable,str(scripts/'verify_coupled_restoration.py'),str(out),str(output)]
    completed=subprocess.run(command,capture_output=True,text=True,env=env,timeout=90)
    assert completed.returncode==0,completed.stdout+completed.stderr
    proof=read(output/'result.json')
    assert proof['status']=='complete' and proof['retained_claim_reproduced']
    assert proof['geometry']['geometry_queries_rerun'] and not proof['quality_approved']


def test_geometry_query_vertices_are_reconstructed_even_after_archive_receipts_rebound(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch)
    # Alter the geometry result only; even newly consistent transport hashes do
    # not replace fresh kernel queries or the whole report comparison.
    path=out/'geometry/geometry.json';geometry=read(path);geometry['samples'][0]['world_planes'][0]['maximum_depth_m']=.001;save(path,geometry)
    cached=read(out/'geometry/result.json');cached['geometry_sha256']=sha256(path);save(out/'geometry/result.json',cached)
    rebind(out,path,out/'geometry/result.json')
    with pytest.raises((AssertionError,ValueError)):replay.run(out,tmp_path/'replay')
    assert not (tmp_path/'replay/result.json').exists()


def test_mid_replay_closed_evidence_mutation_cannot_write_a_passing_result(tmp_path,monkeypatch):
    out,_=study(tmp_path,monkeypatch);mutations=[]
    def mutate(record):
        if record.get('population')=='iteration-1/backoff-0' and not mutations:
            path=out/'baseline/conditions.npz';path.write_bytes(path.read_bytes()+b' ');mutations.append(path)
    with pytest.raises(ValueError,match='changed'):replay.run(out,tmp_path/'replay',progress=mutate)
    assert mutations and read(tmp_path/'replay/pipeline.json')['status']=='failed'


@pytest.mark.parametrize('rotation',[False,True])
def test_raw_translation_rotation_keys_and_native_arithmetic_match_exported_curves(tmp_path,rotation):
    _,_,_,_,permissions_path,scene,_=prepare(tmp_path,rotation=rotation)
    permissions=read(permissions_path);edits=SceneEdits(permissions,scene,permissions['contacts_sha256'],rotation_storage_policy='source-scale')
    problem=SceneProblem(scene,edits);value=problem.initial.copy();value[1::3]=.005
    caps={n+'_metric_'+str(i):c for n,rate in problem.caps.items() for i,c in enumerate(rate.caps)}
    native,key,vector=oracles(scene,problem,permissions,problem.source_world,problem.times,problem.uniform,caps)
    files={n:tmp_path/(n+'.glb') for n in edits.actors}
    for n,path in files.items():edits.export(n,value,path)
    actual,worlds=problem.decoded(files,value)
    np.testing.assert_allclose(native(value,worlds),actual,atol=1e-7,rtol=0)
    np.testing.assert_array_equal(native(value,worlds)>0,actual>0)
    expected=rows(problem,value,worlds);v,b,s=vector(value,worlds)
    np.testing.assert_allclose(v,expected.vectors,atol=1e-12,rtol=0)
    np.testing.assert_array_equal(b,expected.caps);np.testing.assert_array_equal(s,expected.scales)
    spec=copy.deepcopy(read(tmp_path/'contacts.json'))
    for n,p in files.items():spec['actors'][n].update(glb=str(p),sha256=sha256(p))
    assert key(SceneContacts(spec,tmp_path),value)>0
