"""Load an exactly replayed restoration state without rebasing source motion caps."""
from pathlib import Path
import numpy as np
from native_key_interval_restoration import SCHEMA,validate,evaluate
from native_key_interval_model import KeyIntervalModel
from audit_native_key_initializer import require,arrays_equal
from strep import ROOT,read,sha256,save,now


def load(producer,result_digest,request_digest,replay,replay_digest,output):
    producer,replay,output=map(lambda p:Path(p).resolve(),(producer,replay,output))
    require(not output.exists() and not output.is_relative_to(producer),'Fresh separate continuation check required')
    require(sha256(producer/'result.json')==result_digest and sha256(producer/'request.json')==request_digest
        and sha256(replay)==replay_digest,'Trusted continuation bindings changed')
    result=read(producer/'result.json');request=read(producer/'request.json');proof=read(replay)
    require(result['schema']==request['schema']==SCHEMA and result['status']=='complete' and result['source_request_sha256']==request_digest,'Completed original-bound restoration required')
    require(proof['schema']=='strep-native-key-restoration-replay-v1' and proof['status']=='complete'
        and proof['producer_result_sha256']==result_digest and proof['producer_request_sha256']==request_digest
        and proof['retention_history_replayed'] is True and proof['optimizer_executed'] is False,'Matching complete numerical replay required')
    for value in (result,request,proof):
        require(value['original_selected'] is True and value['quality_approved'] is False and value['release_approved'] is False,'Continuation cannot inherit approval')
    require(result['training_admitted'] is False and result['all_original_caps_preserved'] is True,'Original motion-cap reference required')
    for key in ('sampled_conditions_pass','original_rate_failures','floor_failures'):require(proof[key]==result[key],'Replay summary differs from source restoration')
    require([r['label'] for r in proof['cases']]==[r['label'] for r in result['probes']]
        and all(r['exact_bytes_and_complete_observations'] is True for r in proof['cases']),'Complete returned-probe replay required')
    pins=request['source_bindings_sha256'];methods=request['implementation_sha256']
    require(all(sha256(p)==h for p,h in pins.items()),'Original source binding changed')
    require(all(sha256(ROOT/'scripts'/n)==h==sha256(producer/'implementation'/n) for n,h in methods.items()),'Original restoration methods changed')
    recipes=[Path(p) for p in pins if Path(p).suffix=='.json' and read(p).get('schema')==SCHEMA]
    require(len(recipes)==1 and read(recipes[0])==request['recipe'],'Original restoration recipe changed')
    recipe=validate(request['recipe']);original=(recipes[0].parent/recipe['producer']['path']).resolve()
    problem=KeyIntervalModel(original,recipe['producer']['result_sha256'],recipe['producer']['request_sha256'],recipe['active_keys'])
    require(problem.size==request['controls'],'Original complete control population required')
    value=np.asarray(result['selected_controls'],float);problem.controls(value)
    final=producer/'probes/final';record=read(final/'probe.json')
    require(record==result['probes'][-1] and record['label']=='final','Canonical final returned proposal required')
    np.testing.assert_array_equal(record['controls'],value)
    for filename,key in [('character.glb','glb_sha256'),('observations.npz','observations_sha256'),('geometry-result.json','geometry_result_sha256'),('contact-result.json','contact_result_sha256')]:
        require(sha256(final/filename)==record[key],'Verified final proposal artifact changed')
    current=evaluate(problem,value,output)
    require(current['record']['glb_sha256']==record['glb_sha256'],'Continuation does not reproduce exact saved clip')
    for filename in ('observations.npz','contact-observations.npz','geometry-observations.npz'):arrays_equal(final/filename,output/filename)
    ignored={'label','observations_sha256','geometry_result_sha256','contact_result_sha256'}
    require({k:v for k,v in record.items() if k not in ignored}=={k:v for k,v in current['record'].items() if k not in ignored},'Complete continuation decisions changed')
    require(current['record']['decoded_prefix_pass'],'Continuation must retain original edit/contact/root conditions')
    problem.check()
    receipt=dict(schema='strep-native-key-restoration-continuation-v1',status='complete',at=now(),producer=str(producer),producer_result_sha256=result_digest,
        producer_request_sha256=request_digest,numerical_replay_sha256=replay_digest,controls=value.tolist(),original_initializer=str(problem.producer),
        original_rate_caps_preserved=True,exact_final_clip_and_complete_arrays=True,original_selected=True,quality_approved=False,release_approved=False,
        scope='Fresh verification of the saved edited controls against the unchanged original initializer, rig, clocks, contact intent and motion caps. No reference reset or inherited approval.')
    save(output/'continuation.json',receipt)
    return problem,value,current,receipt
