"""Authored orientation vectors, exact side gaps and independent acceptance."""
from pathlib import Path
import sys,copy
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_surface_contact import scene_fixture,policy
from native_scene_contacts import SceneContacts
from native_scene_edit import SceneEdits
from native_scene_fit import SceneProblem
from native_contact_norms import ContactNorms,score,improved,nonregressing
from native_surface_contact import evaluate
import native_surface_model as surface
from native_scene_norms import NormRows
from test_native_surface_model import report
from strep import save,sha256


def prepared(tmp_path,*,angle=30.,partner=False,hold=False):
    _,rig,reader,spec,path,_=scene_fixture(tmp_path)
    if partner:
        spec['actors']['B']=copy.deepcopy(spec['actors']['A']);q=Rotation.from_euler('z',180-angle,degrees=True);v=rig.vertices(reader.sample(1.))[0]
        spec['actors']['B']['placement']=dict(rotation_xyzw=q.as_quat().tolist(),translation_m=(v-q.apply(v)).tolist())
        spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    if hold:
        spec['contacts'][0].update(mode='hold',interval_s=[.8,1.2],limits=dict(position_m=1e-6,relative_speed_m_s=1e-6))
    save(path,spec);p=policy(path,spec)
    if not partner:p['contacts'][spec['contacts'][0]['id']]['target_normal']['normals']=[Rotation.from_euler('x',angle,degrees=True).apply([0.,1,0]).tolist()]
    scene=SceneContacts(spec,tmp_path);digest=sha256(path)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],
        tracks=[dict(node=3,path='rotation',maximum_change=5.)],maximum_joint_displacement_m=.02)))
    problem=SceneProblem(scene,SceneEdits(permissions,scene,digest));return problem,p,digest


@pytest.mark.parametrize('angle',[0.,14.,16.,90.])
@pytest.mark.parametrize('partner',[False,True])
def test_norm_rows_reproduce_independent_audit_angle_and_side_limits(tmp_path,angle,partner):
    problem,p,digest=prepared(tmp_path,angle=angle,partner=partner);guide=ContactNorms(problem,p,digest);worlds=problem.worlds(problem.initial)
    rows,gaps,identity=guide.sample(worlds);r,_=evaluate(problem.scene,p,digest);point=r['contacts'][0]['samples'][0]['points'][0]
    assert point['opposition_error_degrees']==pytest.approx(angle,abs=2e-6)
    assert np.linalg.norm(rows.vectors[0])==pytest.approx(2*np.sin(np.deg2rad(angle)/2),abs=1e-12)
    np.testing.assert_allclose(gaps,[point['source_target_projection_m']+.0005,point['target_source_projection_m']+.0005],atol=1e-12)
    assert bool(np.all(guide.residual(worlds)<=0))==r['surface_contacts_pass']
    assert identity['original_references_and_clocks']


def test_continuous_norm_and_side_jacobians_predict_small_exported_pose_changes(tmp_path):
    problem,p,digest=prepared(tmp_path);guide=ContactNorms(problem,p,digest);x=problem.initial.copy()
    rows,j,identity=guide.linearize(x,problem.worlds(x),.02,step=1e-4)
    assert len(rows.caps)==3 and j.shape==(9,3)
    delta=np.array([1e-5,0.,-1e-5]);actual=guide.residual(problem.worlds(x+delta))
    np.testing.assert_allclose(rows.residual(j,delta),actual,atol=3e-7,rtol=0)
    assert identity['orientation_rows']==1 and identity['side_rows']==2


def test_every_hold_clock_is_retained_and_budgets_never_truncate(tmp_path):
    problem,p,digest=prepared(tmp_path,angle=0.,hold=True);guide=ContactNorms(problem,p,digest)
    rows,gaps,identity=guide.sample(problem.worlds(problem.initial));r,a=evaluate(problem.scene,p,digest)
    assert len(rows.caps)==len(a['contact_0_times_s']) and len(gaps)==2*len(rows.caps)
    np.testing.assert_array_equal([v['time_s'] for v in identity['identity']],a['contact_0_times_s'])
    with pytest.raises(ValueError,match='row budget'):ContactNorms(problem,p,digest,maximum_rows=2).sample(problem.worlds(problem.initial))
    p['maximum_actor_pose_queries']=1
    with pytest.raises(ValueError,match='pose budget'):ContactNorms(problem,p,digest).sample(problem.worlds(problem.initial))


def test_contact_score_cannot_trade_worst_or_total_squared_error_for_the_other():
    assert improved([2.,2.],[1.9,1.9]) and nonregressing([2.,2.],[1.9,1.9])
    assert not nonregressing([2.,2.],[2.1,0.])
    assert not nonregressing([2.,0.],[1.9,1.9])
    np.testing.assert_array_equal(score([-1.,-2.]),[0.,0.])
    with pytest.raises(ValueError):score([float('nan')])


def test_centroid_guidance_matches_union_face_audit(tmp_path):
    _,rig,reader,spec,path,_=scene_fixture(tmp_path);row=spec['contacts'][0]
    row.update(vertices=[[6,0,0],[6,0,1]],reduction='centroid')
    row['target']['points_m']=[rig.vertices(reader.sample(1.))[:2].mean(0).tolist()]
    save(path,spec);p=policy(path,spec);scene=SceneContacts(spec,tmp_path);digest=sha256(path)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],
        tracks=[dict(node=3,path='rotation',maximum_change=5.)],maximum_joint_displacement_m=.02)))
    problem=SceneProblem(scene,SceneEdits(permissions,scene,digest));guide=ContactNorms(problem,p,digest)
    rows,gaps,_=guide.sample(problem.worlds(problem.initial));audit,_=evaluate(scene,p,digest)
    assert len(rows.caps)==1 and audit['surface_contacts_pass']
    np.testing.assert_allclose(rows.vectors,[[0,0,0]],atol=1e-12);np.testing.assert_allclose(gaps,[.0005,.0005],atol=1e-12)


def test_object_guidance_matches_authored_rigid_normal_transform(tmp_path):
    _,rig,reader,spec,path,_=scene_fixture(tmp_path);v=rig.vertices(reader.sample(1.))[0];q=Rotation.from_euler('z',60,degrees=True)
    local=np.array([0,.2,0]);position=v-q.apply(local)
    spec['objects']['box']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.4,.4,.4]),keyframes=[
        dict(time_s=t,translation_m=position.tolist(),rotation_xyzw=Rotation.from_euler('z',angle,degrees=True).as_quat().tolist()) for t,angle in [(0.,0),(2.,120)]])
    spec['contacts'][0]['target']=dict(space='object',object='box',points_m=[local.tolist()]);save(path,spec);p=policy(path,spec)
    p['limits']['maximum_opposition_error_degrees']=70.;scene=SceneContacts(spec,tmp_path);digest=sha256(path)
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],
        tracks=[dict(node=3,path='rotation',maximum_change=5.)],maximum_joint_displacement_m=.02)))
    problem=SceneProblem(scene,SceneEdits(permissions,scene,digest));guide=ContactNorms(problem,p,digest)
    rows,gaps,_=guide.sample(problem.worlds(problem.initial));audit,_=evaluate(scene,p,digest)
    assert audit['surface_contacts_pass'] and np.all(guide.residual(problem.worlds(problem.initial))<=0)
    np.testing.assert_allclose(rows.vectors[0],np.array([0,-1.,0])+q.apply([0,1.,0]),atol=1e-12)
    np.testing.assert_allclose(gaps,[.0005,.0005],atol=1e-12)


@pytest.mark.parametrize('geometry_worse,contact_worse',[(True,False),(False,True),(False,False)])
def test_guided_acceptance_requires_both_geometry_and_contact_nonregression(monkeypatch,geometry_worse,contact_worse):
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1))
    system=NormRows([[0.,0,0]],[1.],[1.]);jac=sparse.csr_matrix((3,1))
    monkeypatch.setattr(surface,'model',lambda *a,**kw:(system,jac,None,{}))
    monkeypatch.setattr(surface,'direction',lambda *a,**kw:(np.array([.01]),dict(status='Solved')))
    guide=SimpleNamespace(residual=lambda worlds:np.array([2. if worlds==0 else (3. if contact_worse else 1.)]))
    def evaluator(x,label):
        initial=label=='start'
        return dict(native=np.array([-1.]),geometry=report(depth=2. if initial else (2.1 if geometry_worse else 1.)),worlds=0 if initial else 1,
            scene=None,policy=None,digest=None,surface_contact=dict(surface_contacts_pass=False))
    x,r=surface.optimize(problem,evaluator,iterations=1,restoration_steps=0,contact_model=guide)
    assert bool(np.any(x))==(not geometry_worse and not contact_worse)
    assert r['history'][0]['before_surface_contact_merit']==[2.,4.]


def test_invalid_or_incomplete_poses_cannot_supply_contact_guidance(tmp_path):
    problem,p,digest=prepared(tmp_path);guide=ContactNorms(problem,p,digest)
    with pytest.raises(ValueError,match='dictionary'):guide.sample({})
    with pytest.raises(ValueError,match='population'):guide.sample({'A':np.zeros((1,1,4,4))})
    with pytest.raises(ValueError):ContactNorms(problem,p,digest,maximum_rows=True)
