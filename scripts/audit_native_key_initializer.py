"""Fresh complete replay of native-key proposals, without running their optimizer."""
import argparse
import copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_key_contact_initializer import prepare,encode,KeyPose,SCHEMA
from native_scene_contacts import SceneContacts,fields
from native_scene_geometry import policy_for,evaluate_to_archive
from sampled_motion_caps import features,measures,SampledMotionCaps
from strep import ROOT,read,save,sha256,now


def require(condition,message):
    if not condition:raise ValueError(message)


def arrays_equal(left,right):
    with np.load(left,allow_pickle=False) as a,np.load(right,allow_pickle=False) as b:
        require(set(a.files)==set(b.files),'Complete observation population changed')
        for name in a.files:
            require(a[name].dtype==b[name].dtype and a[name].shape==b[name].shape and a[name].tobytes()==b[name].tobytes(),'Complete numeric observation changed: '+name)


def bound(producer,expected_result_sha256,expected_request_sha256):
    producer=Path(producer).resolve()
    result_path=producer/'result.json';require(sha256(result_path)==expected_result_sha256,'Expected source result binding changed')
    require(sha256(producer/'request.json')==expected_request_sha256,'Expected original request binding changed')
    result=read(result_path);saved=read(producer/'request.json');request=saved['request'];pins=saved['source_bindings_sha256'];methods=saved['implementation_sha256']
    fields(result,('schema','status','at','keys','pose_failures','glb_sha256','output_animation_index','maximum_joint_displacement_m',
        'maximum_rotation_fraction','root_world_element_error','decoded_edit_samples_pass','contact_samples_pass','geometry_samples_pass',
        'original_rate_rows','failed_original_rate_rows','original_motion_caps_pass','sampled_conditions_pass',
        'original_selected','quality_approved','training_admitted','release_approved','scope'),'native key proposal result')
    fields(saved,('request','source_bindings_sha256','implementation_sha256','source_animation_index','temporal_representation','quality_approved'),'original key proposal request')
    require(saved['quality_approved'] is False,'Original request scope changed')
    require(result['schema']==SCHEMA and result['status']=='complete' and result['original_selected'] is True
        and all(result[k] is False for k in ('quality_approved','training_admitted','release_approved')),'Proposal scope or selection changed')
    require(all(sha256(p)==h for p,h in pins.items()),'Original input binding changed')
    require(all(sha256(ROOT/'scripts'/n)==h==sha256(producer/'implementation'/n) for n,h in methods.items()),'Original source implementation changed')
    candidates=[Path(p) for p,h in pins.items() if h==request['contacts_sha256']];require(len(candidates)==1,'Exact original scene binding required')
    contacts=candidates[0];policies=[];requests=[]
    for p in pins:
        if Path(p).suffix=='.json':
            value=read(p)
            if isinstance(value,dict) and value.get('schema')=='strep-native-scene-geometry-v1' and value.get('contacts_sha256')==request['contacts_sha256']:policies.append(value)
            if isinstance(value,dict) and value.get('schema')==SCHEMA:requests.append(value)
    require(len(policies)==1,'Exact original geometry policy required');policy=policies[0]
    require(len(requests)==1 and requests[0]==request,'Declared original initializer request changed')
    return result,saved,request,pins,methods,contacts,policy


def run(producer,output,expected_result_sha256,expected_request_sha256):
    producer,output=Path(producer).resolve(),Path(output).resolve()
    require(not output.exists() and not output.is_relative_to(producer),'Fresh separate replay output required')
    result,saved,request,pins,methods,contacts,policy=bound(producer,expected_result_sha256,expected_request_sha256)
    result_path=producer/'result.json';spec=read(contacts);scene=SceneContacts(spec,contacts.parent)
    name,nodes,caps,clock,channels=prepare(scene,request,sha256(contacts),policy);actor=scene.actors[name]
    require(type(saved['source_animation_index']) is int and saved['source_animation_index']==actor['animation_index'],'Original animation index changed')
    with worker_lock(),threadpool_limits(limits=1):
        with np.load(producer/'key-controls.npz',allow_pickle=False) as data:
            require(set(data.files)=={'times_s','controls'},'Complete key controls required')
            np.testing.assert_array_equal(data['times_s'],clock);controls=data['controls'].copy()
        require(controls.shape==(len(clock),len(nodes),3) and np.isfinite(controls).all(),'Complete finite key controls required')
        records=read(producer/'key-results.json');require(len(records)==len(clock),'Complete key results required');failed=0
        for index,stamp in enumerate(clock):
            require(records[index]['time_s']==float(stamp),'Original native key clock changed')
            frozen=bool(stamp in request['frozen_times_s'] or not request['window_s'][0]<stamp<request['window_s'][1])
            if frozen:require(not np.any(controls[index]),'Frozen native key changed')
            pose=KeyPose(scene,name,float(stamp),nodes,caps,request['maximum_joint_displacement_m'],policy['planes'],policy['limits']['penetration_m'],request['floor_reserve_m'])
            passed=bool(np.all(pose.evaluate(controls[index].ravel())[0]>=(-1e-7 if records[index]['solved'] else 0)))
            require(records[index]['pose_conditions_pass'] is passed,'Stored key-pose decision changed');failed+=not passed
        output.mkdir(parents=True);index=encode(actor['rig'],actor['animation_index'],nodes,channels,controls,caps,output/'character.glb')
        require(index==result['output_animation_index'] and sha256(output/'character.glb')==result['glb_sha256']==sha256(producer/'character.glb'),'Actual proposal bytes or animation index changed')
        derived=copy.deepcopy(spec)
        for n in derived['actors']:derived['actors'][n]['glb']=str((contacts.parent/derived['actors'][n]['glb']).resolve())
        derived['actors'][name].update(glb=str(producer/'character.glb'),sha256=result['glb_sha256'],animation_index=index)
        require(read(producer/'contacts.json')==derived,'Original scene intent changed')
        decoded=SceneContacts(derived,producer);contact_report,contact_arrays=decoded.evaluate()
        require(contact_report==read(producer/'contact-result.json'),'Complete contact decision changed')
        np.savez_compressed(output/'contact-observations.npz',**contact_arrays);arrays_equal(output/'contact-observations.npz',producer/'contact-observations.npz')
        geo=copy.deepcopy(policy);geo['contacts_sha256']=sha256(producer/'contacts.json')
        require(read(producer/'geometry.json')==geo,'Original geometry intent changed')
        surface,transport=evaluate_to_archive(decoded,geo,geo['contacts_sha256'],output/'geometry-observations.npz')
        surface.update(**transport);require(surface==read(producer/'geometry-result.json'),'Complete geometry result changed')
        arrays_equal(output/'geometry-observations.npz',producer/'geometry-observations.npz')
        geometry_times,_,_=policy_for(policy,scene,sha256(contacts));uniform=np.arange(int(np.floor(scene.duration*120))+1)/120
        times=np.unique(np.concatenate([geometry_times,uniform,clock]+[a for k,a in contact_arrays.items() if k.endswith('_times_s')]))
        before=np.asarray([actor['sampler'].sample(float(t)) for t in times]);after=np.asarray([decoded.actors[name]['sampler'].sample(float(t)) for t in times]);ids=np.searchsorted(times,uniform);joints=actor['rig'].joints
        rates=SampledMotionCaps(features(before[ids],joints),uniform,np.linspace(0,scene.duration,5),tolerance=1e-5)
        residual=np.concatenate([((v-c-rates.tolerance)/np.maximum(c,.001)).ravel() for v,c in zip(measures(features(after[ids],joints),rates.dt),rates.caps)])
        np.savez_compressed(output/'motion-observations.npz',times_s=times,source_world=before,candidate_world=after,uniform_times_s=uniform,rate_residual=residual,**{f'metric_{i}':c for i,c in enumerate(rates.caps)})
        arrays_equal(output/'motion-observations.npz',producer/'motion-observations.npz')
        displacement=float(np.linalg.norm(after[:,joints,:3,3]-before[:,joints,:3,3],axis=-1).max());angles=[]
        for node,cap in zip(nodes,caps):
            parent=actor['rig'].parents[node];a=np.linalg.solve(before[:,parent],before[:,node]);b=np.linalg.solve(after[:,parent],after[:,node])
            angles.append(float(np.rad2deg(np.linalg.norm(Rotation.from_matrix(a[:,:3,:3].swapaxes(-1,-2)@b[:,:3,:3]).as_rotvec(),axis=1)).max())/cap)
        root_error=float(abs(after[:,request['root_node']]-before[:,request['root_node']]).max())
        edit_pass=bool(max(angles)<=1 and displacement<=request['maximum_joint_displacement_m'] and root_error==0)
        expected=dict(keys=len(clock),pose_failures=int(failed),maximum_joint_displacement_m=displacement,maximum_rotation_fraction=max(angles),root_world_element_error=root_error,
            decoded_edit_samples_pass=edit_pass,contact_samples_pass=contact_report['passed'],geometry_samples_pass=surface['sampled_conditions_pass'],original_rate_rows=len(residual),
            failed_original_rate_rows=int((residual>0).sum()),original_motion_caps_pass=bool(np.all(residual<=0)),
            sampled_conditions_pass=bool(edit_pass and contact_report['passed'] and surface['sampled_conditions_pass'] and np.all(residual<=0)))
        require(all(type(result[k]) is type(v) and result[k]==v for k,v in expected.items()),'Typed proposal decision changed')
        require(sha256(result_path)==expected_result_sha256 and sha256(producer/'request.json')==expected_request_sha256 and all(sha256(p)==h for p,h in pins.items()),'Original bindings changed during replay')
        receipt=dict(schema='strep-native-key-initializer-replay-v1',status='complete',at=now(),source_result_sha256=expected_result_sha256,**expected,
            exact_glb_and_complete_arrays=True,optimizer_executed=False,shared_reader_skin_and_pose_methods=True,
            source_request_sha256=expected_request_sha256,auditor_sha256=sha256(Path(__file__)),original_selected=True,quality_approved=False,release_approved=False)
        save(output/'result.json',receipt);return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--expected-result-sha256',required=True);parser.add_argument('--expected-request-sha256',required=True)
    args=parser.parse_args();run(args.producer,args.output,args.expected_result_sha256,args.expected_request_sha256)
