"""Float32 object GLBs with explicit clock collisions and saved contact audits.

Only declared rigid primitive tracks are exported. Actor snapshots remain
unchanged. Import and native-resource authoring observations remain distinct;
no rendering, physics, complete scene geometry or quality approval is inferred.
"""
import argparse,shutil,subprocess
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts,METHODS as CONTACT_METHODS
from gltf_tools import append_accessor,write_glb,read_glb,accessor
from object_geometry_mesh import triangle_mesh
from strep import ROOT,read,save,sha256,now
from native_engine_clock import clock_wire, check_clock_wire

METHODS=tuple(dict.fromkeys(CONTACT_METHODS+('native_object_asset.py','object_geometry_mesh.py','action_worker_lock.py','godot_native_object_asset.gd','native_engine_clock.py','native_engine_clock.gd')))
POSITION_LIMIT_M=1e-6
BASIS_LIMIT=1e-6


def stored_clock(times):
    source=np.asarray(times,float)
    if source.ndim!=1 or len(source)<2 or not np.isfinite(source).all() or source[0]!=0 or np.any(np.diff(source)<=0):
        raise ValueError('Complete strictly increasing finite object clock required')
    rounded=source.astype('<f4').astype(float)
    if not np.isfinite(rounded).all():raise ValueError('Object clock exceeds Float32 storage')
    clock,mapping=np.unique(rounded,return_inverse=True)
    if len(clock)<2:raise ValueError('Object duration collapses in Float32 storage')
    groups=[dict(stored_time_s=float(t),source_indices=np.flatnonzero(mapping==i).tolist(),
        source_times_s=source[mapping==i].tolist()) for i,t in enumerate(clock) if np.count_nonzero(mapping==i)>1]
    return clock,dict(source_times_s=source.tolist(),stored_times_s=clock.tolist(),source_to_stored_index=mapping.tolist(),
        collision_groups=groups,maximum_timestamp_rounding_s=float(abs(rounded-source).max()),
        policy='Unique Float32 clock; resample source rigid interpolation at each stored time, clamped only at source endpoints. Original audit clocks remain unchanged.')


def export(scene,path):
    if not scene.objects:raise ValueError('At least one declared object required')
    doc=dict(asset=dict(version='2.0',generator='Strep native rigid objects'),scene=0,scenes=[dict(nodes=[])],nodes=[],meshes=[],
        materials=[dict(pbrMetallicRoughness=dict(baseColorFactor=[.5,.5,.5,1],metallicFactor=0,roughnessFactor=.8))],
        buffers=[],bufferViews=[],accessors=[],animations=[dict(name='Strep object motion',channels=[],samplers=[])])
    binary=bytearray();clocks={}
    for name,obj in scene.objects.items():
        original=obj['times'] if len(obj['times'])>1 else np.array([0.,scene.duration])
        times,clocks[name]=stored_clock(original)
        p,r=scene.object_poses(name,np.clip(times,0,scene.duration))
        # Exact native knots retain their declared poses. Slerp endpoint
        # recomposition can otherwise introduce tiny rotations at frozen keys.
        ids=np.searchsorted(obj['times'],times);matched=ids<len(obj['times'])
        matched[matched]=obj['times'][ids[matched]]==times[matched]
        p[matched]=obj['positions'][ids[matched]];r[matched]=obj['rotations'][ids[matched]]
        q=Rotation.from_matrix(r).as_quat()
        for i in range(1,len(q)):
            if q[i]@q[i-1]<0:q[i]*=-1
        vertices,normals,approximation=triangle_mesh(obj['geometry']);vertices=vertices.reshape(-1,3);normals=normals.reshape(-1,3)
        pi=append_accessor(doc,binary,vertices,'VEC3');doc['accessors'][pi].update(min=vertices.astype('<f4').min(0).astype(float).tolist(),max=vertices.astype('<f4').max(0).astype(float).tolist())
        ni=append_accessor(doc,binary,normals,'VEC3');node=len(doc['nodes']);mesh=len(doc['meshes'])
        doc['meshes'].append(dict(primitives=[dict(attributes=dict(POSITION=pi,NORMAL=ni),material=0,mode=4)]))
        doc['nodes'].append(dict(name='Object_'+name,mesh=mesh,translation=p[0].astype('<f4').astype(float).tolist(),
            rotation=q[0].astype('<f4').astype(float).tolist(),extras=dict(strep_object_id=name,strep_geometry=obj['geometry'].record(),strep_preview_mesh=approximation)))
        doc['scenes'][0]['nodes'].append(node);ti=append_accessor(doc,binary,times,'SCALAR');animation=doc['animations'][0]
        for prop,values,kind in [('translation',p,'VEC3'),('rotation',q,'VEC4'),('scale',np.ones((len(p),3)),'VEC3')]:
            index=len(animation['samplers']);animation['samplers'].append(dict(input=ti,output=append_accessor(doc,binary,values,kind),interpolation='LINEAR'))
            animation['channels'].append(dict(sampler=index,target=dict(node=node,path=prop)))
    doc['extras']=dict(strep_source_duration_s=scene.duration,scope='Rigid world-metre object tracks; unchanged actor files and placements are separate. Analytic geometry and inscribed preview mesh are distinct.')
    write_glb(path,doc,binary);return clocks


class ObjectAsset:
    def __init__(self,path):
        self.document,self.binary=read_glb(path);d=self.document
        if d.get('skins') or len(d.get('animations',[]))!=1:raise ValueError('One rigid object animation required')
        self.objects={};self.channels=[];a=d['animations'][0]
        for index,node in enumerate(d['nodes']):
            name=node['extras']['strep_object_id']
            if name in self.objects:raise ValueError('Duplicate object ID')
            tracks={}
            for channel in a['channels']:
                if channel['target']['node']!=index:continue
                prop=channel['target']['path'];s=a['samplers'][channel['sampler']]
                if prop not in ('translation','rotation','scale') or prop in tracks or s.get('interpolation')!='LINEAR':raise ValueError('Complete distinct LINEAR TRS required')
                ia=d['accessors'][s['input']];oa=d['accessors'][s['output']]
                if ia['type']!='SCALAR' or ia['componentType']!=5126 or oa['componentType']!=5126 or oa['type']!=('VEC4' if prop=='rotation' else 'VEC3'):raise ValueError('Float32 TRS storage required')
                times=accessor(d,self.binary,s['input']).reshape(-1).astype(float);values=accessor(d,self.binary,s['output']).astype(float)
                if len(times)<2 or times[0]!=0 or np.any(np.diff(times)<=0) or not np.isfinite(times).all() or len(times)!=len(values) or not np.isfinite(values).all():raise ValueError('Valid strictly increasing stored TRS required')
                if ia['min']!=[float(times.min())] or ia['max']!=[float(times.max())]:raise ValueError('Stored clock bounds differ')
                tracks[prop]=(times,values);self.channels.append(dict(object=name,node_name=node['name'],path=prop,times_s=times.tolist(),values=values.tolist()))
            if set(tracks)!=set(('translation','rotation','scale')) or not np.array_equal(tracks['scale'][1],np.ones_like(tracks['scale'][1])):raise ValueError('Complete rigid unit-scale TRS required')
            if not all(np.array_equal(tracks['translation'][0],tracks[k][0]) for k in tracks):raise ValueError('Shared object TRS clock required')
            if np.any(abs(np.linalg.norm(tracks['rotation'][1],axis=1)-1)>1e-6):raise ValueError('Unit-range stored quaternion required')
            self.objects[name]=tracks
        if len(self.channels)!=len(a['channels']):raise ValueError('Unaccounted object channels')

    def object_poses(self,name,times):
        tracks=self.objects[name];clock,p=tracks['translation'];_,q=tracks['rotation'];t=np.clip(np.asarray(times,float),clock[0],clock[-1])
        native=Rotation.from_quat(q);positions=np.stack([np.interp(t,clock,p[:,i]) for i in range(3)],axis=1)
        rotations=Slerp(clock,native)(t).as_matrix();ids=np.searchsorted(clock,t);matched=clock[ids]==t
        positions[matched]=p[ids[matched]];rotations[matched]=native.as_matrix()[ids[matched]]
        return positions,rotations


def audit(scene,asset,times):
    if set(asset.objects)!=set(scene.objects):raise ValueError('Complete unchanged object population required')
    rows={}
    for name in scene.objects:
        p,r=scene.object_poses(name,times);q,s=asset.object_poses(name,times)
        position=float(np.linalg.norm(q-p,axis=1).max());basis=float(abs(s-r).max())
        rows[name]=dict(samples=len(times),maximum_position_error_m=position,maximum_basis_error=basis,
            passed=bool(position<=POSITION_LIMIT_M and basis<=BASIS_LIMIT))
    contacts,arrays=scene.evaluate(object_poses=asset.object_poses)
    return dict(object_poses=rows,contacts=contacts,sampled_conditions_pass=bool(all(r['passed'] for r in rows.values()) and contacts['passed']),
        position_limit_m=POSITION_LIMIT_M,basis_limit=BASIS_LIMIT,geometry_checked=False,engine_playback_verified=False,
        original_selected=True,quality_approved=False,release_approved=False),arrays


def scene_from_snapshots(output):
    spec=read(output/'source-contacts.json');snapshots=read(output/'result.json')['actor_snapshots']
    for name,entry in snapshots.items():spec['actors'][name]['glb']=str(output/entry['path'])
    return SceneContacts(spec,output)


def run(contacts_path,output):
    contacts_path,output=Path(contacts_path).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh object asset output required')
    with worker_lock(),threadpool_limits(limits=1):
        digest=sha256(contacts_path);scene=SceneContacts(read(contacts_path),contacts_path.parent)
        spec=read(contacts_path)
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        shutil.copyfile(contacts_path,output/'source-contacts.json');snapshots={}
        for i,(name,actor) in enumerate(scene.actors.items()):
            src=(contacts_path.parent/spec['actors'][name]['glb']).resolve()
            dest=output/'input'/f'actor-{i}.glb';dest.parent.mkdir(exist_ok=True);shutil.copyfile(src,dest)
            snapshots[name]=dict(path=dest.relative_to(output).as_posix(),sha256=sha256(dest))
        save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            clocks=export(scene,output/'objects.glb');asset=ObjectAsset(output/'objects.glb')
            _,native=scene.evaluate();times=np.unique(np.concatenate([np.array([0.,scene.duration])]+
                [c[2] for a in scene.actors.values() for c in a['sampler'].channels]+[o['times'] for o in scene.objects.values()]+
                [v for k,v in native.items() if k.endswith('_times_s')]))
            report,arrays=audit(scene,asset,times)
            save(output/'clock-storage.json',clocks);save(output/'asset-audit.json',report);np.savez_compressed(output/'contact-observations.npz',**arrays)
            save(output/'engine-payload.json',dict(channels=asset.channels,duration_s=max(scene.duration,max(v['translation'][0][-1] for v in asset.objects.values())),sample_times_s=times.tolist(),sample_clock=clock_wire(times)))
            scene.check_inputs()
            assert sha256(contacts_path)==sha256(output/'source-contacts.json')==digest
            assert all(sha256(ROOT/'scripts'/n)==sha256(archive/n)==h for n,h in methods.items())
            assert all(sha256(output/s['path'])==s['sha256']==read(contacts_path)['actors'][n]['sha256'] for n,s in snapshots.items())
            result=dict(at=now(),status='complete',source_contacts_sha256=digest,source_actor_inputs_sha256=scene.inputs,actor_snapshots=snapshots,
                actor_bytes_unchanged=True,implementation_sha256=methods,files_sha256={n:sha256(output/n) for n in ('objects.glb','source-contacts.json','clock-storage.json','asset-audit.json','contact-observations.npz','engine-payload.json')},
                samples=len(times),sampled_asset_conditions_pass=report['sampled_conditions_pass'],original_selected=True,quality_approved=False,release_approved=False)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


def run_engine(asset_output,output,engine):
    asset_output,output,engine=[Path(p).resolve() for p in (asset_output,output,engine)]
    if output.exists():raise ValueError('Fresh object engine audit output required')
    with worker_lock(),threadpool_limits(limits=1):
        source_result=read(asset_output/'result.json')
        assert source_result['status']=='complete'
        methods=source_result['implementation_sha256']
        if any(sha256(ROOT/'scripts'/n)!=h or sha256(asset_output/'implementation'/n)!=h for n,h in methods.items()):
            raise ValueError('Object asset engine audit requires the recorded unchanged implementation')
        for n,h in source_result['files_sha256'].items():assert sha256(asset_output/n)==h
        scene=scene_from_snapshots(asset_output);asset=ObjectAsset(asset_output/'objects.glb');payload=read(asset_output/'engine-payload.json');times=np.asarray(payload['sample_times_s'])
        check_clock_wire(payload['sample_clock'], times)
        output.mkdir(parents=True);project=output/'project';project.mkdir()
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep rigid object asset audit"\n')
        script=ROOT/'scripts/godot_native_object_asset.gd';shutil.copyfile(script,project/'audit.gd')
        clock_script=ROOT/'scripts/native_engine_clock.gd';shutil.copyfile(clock_script,project/clock_script.name)
        request=dict(asset_path=str(asset_output/'objects.glb'),payload=payload,resource_path=str(output/'native-animation.res'))
        save(output/'request.json',request);save(output/'pipeline.json',dict(status='processing',stage='headless-object-import'))
        bindings=dict(engine_sha256=sha256(engine),script_sha256=sha256(script),clock_script_sha256=sha256(clock_script),request_sha256=sha256(output/'request.json'),source_result_sha256=sha256(asset_output/'result.json'))
        try:
            with (output/'engine.log').open('w') as log:
                child=subprocess.run([str(engine),'--headless','--path',str(project),'--script','audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if child.returncode:raise ValueError('Object asset import failed; inspect retained engine.log')
            raw=read(output/'engine-output.json');reports={};observations={}
            for mode in ('default-import','native-authoring'):
                records=raw[mode];assert set(records)==set(scene.objects)
                measured={}
                for name in scene.objects:
                    rows=records[name];assert len(rows)==len(times)
                    assert np.allclose([r['time_s'] for r in rows],times,rtol=0,atol=1e-14)
                    p=np.asarray([r['translation_m'] for r in rows]);q=np.asarray([r['rotation_xyzw'] for r in rows]);assert np.isfinite(p).all() and np.isfinite(q).all()
                    assert np.all(abs(np.linalg.norm(q,axis=1)-1)<1e-6)
                    measured[name]=(p,Rotation.from_quat(q).as_matrix());observations[mode+'_'+name+'_positions']=p;observations[mode+'_'+name+'_rotations']=measured[name][1]
                class Observed:
                    objects=measured
                    def object_poses(self,name,clock):
                        ids=np.searchsorted(times,clock)
                        if np.any(ids>=len(times)) or not np.array_equal(times[ids],clock):raise ValueError('Missing exact engine contact clock')
                        p,r=self.objects[name];return p[ids],r[ids]
                report,contact_arrays=audit(scene,Observed(),times)
                for name in scene.objects:
                    p,r=asset.object_poses(name,times);q,s=measured[name]
                    report['object_poses'][name].update(maximum_saved_asset_position_error_m=float(np.linalg.norm(q-p,axis=1).max()),maximum_saved_asset_basis_error=float(abs(s-r).max()))
                report.update(manual_authoring_seek=mode=='native-authoring',real_time_playback_verified=False,actor_engine_import_checked=False)
                reports[mode]=report;save(output/(mode+'-audit.json'),report)
                observations.update({mode+'_'+k:v for k,v in contact_arrays.items()})
            np.savez_compressed(output/'observations.npz',**observations)
            assert sha256(script)==sha256(project/'audit.gd')==bindings['script_sha256'] and sha256(engine)==bindings['engine_sha256']
            assert sha256(clock_script)==sha256(project/clock_script.name)==bindings['clock_script_sha256']
            assert sha256(output/'request.json')==bindings['request_sha256'] and sha256(asset_output/'result.json')==bindings['source_result_sha256']
            for n,h in source_result['files_sha256'].items():assert sha256(asset_output/n)==h
            scene.check_inputs()
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(asset_output/'implementation'/n)!=h for n,h in methods.items()):
                raise ValueError('Object asset engine implementation changed')
            result=dict(at=now(),status='complete',bindings=bindings,files_sha256={n:sha256(output/n) for n in ('engine-output.json','engine.log','observations.npz','native-animation.res','default-import-audit.json','native-authoring-audit.json')},
                implementation_sha256=methods,
                modes={k:v['sampled_conditions_pass'] for k,v in reports.items()},engine=raw['engine'],samples=len(times),geometry_checked=False,
                gpu_render_checked=False,physics_checked=False,original_selected=True,quality_approved=False,release_approved=False)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('export');p.add_argument('contacts',type=Path);p.add_argument('output',type=Path)
    p=sub.add_parser('engine');p.add_argument('asset_output',type=Path);p.add_argument('output',type=Path);p.add_argument('--engine',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='export':run(args.contacts,args.output)
    else:run_engine(args.asset_output,args.output,args.engine)
