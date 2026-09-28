"""Offline rigid-body release with pinned Godot, explicit assumptions and no overwrites."""
import copy
import subprocess
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from object_dynamics import finite_array
from release_geometry import body_geometry,geometry_fields,check_installed_geometry

ENGINE=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'


def validate(request):
    required={'position_m','rotation_xyzw','linear_velocity_m_s','angular_velocity_rad_s',
        'mass_kg','physics_fps','steps','friction','restitution','floor_enabled','floor_height_m'}
    if isinstance(request,dict):required|={'geometry'} if 'geometry' in request else {'size_m'}
    if not isinstance(request,dict) or not required<=set(request) or set(request)-required-{'contact_max_allowed_penetration_m','static_colliders','moving_colliders','backend'}:raise ValueError('Invalid release request fields')
    result=copy.deepcopy(request)
    from release_colliders import validate_colliders
    result['static_colliders']=validate_colliders(request.get('static_colliders',[]))
    tolerance=request.get('contact_max_allowed_penetration_m',.01)
    if type(tolerance) not in (int,float) or not np.isfinite(tolerance) or not 0<tolerance<=.01:raise ValueError('Invalid contact solver tolerance')
    result['contact_max_allowed_penetration_m']=tolerance
    geometry=body_geometry(request)
    for name in ['position_m','linear_velocity_m_s','angular_velocity_rad_s']:
        result[name]=finite_array(request[name],(3,),name).tolist()
    q=finite_array(request['rotation_xyzw'],(4,),'rotation')
    if abs(np.linalg.norm(q)-1)>1e-6:raise ValueError('Release rotation must be unit length')
    result['rotation_xyzw']=q.tolist()
    inertia=geometry.uniform_inertia(request['mass_kg'])
    result['inertia_diagonal_kg_m2']=np.diag(inertia).tolist()
    if type(request['physics_fps'])!=int or request['physics_fps'] not in (120,240,480):raise ValueError('Unsupported simulation clock')
    if type(request['steps'])!=int or not 1<=request['steps']<=14400:raise ValueError('Invalid simulation length')
    backend=request.get('backend','Jolt Physics' if geometry.shape=='sphere' else 'GodotPhysics3D')
    if backend not in ['GodotPhysics3D','Jolt Physics']:raise ValueError('Unsupported physics backend')
    result['backend']=backend
    from moving_release_colliders import validate_moving
    result['moving_colliders']=validate_moving(request.get('moving_colliders',[]),request['steps'],result['static_colliders'])
    if result['moving_colliders'] and backend!='Jolt Physics':raise ValueError('Moving colliders require the verified Jolt backend')
    for name in ['friction','restitution']:
        value=request[name]
        if type(value) not in (float,int) or not np.isfinite(value) or not 0<=value<=1:raise ValueError('Invalid '+name)
    if type(request['floor_enabled']) is not bool:raise ValueError('Explicit floor option required')
    if type(request['floor_height_m']) not in (int,float) or not np.isfinite(request['floor_height_m']):raise ValueError('Invalid floor height')
    return result


def simulate(request,output):
    request=validate(request);output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep object release bake"\n[physics]\n3d/physics_engine="'+request['backend']+'"\n3d/default_gravity=9.81\n3d/default_gravity_vector=Vector3(0,-1,0)\n3d/solver/contact_max_allowed_penetration='+str(request['contact_max_allowed_penetration_m'])+'\ncommon/physics_ticks_per_second='+str(request['physics_fps'])+'\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
    if request['backend']=='Jolt Physics':
        with (project/'project.godot').open('a',encoding='utf-8') as config:
            config.write('\n[physics]\njolt_physics_3d/simulation/penetration_slop='+str(request['contact_max_allowed_penetration_m'])+'\njolt_physics_3d/collisions/collision_margin_fraction=0.0\n')
    script=ROOT/'scripts/godot_object_release.gd';shutil.copyfile(script,project/'release.gd')
    save(output/'request.json',request)
    save(output/'provenance.json',dict(at=now(),engine_sha256=sha256(ENGINE),script_sha256=sha256(script),
        driver_sha256=sha256(__file__),geometry_driver_sha256=sha256(ROOT/'scripts/release_geometry.py'),geometry=body_geometry(request).record(),gravity_m_s2=[0,-9.81,0],
        backend=request['backend'],assumptions='Uniform solid primitive with centered COM; optional Y-up floor and explicit static or prescribed kinematic primitives. Prescribed props have infinite effective mass and do not react to impact. Optional actor-derived convex envelopes are approximations; no actor response. Hypothetical mass/material parameters. Zero damping, sleeping disabled, CCD enabled.',static_colliders=request['static_colliders'],moving_collider_ids=[x['id'] for x in request['moving_colliders']]))
    save(output/'pipeline.json',dict(status='running'))
    with (output/'engine.log').open('w',encoding='utf-8') as log:
        try:
            process=subprocess.run([str(ENGINE),'--headless','--path',str(project),'--fixed-fps',str(request['physics_fps']),
                '--script','release.gd','--',str(output/'request.json'),str(output/'engine-output.json')],
                stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
            if process.returncode:raise RuntimeError('Godot release failed; inspect engine.log')
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise
    report=read(output/'engine-output.json')
    try:audit_simulation(request,report)
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise
    save(output/'pipeline.json',dict(status='complete',at=now(),ticks=len(report['observations'])))
    return report


def audit_simulation(request,report):
    observations=report['observations']
    if 'released_geometry' in report:check_installed_geometry(body_geometry(request),report['released_geometry'])
    elif 'geometry' in request:raise ValueError('Missing installed released primitive geometry')
    expected=request.get('static_colliders',[]);actual=report.get('static_colliders',[])
    if len(actual)!=len(expected):raise ValueError('Missing or unexpected static colliders')
    for a,b in zip(actual,expected):
        if a['id']!=b['id']:raise ValueError('Collider identity mismatch')
        for field in ['position_m','friction','restitution']:np.testing.assert_allclose(a[field],b[field],atol=1e-6,rtol=0)
        if 'geometry' in b:check_installed_geometry(body_geometry(b),a['geometry'])
        else:np.testing.assert_allclose(a['size_m'],b['size_m'],atol=1e-6,rtol=0)
        np.testing.assert_allclose(Rotation.from_quat(a['rotation_xyzw']).as_matrix(),Rotation.from_quat(b['rotation_xyzw']).as_matrix(),atol=1e-6,rtol=0)
    from moving_release_colliders import audit_moving
    audit_moving(request,observations,report.get('moving_colliders',[]))
    allowed={c['id'] for c in expected+request.get('moving_colliders',[])}|({'floor'} if request['floor_enabled'] else set())
    for o in observations:
        if expected or 'contact_colliders' in o:
            ids=o.get('contact_colliders')
            if not isinstance(ids,list) or len(ids)!=o['contact_count'] or not set(ids)<=allowed:raise ValueError('Unknown or incomplete collider contact records')
    np.testing.assert_allclose(report.get('contact_max_allowed_penetration_m',.01),request.get('contact_max_allowed_penetration_m',.01),atol=1e-9,rtol=0)
    backend=request.get('backend','GodotPhysics3D')
    if backend=='Jolt Physics':
        if report.get('direct_state_class')!='JoltPhysicsDirectBodyState3D':raise ValueError('Jolt backend not actually active')
        if report.get('collision_margin_fraction')!=0.:raise ValueError('Unexpected rounded collider geometry')
    elif 'direct_state_class' in report and report['direct_state_class']!='GodotPhysicsDirectBodyState3D':raise ValueError('Godot physics backend not actually active')
    if report['backend']!=backend or report['physics_fps']!=request['physics_fps'] or len(observations)!=request['steps']+1:raise ValueError('Simulation backend or clock mismatch')
    if [o['tick'] for o in observations]!=list(range(request['steps']+1)):raise ValueError('Missing simulation ticks')
    steps=np.array([o['step_s'] for o in observations]);np.testing.assert_allclose(steps,1/request['physics_fps'],atol=1e-9,rtol=0)
    for field in ['position_m','rotation_xyzw','linear_velocity_m_s','angular_velocity_rad_s']:
        values=np.array([o[field] for o in observations]);assert np.isfinite(values).all()
    np.testing.assert_allclose(observations[0]['position_m'],request['position_m'],atol=1e-6,rtol=0)
    np.testing.assert_allclose(observations[0]['linear_velocity_m_s'],request['linear_velocity_m_s'],atol=1e-6,rtol=0)
    np.testing.assert_allclose(observations[0]['angular_velocity_rad_s'],request['angular_velocity_rad_s'],atol=1e-6,rtol=0)
    quats=np.array([o['rotation_xyzw'] for o in observations])
    np.testing.assert_allclose(np.linalg.norm(quats,axis=1),1,atol=1e-6,rtol=0)
    np.testing.assert_allclose(Rotation.from_quat(quats[0]).as_matrix(),Rotation.from_quat(request['rotation_xyzw']).as_matrix(),atol=1e-6,rtol=0)
    for o in observations:
        np.testing.assert_allclose(o['gravity_m_s2'],[0,-9.81,0],atol=1e-6,rtol=0)
        np.testing.assert_allclose(o['inverse_mass'],1/request['mass_kg'],atol=1e-7,rtol=1e-6)
        np.testing.assert_allclose(o['inverse_inertia'],1/np.array(request['inertia_diagonal_kg_m2']),atol=1e-7,rtol=1e-6)
        if o['linear_damp']!=0 or o['angular_damp']!=0:raise ValueError('Unexpected damping')


def release_request(track,release_frame,*,mass_kg=5.,physics_fps=240,friction=.6,restitution=0.,contact_max_allowed_penetration_m=.001):
    p=np.asarray(track['positions_m'],dtype=float);q=np.asarray(track['rotations_xyzw'],dtype=float);fps=track['fps']
    if fps!=30 or type(release_frame)!=int or not 2<=release_frame<len(p)-1:raise ValueError('Release requires finite 30fps context and a tail')
    finite_array(p,(len(p),3),'track positions');finite_array(q,(len(p),4),'track rotations')
    if not np.allclose(np.linalg.norm(q,axis=1),1,atol=1e-6,rtol=0):raise ValueError('Invalid track rotations')
    # Causal second-order backward derivative at the release sample.
    velocity=(3*p[release_frame]-4*p[release_frame-1]+p[release_frame-2])*fps/2
    r=Rotation.from_quat(q[release_frame-2:release_frame+1]).as_matrix()
    delta=Rotation.from_matrix(r[1:]@r[:-1].transpose(0,2,1)).as_rotvec()
    if np.any(np.linalg.norm(delta,axis=1)>=np.pi-1e-6):raise ValueError('Ambiguous incoming rotation')
    angular=(3*delta[1]-delta[0])*fps/2
    request=dict(position_m=p[release_frame].tolist(),rotation_xyzw=q[release_frame].tolist(),
        linear_velocity_m_s=velocity.tolist(),angular_velocity_rad_s=angular.tolist(),
        **geometry_fields(track),mass_kg=mass_kg,physics_fps=physics_fps,
        steps=(len(p)-1-release_frame)*(physics_fps//fps),friction=friction,restitution=restitution,
        floor_enabled=True,floor_height_m=0.,contact_max_allowed_penetration_m=contact_max_allowed_penetration_m)
    # The matched drop study retained a >10mm GodotPhysics3D/240Hz sphere
    # impact failure. Jolt/240Hz passed unchanged geometry/contact screens.
    if body_geometry(track).shape=='sphere':request['backend']='Jolt Physics'
    validate(request)
    return request


def bake(track,release_frame,request,report):
    expected=validate(request);observations=report['observations'];stride=expected['physics_fps']//track['fps']
    audit_simulation(expected,report)
    if track['fps']!=30 or type(release_frame)!=int or not 2<=release_frame<len(track['positions_m'])-1:raise ValueError('Invalid bake clock/window')
    np.testing.assert_allclose(request['position_m'],track['positions_m'][release_frame],atol=1e-10,rtol=0)
    np.testing.assert_allclose(Rotation.from_quat(request['rotation_xyzw']).as_matrix(),Rotation.from_quat(track['rotations_xyzw'][release_frame]).as_matrix(),atol=1e-10,rtol=0)
    if body_geometry(request)!=body_geometry(track):raise ValueError('Baked body geometry differs from input track')
    tail=observations[::stride]
    if len(tail)!=len(track['positions_m'])-release_frame:raise ValueError('Baked clock mismatch')
    result=copy.deepcopy(track)
    # Release sample is exactly the authored initial pose, avoiding float32
    # engine roundoff changing the user's retained prefix.
    result['positions_m'][release_frame+1:]=[o['position_m'] for o in tail[1:]]
    result['rotations_xyzw'][release_frame+1:]=[o['rotation_xyzw'] for o in tail[1:]]
    result['provenance']='Authored through release, then offline '+expected['backend']+' rigid-'+body_geometry(track).shape+' bake with optional floor and explicit static/prescribed geometry; no actor response or grip/balance approval.'
    return result
