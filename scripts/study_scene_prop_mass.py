"""Matched current-SDK mass response; source motion and contact intent are fixed.

Reports pose sensitivity, never certifies lifting feasibility or human strength.
Requires separately acquired source assets and the pinned headless engine.
"""
import argparse,copy,json,shutil,subprocess,zipfile
from pathlib import Path
import numpy as np
from action_worker_lock import worker_lock
from object_release import ENGINE
from prop_runtime_collision import verify_actual
from scene_prop_runtime import package,GDS
from scene_prop_physics_timing import first_tick
from strep import ROOT,read,save,sha256,offline_environment,now

AUDIT='godot_scene_prop_mass_audit.gd'
METHODS=tuple(dict.fromkeys(GDS+(AUDIT,'godot_native_scene_observations.gd','study_scene_prop_mass.py','scene_prop_runtime.py','scene_prop_ownership.py','scene_prop_physics_timing.py','prop_runtime_collision.py','scene_collision_profile.py','action_worker_lock.py','strep.py')))
ENGINE_SHA256='c8f0a6bc45a19b33541501e57f6f7cd972ab18453743266339d495cbbe846643'


def require(value,message):
    if not value:raise ValueError(message)


def compare_runs(first,second,prop,masses):
    """Complete held-pose/actor response comparison on matched actual clocks."""
    require(len(masses)==2 and all(type(m) in (int,float) and np.isfinite(m) and .001<=m<=10000 for m in masses) and masses[0]!=masses[1],'Two distinct bounded masses required')
    for run,mass in zip((first,second),masses):
        require(run['faults']==[] and run['quality_approved'] is False and run['release_approved'] is False,'Successful unapproved engine audit required')
        actual_mass=run['bodies'][prop]['mass_kg']
        require(type(actual_mass) in (int,float) and actual_mass==mass and run['bodies'][prop]['continuous_cd'] is True,'Actual selected body mass/CCD required')
        require(type(run['physics_fps']) is int and run['physics_fps'] in (60,120,240)
            and type(run['last_tick']) is int and 2<=run['last_tick']<=14400
            and len(run['records'])==run['last_tick']+1,'Complete bounded native record population required')
    require(first['engine']==second['engine'] and first['collision_settings']==second['collision_settings']
            and first['gravity_m_s2']==second['gravity_m_s2'] and first['gravity_direction']==second['gravity_direction']
            and first['physics_fps']==second['physics_fps'] and first['last_tick']==second['last_tick'],'Matched engine and gravity/settings required')
    left,right=first['records'],second['records']
    require(len(left)==len(right) and len(left)>=3,'Complete matched record population required')
    held=[];prop_error=0.;actor_error=0.;inertia_ratio=[];native_weights=[[],[]]
    for i,(a,b) in enumerate(zip(left,right)):
        require(a['tick']==b['tick']==i and a['session']==b['session']==0 and a['transport']==b['transport']=='live'
            and a['source_time_s']==b['source_time_s'] and a['modes']==b['modes'] and a['members']==b['members'],'Complete identical live clock/ownership required')
        require(a['scene']['actors'] and set(a['scene']['actors'])==set(b['scene']['actors']) and set(a['props'])==set(b['props']),'Matched actors/props required')
        if a['modes'][prop]!='held':continue
        pa=np.asarray(a['props'][prop]['pose'],dtype=float);pb=np.asarray(b['props'][prop]['pose'],dtype=float)
        require(pa.shape==pb.shape==(4,4) and np.isfinite(pa).all() and np.isfinite(pb).all(),'Finite complete held poses required')
        prop_error=max(prop_error,float(abs(pa-pb).max()))
        for index,row in enumerate((a,b)):
            physical=row['props'][prop];g=np.asarray(physical['gravity'],dtype=float);inverse=physical['inverse_mass']
            require(g.shape==(3,) and np.isfinite(g).all() and type(inverse) in (int,float)
                and np.isfinite(inverse) and inverse>0 and abs(inverse-1/masses[index])<=max(1e-10,abs(inverse)*1e-6),'Actual finite body gravity and inverse mass required')
            native_weights[index].append(float(masses[index]*np.linalg.norm(g)))
        for name in a['scene']['actors']:
            av=np.asarray(a['scene']['actors'][name]['bones'],dtype=float);bv=np.asarray(b['scene']['actors'][name]['bones'],dtype=float)
            require(av.shape==bv.shape and av.ndim==3 and av.shape[1:]==(4,3) and len(av)>0 and np.isfinite(av).all() and np.isfinite(bv).all(),'Complete finite actual bone population required')
            actor_error=max(actor_error,float(abs(av-bv).max()))
        held.append(i)
    require(held,'Actual held records required')
    ia=np.asarray(first['bodies'][prop]['inertia_diagonal'],dtype=float);ib=np.asarray(second['bodies'][prop]['inertia_diagonal'],dtype=float)
    require(ia.shape==ib.shape==(3,) and np.isfinite(ia).all() and np.isfinite(ib).all() and (ia>0).all() and (ib>0).all(),'Complete positive native inertia required')
    inertia_ratio=(ib/ia).tolist()
    gravity=float(first['gravity_m_s2']);direction=np.asarray(first['gravity_direction'],dtype=float)
    require(np.isfinite(gravity) and gravity>=0 and direction.shape==(3,) and np.isfinite(direction).all(),'Recorded finite gravity required')
    weights=[float(m*gravity*np.linalg.norm(direction)) for m in masses]
    return dict(schema='strep-scene-prop-mass-response-v1',records=len(left),held_records=len(held),held_ticks=held,
        prop=prop,masses_kg=list(masses),native_inertia_ratios=inertia_ratio,gravity_weight_N=weights,
        held_body_gravity_weight_N=[dict(minimum=min(v),maximum=max(v)) for v in native_weights],
        held_prop_max_component_difference=prop_error,held_actor_max_component_difference=actor_error,
        measured_held_pose_mass_response=prop_error>0 or actor_error>0,
        scope='Matched fixed authored motion while held. Gravity weight is not an actuator-force, balance, grip-capacity, liftability, animation-quality or human-strength certificate.',
        quality_approved=False,release_approved=False)


def study(source,request_path,output,prop,masses):
    source=Path(source).resolve();request_path=Path(request_path).resolve();output=Path(output).resolve()
    require(output.is_relative_to((ROOT/'reports').resolve()) and not output.exists(),'Fresh ignored report folder required')
    author=read(request_path);require(prop in author['physics'],'Explicit physical prop required')
    require(len(masses)==2 and all(type(m) in (int,float) and np.isfinite(m) and .001<=m<=10000 for m in masses) and masses[0]!=masses[1],'Two distinct bounded masses required')
    require(sha256(ENGINE)==ENGINE_SHA256,'Pinned engine required')
    bindings={str(source):sha256(source),str(request_path):sha256(request_path)}
    output.mkdir();save(output/'pipeline.json',dict(status='preparing',at=now(),quality_approved=False,release_approved=False))
    methods=output/'methods';methods.mkdir();hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS}
    for n in hashes:shutil.copyfile(ROOT/'scripts'/n,methods/n)
    save(output/'protocol.json',dict(source_bindings=bindings,methods_sha256=hashes,prop=prop,masses_kg=list(masses),engine_sha256=ENGINE_SHA256,quality_approved=False,release_approved=False))
    try:
        results=[]
        for index,mass in enumerate(masses):
            case=output/f'case-{index}';case.mkdir();request=copy.deepcopy(author);request['physics'][prop]['mass_kg']=mass
            path=case/'request.json';save(path,request);pack=package(source,path,case/'runtime');project=case/'runtime/project'
            for n in (AUDIT,'godot_native_scene_observations.gd'):shutil.copyfile(methods/n,project/'ownership-v1'/n)
            place=np.eye(4);place[1,3]=2
            compiled=read(project/'ownership-v1/prop-runtime.json');source_times=np.frombuffer(bytes.fromhex(compiled['ownership']['clock']['bytes_hex']),dtype='<f8')
            last_tick=first_tick(float(source_times[-1]),author['physics_fps']);require(2<=last_tick<=14400,'Complete finite mass study exceeds explicit tick budget; no truncation')
            native=case/'engine-request.json';raw=case/'engine.json';save(native,dict(asset_folder=str(project),config=compiled,placement=place.tolist(),last_tick=last_tick))
            with worker_lock(),(case/'engine.log').open('w',encoding='utf8') as log:
                run=subprocess.run([str(ENGINE),'--headless','--path',str(project),'--fixed-fps',str(author['physics_fps']),'--script','ownership-v1/'+AUDIT,'--',str(native),str(raw)],stdout=log,stderr=subprocess.STDOUT,timeout=90,env=offline_environment())
            require(run.returncode==0,'Native mass audit failed; inspect engine.log')
            actual=read(raw)
            if 'collision_profile' in request:verify_actual(read(project/'ownership-v1/prop-runtime.json')['collision_profile'],actual['collision_settings'],author['physics_fps'])
            with zipfile.ZipFile(case/'runtime/prop-runtime-assets.zip') as z:
                require(all(z.read(n)==(project/n).read_bytes() for n in pack['files_sha256']),'Original complete packaged members changed')
            results.append(actual)
        measured=compare_runs(*results,prop,masses)
        require(all(sha256(ROOT/'scripts'/n)==sha256(methods/n)==h for n,h in hashes.items()),'Methods changed during study')
        require(all(sha256(Path(p))==h for p,h in bindings.items()),'Original inputs changed')
        result=dict(status='complete',at=now(),measurement=measured,protocol_sha256=sha256(output/'protocol.json'),raw_sha256=[sha256(output/f'case-{i}/engine.json') for i in range(2)],quality_approved=False,release_approved=False)
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=repr(exc),at=now(),quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('request');parser.add_argument('output');parser.add_argument('--prop',required=True);parser.add_argument('--masses',type=float,nargs=2,required=True);args=parser.parse_args()
    print(json.dumps(study(args.source,args.request,args.output,args.prop,args.masses)))
