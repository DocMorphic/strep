"""Complete sampled geometry with exact full-input reuse across saved clips.

All declared times remain in the output. Any changed query input triggers a
fresh whole-scene sample; unchanged samples retain complete numeric evidence.
Historical geometry kernels and existing study workers remain untouched.
"""
import copy
import argparse
import hashlib
import platform
import re
from pathlib import Path
import sys
import numpy as np
import scipy
import trimesh
from native_scene_contacts import SceneContacts
import native_scene_geometry as geometry
from native_observation_archive import ObservationArchive,verify,logical_sha256
from engine_contact_sampling import contract_sha256
from strep import ROOT,read,save,sha256,now
from action_worker_lock import worker_lock
from threadpoolctl import threadpool_limits


def runtime():
    return dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,trimesh=trimesh.__version__,
                platform=platform.system(),machine=platform.machine(),byteorder=sys.byteorder)


def methods():
    return {n:sha256(ROOT/'scripts'/n) for n in (*geometry.METHODS,'native_geometry_cache.py')}


class Donor:
    """A complete cache produced by this API, with original inputs still bound."""
    def __init__(self,folder):
        self.folder=Path(folder).resolve();self.result=read(self.folder/'result.json')
        self.request=read(self.folder/'request.json');self.report=read(self.folder/'geometry.json')
        self.archive=self.folder/'observations.npz'
        if (self.result.get('schema')!='strep-native-geometry-cache-result-v1' or self.result.get('status')!='complete'
                or self.request.get('schema')!='strep-native-geometry-cache-request-v1'
                or self.result.get('request_sha256')!=sha256(self.folder/'request.json')
                or self.result.get('geometry_sha256')!=sha256(self.folder/'geometry.json')
                or self.result.get('reuse_sha256')!=sha256(self.folder/'reuse.json')
                or self.result.get('observations_sha256')!=sha256(self.archive)
                or self.result.get('receipt_sha256')!=sha256(Path(str(self.archive)+'.receipt.json'))
                or self.request.get('runtime')!=runtime() or self.request.get('implementation_sha256')!=methods()):
            raise ValueError('Complete unchanged cache, matching geometry kernel and runtime required')
        if any(self.result.get(k) is not False for k in ('quality_approved','release_approved')):
            raise ValueError('Geometry cache cannot grant release approval')
        receipt=verify(self.archive)
        if receipt['logical_bytes']>self.request['maximum_logical_bytes']:raise ValueError('Donor exceeds its declared total logical byte budget')
        self.bindings={str(p):sha256(p) for p in (self.folder/'result.json',self.folder/'request.json',self.folder/'geometry.json',self.folder/'reuse.json',self.archive,Path(str(self.archive)+'.receipt.json'))}
        self.bindings.update(self.request['inputs_sha256']);self.check()
        if self.report.get('status')!='complete' or self.report['times_s']!=self.request['times_s']:
            raise ValueError('Complete ordered donor samples required')
        if [s['time_s'] for s in self.report['samples']]!=self.report['times_s']:
            raise ValueError('Complete donor decision clock required')

    def check(self):
        if any(value!=read(self.folder/name) for value,name in ((self.request,'request.json'),(self.result,'result.json'),(self.report,'geometry.json'))):
            raise ValueError('Loaded geometry cache metadata changed')
        if self.request['runtime']!=runtime() or self.request['implementation_sha256']!=methods():
            raise ValueError('Geometry cache kernel or runtime changed')
        if any(sha256(p)!=digest for p,digest in self.bindings.items()):
            raise ValueError('Geometry cache or original source input changed')


def _vertices(scene,name,time):
    actor=scene.actors[name];p,r=actor['placement']
    return actor['rig'].vertices(actor['sampler'].sample(float(time)))@r.T+p


def evaluate_to_cache(contacts_path,policy_path,output,*,donor=None,progress=None,maximum_array_bytes=256*1024**2,maximum_logical_bytes=16*1024**3):
    """Caller owns the worker lock; write a fresh complete archive and provenance.

    Donor equality uses every placed vertex, triangle index, primitive shape,
    object pose, declared plane and numeric limit. No joint dependency guess,
    changed-vertex subset, coefficient threshold or clock thinning is used.
    """
    contacts_path,policy_path,output=[Path(p).resolve() for p in (contacts_path,policy_path,output)]
    if type(maximum_logical_bytes) is not int or not 1024<=maximum_logical_bytes<=1024**4:
        raise ValueError('Explicit total logical byte budget of 1 KiB..1 TiB required')
    if output.exists():raise ValueError('Fresh geometry cache output required')
    scene=SceneContacts(read(contacts_path),contacts_path.parent);policy=read(policy_path);digest=sha256(contacts_path)
    times,populations,_=geometry.policy_for(policy,scene,digest)
    implementation=methods();environment=runtime();inputs={str(p):sha256(p) for p in (contacts_path,policy_path)};inputs.update(scene.inputs)
    if donor is not None and not isinstance(donor,Donor):raise ValueError('Verified complete geometry donor required')
    if donor is not None:donor.check()
    faces={};topology={}
    for name,actor in scene.actors.items():
        faces[name],primitives=geometry.faces_for(actor['rig'])
        topology[name]=dict(vertices=sum(len(p['positions']) for p in actor['rig'].primitives),faces=len(faces[name]),
            faces_sha256=hashlib.sha256(faces[name].astype('<i8').tobytes()).hexdigest(),primitives=primitives)
    poses={n:scene.object_poses(n,times) for n in scene.objects}
    shapes={n:obj['geometry'].record() for n,obj in scene.objects.items()}
    output.mkdir(parents=True)
    request=dict(schema='strep-native-geometry-cache-request-v1',at=now(),inputs_sha256=inputs,implementation_sha256=implementation,runtime=environment,
        maximum_logical_bytes=maximum_logical_bytes,
        actors=list(scene.actors),objects=shapes,limits=copy.deepcopy(policy['limits']),planes=copy.deepcopy(policy['planes']),times_s=times.tolist(),
        source_epoch='Complete placed canonical RigAsset vertices used by the unchanged geometry kernel',
        donor_bindings=None if donor is None else dict(donor.bindings))
    save(output/'request.json',request)
    old=np.load(donor.archive,allow_pickle=False) if donor is not None else None
    try:
        if old is not None and not np.array_equal(old['times_s'],donor.request['times_s']):raise ValueError('Donor numeric clock differs')
        compatible=bool(donor is not None and donor.request['actors']==list(scene.actors)
            and list(donor.request['objects'])==list(shapes) and donor.request['objects']==shapes
            and donor.request['limits']==policy['limits'] and list(donor.request['planes'])==list(policy['planes'])
            and donor.request['planes']==policy['planes'])
        old_lookup={} if donor is None else {float(t):i for i,t in enumerate(donor.request['times_s'])}
        frame_arrays={}
        if old is not None:
            for key in old.files:
                match=re.match(r'^frame_(\d+)_',key)
                if match is not None:frame_arrays.setdefault(int(match.group(1)),[]).append(key)
        if compatible:
            compatible=all(np.array_equal(faces[n],old[f'topology_{n}_faces']) for n in scene.actors)
        mapping=[];saved_vertices={};archive=output/'observations.npz'
        class BoundedArchive(ObservationArchive):
            def __setitem__(self,key,value):
                if self.bytes+np.asarray(value).nbytes>maximum_logical_bytes:
                    raise ValueError('Complete cache exceeds total logical byte budget; no subset returned')
                super().__setitem__(key,value)
        with BoundedArchive(archive,maximum_array_bytes=maximum_array_bytes) as sink:
            sink['times_s']=times
            for n,f in faces.items():sink[f'topology_{n}_faces']=f
            for n,(p,r) in poses.items():sink[f'object_{n}_positions_m']=p;sink[f'object_{n}_rotations']=r
            for frame,time in enumerate(times):
                previous=old_lookup.get(float(time));same=compatible and previous is not None
                for name in scene.actors:
                    v=_vertices(scene,name,time)
                    if v.shape!=(topology[name]['vertices'],3) or not np.isfinite(v).all():raise ValueError('Complete finite placed actor vertices required')
                    key=f'frame_{frame}_{name}_vertices_world_m';sink[key]=v;saved_vertices[frame,name]=sink.arrays[key]['logical_sha256']
                    if same and not np.array_equal(v,old[f'frame_{previous}_{name}_vertices_world_m']):same=False
                if same:
                    for name,(p,r) in poses.items():
                        if (not np.array_equal(p[frame],old[f'object_{name}_positions_m'][previous])
                                or not np.array_equal(r[frame],old[f'object_{name}_rotations'][previous])):same=False;break
                mapping.append(previous if same else None)
            changed=np.flatnonzero([i is None for i in mapping])
            # The unchanged kernel requires both clip endpoints for any query
            # clock. Requery them if a fresh subset is needed; never remove an
            # endpoint or force the historical kernel to accept a partial clip.
            fresh_ids=np.unique(np.r_[0,changed,len(times)-1]).astype(int) if len(changed) else np.array([],int)
            for i in fresh_ids:mapping[i]=None
            fresh_report=None
            if len(fresh_ids):
                subset=copy.deepcopy(policy);subset['clock']=dict(mode='explicit',times_s=times[fresh_ids].tolist())
                def vertices(name,time):
                    frame=int(np.searchsorted(times,time));v=_vertices(scene,name,time)
                    if frame==len(times) or times[frame]!=time or logical_sha256(v)!=saved_vertices[frame,name]:
                        raise ValueError('Canonical vertex inputs changed between equality and geometry query')
                    return v
                def objects(name,clock):
                    ids=np.searchsorted(times,clock)
                    if np.any(ids>=len(times)) or not np.array_equal(times[ids],clock):raise ValueError('Exact object query clocks required')
                    return poses[name][0][ids],poses[name][1][ids]
                class RemappedSink:
                    def __setitem__(self,key,value):
                        if key=='times_s':return
                        match=re.match(r'^frame_(\d+)_',key)
                        if match is None:raise ValueError('Unknown geometry observation key')
                        local=int(match.group(1));sink[f'frame_{fresh_ids[local]}_'+key[match.end():]]=value
                fresh_report,_=geometry.evaluate(scene,subset,digest,progress,actor_vertices=vertices,object_poses=objects,observation_sink=RemappedSink())
            fresh_lookup={int(i):k for k,i in enumerate(fresh_ids)};samples=[];provenance=[]
            for frame,previous in enumerate(mapping):
                if previous is None:
                    samples.append(copy.deepcopy(fresh_report['samples'][fresh_lookup[frame]]));kind='fresh'
                else:
                    samples.append(copy.deepcopy(donor.report['samples'][previous]));kind='reused-exact-full-inputs'
                    prefix=f'frame_{previous}_';vertex_keys={prefix+n+'_vertices_world_m' for n in scene.actors}
                    for key in frame_arrays.get(previous,()):
                        if key.startswith(prefix) and key not in vertex_keys:sink[f'frame_{frame}_'+key[len(prefix):]]=old[key]
                provenance.append(dict(sample=frame,time_s=float(times[frame]),kind=kind,donor_sample=previous))
            report=copy.deepcopy(fresh_report if fresh_report is not None else donor.report)
            report.update(samples=samples,times_s=times.tolist(),sampled_conditions_pass=bool(all(s['passed'] for s in samples)),
                clock_mode=policy['clock']['mode'],topology=topology,limits=copy.deepcopy(policy['limits']),declared_planes=list(policy['planes']),
                frame_populations=[dict(id=p['id'],rate_hz=p['rate_hz'],phase_offset_frames=p['phase_offset_frames'],times_s=p['times_s'].tolist()) for p in populations],
                frame_contract_sha256=contract_sha256())
        scene.check_inputs()
        if any(sha256(p)!=d for p,d in inputs.items()) or methods()!=implementation or runtime()!=environment:
            raise ValueError('Geometry cache source, kernel or runtime changed')
        if donor is not None:donor.check()
        save(output/'geometry.json',report);save(output/'reuse.json',dict(samples=provenance,reused_samples=sum(i is not None for i in mapping),fresh_samples=len(fresh_ids)))
        result=dict(schema='strep-native-geometry-cache-result-v1',status='complete',request_sha256=sha256(output/'request.json'),
            geometry_sha256=sha256(output/'geometry.json'),reuse_sha256=sha256(output/'reuse.json'),observations_sha256=sha256(archive),
            receipt_sha256=sha256(Path(str(archive)+'.receipt.json')),complete_samples=len(times),reused_samples=sum(i is not None for i in mapping),
            maximum_logical_bytes=maximum_logical_bytes,logical_bytes=read(Path(str(archive)+'.receipt.json'))['logical_bytes'],
            fresh_samples=len(fresh_ids),sampled_conditions_pass=report['sampled_conditions_pass'],quality_approved=False,release_approved=False,
            scope='Complete sampled scene conditions. Exact query-input reuse only; no contact, motion-rate, continuous collision, engine or human quality approval.')
        save(output/'result.json',result);return result
    finally:
        if old is not None:old.close()


def run(contacts_path,policy_path,output,*,donor_path=None,maximum_array_bytes=256*1024**2,maximum_logical_bytes=16*1024**3):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh geometry cache output required')
    with worker_lock(),threadpool_limits(limits=1):
        donor=Donor(donor_path) if donor_path is not None else None
        def progress(record):save(output/'pipeline.json',dict(**record,stage='fresh-whole-scene-geometry'))
        try:
            result=evaluate_to_cache(contacts_path,policy_path,output,donor=donor,progress=progress,
                maximum_array_bytes=maximum_array_bytes,maximum_logical_bytes=maximum_logical_bytes)
            save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:
            if output.exists():save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('contacts','policy','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--donor',type=Path)
    parser.add_argument('--maximum-logical-bytes',type=int,default=16*1024**3)
    parser.add_argument('--maximum-array-bytes',type=int,default=256*1024**2)
    args=parser.parse_args()
    run(args.contacts,args.policy,args.output,donor_path=args.donor,
        maximum_array_bytes=args.maximum_array_bytes,maximum_logical_bytes=args.maximum_logical_bytes)
