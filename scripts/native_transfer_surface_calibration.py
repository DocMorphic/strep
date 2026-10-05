"""Whole-clip transfer calibration with authored normals and decoded geometry.

Original targets, source motion caps, mesh topology and clips stay protected.
Winding-derived surface conditions are not anatomical or quality approval.
"""
import argparse
import copy
from pathlib import Path
import shutil

import numpy as np
from threadpoolctl import threadpool_limits

import native_transfer_calibration as base
import native_transfer_scene as bridge
import native_rig_transfer as transfer
import native_surface_contact as surface
import native_scene_geometry as geometry
from native_contact_norms import ContactNorms
from native_scene_contacts import SceneContacts,fields,scalar
from action_worker_lock import worker_lock
from strep import read,save,sha256,now

SCHEMA='strep-native-transfer-surface-calibration-v1'
SCRIPT_ROOT=Path(__file__).resolve().parent
GEOMETRY_SCALAR_LIMIT=33554432
METHODS=tuple(dict.fromkeys(base.METHODS+surface.METHODS+(
    'native_transfer_surface_calibration.py','native_contact_norms.py','native_scene_norms.py',
    'native_surface_lift.py','native_scene_conic.py','native_scene_fit.py','native_scene_edit.py',
    'native_scene_geometry.py')))
require=base.require


def validate_recipe(recipe):
    fields(recipe,('schema','comparison','actors','search','surface_policy','geometry_policy'),'surface calibration recipe')
    require(recipe['schema']==SCHEMA,'Explicit surface calibration schema required')
    for name in ('comparison','surface_policy','geometry_policy'):
        fields(recipe[name],('path','sha256'),name+' binding')
        require(isinstance(recipe[name]['path'],str) and bool(recipe[name]['path']),'Explicit bound input path required')


class SurfaceProblem(base.CalibrationProblem):
    def __init__(self,folder,recipe,surface_policy,geometry_policy):
        validate_recipe(recipe)
        permissions={k:copy.deepcopy(recipe[k]) for k in ('comparison','actors','search')};permissions['schema']=base.SCHEMA
        super().__init__(folder,permissions)
        digest=sha256(self.folder/'contacts.json')
        self.surface_policy=copy.deepcopy(surface_policy);self.geometry_policy=copy.deepcopy(geometry_policy)
        surface.policy_for(self.surface_policy,self.scene,digest)
        geometry_times,_,_=geometry.policy_for(self.geometry_policy,self.scene,digest)
        scalars=len(geometry_times)*(1+5*len(self.scene.objects)*sum(len(geometry.faces_for(a['rig'])[0]) for a in self.scene.actors.values()))
        require(scalars<=GEOMETRY_SCALAR_LIMIT,'Complete geometry observations exceed fixed 256 MiB scalar budget; no truncation')
        self.rows=[dict(entry=entry,times=clock) for clock,(_,entry) in zip(self.clocks,self.fixed_points.values())]
        # Count the full proposed surface population before any normal queries.
        queries=sum(len(row['times'])*(2 if row['entry']['authored']['target']['space']=='actor' else 1) for row in self.rows)
        points=sum(len(row['times'])*(len(row['entry']['ids']) if row['entry']['authored']['reduction']=='individual' else 1) for row in self.rows)
        require(queries<=self.surface_policy['maximum_actor_pose_queries'] and 3*points<=100000,
            'Complete surface proposal exceeds its fixed budget; no partial normal rows')
        self.normal_model=ContactNorms(self,self.surface_policy,digest,maximum_rows=100000)

    def measure(self,value,worlds=None,*,contact_fraction=1.):
        worlds=self.worlds(value) if worlds is None else worlds
        residual,bounds=super().measure(value,worlds,contact_fraction=contact_fraction)
        rows,gaps,identity=self.normal_model.sample(worlds)
        length=np.linalg.norm(rows.vectors,axis=1)
        orientation=(length-rows.caps*contact_fraction)/rows.scales
        side=-gaps/.005
        bounds['surface']=dict(normal_rows=len(length),actor_pose_queries=identity['actor_pose_queries'],
            maximum_opposition_error_degrees=float(np.rad2deg(2*np.arcsin(np.clip(length/2,0,1))).max()),
            minimum_facing_projection_m=float(gaps.min()-self.normal_model.limits['backface_allowance_m']),
            common_clock_surface_conditions_pass=bool(np.all(length<=rows.caps) and np.all(gaps>=0)))
        return np.r_[residual,orientation,side],bounds


def rebound(policy,digest):
    result=copy.deepcopy(policy);result['contacts_sha256']=digest;return result


def audits(problem,spec,output):
    scene=SceneContacts(spec,output);digest=sha256(output/'contacts.json')
    comparison,points,_,frames=bridge.evaluate(problem.scene,scene)
    worlds={n:np.array([a['sampler'].sample(float(t)) for t in problem.times]) for n,a in scene.actors.items()}
    controls=np.asarray(read(output/'search.json')['controls'],float)
    residual,bounds=problem.measure(controls,worlds)
    sp=rebound(problem.surface_policy,digest);gp=rebound(problem.geometry_policy,digest)
    orientation,normals=surface.evaluate(scene,sp,digest)
    mesh,triangles=geometry.evaluate(scene,gp,digest)
    return comparison,points,frames,residual,bounds,sp,gp,orientation,normals,mesh,triangles


def outcome(status,comparison=None,bounds=None,residual=None,orientation=None,mesh=None):
    result=base.outcome(status,comparison,bounds,residual);result['schema']=SCHEMA
    done=status=='complete'
    result.update(surface_common_clock_pass=bool(done and bounds['surface']['common_clock_surface_conditions_pass']),
        surface_contact_samples_pass=bool(done and orientation['surface_contacts_pass']),
        geometry_samples_pass=bool(done and mesh['sampled_conditions_pass']),
        sampled_authoring_conditions_pass=bool(done and result['sampled_calibration_conditions_pass']
            and bounds['surface']['common_clock_surface_conditions_pass'] and orientation['surface_contacts_pass'] and mesh['sampled_conditions_pass']),
        collision_verified=False,continuous_collision_certified=False,anatomical_reviewed=False,
        scope='Separate whole-clip reference-profile candidate. Exact authored targets/times/limits and source-rate caps retained. '
            'Complete common-clock winding normals, decoded full-mesh actor/object/partner/plane samples. '
            'No self-collision, continuous-time, dynamics, engine, anatomical or human quality approval.')
    return result


def verified_problem(output):
    recipe=read(output/'recipe.json');validate_recipe(recipe)
    for name in ('surface_policy','geometry_policy'):
        require(sha256(output/('input-'+name+'.json'))==recipe[name]['sha256'],'Original surface/geometry policy binding changed')
    return SurfaceProblem(output/'comparison',recipe,read(output/'input-surface_policy.json'),read(output/'input-geometry_policy.json'))


def verify(output,expected_result_sha256=None):
    output=Path(output).resolve();result=read(output/'result.json')
    if expected_result_sha256 is not None:require(sha256(output/'result.json')==expected_result_sha256,'Selected surface calibration changed')
    require(result.get('status') in ('complete','incompatible_with_joint_bound'),'Completed surface calibration required')
    require(result.get('files_sha256')==base.payload_hashes(output),'Complete surface calibration payload changed')
    request=read(output/'request.json')
    fields(request,('schema','at','recipe_sha256','implementation_sha256'),'surface calibration request')
    require(request['schema']==SCHEMA and request['recipe_sha256']==sha256(output/'recipe.json')
        and set(request['implementation_sha256'])==set(METHODS),'Surface calibration request/method binding changed')
    for name,digest in request['implementation_sha256'].items():
        require(sha256(SCRIPT_ROOT/name)==digest==sha256(output/'implementation'/name),'Surface calibration method changed')
    problem=verified_problem(output);preflight=problem.preflight()
    require(read(output/'preflight.json')==preflight,'Surface calibration reach certificate changed')
    if result['status']=='incompatible_with_joint_bound':
        require(preflight['status']=='incompatible_with_joint_bound' and not any((output/n).exists() for n in ('search.json','contacts.json'))
            and not list(output.glob('transfer-*')),'Incompatible surface calibration must not export')
        expected=outcome(result['status'])
    else:
        require(preflight['status']=='not_ruled_out','Incompatible surface calibration was fitted')
        search=read(output/'search.json');controls=np.asarray(search['controls'],float);problem.decode(controls)
        require(search.get('quality_approved') is False and search['search_contact_fraction']==base.SEARCH_CONTACT_FRACTION
            and type(search['objective_calls']) is int and search['objective_calls']==len(search['history'])
            and 1<=search['objective_calls']<=problem.search['calls']
            and len(search['starts'])<=problem.search['starts']
            and sum(s['evaluations'] for s in search['starts'])<=problem.search['evaluations'],'Surface calibration search budget changed')
        scalar(search['elapsed_s'],0,1e12,'search elapsed time')
        merit,_=problem.measure(controls,contact_fraction=base.SEARCH_CONTACT_FRACTION);positive=np.maximum(merit,0)
        require(np.allclose(search['selected_score'],[positive.max(initial=0),positive@positive],atol=1e-10,rtol=1e-10),'Surface calibration selected score changed')
        spec=base.candidate_spec(problem,output,problem.profiles(controls))
        require(spec==read(output/'contacts.json'),'Protected surface calibration scene intent changed')
        comparison,points,frames,residual,bounds,sp,gp,orientation,normals,mesh,triangles=audits(problem,spec,output)
        for name,value in [('contact-comparison',comparison),('decoded-bounds',bounds),('surface-policy',sp),('geometry-policy',gp),
            ('surface-audit',orientation),('geometry-audit',mesh)]:require(read(output/(name+'.json'))==value,'Surface calibration '+name+' changed')
        frame=read(output/'frame-audit.json')
        canonical=lambda v:{Path(*Path(p).parts[-2:]).as_posix():h for p,h in v.items()}
        require({k:v for k,v in frame.items() if k!='inputs_sha256'}=={k:v for k,v in frames.items() if k!='inputs_sha256'}
            and len(frame['inputs_sha256'])==len(frames['inputs_sha256']) and canonical(frame['inputs_sha256'])==canonical(frames['inputs_sha256']),
            'Surface calibration frame bindings changed')
        for name,arrays in [('observations',points),('surface-observations',normals),('geometry-observations',triangles)]:
            with np.load(output/(name+'.npz'),allow_pickle=False) as stored:
                require(set(stored.files)==set(arrays) and all(stored[k].dtype==v.dtype and stored[k].shape==v.shape
                    and stored[k].tobytes()==v.tobytes() for k,v in arrays.items()),'Complete surface calibration '+name+' changed')
        expected=outcome('complete',comparison,bounds,residual,orientation,mesh)
    require(set(result)==set(expected)|{'files_sha256'} and all(type(result[k]) is type(v) and result[k]==v for k,v in expected.items()),
        'Typed surface calibration scope/results disagree with replay')
    return result


def run(recipe_path,output):
    recipe_path=Path(recipe_path).resolve();output=Path(output).resolve();require(not output.exists(),'Fresh surface calibration output required')
    recipe=read(recipe_path);validate_recipe(recipe)
    paths={name:(recipe_path.parent/recipe[name]['path']).resolve() for name in ('comparison','surface_policy','geometry_policy')}
    require(not output.is_relative_to(paths['comparison']),'Output cannot be inside comparison')
    for name in ('surface_policy','geometry_policy'):require(sha256(paths[name])==recipe[name]['sha256'],'Bound surface/geometry input changed')
    SurfaceProblem(paths['comparison'],recipe,read(paths['surface_policy']),read(paths['geometry_policy']))
    methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS};inputs={p:sha256(p) for p in (recipe_path,paths['surface_policy'],paths['geometry_policy'])}
    with worker_lock(),threadpool_limits(limits=1):
        output.mkdir(parents=True);save(output/'pipeline.json',dict(status='processing',original_selected=True,quality_approved=False))
        try:
            archive=output/'implementation';archive.mkdir()
            for name in METHODS:shutil.copyfile(SCRIPT_ROOT/name,archive/name)
            shutil.copytree(paths['comparison'],output/'comparison');shutil.copyfile(recipe_path,output/'recipe.json')
            for name in ('surface_policy','geometry_policy'):shutil.copyfile(paths[name],output/('input-'+name+'.json'))
            save(output/'request.json',dict(schema=SCHEMA,at=now(),recipe_sha256=inputs[recipe_path],implementation_sha256=methods))
            problem=verified_problem(output);preflight=problem.preflight();save(output/'preflight.json',preflight)
            if preflight['status']=='not_ruled_out':controls,search=base.fit(problem);save(output/'search.json',search)
            else:
                result=outcome('incompatible_with_joint_bound');result['files_sha256']=base.payload_hashes(output);save(output/'result.json',result)
                verify(output,sha256(output/'result.json'));save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise
    # Transfer owns its own OS worker lock; do not nest locks.
    try:
        profiles=problem.profiles(controls)
        for name,profile in profiles.items():
            bound=problem.actors[name]['inputs'];folder=bound[0];path=output/(name+'-profile.json');save(path,profile)
            transfer.export(folder/'source.glb',folder/'source-profile.json',folder/'target.glb',path,
                bound[1]['source_animation_index'],output/('transfer-'+name),bound[1]['sampling_rate_hz'])
        with worker_lock(),threadpool_limits(limits=1):
            spec=base.candidate_spec(problem,output,profiles);save(output/'contacts.json',spec)
            comparison,points,frames,residual,bounds,sp,gp,orientation,normals,mesh,triangles=audits(problem,spec,output)
            for name,value in [('contact-comparison',comparison),('decoded-bounds',bounds),('frame-audit',frames),('surface-policy',sp),
                ('geometry-policy',gp),('surface-audit',orientation),('geometry-audit',mesh)]:save(output/(name+'.json'),value)
            for name,arrays in [('observations',points),('surface-observations',normals),('geometry-observations',triangles)]:np.savez_compressed(output/(name+'.npz'),**arrays)
            require(all(sha256(p)==h for p,h in inputs.items()),'Surface calibration source changed')
            bridge.verify(paths['comparison'],recipe['comparison']['sha256'])
            result=outcome('complete',comparison,bounds,residual,orientation,mesh);result['files_sha256']=base.payload_hashes(output)
            save(output/'result.json',result);verify(output,sha256(output/'result.json'))
            save(output/'pipeline.json',dict(status='complete',original_selected=True,quality_approved=False));return result
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(run(args.recipe,args.output))
