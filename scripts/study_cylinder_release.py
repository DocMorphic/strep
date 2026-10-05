"""Saved serial cylinder-release fixtures; no models, actors, renderer or overwrites.

The numerical collision/settling screen is retained even when it fails. Each
case binds source, installed shapes/inertia, all engine ticks and a 30 Hz bake.
This fixture study never supplies held-out motion or human release evidence.
"""
import argparse
import copy
import json
import time
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from action_worker_lock import worker_lock
from object_geometry import Geometry
from object_release import ENGINE,release_request,validate,simulate,bake
from release_colliders import audit_collisions
from scene_object_export import export_objects
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from strep import ROOT,now,save,sha256

METHODS=['study_cylinder_release.py','object_release.py','release_geometry.py','primitive_penetration_bounds.py',
         'release_colliders.py','moving_release_colliders.py','convex_colliders.py','object_geometry.py',
         'object_geometry_mesh.py','scene_object_export.py','scene_constraints.py','rig_clip_import.py','gltf_tools.py',
         'godot_object_release.gd','strep.py']


def input_request(validated):
    """Remove derived validation outputs before entering public request APIs."""
    result=copy.deepcopy(validated);result.pop('inertia_diagonal_kg_m2')
    for collider in result['moving_colliders']:collider.pop('center_of_mass_local_m',None)
    return result


def fixtures():
    cylinder=Geometry('cylinder',(.2,.6));box=Geometry('box',(.4,.4,.4));sphere=Geometry('sphere',(.2,))
    cases=[]
    for backend in ['GodotPhysics3D','Jolt Physics']:
        for variant in ['flight','floor-upright','floor-tilted','static-box','static-cylinder','static-sphere','box-on-cylinder','sphere-on-cylinder']:
            entry=dict(id=backend.replace(' ','')+'-'+variant,backend=backend,variant=variant,geometry=cylinder,position=[0,1.5,0],
                       rotation=[0,0,0,1],velocity=[0,0,0],angular=[0,0,0],seconds=2.,floor=True)
            if variant=='flight':entry.update(position=[0,10,0],velocity=[.2,1.,-.1],angular=[0,1.,0],seconds=1.,floor=False)
            elif variant=='floor-tilted':entry.update(rotation=Rotation.from_rotvec([.7,.2,.3]).as_quat().tolist(),seconds=3.)
            elif variant.startswith('static-'):
                support={'static-box':Geometry('box',(2.,.2,2.)),'static-cylinder':Geometry('cylinder',(.6,.2)),'static-sphere':Geometry('sphere',(.5,))}[variant]
                entry['static']=dict(id='support',geometry=support.record(),position_m=[0,.1 if support.shape!='sphere' else .5,0],rotation_xyzw=[0,0,0,1],friction=.6,restitution=0.)
            elif variant.endswith('on-cylinder'):
                entry['geometry']=box if variant.startswith('box-') else sphere
                entry['static']=dict(id='support',geometry=Geometry('cylinder',(.6,.2)).record(),position_m=[0,.1,0],rotation_xyzw=[0,0,0,1],friction=.6,restitution=0.)
            cases.append(entry)
    for shape in ['box','cylinder','convex']:
        cases.append(dict(id='Jolt-moving-'+shape,backend='Jolt Physics',variant='moving-'+shape,geometry=cylinder,
                          position=[0,1.3,0],rotation=[0,0,0,1],velocity=[.2,.15,0],angular=[0,.2,0],seconds=2.,floor=True,moving=shape))
    return cases


def run_case(case,folder):
    geometry=case['geometry'];frames=int(case['seconds']*30)+3;release=2
    times=(np.arange(frames)-release)/30
    rotations=Rotation.from_rotvec(times[:,None]*case['angular'])*Rotation.from_quat(case['rotation'])
    source=dict(fps=30,geometry=geometry.record(),positions_m=(np.array(case['position'])+times[:,None]*case['velocity']).tolist(),rotations_xyzw=rotations.as_quat().tolist())
    folder.mkdir();save(folder/'source-track.json',source);before=copy.deepcopy(source)
    request=release_request(source,release);request.update(backend=case['backend'],floor_enabled=case['floor'])
    if 'static' in case:request['static_colliders']=[case['static']]
    if 'moving' in case:
        ticks=np.arange(-1,request['steps']+1)/request['physics_fps']
        moving=dict(id='actor:fixture:hull' if case['moving']=='convex' else 'support',friction=.6,restitution=0.,
                    positions_m=(np.array([0,.9,0])+ticks[:,None]*[.2,.15,0]).tolist(),
                    rotations_xyzw=Rotation.from_rotvec(ticks[:,None]*[0,.2,0]).as_quat().tolist())
        if case['moving']=='convex':
            import itertools
            moving.update(shape='convex',points_m=list(map(list,itertools.product([-.6,.7],[-.1,.1],[-.6,.5]))))
        else:moving['geometry']=(Geometry('cylinder',(.6,.2)) if case['moving']=='cylinder' else Geometry('box',(1.3,.2,1.1))).record()
        request['moving_colliders']=[moving]
    request=validate(request);save(folder/'request.json',request)
    supplied=input_request(request)
    started=time.monotonic();report=simulate(supplied,folder/'simulation')
    physics_s=time.monotonic()-started;observations=report['observations']
    candidate=bake(source,release,supplied,report)
    assert source==before and candidate['positions_m'][:release+1]==source['positions_m'][:release+1] and candidate['rotations_xyzw'][:release+1]==source['rotations_xyzw'][:release+1]
    save(folder/'baked-track.json',candidate)
    keys=[dict(frame=f,translation_m=p,rotation_xyzw=q) for f,(p,q) in enumerate(zip(candidate['positions_m'],candidate['rotations_xyzw']))]
    glb=folder/'baked-object.glb';export_objects(dict(fps=30,frame_count=frames,objects={'prop':dict(geometry=geometry.record(),keyframes=keys)}),glb)
    doc,binary=read_glb(glb);sampler=AnimationSampler(doc,binary,0)
    rotation=Rotation.from_quat(candidate['rotations_xyzw']).as_matrix()
    errors=[]
    for f,p in enumerate(candidate['positions_m']):
        actual=sampler.sample(f/30)[0]
        errors.append([float(np.linalg.norm(actual[:3,3]-p)),float(np.abs(actual[:3,:3]-rotation[f]).max())])
    error=np.max(errors,axis=0);assert error[0]<=1e-6 and error[1]<=1e-6
    collision=audit_collisions(request,observations,release);save(folder/'collision-audit.json',collision)
    expected_contact='floor' if case['variant'].startswith('floor-') else 'actor:fixture:hull' if case.get('moving')=='convex' else 'support'
    contact=any(expected_contact in o['contact_colliders'] for o in observations)
    analytic=None
    if case['variant']=='flight':
        t=np.arange(len(observations))/request['physics_fps'];dt=1/request['physics_fps']
        expected=np.array(request['position_m'])+t[:,None]*request['linear_velocity_m_s']+.5*(t*t+t*dt)[:,None]*[0,-9.81,0]
        analytic=float(np.abs(np.array([o['position_m'] for o in observations])-expected).max())
    result=dict(id=case['id'],backend=report['backend'],variant=case['variant'],status='complete',samples=len(observations),physics_s=physics_s,
                released_geometry=report['released_geometry'],expected_contact_seen=contact,source_prefix_unchanged=True,
                source_glb_position_error_m=float(error[0]),source_glb_rotation_element_error=float(error[1]),
                freeflight_discrete_position_error_m=analytic,collision_and_settling_screens_passed=collision['collision_and_settling_screens_passed'],
                max_floor_penetration_m=collision['max_floor_penetration_m'],max_collider_penetration_upper_m=max([0.]+[r['max_penetration_m'] for r in collision['colliders']]),
                actor_motion_responds=False,renderer_executed=False,quality_approved=False,release_approved=False)
    save(folder/'result.json',result)
    return result


def study(output):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'reports').resolve()):raise ValueError('Study output must be a fresh reports folder')
    with worker_lock():
        output.mkdir(parents=True,exist_ok=False)
        methods={name:sha256(ROOT/'scripts'/name) for name in METHODS}
        import shutil
        snapshot=output/'methods';snapshot.mkdir()
        for name,digest in methods.items():
            shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            assert sha256(snapshot/name)==digest
        save(output/'request.json',dict(at=now(),methods_sha256=methods,engine_sha256=sha256(ENGINE),fixtures=[dict(c,geometry=c['geometry'].record()) for c in fixtures()],
                                       physics_fps=240,solver_slop_m=.001,start_overlap_limit_m=.001,collision_and_settling_limit_m=.01,relative_speed_m_s=.1,relative_spin_rad_s=.1))
        rows=[]
        for case in fixtures():
            try:result=run_case(case,output/case['id'])
            except Exception as exc:
                result=dict(id=case['id'],status='failed',error=repr(exc),quality_approved=False,release_approved=False)
                save(output/case['id']/'failure.json',result)
            rows.append(result);print(json.dumps(result),flush=True)
        assert all(sha256(ROOT/'scripts'/n)==sha256(snapshot/n)==h for n,h in methods.items())
        result=dict(schema='strep-cylinder-release-fixture-study-v1',at=now(),status='complete',cases=rows,source_and_copy_current=True,
                    request_sha256=sha256(output/'request.json'),models_sampled=False,production_actor_queried=False,human_reviewed=False,
                    continuous_collision_certified=False,quality_approved=False,release_approved=False)
        save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    study(parser.parse_args().output)
