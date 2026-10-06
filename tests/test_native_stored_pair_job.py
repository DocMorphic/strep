"""Pinned offline jobs, original caps and immutable rejected proposals."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_stored_pair_job import Job,run,SCHEMA
from native_scene_contacts import SceneContacts
from native_scene_fit import SceneProblem
from native_scene_boundary_edit import BoundarySceneEdits
from native_rotation_storage_repair import StorageAdjustedEdits,authoring_digest
from native_surface_model import include_times
from native_observation_archive import verify
from test_native_stored_pair_model import fixture
from strep import read,save,sha256


def prepare(tmp_path):
    problem,_,_,spec,_,policy=fixture(tmp_path)
    actor=problem.scene.actors['A'];p,r=actor['placement'];point=actor['rig'].vertices(actor['sampler'].sample(0))[0]@r.T+p
    spec['contacts']=[dict(id='touch',actor='A',vertices=[actor['skin'].vertex_references[0].tolist()],reduction='centroid',
        target=dict(space='world',points_m=[point.tolist()]),mode='touch',interval_s=[0.,0.],limits=dict(position_m=.0001))]
    source=tmp_path/'source.json';save(source,spec);reference=tmp_path/'reference.json';save(reference,spec)
    digest=sha256(source);scene=SceneContacts(spec,tmp_path);request=copy.deepcopy(problem.edits.request);request['permissions']['contacts_sha256']=digest
    base=BoundarySceneEdits(request,scene,digest,rotation_storage_policy='source-scale');storage=copy.deepcopy(problem.edits.policy);storage['authoring_sha256']=authoring_digest(base)
    editor=StorageAdjustedEdits(base,storage,[]);problem=SceneProblem(scene,editor);policy['contacts_sha256']=digest;include_times(problem,policy['clock']['times_s'])
    x=base.initial.copy();anchor=tmp_path/'job-anchor.glb';editor.export('A',x,anchor)
    roles=dict(source_scene=source,reference_scene=reference,edit_request=tmp_path/'edit.json',storage_policy=tmp_path/'storage.json',geometry_policy=tmp_path/'geometry.json',source_rate_caps=tmp_path/'caps.npz')
    save(roles['edit_request'],request);save(roles['storage_policy'],storage);save(roles['geometry_policy'],policy)
    np.savez(roles['source_rate_caps'],times_s=problem.uniform,**{'A_metric_'+str(i):a for i,a in enumerate(problem.caps['A'].caps)})
    controls=tmp_path/'controls.npz';np.savez(controls,controls=x)
    pin=lambda p:dict(path=str(p),sha256=sha256(p))
    job=dict(schema=SCHEMA,**{k:pin(p) for k,p in roles.items()},anchor=dict(controls=pin(controls),array='controls',corrections=[],actor_files={'A':pin(anchor)}),
        settings=dict(trust=.02,difference_step=.001,maximum_rows=400000,maximum_nonzeros=60000000,fractions=[1.]))
    path=tmp_path/'job.json';save(path,job);return path


def test_complete_job_preserves_inputs_and_audits_every_export(tmp_path):
    request=prepare(tmp_path);before=Job(request).inputs.copy();out=tmp_path/'output';result=run(request,out)
    assert result['status']=='complete' and result['original_selected'] and result['original_rate_caps_recomputed']
    assert result['records'] and not result['quality_approved'] and not result['release_approved']
    for p,h in before.items():assert sha256(p)==h
    for role,pin in result['input_snapshots'].items():assert sha256(out/pin['path'])==pin['sha256']
    for record in result['records']:
        assert record['geometry_assessed'] and not record['retained'];verify(out/record['label']/'geometry-observations.npz')
        assert record['numerical_conditions_pass']==(record['native_conditions_pass'] and record['reference_bounds']['passed'] and record['geometry_conditions_pass'])
    frozen=Job(request);np.testing.assert_array_equal(frozen.problem.source_world['B'],np.array([frozen.scene.actors['B']['sampler'].sample(float(t)) for t in frozen.problem.times]))
    with pytest.raises(ValueError,match='Fresh output'):run(request,out)


@pytest.mark.parametrize('fault',['schema','extra','trust-bool','row-budget','nonzero-budget','fractions-bool','fractions-duplicate','fractions-order','actor-set','pin'])
def test_invalid_request_rejects_before_output_creation(tmp_path,fault):
    path=prepare(tmp_path);job=read(path)
    if fault=='schema':job['schema']='other'
    elif fault=='extra':job['extra']=True
    elif fault=='trust-bool':job['settings']['trust']=True
    elif fault=='row-budget':job['settings']['maximum_rows']=400001
    elif fault=='nonzero-budget':job['settings']['maximum_nonzeros']=True
    elif fault=='fractions-bool':job['settings']['fractions']=[True]
    elif fault=='fractions-duplicate':job['settings']['fractions']=[1.,1.]
    elif fault=='fractions-order':job['settings']['fractions']=[.5,1.]
    elif fault=='actor-set':job['anchor']['actor_files']={}
    elif fault=='pin':job['anchor']['controls']['sha256']='a'*64
    save(path,job);out=tmp_path/'output'
    with pytest.raises(ValueError):run(path,out)
    assert not out.exists()


def test_rehashed_weakened_caps_still_fail_reference_recomputation(tmp_path):
    path=prepare(tmp_path);job=read(path);caps=Path(job['source_rate_caps']['path'])
    with np.load(caps,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
    data['A_metric_0']+=.001;np.savez(caps,**data);job['source_rate_caps']['sha256']=sha256(caps);save(path,job)
    with pytest.raises(ValueError,match='exactly recompute'):Job(path)


def test_input_mutation_after_preflight_rejects(tmp_path):
    path=prepare(tmp_path);job=Job(path);p=job.roles['edit_request'];p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='input bytes changed'):job.check()
