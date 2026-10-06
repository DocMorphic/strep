"""Prepare explicit editable curves for static joints in a separate clip.

All original clips and static payloads remain. Float32 pose drift is measured
against the original clip; this preparation never approves motion quality.
"""
import argparse,copy,shutil,traceback
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from native_scene_contacts import fields,scalar,METHODS as CONTACT_METHODS
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb,authored_animation
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-static-rotation-variant-v1'
METHODS=tuple(sorted(set(CONTACT_METHODS)|{'native_static_rotation_variant.py','native_support_clock.py','rig_clip_import.py',
    'rig_asset.py','gltf_tools.py','action_worker_lock.py','strep.py'}))


def static_quaternion(node):
    if 'matrix' in node:raise ValueError('Static rotation preparation requires an existing TRS node')
    q=np.asarray(node.get('rotation',[0.,0.,0.,1.]),float)
    if q.shape!=(4,) or not np.isfinite(q).all() or np.linalg.norm(q)<1e-8:raise ValueError('Finite nonzero static quaternion required')
    return q.copy(),(q/np.linalg.norm(q)).astype(np.float32)


def prepare(request,path):
    fields(request,('schema','source','nodes','clock_from','sample_times_s','limits','label','acknowledge_float32_pose_drift'),'static rotation variant request')
    if request['schema']!=SCHEMA or request['acknowledge_float32_pose_drift'] is not True:raise ValueError('Explicit static rotation variant and Float32 drift acknowledgement required')
    source=request['source'];fields(source,('path','sha256','animation_index'),'source clip')
    if not isinstance(source['path'],str) or not source['path'] or type(source['animation_index']) is not int:raise ValueError('Pinned existing clip required')
    p=(Path(path).parent/source['path']).resolve()
    if not p.is_file() or sha256(p)!=source['sha256']:raise ValueError('Source clip bytes differ')
    rig=RigAsset.load(p);sampler=NativeSupportSampler(rig.document,rig.binary,source['animation_index'])
    nodes=request['nodes']
    if not isinstance(nodes,list) or not 1<=len(nodes)<=16 or any(type(n) is not int or n not in rig.joints for n in nodes) or len(set(nodes))!=len(nodes):raise ValueError('Choose 1-16 distinct existing skin joints')
    seeds={}
    for n in nodes:
        if any(c[:2]==(n,'rotation') for c in sampler.channels):raise ValueError('Requested joint already has a rotation channel')
        seeds[n]=static_quaternion(rig.document['nodes'][n])
    template=request['clock_from'];fields(template,('node','path'),'clock template')
    if type(template['node']) is not int or template['path'] not in ('rotation','translation','scale'):raise ValueError('Explicit existing clock template required')
    matches=[c for c in sampler.channels if c[:2]==(template['node'],template['path'])]
    if len(matches)!=1:raise ValueError('Clock template channel unavailable')
    clock=matches[0][2]
    if len(clock)<2 or clock[0]!=0 or float(clock[-1])!=sampler.duration:raise ValueError('Clock template must include both exact clip endpoints')
    label=request['label']
    if not isinstance(label,str) or not 1<=len(label)<=160 or not label.strip():raise ValueError('Explicit variant label required')
    limits=request['limits'];fields(limits,('matrix_error_max','vertex_error_max_m'),'sampled fidelity limits')
    for k,v in limits.items():scalar(v,1e-12,1e-5,k)
    values=request['sample_times_s']
    if not isinstance(values,list) or not 2<=len(values)<=20000:raise ValueError('Explicit complete fidelity clock required')
    times=np.array([scalar(v,0,sampler.duration,'fidelity sample') for v in values])
    if times[0]!=0 or times[-1]!=sampler.duration or np.any(np.diff(times)<=0):raise ValueError('Sorted unique fidelity samples with both endpoints required')
    native=[c[2].astype(float) for c in sampler.channels]
    mids=[(t[:-1]+t[1:])/2 for t in native if len(t)>1]
    uniform=np.arange(int(np.floor(sampler.duration*120))+1)/120
    times=np.unique(np.concatenate([times,uniform]+native+mids))
    if len(times)>20000:raise ValueError('Complete fidelity clock exceeds resource budget; no subset returned')
    return p,rig,sampler,seeds,clock,times


def run(request_path,output):
    request_path=Path(request_path).resolve();output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        if output.exists():raise ValueError('Fresh immutable preparation output required')
        request=read(request_path);source,rig,old,seeds,clock,times=prepare(request,request_path)
        inputs={str(request_path):sha256(request_path),str(source):sha256(source)};hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True);(output/'implementation').mkdir()
        try:
            for n in hashes:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
            shutil.copyfile(request_path,output/'request.json');shutil.copyfile(source,output/'source.glb')
            doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary);variant=copy.deepcopy(doc['animations'][request['source']['animation_index']])
            variant['name']=authored_animation(request['label'])['name']
            channel=next(c for c in variant['channels'] if (c['target'].get('node'),c['target'].get('path'))==(request['clock_from']['node'],request['clock_from']['path']))
            input_accessor=variant['samplers'][channel['sampler']]['input']
            for n,(_,q) in seeds.items():
                accessor=append_accessor(doc,binary,np.tile(q,(len(clock),1)),'VEC4')
                variant['channels'].append(dict(sampler=len(variant['samplers']),target=dict(node=n,path='rotation')))
                variant['samplers'].append(dict(input=input_accessor,output=accessor,interpolation='LINEAR'))
            index=len(doc['animations']);doc['animations'].append(variant);candidate=output/'character.glb';write_glb(candidate,doc,binary)
            actual=RigAsset.load(candidate);reader=NativeSupportSampler(actual.document,actual.binary,index)
            if actual.document['animations'][:-1]!=rig.document['animations'] or actual.binary[:len(rig.binary)]!=rig.binary:raise ValueError('Original animation library or binary payload changed')
            for key in ('nodes','skins','meshes','materials','images','textures','scenes','scene'):
                if actual.document.get(key)!=rig.document.get(key):raise ValueError('Static asset metadata changed')
            if reader.duration!=old.duration:raise ValueError('Variant changed clip duration')
            channels={(n,p):(t,v,m) for n,p,t,v,m in reader.channels}
            for n,p,t,v,m in old.channels:
                a,b,c=channels[n,p]
                if not np.array_equal(a,t) or not np.array_equal(b,v) or c!=m:raise ValueError('Existing native channel changed')
            for n,(_,q) in seeds.items():
                t,v,m=channels[n,'rotation']
                if not np.array_equal(t,clock) or not np.array_equal(v,np.tile(q,(len(clock),1))) or m!='LINEAR':raise ValueError('Seeded static channel differs')
            before=[];after=[];matrix_errors=[];vertex_errors=[];exact_world=True;exact_skin=True
            for i,time in enumerate(times):
                a=old.sample(float(time));b=reader.sample(float(time));av=rig.vertices(a);bv=actual.vertices(b)
                before.append(a);after.append(b);matrix_errors.append(float(np.abs(a-b).max()));vertex_errors.append(float(np.linalg.norm(av-bv,axis=1).max()))
                exact_world&=a.tobytes()==b.tobytes();exact_skin&=av.tobytes()==bv.tobytes()
                if i==0 or (i+1)%250==0 or i+1==len(times):
                    save(output/'pipeline.json',dict(status='processing',completed_samples=i+1,total_samples=len(times),at=now()));print('Fidelity',i+1,'/',len(times),flush=True)
            np.savez_compressed(output/'observations.npz',times_s=times,source_worlds=np.array(before),variant_worlds=np.array(after),matrix_errors=matrix_errors,vertex_errors_m=vertex_errors)
            passed=max(matrix_errors)<=request['limits']['matrix_error_max'] and max(vertex_errors)<=request['limits']['vertex_error_max_m']
            if any(sha256(p)!=h for p,h in inputs.items()) or any(sha256(ROOT/'scripts'/n)!=h or sha256(output/'implementation'/n)!=h for n,h in hashes.items()):raise ValueError('Preparation input or method bytes changed')
            result=dict(schema=SCHEMA,status='complete',at=now(),source=dict(path=str(source),sha256=sha256(source),animation_index=request['source']['animation_index']),
                candidate=dict(path=str(candidate),sha256=sha256(candidate),animation_index=index),clock_from=request['clock_from'],
                seeds=[dict(node=n,original_static_quaternion=q.tolist(),stored_quaternion=f.tolist()) for n,(q,f) in seeds.items()],
                sampled_fidelity_pass=bool(passed),maximum_matrix_error=max(matrix_errors),maximum_vertex_error_m=max(vertex_errors),limits=request['limits'],
                sampled_world_bytes_equal=bool(exact_world),sampled_skin_bytes_equal=bool(exact_skin),fidelity_samples=len(times),
                original_animation_count=len(rig.document['animations']),original_library_and_binary_prefix_preserved=True,
                inputs_sha256=inputs,methods_sha256=hashes,observations_sha256=sha256(output/'observations.npz'),
                original_selected=True,quality_approved=False,release_approved=False,
                scope='Separate clip with explicitly requested constant Float32 rotation channels for previously static TRS skin joints. All original animations/static payloads and existing channels remain. Fidelity covers supplied samples plus every native key, midpoint and uniform 120 Hz sample, not continuous-time identity. No edit permission, reference/rate/contact/geometry rebaseline, correction, engine or motion-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except BaseException as exc:
            save(output/'failure.json',dict(error=str(exc),traceback=traceback.format_exc(),at=now()));save(output/'pipeline.json',dict(status='failed',at=now()));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();r=run(a.request,a.output);print('Prepared variant',r['candidate']['animation_index'],'sampled fidelity',r['sampled_fidelity_pass'],'original selected')

if __name__=='__main__':main()
