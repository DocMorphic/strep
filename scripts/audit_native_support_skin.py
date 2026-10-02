"""Reconstruct actual imported support skin using bound engine bone samples."""
import argparse
from pathlib import Path
import shutil
import subprocess
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_leg_floor import foot_region
from native_support_skin import NativeSupportSkin as BoundSkin
from native_engine_clock import clock_echo_matches
from native_support_imported_surfaces import ImportedSupportSurfaces
from run_native_support_engine import unchanged,bind_study

SOURCE_DIR=Path(__file__).resolve().parent


def check_skin(case,observed,poses,rig,sampler,rows):
    if observed['id']!=case['id'] or observed['path']!=case['path']:
        raise ValueError('Matching imported support surfaces required')
    if poses['id']!=case['id'] or poses['path']!=case['path'] or len(poses['frames'])!=case['frames']:
        raise ValueError('Matching bound engine bone observations required')
    imported=ImportedSupportSurfaces(rig,observed['surfaces'])
    data_check=imported.data_check
    skin=BoundSkin(rig);regions=[foot_region(skin,rig.parents,r['chain'][-1]) for r in rows]
    height_records=[dict(id=r['id'],times_s=[],lowest_heights_m=[]) for r in rows];errors=[]
    if len(case['sample_times_s'])!=case['frames']:raise ValueError('Support skin clock population differs')
    for time,frame in zip(case['sample_times_s'],poses['frames']):
        if not clock_echo_matches(time,frame['requested_time_s']) or not clock_echo_matches(time,frame['actual_time_s']):
            raise ValueError('Support skin bone clock differs')
        actual=imported.vertices(frame['bones'],poses['bone_names']);source=rig.vertices(sampler.sample(time))
        errors.append(dict(time_s=time,maximum_vertex_distance_m=float(np.linalg.norm(actual-source,axis=1).max())))
        for r,region,record in zip(rows,regions,height_records):
            if r['stance_s'][0]<=time<=r['stance_s'][1]:
                record['times_s'].append(time);record['lowest_heights_m'].append(float((actual[region]@r['up']+r['offset']).min()))
    supports=[]
    for r,record in zip(rows,height_records):
        h=np.asarray(record['lowest_heights_m'])
        if not len(h):raise ValueError('Missing authored support skin samples')
        supports.append(dict(id=r['id'],samples=len(h),minimum_height_m=float(h.min()),maximum_lowest_height_m=float(h.max()),
            imported_skin_support_pass=bool(h.min()>=-1e-8 and h.max()<=r['maximum_height'])))
    return dict(id=case['id'],skin_data_check=data_check,surface_checks=imported.surface_checks,samples=len(errors),
        maximum_vertex_distance_m=max(e['maximum_vertex_distance_m'] for e in errors),supports=supports,
        imported_skin_support_pass=all(s['imported_skin_support_pass'] for s in supports)),errors,height_records


def run(engine_audit,output,*,engine=None):
    engine_audit,output=Path(engine_audit).resolve(),Path(output).resolve()
    if output.exists() or output.parent!=ROOT/'reports':raise ValueError('Fresh immediate reports output required')
    eq,er=read(engine_audit/'request.json'),read(engine_audit/'result.json')
    if read(engine_audit/'pipeline.json').get('status')!='complete' or er.get('status')!='complete' or not er.get('engine_pose_pass') or not eq.get('native_tracks') or not eq.get('authoring_seek'):
        raise ValueError('Passing completed native support engine audit required')
    files=dict(eq['inputs'])
    def bind(path,digest):
        name=str(Path(path).resolve())
        if name in files and files[name]!=digest:raise ValueError('Conflicting imported skin evidence')
        files[name]=digest
    for name,digest in er['outputs'].items():
        path=(engine_audit/name).resolve()
        if not path.is_relative_to(engine_audit):raise ValueError('Escaping imported skin evidence')
        bind(path,digest)
    for name in ('request.json','result.json','pipeline.json'):bind(engine_audit/name,sha256(engine_audit/name))
    unchanged(files)
    study=Path(eq['study']);request,fit,study_files=bind_study(study)
    if any(files.get(p)!=h for p,h in study_files.items()):raise ValueError('Unbound support study')
    if [c['id'] for c in eq['cases']]!=['input','trial-0','trial-1','trial-2','trial-3']:
        raise ValueError('Input and four support proposals required')
    engine=Path(engine).resolve() if engine else ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    if files.get(str(engine))!=sha256(engine):raise ValueError('Use the bound engine executable')
    bone_data=read(engine_audit/'engine-output.json')
    if len(bone_data['cases'])!=5:raise ValueError('Missing bound bone cases')
    names=('audit_native_support_skin.py','native_support_skin_data.gd','imported_skin_evidence.py','imported_skin_reconstruction.py',
        'run_native_support_engine.py','native_engine_clock.py','native_support_clock.py','native_support_spec.py','native_leg_floor.py',
        'paired_approach_basis.py','contact_rate_path.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','strep.py',
        'elbow_swivel.py','paired_temporal_neighbor.py','paired_guarded_temporal.py','two_bone_waypoint.py','contact_locked_native.py','timed_rotation_edit.py','native_support_skin.py','native_support_imported_surfaces.py')
    methods={SOURCE_DIR/n:sha256(SOURCE_DIR/n) for n in names}
    output.mkdir();archive=output/'implementation';archive.mkdir();project=output/'project';project.mkdir()
    for p,h in methods.items():target=archive/p.name;shutil.copyfile(p,target);bind(target,h)
    shutil.copyfile(SOURCE_DIR/'native_support_skin_data.gd',project/'audit.gd');bind(project/'audit.gd',methods[SOURCE_DIR/'native_support_skin_data.gd'])
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep imported support skin"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
    save(output/'request.json',dict(at=now(),engine_audit=str(engine_audit),inputs=files,cases=eq['cases'],
        scope='Imported positions, unrenormalized weights and bind matrices combined with bound engine bone samples; CPU reconstruction, not GPU rendering'))
    save(output/'pipeline.json',dict(status='processing'))
    try:
        unchanged(files)
        with (output/'engine.log').open('w',encoding='utf8') as log:
            process=subprocess.run([str(engine),'--headless','--path',str(project),'--script','audit.gd','--',str(output/'request.json'),str(output/'skin-data.json')],
                stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if process.returncode:raise ValueError('Godot skin import failed; retained engine.log')
        observed=read(output/'skin-data.json')
        if observed['engine']!=bone_data['engine'] or len(observed['cases'])!=5:raise ValueError('Skin engine/case population differs')
        original=RigAsset.load(study/'input.glb');s=NativeSupportSampler(original.document,original.binary,0)
        _,rows=validate(request['spec'],original,s,sha256(study/'input.glb'));checks=[]
        for case,surface,poses in zip(eq['cases'],observed['cases'],bone_data['cases']):
            if files.get(str(Path(case['path']).resolve()))!=sha256(case['path']):raise ValueError('Unbound skin clip')
            rig=RigAsset.load(case['path']);sampler=NativeSupportSampler(rig.document,rig.binary,0)
            check,errors,heights=check_skin(case,surface,poses,rig,sampler,rows);checks.append(check)
            save(output/f"{case['id']}-vertex-errors.json",errors);save(output/f"{case['id']}-support.json",heights)
        unchanged(files)
        if any(sha256(p)!=h for p,h in methods.items()):raise ValueError('Support skin method changed')
        passed=all(c['skin_data_check']['passed'] for c in checks)
        save(output/'verification.json',dict(at=now(),engine=observed['engine'],checks=checks,imported_data_pass=passed,
            scope='Actual imported skin data, correspondence and sampled CPU reconstruction with observed engine bones. No GPU, continuous collision, stationary sole, force, derivative-rate or human-quality certification.',
            quality_approved=False,gpu_render_verified=False,selected_for_studio=False))
        save(output/'result.json',dict(at=now(),status='complete',imported_data_pass=passed,
            outputs={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file() and p.name!='pipeline.json'},quality_approved=False))
        save(output/'pipeline.json',dict(status='complete',imported_data_pass=passed))
        print(checks,flush=True);return passed
    except Exception as error:
        save(output/'pipeline.json',dict(status='failed',reason=str(error)));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('engine_audit',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--engine',type=Path)
    args=parser.parse_args()
    if not run(args.engine_audit,args.output,engine=args.engine):raise SystemExit(2)
