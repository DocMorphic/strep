"""Vector population parity and genuine conic conflicts, not motion approval."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_fit import prepare
from test_native_scene_contacts import setup,object_target
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem,run
from native_scene_norms import NormRows,rows,linearize
from native_scene_conic import direction,solver_identity
from strep import save,sha256,read


@pytest.mark.parametrize('rotation',[False,True])
def test_vector_rows_match_all_original_constraints_and_decoded_exports(tmp_path,rotation):
    _,_,_,_,_,scene,edits=prepare(tmp_path,rotation=rotation); problem=SceneProblem(scene,edits)
    for fraction in (0.,.01,-.02):
        value=edits.initial.copy();value.reshape(-1,3)[:,1]=fraction
        out=tmp_path/(str(fraction)+'.glb');edits.export('A',value,out)
        actual,worlds=problem.decoded({'A':out},value)
        vector=rows(problem,value,worlds)
        np.testing.assert_allclose(vector.residual(),actual,atol=1e-10,rtol=1e-12)
        np.testing.assert_allclose(rows(problem,value).residual(),problem.model(value),atol=1e-10,rtol=1e-12)


@pytest.mark.parametrize('target',['object','actor'])
def test_moving_object_and_partner_hold_vectors_match_individual_clock_rows(tmp_path,target):
    source,rig,reader,spec=setup(tmp_path,rotating=True)
    if target=='object':object_target(spec,reader,rig,gap=.001)
    else:
        spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
        spec['actors']['B']['placement']['translation_m'][0]=.04
        spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    path=tmp_path/'contacts.json';save(path,spec)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=sha256(path),actors=dict(A=dict(
        window_s=[0,2],protected_s=[],knots_s=[0,.5,1,1.5,2],tracks=[dict(node=3,path='rotation',maximum_change=5)],
        maximum_joint_displacement_m=.02)))
    scene=SceneContacts(spec,tmp_path);edits=SceneEdits(permissions,scene,sha256(path));problem=SceneProblem(scene,edits)
    value=edits.initial.copy();value.reshape(-1,3)[:,0]=.01
    np.testing.assert_allclose(rows(problem,value).residual(),problem.model(value),atol=1e-9,rtol=1e-12)


def test_unavailable_hold_clock_remains_a_fixed_failed_condition(tmp_path):
    _,spec,path,p,_,_,_=prepare(tmp_path)
    spec['contacts'][0]['interval_s']=[.853725,.853726];save(path,spec)
    p['contacts_sha256']=sha256(path);scene=SceneContacts(spec,tmp_path);edits=SceneEdits(p,scene,sha256(path))
    problem=SceneProblem(scene,edits);vector=rows(problem,edits.initial)
    np.testing.assert_allclose(vector.residual(),problem.model(edits.initial),atol=1e-10,rtol=1e-12)
    assert (vector.caps==-1).sum()==12


def test_vector_differences_preserve_the_norm_on_both_sides_of_zero(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path);problem=SceneProblem(scene,edits)
    system,jac,record=linearize(problem,problem.initial)
    assert record['quantized_native_keys'] and len(record['actual_steps'])==problem.size
    # Native key-edit norms start at zero; their affine vector is exactly linear.
    size=len(edits.actors['A']['tracks'][0]['ids']);index=next(i for i in range(size) if jac[3*i:3*i+3].nnz)
    delta=np.zeros(problem.size);delta[0]=.1
    a=system.residual(jac,delta)[index];b=system.residual(jac,-delta)[index]
    assert a==pytest.approx(b,abs=1e-12) and a>-1
    with pytest.raises(ValueError,match='resource limit'):linearize(problem,problem.initial,maximum_elements=1)
    with pytest.raises(ValueError):linearize(problem,problem.initial,step=0)


def test_sparse_vector_differences_and_cones_match_dense_reference_without_row_loss(tmp_path):
    _,_,_,_,_,scene,edits=prepare(tmp_path);problem=SceneProblem(scene,edits)
    system,jac,record=linearize(problem,problem.initial,step=.001)
    assert sparse.issparse(jac) and record['stored_nonzero_jacobian_elements']==jac.nnz
    dense=np.empty((*system.vectors.shape,problem.size))
    for column in range(problem.size):
        x=problem.initial.copy();x[column]+=.001
        dense[:,:,column]=(rows(problem,x).vectors-system.vectors)/.001
    np.testing.assert_array_equal(jac.toarray().reshape(dense.shape),dense)
    delta=np.linspace(-.01,.01,problem.size)
    np.testing.assert_allclose(system.residual(jac,delta),system.residual(dense,delta),atol=1e-12,rtol=0)
    toy=NormRows([[0,0,0],[-1,0,0]],[.2,0],[1,1]);dense=np.stack([np.eye(3)]*2)
    a,record_a=direction(toy,dense,np.zeros(3),-np.ones(3),np.ones(3),1.)
    b,record_b=direction(toy,sparse.csc_matrix(dense.reshape(6,3)),np.zeros(3),-np.ones(3),np.ones(3),1.)
    np.testing.assert_allclose(a,b,atol=1e-10,rtol=0)
    assert record_a['active_cones']==record_b['active_cones']==2


def test_vector_model_keeps_radial_conflict_without_scalar_cancellation():
    system=NormRows([[0,0,0],[-1,0,0]],[.2,0],[1,1]);jac=np.stack([np.eye(3)]*2)
    delta,info=direction(system,jac,np.zeros(3),-np.ones(3),np.ones(3),1.)
    assert delta is not None and info['active_cones']==2
    np.testing.assert_allclose(delta,[.6,0,0],atol=2e-5,rtol=0)
    assert max(system.residual(jac,delta))==pytest.approx(.4,abs=2e-5)
    # A radial corner has a positive norm even when its coordinates sum to zero.
    assert system.residual(jac,[1,-1,0])[0]>1


def test_conic_step_respects_control_boxes_and_fixed_failed_rows():
    system=NormRows([[0,0,0],[-1,0,0]],[.2,0],[1,1]);jac=np.stack([np.eye(3)]*2)
    delta,_=direction(system,jac,np.zeros(3),-np.ones(3),np.array([.1,1,1]),1.)
    assert delta[0]<=.1 and delta[0]==pytest.approx(.1,abs=1e-6)
    fixed=NormRows([[0,0,0],[-1,0,0],[0,0,0]],[0,0,-1],[1,1,1])
    jac=np.zeros((3,3,3));jac[1]=np.eye(3)
    delta,info=direction(fixed,jac,np.zeros(3),-np.ones(3),np.ones(3),1.)
    assert info['fixed_failed_rows']==1 and info['omitted_fixed_passing_rows']==1
    assert max(fixed.residual(jac,delta))>=1.


def test_only_norms_bounded_passing_throughout_the_trust_box_are_screened():
    system=NormRows([[0,0,0],[-1,0,0],[0,0,0]],[10.,0.,1e-5],[1.,1.,1.])
    jac=np.stack([np.eye(3),np.eye(3),np.eye(3)*1e-9])
    delta,info=direction(system,jac,np.zeros(3),-np.ones(3),np.ones(3),1.)
    assert info['active_cones']==1 and info['omitted_affine_box_passing_rows']==2
    assert delta[0]==pytest.approx(1.,abs=1e-6)
    for corner in [np.array([x,y,z]) for x in (-1,1) for y in (-1,1) for z in (-1,1)]:
        assert np.all(system.residual(jac,corner)[[0,2]]<=0)
    # A source-passing radial row that can fail at a box corner stays active.
    tight=NormRows([[0,0,0],[-1,0,0]],[.2,0.],[1.,1.]);j=np.stack([np.eye(3)]*2)
    _,info=direction(tight,j,np.zeros(3),-np.ones(3),np.ones(3),1.)
    assert info['active_cones']==2 and info['omitted_affine_box_passing_rows']==0


@pytest.mark.parametrize('fault',['vector-shape','cap-shape','scale-zero','nan'])
def test_invalid_vector_rows_reject(fault):
    vector,cap,scale=np.zeros((2,3)),np.ones(2),np.ones(2)
    if fault=='vector-shape':vector=np.zeros((2,2))
    if fault=='cap-shape':cap=np.ones(1)
    if fault=='scale-zero':scale[0]=0
    if fault=='nan':vector[0,0]=np.nan
    with pytest.raises(ValueError):NormRows(vector,cap,scale)


def test_vector_job_records_solver_and_keeps_originals_pending_geometry(tmp_path):
    source,_,contacts,_,permissions,_,_=prepare(tmp_path)
    result=run(contacts,permissions,tmp_path/'vector-job',iterations=1,proposal_model='vector')
    assert result['proposal_model']=='vector' and result['original_selected']
    assert result['conic_solver']['version']=='0.11.1' and result['conic_solver']['files_sha256']
    assert sha256(tmp_path/'vector-job'/result['selected_files']['A'])==sha256(source)
    assert not result['release_approved'] and not result['collision_verified']
    request=read(tmp_path/'vector-job/request.json')
    assert request['conic_solver']==result['conic_solver']
    assert request['vector_difference_step']==result['vector_difference_step']==.001


@pytest.mark.parametrize('model,step',[('scalar',.001),('vector',True),('vector',.02),('vector',0)])
def test_invalid_or_ignored_difference_settings_reject_before_job(tmp_path,model,step):
    _,_,contacts,_,permissions,_,_=prepare(tmp_path)
    out=tmp_path/'invalid'
    with pytest.raises(ValueError):run(contacts,permissions,out,proposal_model=model,vector_difference_step=step)
    assert not out.exists()


def test_solver_mutation_during_job_rejects_instead_of_publishing_result(tmp_path,monkeypatch):
    _,_,contacts,_,permissions,_,_=prepare(tmp_path)
    import native_scene_conic
    identity=solver_identity();calls=[]
    def changed():
        calls.append(1)
        return identity if len(calls)==1 else dict(identity,version='changed')
    monkeypatch.setattr(native_scene_conic,'solver_identity',changed)
    out=tmp_path/'changed-solver'
    with pytest.raises(ValueError,match='solver changed'):
        run(contacts,permissions,out,iterations=1,proposal_model='vector')
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'result.json').exists()


def test_storage_aligned_changed_body_fixture_can_pass_the_unchanged_native_conditions(tmp_path):
    source,spec,_,_,_,scene,edits=prepare(tmp_path);problem=SceneProblem(scene,edits)
    track=edits.actors['A']['tracks'][0];spacing=np.spacing(track['source'][:,1].astype(np.float32))
    assert np.all(spacing==spacing[0])
    ordinary=edits.initial.copy();ordinary.reshape(-1,3)[:,1]=[.05,.1,.05]
    original_path=tmp_path/'ordinary.glb';edits.export('A',ordinary,original_path)
    residual,_=problem.decoded({'A':original_path},ordinary)
    assert residual.max()>0
    # The fixture's ten uniform native intervals admit a root triangle with
    # five equal stored increments up and five down. No acceptance limit moves.
    per_key=float(np.rint(.002/5/spacing[0])*spacing[0]);aligned=edits.initial.copy()
    aligned.reshape(-1,3)[:,1]=np.array([.5,1,.5])*(5*per_key)/track['unit']
    path=tmp_path/'aligned.glb';edits.export('A',aligned,path)
    residual,worlds=problem.decoded({'A':path},aligned)
    assert residual.max()<=0 and edits.audit('A',path,0)['passed']
    assert sha256(path)!=sha256(source)
    changed=copy.deepcopy(spec);changed['actors']['A'].update(glb=path.name,sha256=sha256(path))
    contact,_=SceneContacts(changed,tmp_path).evaluate()
    assert contact['passed'] and not contact['engine_playback_verified'] and not contact['quality_approved']
    assert np.abs(worlds['A'][np.searchsorted(problem.times,1.),0,1,3]-problem.source_world['A'][np.searchsorted(problem.times,1.),0,1,3])>.0019
