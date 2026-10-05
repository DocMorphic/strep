import copy
import itertools
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from object_geometry import Geometry
from primitive_penetration_bounds import ring
from convex_colliders import ConvexCylinderTest
from release_geometry import primitive_gap,convex_test,convex_gap
from object_release import release_request,validate,simulate,bake,audit_simulation,ENGINE
from release_colliders import audit_collisions,validate_colliders
from moving_release_colliders import validate_moving

I=np.eye(3)
C=Geometry('cylinder',(.2,.6))
POINTS=np.array(list(itertools.product([-.6,.7],[-.1,.1],[-.6,.5])))


def track():
    return dict(fps=30,geometry=C.record(),positions_m=[[0,1.5,0] for _ in range(61)],rotations_xyzw=[[0,0,0,1] for _ in range(61)])


def test_cylinder_release_preserves_geometry_at_all_public_entry_points():
    body=dict(geometry=C.record(),position_m=[0,1,0],rotation_xyzw=[0,0,0,1],friction=.4,restitution=0.)
    request=dict(body,linear_velocity_m_s=[0,0,0],angular_velocity_rad_s=[0,0,0],mass_kg=1.,physics_fps=240,steps=8,floor_enabled=True,floor_height_m=0.)
    assert validate(request)['geometry']==C.record()
    assert validate_colliders([dict(body,id='can')])[0]['geometry']==C.record()
    moving=dict(id='can',geometry=C.record(),positions_m=[[0,1,0]]*10,rotations_xyzw=[[0,0,0,1]]*10,friction=.4,restitution=0.)
    assert validate_moving([moving],8)[0]['geometry']==C.record()
    assert primitive_gap(C,[0,0,0],I,Geometry('sphere',(.1,)),[0,1,0],I)>0


@pytest.mark.parametrize('seed',range(8))
def test_complete_noncentral_convex_hull_matches_independent_minkowski_depth(seed):
    rng=np.random.default_rng(seed);r,s=Rotation.random(random_state=rng).as_matrix(),Rotation.random(random_state=rng).as_matrix()
    p,q=rng.uniform(-.1,.1,(2,3));test=ConvexCylinderTest(POINTS.tolist())
    result=test.bounds(p,r,C.dimensions,q,s,radial_tolerance_m=.004)
    n=result['radial_segments']
    for outer,key in [(False,'penetration_lower_m'),(True,'penetration_upper_m')]:
        radial=ring(n,outer)[0]*.2/(np.cos(np.pi/n) if outer else 1)
        a=radial.copy();a[:,1]=.3;b=radial.copy();b[:,1]=-.3
        cylinder=np.concatenate([a,b])@r.T+p;convex=POINTS@s.T+q
        hull=ConvexHull((cylinder[:,None]-convex[None]).reshape(-1,3))
        depth=max(0.,-float(hull.equations[:,3].max()))
        assert result[key]==pytest.approx(depth,abs=result['numerical_padding_m']*1.01)
    finer=test.bounds(p,r,C.dimensions,q,s)
    assert finer['penetration_lower_m']>=result['penetration_lower_m']-1e-12
    assert finer['penetration_upper_m']<=result['penetration_upper_m']+1e-12
    common=Rotation.from_rotvec([.3,-.4,.8]).as_matrix();offset=np.array([10.,-30.,20.])
    moved=test.bounds(common@p+offset,common@r,C.dimensions,common@q+offset,common@s,radial_tolerance_m=.004)
    assert moved['penetration_upper_m']==pytest.approx(result['penetration_upper_m'],abs=1e-12)


def test_convex_cylinder_uncertainty_gap_and_budget_are_not_sphere_fallback():
    test=convex_test(C,POINTS.tolist());p=[0,.4,0]
    result=test.bounds(p,I,C.dimensions,[0,0,0],I)
    assert isinstance(test,ConvexCylinderTest) and result['penetration_upper_m']<.001
    assert convex_gap(test,C,p,I,[0,0,0],I)==result['outer_projection_gap_m']-result['numerical_padding_m']
    assert not result['floating_point_interval_certified'] and not result['release_approved']
    with pytest.raises(ValueError,match='segment budget'):test.bounds(p,I,C.dimensions,[0,0,0],I,radial_tolerance_m=1e-12)
    with pytest.raises(ValueError,match='rigid'):test.bounds(p,I*2,C.dimensions,[0,0,0],I)


@pytest.mark.parametrize('count',[32,64,128])
def test_irregular_convex_uses_every_hull_vertex_up_to_public_resource_limit(count):
    y=1-2*(np.arange(count)+.5)/count;theta=np.arange(count)*np.pi*(3-np.sqrt(5));radial=np.sqrt(1-y*y)
    points=np.c_[radial*np.cos(theta),y,radial*np.sin(theta)]*[.4,.5,.3]+[.1,-.03,.07]
    test=ConvexCylinderTest(points.tolist());r=Rotation.from_rotvec([.2,.4,-.1]).as_matrix()
    result=test.bounds([0,0,0],r,C.dimensions,[0,0,0],I,radial_tolerance_m=.004)
    assert result['hull_vertices']==count and np.array_equal(test.points,points)
    n=result['radial_segments']
    for outer,key in [(False,'penetration_lower_m'),(True,'penetration_upper_m')]:
        v=ring(n,outer)[0]*.2/(np.cos(np.pi/n) if outer else 1)
        a=v.copy();a[:,1]=.3;b=v.copy();b[:,1]=-.3;v=np.concatenate([a,b])@r.T
        hull=ConvexHull((v[:,None]-points[None]).reshape(-1,3))
        assert result[key]==pytest.approx(max(0.,-hull.equations[:,3].max()),abs=result['numerical_padding_m']*1.01)


def test_convex_cylinder_retains_near_parallel_edges_and_rejects_incomplete_hulls():
    points=np.array(list(itertools.product([-.5,.5],repeat=3)))
    test=ConvexCylinderTest(points.tolist());parallel=test.bounds([0,0,0],I,C.dimensions,[0,0,0],I)
    near=test.bounds([0,0,0],Rotation.from_rotvec([0,0,1e-13]).as_matrix(),C.dimensions,[0,0,0],I)
    assert near['axes_evaluated']>parallel['axes_evaluated']
    with pytest.raises(ValueError,match='4–128'):ConvexCylinderTest([[0,0,0]]*129)
    with pytest.raises(ValueError,match='hull vertices'):ConvexCylinderTest(np.vstack([points,[0,0,0]]).tolist())


def test_cylinder_request_uniform_inertia_incoming_motion_and_size_limits():
    source=track();t=np.arange(61)/30;source['positions_m']=np.c_[t,10+2*t,np.zeros(len(t))].tolist()
    source['rotations_xyzw']=Rotation.from_rotvec(t[:,None]*[0,1,0]).as_quat().tolist()
    req=release_request(source,30,mass_kg=3.)
    assert req['backend']=='Jolt Physics'
    np.testing.assert_allclose(validate(req)['inertia_diagonal_kg_m2'],[.12,.06,.12])
    np.testing.assert_allclose(req['linear_velocity_m_s'],[1,2,0],atol=1e-12)
    np.testing.assert_allclose(req['angular_velocity_rad_s'],[0,1,0],atol=1e-12)
    source['positions_m'][31]=[999,999,999]
    assert release_request(source,30,mass_kg=3.)==req
    mixed=dict(req,size_m=[1,1,1])
    with pytest.raises(ValueError):validate(mixed)
    big=dict(id='can',geometry=Geometry('cylinder',(51.,1.)).record(),position_m=[0,0,0],rotation_xyzw=[0,0,0,1],friction=.6,restitution=0.)
    with pytest.raises(ValueError,match='shape'):validate_colliders([big])


def test_default_backend_uses_whole_cylinder_world_and_keeps_explicit_comparison():
    source=track();source.pop('geometry');source['size_m']=[.4]*3
    req=release_request(source,2)
    assert validate(req)['backend']=='GodotPhysics3D'
    req['static_colliders']=[dict(id='support',geometry=C.record(),position_m=[0,0,0],rotation_xyzw=[0,0,0,1],friction=.6,restitution=0.)]
    assert validate(req)['backend']=='Jolt Physics'
    req['backend']='GodotPhysics3D'
    assert validate(req)['backend']=='GodotPhysics3D'


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned local Godot unavailable')
@pytest.mark.parametrize('released',['cylinder','box','sphere'])
def test_actual_default_cylinder_world_contacts_keep_original_depth_and_settling_limits(tmp_path,released):
    source=track()
    if released!='cylinder':source['geometry']=(Geometry('box',(.4,.4,.4)) if released=='box' else Geometry('sphere',(.2,))).record()
    req=release_request(source,2)
    req['static_colliders']=[dict(id='support',geometry=Geometry('cylinder',(.6,.2)).record(),position_m=[0,.1,0],rotation_xyzw=[0,0,0,1],friction=.6,restitution=0.)]
    report=simulate(req,tmp_path/released)
    assert report['backend']=='Jolt Physics'
    assert report['static_colliders'][0]['geometry']['shape']=='cylinder'
    assert any('support' in o['contact_colliders'] for o in report['observations'])
    audit=audit_collisions(validate(req),report['observations'],2)
    assert audit['collision_and_settling_screens_passed'] and audit['colliders'][0]['max_penetration_m']<=.01


@pytest.mark.parametrize('support',['box','sphere','cylinder','convex'])
def test_saved_clock_audit_uses_upper_bound_and_never_proximity_as_contact(support):
    req=release_request(track(),2);req.update(steps=1,floor_enabled=False,backend='Jolt Physics')
    if support=='convex':
        req['moving_colliders']=[dict(id='support',shape='convex',points_m=POINTS.tolist(),positions_m=[[0,0,0]]*3,rotations_xyzw=[[0,0,0,1]]*3,friction=.6,restitution=0.)]
        height=.4
    else:
        g={'box':Geometry('box',(1.,.2,1.)),'sphere':Geometry('sphere',(.5,)),'cylinder':Geometry('cylinder',(.5,.2))}[support]
        req['static_colliders']=[dict(id='support',geometry=g.record(),position_m=[0,0,0],rotation_xyzw=[0,0,0,1],friction=.6,restitution=0.)]
        height=.8 if support=='sphere' else .4
    req=validate(req)
    obs=[dict(tick=t,position_m=[0,height,0],rotation_xyzw=[0,0,0,1],contact_colliders=[],linear_velocity_m_s=[0,0,0],angular_velocity_rad_s=[0,0,0]) for t in range(2)]
    audit=audit_collisions(req,obs,2);row=audit['colliders'][0]
    assert len(row['penetration_bounds_by_tick'])==2 and row['max_penetration_m']<.001
    assert row['max_penetration_m']>=row['max_penetration_lower_m']
    assert not audit['collision_and_settling_screens_passed']
    obs[-1]['contact_colliders']=['support']
    assert audit_collisions(req,obs,2)['collision_and_settling_screens_passed']
    obs[0]['position_m'][1]-=.011
    assert not audit_collisions(req,obs,2)['collision_and_settling_screens_passed']


@pytest.mark.parametrize('mode',['static_scene','moving_scene','convex_skin'])
@pytest.mark.parametrize('overlap',[False,True])
def test_scene_start_guard_uses_conservative_cylinder_depth(monkeypatch,mode,overlap):
    import scene_release_job as job
    import actor_collision_proxies
    obj=dict(geometry=C.record(),keyframes=[dict(frame=0,translation_m=[0,.4-(.005 if overlap else 0),0],rotation_xyzw=[0,0,0,1])])
    support=dict(geometry=Geometry('cylinder',(.5,.2)).record(),keyframes=[dict(frame=0,translation_m=[0,0,0],rotation_xyzw=[0,0,0,1])])
    scene=dict(frame_count=5,fps=30,actors={},objects=dict(can=obj),contacts=[])
    if mode!='convex_skin':scene['objects']['support']=support
    monkeypatch.setattr(job,'source_metadata',lambda url:dict(revision='r',bundle=dict(scene=scene),base=Path('.')))
    def proxies(*args,**kwargs):
        return [dict(id='actor:A:hull',shape='convex',points_m=POINTS.tolist(),positions_m=[[0,0,0]]*18,rotations_xyzw=[[0,0,0,1]]*18,friction=.6,restitution=0.)],{}
    monkeypatch.setattr(actor_collision_proxies,'compile_actor_proxies',proxies)
    data=dict(source_url='/files/fixture',revision='r',object='can',release_frame=2,mass_kg=1.,friction=.6,restitution=0.,label='Fixture',
              collision_mode=mode if mode!='convex_skin' else 'floor_only',actor_collision_mode='convex_skin' if mode=='convex_skin' else 'none')
    if overlap:
        with pytest.raises(ValueError,match='overlaps'):job.validate(data)
    else:
        _,authored,request=job.validate(data)
        assert authored['geometry']==request['geometry']==C.record()


@pytest.mark.parametrize('geometry',[C,Geometry('box',(.4,.6,.4)),Geometry('sphere',(.3,))])
@pytest.mark.parametrize('penetration',[0.,.0009,.0011,.02])
def test_scene_floor_start_guard_matches_analytic_shape_and_original_limit(monkeypatch,geometry,penetration):
    import scene_release_job as job
    obj=dict(geometry=geometry.record(),keyframes=[dict(frame=0,translation_m=[0,.3-penetration,0],rotation_xyzw=[0,0,0,1])])
    scene=dict(frame_count=5,fps=30,actors={},objects=dict(can=obj),contacts=[])
    monkeypatch.setattr(job,'source_metadata',lambda url:dict(revision='r',bundle=dict(scene=scene),base=Path('.')))
    data=dict(source_url='/files/fixture',revision='r',object='can',release_frame=2,mass_kg=1.,friction=.6,restitution=0.,label='Fixture')
    if penetration>.001:
        with pytest.raises(ValueError,match='overlaps floor'):job.validate(data)
    else:assert job.validate(data)[2]['floor_enabled']


def test_study_preserves_supplied_request_after_derived_fields_and_covers_both_backends():
    from study_cylinder_release import input_request,fixtures
    req=validate(release_request(track(),2));before=copy.deepcopy(req)
    assert validate(input_request(req))==req and req==before
    cases=fixtures()
    assert len(cases)==19 and len({c['id'] for c in cases})==19
    assert {c['backend'] for c in cases}=={'Jolt Physics','GodotPhysics3D'}
    assert {c.get('moving') for c in cases if 'moving' in c}=={'box','cylinder','convex'}


@pytest.mark.skipif(not ENGINE.exists(),reason='Pinned local Godot unavailable')
def test_actual_cylinder_freeflight_spin_installed_inertia_and_prefix(tmp_path):
    source=track();t=np.arange(61)/30;source['positions_m']=np.c_[t,10+2*t,np.zeros(len(t))].tolist()
    source['rotations_xyzw']=Rotation.from_rotvec(t[:,None]*[0,1,0]).as_quat().tolist();before=copy.deepcopy(source)
    req=release_request(source,30);req.update(floor_enabled=False,backend='Jolt Physics')
    report=simulate(req,tmp_path/'flight');obs=report['observations'];times=np.arange(len(obs))/240
    expected=np.array(req['position_m'])+times[:,None]*req['linear_velocity_m_s']+.5*(times*times+times/240)[:,None]*[0,-9.81,0]
    np.testing.assert_allclose([o['position_m'] for o in obs],expected,atol=3e-5,rtol=0)
    rotation=Rotation.from_rotvec(times[:,None]*req['angular_velocity_rad_s'])*Rotation.from_quat(req['rotation_xyzw'])
    np.testing.assert_allclose(Rotation.from_quat([o['rotation_xyzw'] for o in obs]).as_matrix(),rotation.as_matrix(),atol=1e-5,rtol=0)
    assert report['released_geometry']['shape']=='cylinder'
    # Godot records Float32 dimensions; audit_simulation already enforces the
    # existing 1e-6 installation bound, rather than decimal JSON equality.
    np.testing.assert_allclose([report['released_geometry']['radius_m'],report['released_geometry']['height_m']],C.dimensions,atol=1e-6,rtol=0)
    candidate=bake(source,30,req,report)
    assert source==before and candidate['positions_m'][:31]==source['positions_m'][:31] and candidate['rotations_xyzw'][:31]==source['rotations_xyzw'][:31]
    wrong=copy.deepcopy(report);wrong['released_geometry']['height_m']=.7
    with pytest.raises(AssertionError):audit_simulation(validate(req),wrong)
    wrong=copy.deepcopy(report);wrong['observations'][3]['inverse_inertia'][1]*=1.1
    with pytest.raises(AssertionError):audit_simulation(validate(req),wrong)
