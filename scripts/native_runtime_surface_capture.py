"""Seal and read compact CPU surfaces from complete native runtime captures.

Preserves captured clocks, raw skin weights and observed mesh-world placement.
Rigid object queries explicitly report the projection of Float32 bases onto
proper rotations. This reference-based format does not certify animation,
continuous collision, physics, GPU buffers or the configured mode of another
export. Callers must pin the returned receipt digest.
"""
import argparse, copy, gc, shutil, zipfile
from pathlib import Path
from types import MappingProxyType
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256
from native_scene_contacts import SceneContacts
from native_scene_geometry import policy_for, faces_for
from native_scene_imported_skin import ImportedSceneSkin
from native_runtime_affine_skin import AffineSkin
from native_engine_clock import clock_echo_matches, clock_wire
from native_engine_contacts import matrices
from native_scene_engine import OBJECT_TOLERANCE
from native_scene_runtime import package_members
from native_scene_runtime_modes import ModeFiles, METHODS as RUNTIME_METHODS
from native_runtime_mode_stream import records

SCHEMA='strep-runtime-surface-capture-v1'
METHODS=tuple(dict.fromkeys(RUNTIME_METHODS+('native_runtime_surface_capture.py','native_runtime_mode_stream.py')))
FILES={'capture.json','capture.npz','source-scene.json','source-policy.json'}
FLOATS=('world','skeleton_world','mesh_world','weights','points')
INTS=('nodes','mesh_index','source_mapping','faces')
ARRAY_LIMIT=256*1024**2
TOTAL_LIMIT=512*1024**2


def require(value,message):
    if not value:raise ValueError(message)


def masks(names):
    return {mode:{name:('extracted' if mode=='extracted' or mode=='mixed' and i%2==0 else 'embedded')
        for i,name in enumerate(names)} for mode in ('embedded','extracted','mixed')}


def _npz(path,keys):
    """Check declared complete selected arrays before decompression; never truncate."""
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        require(len(names)==len(set(names)),'Distinct observation arrays required')
        selected=[i for i in infos if i.filename in {k+'.npy' for k in keys}]
        require(len(selected)==len(keys),'Complete selected observation population required')
        require(all(i.file_size<=ARRAY_LIMIT for i in selected) and sum(i.file_size for i in selected)<=TOTAL_LIMIT,
            'Complete selected arrays exceed capture budget; no partial population')
    with np.load(path,allow_pickle=False) as stored:return {k:stored[k].copy() for k in keys}


def _rigid(world):
    require(world.ndim==3 and world.shape[1:]==(4,4) and np.isfinite(world).all()
        and np.array_equal(world[:,3],np.broadcast_to([0,0,0,1],world[:,3].shape)),'Complete finite affine object poses required')
    require(np.all(np.linalg.det(world[:,:3,:3])>0),'Proper captured object bases required')
    rotation=Rotation.from_matrix(world[:,:3,:3]).as_matrix()
    error=float(abs(rotation-world[:,:3,:3]).max())
    require(error<=OBJECT_TOLERANCE,'Captured object is not rigid within the existing pose tolerance')
    return rotation,error


def _source(folder,expected_sha256,mode):
    folder=Path(folder).resolve();result_path=folder/'result.json'
    require(sha256(result_path)==expected_sha256,'Pinned completed runtime result required')
    result=read(result_path)
    require(result['schema']=='strep-native-scene-runtime-mode-audit-v1' and result['status']=='complete'
        and type(result['all_sampled_runtime_conditions_pass']) is bool,'Complete mode-file runtime required')
    require(result['source_bytes_unchanged'] is True and result['arrays_roundtrip_exact'] is True
        and all(result[k] is False for k in ('quality_approved','physics_verified','release_approved')),'Original diagnostic runtime scope required')
    pins={str(result_path):expected_sha256}
    for group in ('files_sha256','raw_mode_files_sha256'):
        for name,h in result[group].items():
            p=(folder/name).resolve();require(p.parent==folder and sha256(p)==h,'Runtime artifact changed or escaped')
            pins[str(p)]=h
    archive=folder/'implementation';methods=result['implementation_sha256']
    require({p.name for p in archive.iterdir() if p.is_file()}==set(methods),'Complete producer archive required')
    for name,h in methods.items():
        require(Path(name).name==name and '\\' not in name and ':' not in name,'Plain archived producer filename required')
        p=archive/name;require(sha256(p)==h,'Producer archive changed');pins[str(p)]=h
    for name,h in result['executed_script_sha256'].items():
        p=(folder/'project/runtime-v1'/name).resolve()
        require(p.parent==folder/'project/runtime-v1' and methods.get(name)==h and sha256(p)==h,'Executed runtime script changed')
        pins[str(p)]=h
    with zipfile.ZipFile(folder/'source-game-assets.zip') as z:
        manifest=package_members(z)
        for name,h in manifest['files_sha256'].items():
            p=(folder/'project'/name).resolve()
            require(p.is_relative_to(folder/'project') and sha256(p)==h,'Original runtime game asset changed')
            pins[str(p)]=h
    source_scene_conditions=manifest.get('sampled_scene_conditions_pass')
    require(source_scene_conditions is None or type(source_scene_conditions) is bool,'Explicit original scene status required')
    cp=folder/'project/scene.json';gp=folder/'project/geometry-policy.json'
    scene=SceneContacts(read(cp),cp.parent);policy=read(gp)
    geometry_times=policy_for(policy,scene,sha256(cp))[0]
    package=read(folder/'package.json');configured=package['runtime_root_modes'];choices=masks(scene.actors)
    if mode is None:
        matches=[name for name,value in choices.items() if value==configured]
        require(bool(matches),'Configured root combination has no exact captured mode; capture that combination first')
        mode=matches[0]
    require(type(mode) is str and mode in choices,'Choose an actually captured root mode')
    raw=ModeFiles(folder,read(folder/'engine-output.json'));mode_path=raw.entries[mode][0]
    return folder,result,scene,cp,gp,geometry_times,raw,mode_path,mode,choices[mode],configured,source_scene_conditions,pins


def stage(runtime,source_result_sha256,output,*,mode=None):
    output=Path(output).resolve();runtime=Path(runtime).resolve()
    require(not output.exists() and not output.is_relative_to(runtime),'Fresh capture outside immutable runtime required')
    with worker_lock(),threadpool_limits(limits=1):
        folder,result,scene,cp,gp,geometry_times,raw,mode_path,mode,selected,configured,source_scene_conditions,pins=_source(runtime,source_result_sha256,mode)
        require(not any(Path(p).is_relative_to(output) for p in pins),'Capture contains its own input')
        keys={'times_s'}
        for i,name in enumerate(scene.actors):
            p=f'{mode}_actor_{i}'
            keys.update({p+('_extracted_world' if selected[name]=='extracted' else '_world'),p+'_skeleton_world',p+'_mesh_world'})
        keys.update(f'{mode}_object_{i}_world' for i in range(len(scene.objects)))
        observed=_npz(folder/'observations.npz',keys);times=observed['times_s'];clock_wire(times)
        require(times[-1]==scene.duration and len(times)==result['samples'] and np.isin(geometry_times,times).all(),
            'Complete original runtime and geometry clocks required')
        arrays={'times_s':times};actors={};objects={};reference={};affines={};mappings={};orders={}
        indices=np.unique(np.linspace(0,len(times)-1,min(5,len(times)),dtype=int))
        frame_count=None
        for kind,key,value in records(mode_path):
            if kind=='field' and key=='actors':
                require(isinstance(value,dict) and set(value)==set(scene.actors),'Complete captured actors required')
                for i,(name,actor) in enumerate(scene.actors.items()):
                    p=f'actor_{i}';source=f'{mode}_actor_{i}';data=value[name]
                    skin=ImportedSceneSkin(actor['rig'],data);affine=AffineSkin(data)
                    mesh_nodes=result['modes'][mode]['actors'][name]['affine_skin']['mesh_nodes']
                    require(mesh_nodes==sorted(affine.nodes),'Complete ordered mesh-world transforms required')
                    arrays[p+'_world']=observed[source+('_extracted_world' if selected[name]=='extracted' else '_world')]
                    for suffix in ('skeleton_world','mesh_world'):arrays[p+'_'+suffix]=observed[source+'_'+suffix]
                    arrays.update({p+'_nodes':skin.nodes.copy(),p+'_weights':skin.weights.copy(),p+'_points':skin.points.copy(),
                        p+'_mesh_index':np.array([mesh_nodes.index(r[0]) for r in skin.report['imported_references']],dtype='<i8'),
                        p+'_source_mapping':skin.mapping.copy(),p+'_faces':faces_for(actor['rig'])[0].copy()})
                    actors[name]=dict(prefix=p,joints=len(actor['rig'].joints),vertices=len(skin.nodes),faces=len(arrays[p+'_faces']),
                        mesh_nodes=mesh_nodes,root_mode=selected[name],animation_index=actor['animation_index'],glb_sha256=read(cp)['actors'][name]['sha256'])
                    reference[name]=[];affines[name]=affine;mappings[name]=skin.mapping.copy();orders[name]=np.argsort(skin.bone_map)
                if scene.actors:del data,skin,affine
            elif kind=='frame':
                require(set(actors)==set(scene.actors),'Actor headers must precede canonical mode frames')
                i=key
                require(i<len(times) and isinstance(value,dict) and {'pose_time_s','playback_time_s','actors','objects'}<=set(value),
                    'Complete raw frame clock required')
                require(clock_echo_matches(times[i],value['pose_time_s']) and clock_echo_matches(times[i],value['playback_time_s'])
                    and set(value['actors'])==set(scene.actors) and set(value['objects'])==set(scene.objects),'Complete raw frame clock required')
                for name in actors:
                    info=actors[name];p=info['prefix'];f=value['actors'][name]
                    require(isinstance(f,dict) and {'time_s','bones','skeleton_world','mesh_world'}<=set(f)
                        and clock_echo_matches(times[i],f['time_s']),'Complete actor pose clock required')
                    require(set(f['mesh_world'])==set(info['mesh_nodes'])
                        and np.array_equal(arrays[p+'_world'][i],matrices(f['bones'])[orders[name]])
                        and np.array_equal(arrays[p+'_skeleton_world'][i],matrices(f['skeleton_world']))
                        and np.array_equal(arrays[p+'_mesh_world'][i],np.asarray([matrices(f['mesh_world'][n]) for n in info['mesh_nodes']],dtype='<f8')),
                        'Every captured joint, skeleton and mesh transform must match the raw frames')
                    if i in indices:reference[name].append(affines[name].positions(f)[mappings[name]])
                for j,name in enumerate(scene.objects):
                    require(np.array_equal(observed[f'{mode}_object_{j}_world'][i],matrices(value['objects'][name])),
                        'Every captured object pose must match raw frames')
            elif kind=='frame_count':frame_count=key
        require(frame_count==len(times) and set(actors)==set(scene.actors),'Complete streamed frame population required')
        for i,name in enumerate(scene.objects):
            p=f'object_{i}';world=observed[f'{mode}_object_{i}_world'];rotation,error=_rigid(world)
            arrays[p+'_world']=world;arrays[p+'_rotation']=rotation
            objects[name]=dict(prefix=p,maximum_basis_projection_error=error,projection_limit=OBJECT_TOLERANCE)
        raw.baseline=None
        if scene.actors:del f
        del observed,affines,mappings,orders,value;gc.collect()
        meta=dict(schema=SCHEMA,mode=mode,source_runtime=str(folder),source_result_sha256=source_result_sha256,
            contacts_path=str(cp),policy_path=str(gp),samples=len(times),actors=actors,objects=objects,
            selected_root_modes=selected,configured_root_modes=configured,matches_export_configuration=selected==configured,
            source_runtime_conditions_pass=result['all_sampled_runtime_conditions_pass'],reference_based=True,
            source_scene_conditions_pass=source_scene_conditions,
            raw_weights_renormalized=False,object_pose_projection='Nearest proper rigid basis; raw matrices retained, existing object pose tolerance enforced.',
            quality_approved=False,physics_verified=False,release_approved=False)
        capture=SurfaceCapture(meta,arrays,scene)
        checks={}
        for name in actors:
            error=max(float(abs(capture.actor_vertices(name,float(times[j]))-v).max()) for j,v in zip(indices,reference[name]))
            require(error<=1e-12,'Compact source reconstruction differs from raw affine skin')
            checks[name]=dict(indices=indices.tolist(),vertices=actors[name]['vertices'],maximum_coordinate_error_m=error)
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);(output/'implementation').mkdir()
        try:
            for n in methods:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
            shutil.copyfile(cp,output/'source-scene.json');shutil.copyfile(gp,output/'source-policy.json')
            save(output/'capture.json',meta);np.savez_compressed(output/'capture.npz',**arrays)
            require(all(sha256(p)==h for p,h in pins.items()),'Runtime source changed during capture')
            require(all(sha256(ROOT/'scripts'/n)==sha256(output/'implementation'/n)==h for n,h in methods.items()),'Capture implementation changed')
            save(output/'receipt.json',dict(schema=SCHEMA,inputs_sha256=pins,implementation_sha256=methods,
                files_sha256={n:sha256(output/n) for n in FILES},source_runtime=str(folder),source_result_sha256=source_result_sha256,
                reference_checks=checks,reference_based=True,quality_approved=False,release_approved=False))
            digest=sha256(output/'receipt.json');loaded=load(output,digest)
            require(set(loaded.arrays)==set(arrays) and all(loaded.arrays[n].dtype==v.dtype and loaded.arrays[n].shape==v.shape
                and loaded.arrays[n].tobytes()==v.tobytes() for n,v in arrays.items()),'Complete compact array roundtrip differs')
            value=dict(schema=SCHEMA,status='complete',receipt_sha256=digest,mode=mode,samples=len(times),actors=len(actors),objects=len(objects),
                source_runtime_conditions_pass=meta['source_runtime_conditions_pass'],matches_export_configuration=selected==configured,
                source_scene_conditions_pass=source_scene_conditions,
                reference_checks=checks,arrays_roundtrip_exact=True,reference_based=True,quality_approved=False,physics_verified=False,release_approved=False)
            save(output/'result.json',value);return value
        except Exception as exc:
            save(output/'result.json',dict(status='failed',error=str(exc),quality_approved=False,release_approved=False));raise


class SurfaceCapture:
    def __init__(self,meta,arrays,scene):
        self._meta=copy.deepcopy(meta);self.arrays=MappingProxyType(dict(arrays));self.scene=scene;self.times=arrays['times_s'];self._bindings={}
        clock_wire(self.times)
        require(meta['schema']==SCHEMA and meta['samples']==len(self.times) and self.times[-1]==scene.duration,'Complete surface capture clock required')
        require(list(meta['actors'])==list(scene.actors) and list(meta['objects'])==list(scene.objects),'Complete ordered surface participants required')
        require(meta['raw_weights_renormalized'] is False and meta['reference_based'] is True
            and all(meta[k] is False for k in ('quality_approved','physics_verified','release_approved')),'Unapproved raw surface scope required')
        require(meta['selected_root_modes']==masks(scene.actors).get(meta['mode'])
            and meta['matches_export_configuration']==(meta['selected_root_modes']==meta['configured_root_modes']),'Captured mode selection differs')
        expected={'times_s'};count=len(self.times)
        for i,(name,actor) in enumerate(scene.actors.items()):
            info=meta['actors'][name];p=f'actor_{i}';v=info['vertices'];j=info['joints'];m=len(info['mesh_nodes'])
            require(info['prefix']==p and v==sum(len(primitive['positions']) for primitive in actor['rig'].primitives)
                and j==len(actor['rig'].joints) and m>0 and info['mesh_nodes']==sorted(set(info['mesh_nodes'])),'Complete actor surface dimensions required')
            require(info['glb_sha256']==read(meta['contacts_path'])['actors'][name]['sha256'] and info['animation_index']==actor['animation_index']
                and info['root_mode']==meta['selected_root_modes'][name],'Original actor selection changed')
            expected.update(p+'_'+s for s in FLOATS+INTS)
            shapes={'world':(count,j,4,4),'skeleton_world':(count,4,4),'mesh_world':(count,m,4,4),'weights':(v,8),'points':(v,8,4),
                'nodes':(v,8),'mesh_index':(v,),'source_mapping':(v,),'faces':(info['faces'],3)}
            for suffix,shape in shapes.items():
                a=arrays[p+'_'+suffix];require(a.shape==shape and a.dtype==np.dtype('<f8' if suffix in FLOATS else '<i8') and np.isfinite(a).all(),'Complete typed actor arrays required')
                if suffix in ('world','skeleton_world','mesh_world'):
                    require(np.array_equal(a[...,3,:],np.broadcast_to([0,0,0,1],a.shape[:-2]+(4,))),'Complete affine actor transforms required')
            require(np.array_equal(arrays[p+'_faces'],faces_for(actor['rig'])[0]),'Complete source triangle population required')
            require(np.all((arrays[p+'_nodes']>=0)&(arrays[p+'_nodes']<j)) and np.all((arrays[p+'_mesh_index']>=0)&(arrays[p+'_mesh_index']<m))
                and np.all(arrays[p+'_source_mapping']>=0),'Valid complete skin references required')
            require(np.all((arrays[p+'_weights']>=0)&(arrays[p+'_weights']<=1)) and np.all(arrays[p+'_weights'].sum(axis=1)>0),'Finite nonzero raw skin weights required')
            require(np.all(abs(np.linalg.det(arrays[p+'_skeleton_world'][:,:3,:3]))>1e-12),'Invertible captured skeleton transforms required')
        for i,name in enumerate(scene.objects):
            info=meta['objects'][name];p=f'object_{i}';expected.update({p+'_world',p+'_rotation'})
            require(info['prefix']==p and arrays[p+'_world'].shape==(count,4,4) and arrays[p+'_rotation'].shape==(count,3,3)
                and arrays[p+'_world'].dtype==arrays[p+'_rotation'].dtype==np.dtype('<f8'),'Complete typed object poses required')
            rotation,error=_rigid(arrays[p+'_world'])
            require(np.array_equal(rotation,arrays[p+'_rotation']) and error==info['maximum_basis_projection_error']
                and info['projection_limit']==OBJECT_TOLERANCE,'Declared object pose projection changed')
        require(set(arrays)==expected,'Complete exact capture array population required')
        for array in self.arrays.values():array.setflags(write=False)

    @property
    def meta(self):return copy.deepcopy(self._meta)

    def _indices(self,times):
        a=np.asarray(times);require(a.ndim==1 and a.dtype.kind in 'fiu' and np.isfinite(a).all(),'Finite numeric captured times required')
        indices=np.searchsorted(self.times,a)
        require(np.all(indices<len(self.times)) and np.array_equal(self.times[indices],a),'Exact captured times required; no interpolation or rounding')
        return indices

    def actor_vertices(self,name,time):
        require(name in self._meta['actors'],'Unknown captured actor')
        i=int(self._indices([time])[0]);info=self._meta['actors'][name];p=info['prefix'];a=self.arrays
        local=np.linalg.inv(a[p+'_skeleton_world'][i])@a[p+'_world'][i]
        result=np.einsum('vkij,vkj,vk->vi',local[a[p+'_nodes'],:3,:],a[p+'_points'],a[p+'_weights'])
        for mesh_index in range(len(info['mesh_nodes'])):
            mask=a[p+'_mesh_index']==mesh_index;matrix=a[p+'_mesh_world'][i,mesh_index]
            result[mask]=result[mask]@matrix[:3,:3].T+matrix[:3,3]
        return result

    def actor_points(self,name,ids,times):
        ids=np.asarray(ids);require(name in self._meta['actors'] and ids.ndim==1 and ids.dtype.kind in 'iu'
            and np.all((ids>=0)&(ids<self._meta['actors'][name]['vertices'])),'Existing source vertex references required')
        self._indices(times)
        return np.array([self.actor_vertices(name,float(t))[ids] for t in times])

    def object_poses(self,name,times):
        require(name in self._meta['objects'],'Unknown captured object');indices=self._indices(times);p=self._meta['objects'][name]['prefix']
        return self.arrays[p+'_world'][indices,:3,3].copy(),self.arrays[p+'_rotation'][indices].copy()

    def check_inputs(self):
        require(all(sha256(p)==h for p,h in self._bindings.items()),'Sealed surface capture source changed')
        self.scene.check_inputs()


def load(folder,receipt_sha256):
    folder=Path(folder).resolve();require(sha256(folder/'receipt.json')==receipt_sha256,'Pinned surface receipt changed')
    receipt=read(folder/'receipt.json')
    require(receipt['schema']==SCHEMA and receipt['reference_based'] is True and receipt['quality_approved'] is False
        and receipt['release_approved'] is False and set(receipt['files_sha256'])==FILES,'Complete unapproved surface receipt required')
    require(set(receipt['implementation_sha256'])==set(METHODS),'Complete surface measurement methods required')
    for n,h in receipt['implementation_sha256'].items():require(sha256(ROOT/'scripts'/n)==sha256(folder/'implementation'/n)==h,'Surface measurement code changed')
    for n,h in receipt['files_sha256'].items():require(sha256(folder/n)==h,'Sealed surface artifact changed')
    require(all(sha256(p)==h for p,h in receipt['inputs_sha256'].items()),'Sealed surface input changed')
    meta=read(folder/'capture.json');cp=Path(meta['contacts_path']);gp=Path(meta['policy_path'])
    require(meta['source_runtime']==receipt['source_runtime'] and meta['source_result_sha256']==receipt['source_result_sha256']
        and receipt['inputs_sha256'].get(str(Path(meta['source_runtime'])/'result.json'))==meta['source_result_sha256'],'Original runtime binding changed')
    require(sha256(cp)==sha256(folder/'source-scene.json')==receipt['inputs_sha256'].get(str(cp))
        and sha256(gp)==sha256(folder/'source-policy.json')==receipt['inputs_sha256'].get(str(gp)),'Exact source scene/policy snapshots required')
    scene=SceneContacts(read(cp),cp.parent);policy=read(gp);times=policy_for(policy,scene,sha256(cp))[0]
    expected={'times_s'}
    for a in meta['actors'].values():expected.update(a['prefix']+'_'+s for s in FLOATS+INTS)
    for o in meta['objects'].values():expected.update({o['prefix']+'_world',o['prefix']+'_rotation'})
    with zipfile.ZipFile(folder/'capture.npz') as z:require(set(z.namelist())=={k+'.npy' for k in expected},'Exact compact archive population required')
    arrays=_npz(folder/'capture.npz',expected);capture=SurfaceCapture(meta,arrays,scene)
    require(np.isin(times,capture.times).all(),'Complete original geometry clock required')
    capture._bindings={**receipt['inputs_sha256'],str(folder/'receipt.json'):receipt_sha256,
        **{str(folder/n):h for n,h in receipt['files_sha256'].items()}}
    capture.check_inputs();return capture


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('stage');p.add_argument('runtime');p.add_argument('source_result_sha256');p.add_argument('output');p.add_argument('--mode',choices=['embedded','extracted','mixed'])
    p=sub.add_parser('verify');p.add_argument('capture');p.add_argument('receipt_sha256');args=parser.parse_args()
    if args.command=='stage':print(stage(args.runtime,args.source_result_sha256,args.output,mode=args.mode))
    else:
        value=load(args.capture,args.receipt_sha256);print(dict(status='verified',samples=len(value.times),actors=len(value.meta['actors']),objects=len(value.meta['objects']),quality_approved=False,release_approved=False))
