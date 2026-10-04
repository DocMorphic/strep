"""Hard pose domains, analytic derivatives and retained complete contact gates."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_object_correspondence_fit import fixture
from test_native_scene_geometry import policy
from native_object_bounded_fit import SCHEMA,fit_bounded,residual_jacobian,base_request,initial_for,proposal,run
from native_object_correspondence_fit import proposal as unconstrained
from native_scene_contacts import SceneContacts
from native_object_hold_fit import audit_bounds
from strep import save,read,sha256


def solver():return dict(schema='strep-object-pose-solver-v1',maximum_iterations=100,ftol=1e-12,bound_reserve_fraction=1e-6)


def request(value):
    value=copy.deepcopy(value);value.update(schema=SCHEMA,initial_scene=None,solver=solver());return value


def axes():return np.array([[1.,0,0],[-1.,0,0],[0,1.,0],[0,-1.,0],[0,0,1.],[0,0,-1.]])*.1


@pytest.mark.parametrize('angle',[0.,.000001,.4,.78])
def test_analytic_point_derivative_matches_independent_central_differences(angle):
    local=axes()+[.03,.02,-.04];observed=local+[.2,-.1,.05];p0=np.array([1.,-2.,3.])
    r0=Rotation.from_euler('xyz',[33,-77,126],degrees=True).as_matrix();x=np.array([.1,-.2,.3,.2,-.3,.4])
    rs=angle if angle else .01;x[3:]=[0.,0.,0.] if angle==0 else x[3:]
    residual,jac=residual_jacobian(x,local,observed,p0,r0,.002,rs)
    def forward(z):return Rotation.from_rotvec(z[3:]*rs).apply(local@r0.T)+p0+z[:3]*.002-observed
    np.testing.assert_allclose(residual,forward(x),atol=1e-15)
    eps=1e-5
    numerical=np.stack([(forward(x+np.eye(6)[i]*eps)-forward(x-np.eye(6)[i]*eps))/(2*eps) for i in range(6)],axis=2)
    np.testing.assert_allclose(jac,numerical,rtol=1e-5,atol=6e-11)


def test_translation_ball_matches_known_global_solution_without_rotation_escape():
    local=axes();observed=local+[.01,0,0]
    p,r,e,x,record=fit_bounded(local,observed,np.zeros(3),np.eye(3),.002,2.,solver())
    assert record['solver_success'] and record['translation_m']<=.002
    np.testing.assert_allclose(p,[.002*(1-1e-6),0.,0.],atol=1e-10)
    np.testing.assert_allclose(r,np.eye(3),atol=1e-8)
    np.testing.assert_allclose(e,.01-p[0],atol=1e-9)
    assert np.linalg.norm(x[:3])<=1 and np.linalg.norm(x[3:])<=1


def test_rotation_ball_matches_known_isotropic_solution():
    local=axes();observed=Rotation.from_euler('z',10,degrees=True).apply(local)
    p,r,_,_,record=fit_bounded(local,observed,np.zeros(3),np.eye(3),.002,2.,solver())
    assert record['solver_success'] and record['rotation_degrees']<=2.
    np.testing.assert_allclose(p,0.,atol=1e-10)
    np.testing.assert_allclose(r,Rotation.from_euler('z',2*(1-1e-6),degrees=True).as_matrix(),atol=1e-9)


def test_feasible_closed_form_uses_all_points_and_no_optimizer(monkeypatch):
    import native_object_bounded_fit as module
    local=axes();observed=Rotation.from_euler('x',1,degrees=True).apply(local)+[.0001,.0002,0.]
    def unexpected(*args,**kwargs):raise AssertionError('Unnecessary optimizer')
    monkeypatch.setattr(module,'minimize',unexpected)
    p,r,error,_,record=fit_bounded(local,observed,np.zeros(3),np.eye(3),.002,2.,solver())
    np.testing.assert_allclose(local@r.T+p,observed,atol=1e-14)
    assert record['solver_success'] and record['iterations']==0 and error.max()<1e-14


def test_iteration_failure_is_visible_and_output_stays_bounded():
    config=solver();config['maximum_iterations']=1
    p,r,_,_,record=fit_bounded(axes(),axes()+[.01,.005,0.],np.zeros(3),np.eye(3),.002,2.,config)
    assert not record['solver_success'] and np.linalg.norm(p)<=.002
    assert np.rad2deg(Rotation.from_matrix(r).magnitude())<=2.
    assert record['final_scaled_cost']<=record['initial_scaled_cost']+1e-14


@pytest.mark.parametrize('fault',['bad_pose','reflection','collinear','two','nonfinite','translation_bool','rotation_large','iterations_bool','ftol_bool','reserve_zero','extra_solver'])
def test_kernel_invalid_inputs_reject(fault):
    local=axes();observed=local.copy();p=np.zeros(3);r=np.eye(3);ts=.002;rs=2.;config=solver()
    if fault=='bad_pose':r[0,0]=2.
    if fault=='reflection':r[0,0]=-1.
    if fault=='collinear':local[:,1:]=0.
    if fault=='two':local=local[:2];observed=observed[:2]
    if fault=='nonfinite':observed[0,0]=np.nan
    if fault=='translation_bool':ts=True
    if fault=='rotation_large':rs=46.
    if fault=='iterations_bool':config['maximum_iterations']=True
    if fault=='ftol_bool':config['ftol']=True
    if fault=='reserve_zero':config['bound_reserve_fraction']=0.
    if fault=='extra_solver':config['unknown']=1
    with pytest.raises(ValueError):fit_bounded(local,observed,p,r,ts,rs,config)


def test_initial_reference_is_explicit_and_cannot_reset_pose_epoch(tmp_path):
    source,path,spec,scene,value=fixture(tmp_path);value=request(value)
    keys,_,_=unconstrained(scene,{k:v for k,v in value.items() if k not in ['initial_scene','solver']}|{'schema':'strep-native-object-correspondence-fit-v1'},sha256(path))
    initial_spec=copy.deepcopy(spec);initial_spec['objects']['item']['keyframes']=keys
    initial_path=tmp_path/'initial.json';save(initial_path,initial_spec)
    value['initial_scene']=dict(path=initial_path.name,sha256=sha256(initial_path));initial,_=initial_for(spec,scene,value,tmp_path)
    value['maximum_translation_m']=.0001
    fitted,arrays,_,records=proposal(scene,value,sha256(path),initial);candidate=copy.deepcopy(spec);candidate['objects']['item']['keyframes']=fitted
    audit=audit_bounds(scene,SceneContacts(candidate,tmp_path),value,arrays['times_s'])
    assert audit['passed'] and audit['maximum_translation_m']<=.0001
    assert any(r['initial_projection_change']>0 for r in records)
    assert sha256(source)==spec['actors']['A']['sha256'] and read(initial_path)==initial_spec


@pytest.mark.parametrize('fault',['binding','contact_intent','placement','other_object','geometry','initial_type','path_type','schema','extra'])
def test_initial_and_request_contracts_reject_changes(tmp_path,fault):
    _,path,spec,scene,value=fixture(tmp_path);value=request(value);initial_spec=copy.deepcopy(spec);initial_path=tmp_path/'initial.json'
    if fault=='contact_intent':initial_spec['contacts'][0]['limits']['position_m']+=.001
    if fault=='placement':initial_spec['actors']['A']['placement']['translation_m']=[1.,0.,0.]
    if fault=='other_object':initial_spec['objects']['other']=copy.deepcopy(initial_spec['objects']['item'])
    if fault=='geometry':initial_spec['objects']['item']['geometry']['size_m'][0]+=.1
    save(initial_path,initial_spec);value['initial_scene']=dict(path=initial_path.name,sha256=sha256(initial_path))
    if fault=='binding':value['initial_scene']['sha256']='0'*64
    if fault=='initial_type':value['initial_scene']=[]
    if fault=='path_type':value['initial_scene']['path']=[]
    if fault=='schema':value['schema']='strep-native-object-correspondence-fit-v1'
    if fault=='extra':value['silently_select']=True
    with pytest.raises(ValueError):
        base_request(value);initial_for(spec,scene,value,tmp_path)


def test_saved_complete_pipeline_passes_and_preserves_character_and_contact_intent(tmp_path):
    source,path,spec,scene,value=fixture(tmp_path);value=request(value);rp=tmp_path/'request.json';save(rp,value)
    pp=tmp_path/'policy.json';save(pp,policy(path));folder=tmp_path/'bounded';result=run(path,rp,pp,folder)
    assert result['sampled_constraints_pass'] and result['bounds']['passed'] and result['all_solver_frames_converged']
    assert result['actor_bytes_unchanged'] and result['original_selected']
    assert not result['quality_approved'] and not result['release_approved'] and not result['training_admitted']
    assert sha256(source)==spec['actors']['A']['sha256'] and read(folder/'proposal-contacts.json')['contacts']==spec['contacts']
    assert not result['initial_contact_conditions_pass'] and not result['initial_geometry_rechecked']
    for name,digest in result['files_sha256'].items():assert sha256(folder/name)==digest
    for name,digest in result['implementation_sha256'].items():assert sha256(folder/'implementation'/name)==digest
    with pytest.raises(ValueError,match='Fresh'):run(path,rp,pp,folder)


def test_hard_bounds_do_not_erase_unachieved_contact_conditions(tmp_path):
    _,path,spec,_,value=fixture(tmp_path);value=request(value);value['maximum_translation_m']=.0001
    for row in spec['contacts']:row['limits']['position_m']=.00001
    save(path,spec);value['contacts_sha256']=sha256(path);rp=tmp_path/'request.json';save(rp,value)
    pp=tmp_path/'policy.json';save(pp,policy(path));folder=tmp_path/'contact-failure';result=run(path,rp,pp,folder)
    assert result['bounds']['passed'] and not result['all_contact_conditions_pass'] and not result['sampled_constraints_pass']
    assert result['original_selected'] and not result['quality_approved']
    assert read(folder/'proposal-contacts.json')['contacts']==spec['contacts']


@pytest.mark.parametrize('stage',['during','after'])
def test_initial_digest_cannot_be_reset_when_reference_changes(tmp_path,monkeypatch,stage):
    import native_object_bounded_fit as module
    _,path,spec,scene,value=fixture(tmp_path);value=request(value);initial_path=tmp_path/'initial.json';save(initial_path,spec)
    value['initial_scene']=dict(path=initial_path.name,sha256=sha256(initial_path))
    def change():
        modified=copy.deepcopy(spec);modified['objects']['item']['keyframes'][0]['translation_m'][0]+=.001;save(initial_path,modified)
    if stage=='during':
        original_read=module.read
        def raced_read(p):
            data=original_read(p)
            if Path(p)==initial_path:change()
            return data
        monkeypatch.setattr(module,'read',raced_read)
        with pytest.raises(ValueError,match='changed during validation'):initial_for(spec,scene,value,tmp_path)
    else:
        original_initial=module.initial_for
        def raced_initial(*args):
            result=original_initial(*args);change();return result
        monkeypatch.setattr(module,'initial_for',raced_initial)
        rp=tmp_path/'request.json';save(rp,value);pp=tmp_path/'policy.json';save(pp,policy(path))
        folder=tmp_path/'race';binding=value['initial_scene']['sha256']
        with pytest.raises(ValueError,match='changed after validation'):run(path,rp,pp,folder)
        assert sha256(initial_path)!=binding and not folder.exists()
