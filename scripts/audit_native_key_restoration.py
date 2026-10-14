"""Replay every returned restoration clip and retention decision, not the solver."""
import argparse
import copy
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_key_interval_model import KeyIntervalModel
from native_key_interval_restoration import SCHEMA,validate,evaluate,retain
from native_scene_contacts import fields
from audit_native_key_initializer import require,arrays_equal
from strep import ROOT,read,save,sha256,now


def run(producer,output,result_digest,request_digest):
    producer,output=Path(producer).resolve(),Path(output).resolve()
    require(not output.exists() and not output.is_relative_to(producer),'Fresh separate restoration replay required')
    require(sha256(producer/'result.json')==result_digest and sha256(producer/'request.json')==request_digest,'Trusted restoration result/request changed')
    result=read(producer/'result.json');request=read(producer/'request.json')
    fields(result,('schema','status','at','stop_reason','probes','history','selected_controls','source_request_sha256','sampled_conditions_pass',
        'original_rate_failures','floor_failures','all_original_caps_preserved','original_selected','quality_approved','training_admitted','release_approved','scope'),'restoration result')
    fields(request,('schema','recipe','source_bindings_sha256','implementation_sha256','solver','controls','original_selected','quality_approved','release_approved'),'restoration request')
    require(result['schema']==request['schema']==SCHEMA and result['status']=='complete' and result['source_request_sha256']==request_digest,'Bound completed restoration required')
    require(result['original_selected'] is True and request['original_selected'] is True and result['all_original_caps_preserved'] is True
        and all(result[k] is False for k in ('quality_approved','training_admitted','release_approved'))
        and request['quality_approved'] is False and request['release_approved'] is False,'Restoration scope/approval changed')
    pins=request['source_bindings_sha256'];methods=request['implementation_sha256']
    require(all(sha256(p)==h for p,h in pins.items()),'Original restoration input changed')
    require(all(sha256(ROOT/'scripts'/n)==h==sha256(producer/'implementation'/n) for n,h in methods.items()),'Original restoration method changed')
    recipes=[Path(p) for p in pins if Path(p).suffix=='.json' and read(p).get('schema')==SCHEMA]
    require(len(recipes)==1 and read(recipes[0])==request['recipe'],'Exact original restoration recipe required');recipe=validate(request['recipe'])
    original=(recipes[0].parent/recipe['producer']['path']).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        problem=KeyIntervalModel(original,recipe['producer']['result_sha256'],recipe['producer']['request_sha256'],recipe['active_keys'])
        require(problem.size==request['controls'],'Complete original control population required')
        output.mkdir(parents=True);fresh={};cases=[]
        for record in result['probes']:
            label=record['label'];require(type(label) is str and (label in ('start','final') or label.replace('-','').isdigit()) and label not in fresh,'Distinct contained probe label required')
            folder=producer/'probes'/label;value=np.asarray(record['controls'],float)
            require(read(folder/'probe.json')==record,'Original returned probe record changed')
            for filename,key in [('character.glb','glb_sha256'),('observations.npz','observations_sha256'),('geometry-result.json','geometry_result_sha256'),('contact-result.json','contact_result_sha256')]:
                require(sha256(folder/filename)==record[key],'Returned probe artifact changed')
            current=evaluate(problem,value,output/'probes'/label);fresh[label]=current;newfolder=output/'probes'/label
            require(current['record']['glb_sha256']==record['glb_sha256'],'Reconstructed clip differs')
            old_spec=read(folder/'contacts.json');new_spec=read(newfolder/'contacts.json')
            require(old_spec['actors'][problem.name]['glb']==str(folder/'character.glb'),'Canonical returned actor required')
            new_spec['actors'][problem.name]['glb']=old_spec['actors'][problem.name]['glb'];require(new_spec==old_spec,'Protected scene intent changed')
            for name in ('observations.npz','contact-observations.npz','geometry-observations.npz'):arrays_equal(folder/name,newfolder/name)
            old_contact=read(folder/'contact-result.json');new_contact=read(newfolder/'contact-result.json')
            translated={str(folder/'character.glb') if p==str(newfolder/'character.glb') else p:h for p,h in new_contact['inputs_sha256'].items()}
            new_contact['inputs_sha256']=translated;require(old_contact==new_contact,'Complete contact audit changed')
            require(read(folder/'geometry-result.json')==current['geometry'],'Complete geometry audit changed')
            ignored={'observations_sha256','geometry_result_sha256','contact_result_sha256'}
            require({k:v for k,v in record.items() if k not in ignored}=={k:v for k,v in current['record'].items() if k not in ignored},'Decoded probe decision changed')
            cases.append(dict(label=label,exact_bytes_and_complete_observations=True,original_rate_failures=current['record']['original_rate_failures'],floor_failures=current['record']['floor_failures']))
        require('start' in fresh and 'final' in fresh,'Complete endpoints required');selected=fresh['start'];value=problem.initial.copy()
        np.testing.assert_array_equal(selected['record']['controls'],value);visited={'start','final'}
        for entry in result['history']:
            iteration=entry['iteration'];require(type(iteration) is int and 1<=iteration<=recipe['iterations'],'Bounded original iteration required')
            choices=entry['probes'];require(len(choices)<=recipe['backoffs'],'Original backoff budget exceeded');accepted=None
            for index,choice in enumerate(choices):
                label=choice['label'];require(label==f'{iteration}-{index}' and label in fresh and label not in visited,'Complete ordered iteration probe required');visited.add(label)
                require(choice['fraction']==.5**index,'Original backoff fraction changed')
                with np.load(producer/'iterations'/str(iteration)/'direction.npz') as data:delta=data['delta']
                expected=np.clip(value+choice['fraction']*delta,problem.lower,problem.upper)
                np.testing.assert_array_equal(fresh[label]['record']['controls'],expected)
                actual=retain(selected,fresh[label]);require(choice['accepted'] is actual,'Decoded retention decision changed')
                if actual:
                    require(index==len(choices)-1,'Search continued after accepted step');selected=fresh[label];value=expected;accepted=choice['fraction']
            require(entry['accepted_fraction']==accepted,'Accepted iteration fraction changed')
        require(visited==set(fresh),'Returned probe missing from retention history')
        np.testing.assert_array_equal(result['selected_controls'],value);np.testing.assert_array_equal(fresh['final']['record']['controls'],value)
        require(all(result[k]==fresh['final']['record'][k] for k in ('sampled_conditions_pass','original_rate_failures','floor_failures')),'Final result changed')
        problem.check();require(all(sha256(p)==h for p,h in pins.items()) and sha256(producer/'result.json')==result_digest and sha256(producer/'request.json')==request_digest,'Original replay bindings changed')
        receipt=dict(schema='strep-native-key-restoration-replay-v1',status='complete',at=now(),producer_result_sha256=result_digest,producer_request_sha256=request_digest,
            cases=cases,retention_history_replayed=True,sampled_conditions_pass=result['sampled_conditions_pass'],original_rate_failures=result['original_rate_failures'],
            floor_failures=result['floor_failures'],optimizer_executed=False,original_selected=True,quality_approved=False,release_approved=False,
            auditor_sha256=sha256(Path(__file__)),scope='Fresh complete returned-export and retention replay with shared curve/reader/skin/audit methods. No solver/Jacobian rerun, continuous dynamics, engine or human approval.')
        save(output/'result.json',receipt);return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--expected-result-sha256',required=True);parser.add_argument('--expected-request-sha256',required=True)
    args=parser.parse_args();run(args.producer,args.output,args.expected_result_sha256,args.expected_request_sha256)
