"""Direct native constraints without downloaded models, skin assets or inference."""
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_pose_restoration import reference_slacks,RestorationProblem,run
from grasp_pose_witness import PoseProblem
from object_geometry import Geometry


def fixture():
    p=torch.zeros((2,3),dtype=torch.float64)
    refs={name:torch.zeros((3,2,3),dtype=torch.float64) for name in ['raw','limb','previous']}
    return p,refs,{0:p.clone(),2:p.clone()}


def test_all_three_reference_balls_and_both_temporal_sides_are_required():
    p,refs,neighbors=fixture();refs['raw'][1,0,0]=.221
    assert reference_slacks(p,refs,neighbors,1)[0]<0
    refs['raw'].zero_();refs['limb'][2,1,1]=.051
    slack=reference_slacks(p,refs,neighbors,1)
    assert slack[0]>0 and slack[1]>0 and slack[2]<0
    refs['limb'].zero_();refs['previous'][0,0,2]=.051
    assert reference_slacks(p,refs,neighbors,1)[1]<0


def test_maxima_have_exact_same_feasible_set_as_all_reference_and_joint_rows():
    rng=np.random.default_rng(937)
    for _ in range(20):
        p,refs,neighbors=fixture()
        p[:]=torch.as_tensor(rng.normal(0,.02,(2,3)))
        for ref in refs.values():ref[:]=torch.as_tensor(rng.normal(0,.01,(3,2,3)))
        for v in neighbors.values():v[:]=torch.as_tensor(rng.normal(0,.02,(2,3)))
        all_rows=[]
        for ref in refs.values():
            all_rows.extend((1-((p-ref[1])**2).sum(-1)/.22**2).tolist())
            for f,v in neighbors.items():
                all_rows.extend((1-((((p-ref[1])-(v-ref[f]))*30)**2).sum(-1)/1.5**2).tolist())
        assert bool((reference_slacks(p,refs,neighbors,1)>=0).all())==all(v>=0 for v in all_rows)


def test_reference_constraint_gradient_matches_finite_difference_away_from_ties():
    p,refs,neighbors=fixture();p[0]=torch.tensor([.03,.01,-.02]);refs['previous'][1,0,0]=-.02
    p.requires_grad_();values=reference_slacks(p,refs,neighbors,1)
    direction=torch.tensor([[.2,-.1,.3],[-.2,.3,-.4]],dtype=torch.float64);h=1e-7
    fd=(reference_slacks(p+h*direction,refs,neighbors,1)-reference_slacks(p-h*direction,refs,neighbors,1))/(2*h)
    for i,v in enumerate(values):
        gradient=torch.autograd.grad(v,p,retain_graph=True)[0]
        np.testing.assert_allclose((gradient*direction).sum().item(),fd[i].item(),rtol=1e-7,atol=1e-7)


def test_joint_group_rows_preserve_every_global_reference_inequality():
    rng=np.random.default_rng(201)
    for _ in range(20):
        p,refs,neighbors=fixture();p[:]=torch.as_tensor(rng.normal(0,.05,(2,3)))
        for ref in refs.values():ref[:]=torch.as_tensor(rng.normal(0,.02,(3,2,3)))
        grouped=reference_slacks(p,refs,neighbors,1,grouped=True).reshape(3,2)
        np.testing.assert_allclose(grouped.amin(1).numpy(),reference_slacks(p,refs,neighbors,1).numpy(),rtol=0,atol=0)


def test_native_skin_group_inequalities_cover_every_original_vertex():
    p=RestorationProblem.__new__(RestorationProblem)
    p.t=lambda a:torch.as_tensor(a,dtype=torch.float64);p.frame=1;p.grouping='native-joint';p.headroom_m=1e-6
    p.contacts=[];p.point_limits=[];p.normals=[]
    p.config={'normal_tolerance_degrees':10,'clearance_m':.002}
    _,p.references,p.neighbors=fixture();positions=torch.zeros((2,3),dtype=torch.float64)
    vertices=torch.tensor([[.19,.4,0],[.5,.4,0],[0,.59,0],[0,.9,0]],dtype=torch.float64)
    p.fk=lambda x:(None,positions,None,vertices)
    p.objects=[(Geometry('box',(.4,.4,.4)),'box',p.t([[0,.4,0]]),p.t(np.eye(3)[None]))]
    p.margins={'box':np.full(4,1e-5)};p.vertex_groups=[('one',np.array([0,1])),('two',np.array([2,3]))]
    grouped=p.geometry_slack(p.t([0]));p.grouping='global';global_values=p.geometry_slack(p.t([0]))
    assert grouped[1]<0 and grouped[2]<0
    np.testing.assert_allclose(grouped[1:3].min(),global_values[1],rtol=0,atol=0)


@pytest.mark.parametrize('frame,keys',[(0,{1}),(2,{1})])
def test_endpoints_require_only_the_available_neighbor(frame,keys):
    p,refs,_=fixture()
    assert reference_slacks(p,refs,{k:p.clone() for k in keys},frame).shape==(2,)


@pytest.mark.parametrize('change',[
    lambda p,r,n:(None,r,n,1),
    lambda p,r,n:(p.float(),r,n,1),
    lambda p,r,n:(p,{k:v for k,v in r.items() if k!='raw'},n,1),
    lambda p,r,n:(p,{**r,'raw':r['raw'][:2]},n,1),
    lambda p,r,n:(p,r,{0:n[0]},1),
    lambda p,r,n:(p,r,{0:None,2:n[2]},1),
    lambda p,r,n:(p,r,n,True),
    lambda p,r,n:(p,r,n,-1),
    lambda p,r,n:(p,r,{0:n[0]*float('nan'),2:n[2]},1),
])
def test_incomplete_or_nonfinite_reference_input_is_rejected(change):
    with pytest.raises(ValueError):reference_slacks(*change(*fixture()))


@pytest.mark.parametrize('name,value',[('position_limit',0),('position_limit',float('nan')),('speed_limit',-1),('speed_limit',True)])
def test_invalid_budgets_are_rejected(name,value):
    with pytest.raises(ValueError):reference_slacks(*fixture(),frame=1,**{name:value})


def independent_problem(monkeypatch,vertex):
    """Full 77-joint audit stub isolates the independent acceptance gates."""
    p=RestorationProblem.__new__(RestorationProblem)
    p.frame=1;p.editable=list(range(58));p.limits=np.ones(58)
    identity=np.tile(np.eye(3),(3,77,1,1))
    p.previous={'local_rot_mats':identity}
    motion={'local_rot_mats':identity[1:2].copy(),'global_rot_mats':identity[1:2].copy(),'posed_joints':np.zeros((1,77,3))}
    monkeypatch.setattr(PoseProblem,'independent',lambda self,x:({},motion))
    class Surface:
        def vertices(self,*args):return np.asarray([vertex],dtype=float)
    p.surface=Surface();p.contacts=[];p.point_limits=[];p.normals=[]
    p.config={'normal_tolerance_degrees':10,'max_root_lift_m':.22,'clearance_m':.002}
    p.references={n:torch.zeros((3,77,3),dtype=torch.float64) for n in ['raw','limb','previous']}
    p.neighbors={f:torch.zeros((77,3),dtype=torch.float64) for f in [0,2]}
    p.objects=[(Geometry('box',(.4,.4,.4)),'box',torch.tensor([[0.,.4,0.]],dtype=torch.float64),torch.eye(3,dtype=torch.float64)[None])]
    p.margins={'box':np.array([1e-5])}
    return p,np.zeros(175),motion


def test_intentional_contact_region_never_exempts_physical_penetration(monkeypatch):
    p,x,_=independent_problem(monkeypatch,[.199,.4,0])
    audit,_=p.independent(x)
    assert not audit['pose_checks_passed']
    assert audit['objects'][0]['maximum_physical_vertex_depth_m']==pytest.approx(.001)
    p.surface.vertices=lambda *a:np.array([[.201,.4,0]])
    assert p.independent(x)[0]['pose_checks_passed']


def test_independent_body_gate_checks_raw_and_fixed_neighbor_added_speed(monkeypatch):
    p,x,m=independent_problem(monkeypatch,[.201,.4,0])
    p.references['raw'][1,5,0]=.221
    assert not p.independent(x)[0]['body']['raw']['passed']
    p.references['raw'].zero_();p.neighbors[2][4,1]=.051
    audit,_=p.independent(x)
    assert not audit['pose_checks_passed']
    assert audit['body']['previous']['neighbor_max_added_speeds_m_s'][1]==pytest.approx(1.53)


def test_active_anchor_audit_is_finite_json_serializable(monkeypatch):
    import json
    p,x,_=independent_problem(monkeypatch,[.201,.4,0])
    p.contacts=[dict(region='LeftHand',vertex=0,target=[.201,.4,0])]
    p.point_limits=np.array([.00499])
    audit,_=p.independent(x)
    assert audit['pose_checks_passed']
    assert json.loads(json.dumps(audit,allow_nan=False))['points'][0]['passed'] is True


def test_explicit_saved_audit_checks_actual_root_and_never_reconstructs(monkeypatch):
    p,x,m=independent_problem(monkeypatch,[.201,.4,0]);p.base={'root_positions':np.zeros((3,3))}
    m['root_positions']=np.array([[0.,.23,0.]])
    monkeypatch.setattr(PoseProblem,'independent',lambda *a:pytest.fail('Saved audit reconstructed motion'))
    before={k:v.copy() for k,v in m.items()};audit=p.audit_motion(m)
    assert not audit['root_budget_passed'] and not audit['pose_checks_passed']
    for key in m:np.testing.assert_array_equal(before[key],m[key])
    m['root_positions'][0,1]=.01
    assert p.audit_motion(m)['pose_checks_passed']


@pytest.mark.parametrize('damage',['joints','local','global','root','nan'])
def test_incomplete_saved_native_pose_is_rejected(monkeypatch,damage):
    p,x,m=independent_problem(monkeypatch,[.201,.4,0]);p.base={'root_positions':np.zeros((3,3))}
    m['root_positions']=np.zeros((1,3))
    if damage=='joints':m['posed_joints']=m['posed_joints'][:,:76]
    if damage=='local':m['local_rot_mats']=m['local_rot_mats'].astype(int)
    if damage=='global':m['global_rot_mats']=m['global_rot_mats'][:,:76]
    if damage=='root':m['root_positions']=m['root_positions'][0]
    if damage=='nan':m['posed_joints'][0,0,0]=float('nan')
    with pytest.raises(ValueError):p.audit_motion(m)


def test_failed_new_study_has_terminal_failure_and_does_not_overwrite_old_output(tmp_path,monkeypatch):
    import scene_pose_restoration as module
    from contextlib import nullcontext
    monkeypatch.setattr(module,'worker_lock',nullcontext)
    def fail(study,output,*args):
        output.mkdir();raise ValueError('Preserved test failure')
    monkeypatch.setattr(module,'_run',fail)
    output=tmp_path/'pose'
    with pytest.raises(ValueError):run(tmp_path,output,1)
    assert module.read(output/'pipeline.json')['status']=='failed'
    before=(output/'pipeline.json').read_bytes()
    with pytest.raises(FileExistsError):run(tmp_path,output,1)
    assert (output/'pipeline.json').read_bytes()==before
