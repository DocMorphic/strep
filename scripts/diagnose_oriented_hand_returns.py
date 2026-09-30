"""Decode completed hand solver returns and attribute original motion-cap failures."""
import argparse,shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now


def load_evidence(study):
    study=Path(study).resolve();result=read(study/'result.json');request=read(study/'request.json')
    if result['status']!='complete' or not request.get('hand_orientation'):raise ValueError('Completed oriented hand study required')
    files={str(study/'result.json'):sha256(study/'result.json')}
    for name in ['request','witnesses','source-queries','selected','solvers','evaluations','decoded','geometry']:
        path=study/(name+'.json');digest=result[name.replace('-','_')+'_sha256']
        if sha256(path)!=digest:raise ValueError('Hand study artifact changed')
        files[str(path)]=digest
    for name,digest in request['implementation'].items():
        path=(study/'implementation'/name).resolve()
        if path.parent!=study/'implementation' or sha256(path)!=digest or sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Hand study method differs')
        files[str(path)]=digest
    return request,files


def run(study,output):
    from bound_evidence import bind_inputs
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from sampled_motion_caps import SampledMotionCaps,features
    from independent_hand_motion import layout,SYMMETRIC_LAYOUT
    from diagnose_terminal_hand_rates import explain
    from hand_geometry_comparison import compare,load_warm_geometry
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh return diagnosis required')
    request,files=load_evidence(study);terminal=read(Path(request['study'])/'request.json')
    _,model_type,_,margins=layout(request.get('control_layout',SYMMETRIC_LAYOUT))
    plan=read(Path(terminal['plan'])/'request.json');protocol=read(Path(plan['source_plan'])/'request.json');baseline=Path(protocol['study'])
    original,_,required=load_bound_study(baseline);files.update(bind_inputs(required,request['inputs']))
    warm_geometry=None
    if request.get('warm_start_study'):
        warm_geometry,warm_files=load_warm_geometry(request,files);files.update(warm_files)
    prepared,actors=load_actors(Path(original['prepared_request']).parent)
    selected=read(baseline/'result.json')['selected'];trial=next(r for r in read(baseline/'trials.json') if r['folder']==selected)
    times=np.asarray(terminal['sample_times_s']);native=np.asarray(request['edit_native_times_s']);ids=np.asarray(request['sample_indices'])
    models=[];sources=[];worlds=[];labels=[]
    for i,(actor,entry) in enumerate(zip(actors,trial['actors'])):
        path=(baseline/selected/entry['path']).resolve()
        if path.parent!=(baseline/selected).resolve() or files.get(str(path))!=entry['sha256'] or sha256(path)!=entry['sha256']:
            raise ValueError('Bound baseline clip required')
        rig=RigAsset.load(path);reader=AnimationSampler(rig.document,rig.binary,0)
        sources.append(rig);worlds.append(np.array([reader.sample(t) for t in times]))
        models.append(model_type(rig,protocol['chains'][actor['name']],native,times,prepared['protected_seconds'],actor['rotation'],i))
        labels.extend(actor['name']+':'+rig.document['nodes'][n]['name'] for n in rig.joints)
    def payload(world,indices):
        parts=[features(w[indices],r.joints) for w,r in zip(world,sources)]
        return dict(indices=indices,**{k:np.concatenate([p[k] for p in parts],axis=1) for k in ['positions','rotations']})
    caps=SampledMotionCaps(payload(worlds,np.arange(len(times))),times,request['original_bins_s'])
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in sorted(set(request['implementation'])|{'diagnose_oriented_hand_returns.py','diagnose_terminal_hand_rates.py','hand_geometry_comparison.py'}):
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),study=str(study),inputs=files,implementation=methods,
        scope='Selected controls and every final optimizer return, decoded from actual GLBs under original caps. No mesh query, tolerance change, source mutation or acceptance.',quality_approved=False))
    candidates=[('selected',read(study/'selected.json')['controls'])]+[(f'return-{i}',r['returned_controls']) for i,r in enumerate(read(study/'solvers.json'))]
    records=[]
    for name,control in candidates:
        controls=np.asarray(control)
        try:predicted=[m.evaluate_vector(controls) for m in models]
        except ValueError as error:
            if 'outside two-bone reach' not in str(error):raise
            records.append(dict(name=name,controls=control,exported=False,reason='outside two-bone reach'));continue
        maximum=max(r[1] for r in predicted);record=dict(name=name,controls=control,maximum_native_edit_deg=maximum,
            minimum_guide_margin=float(margins(controls,native,plan['guide_rate_limits']).min()))
        if maximum>45.+1e-4:
            records.append(dict(record,exported=False,reason='native edit budget exceeded'));continue
        actual=[];clips=[]
        for i,(model,(expected,_)) in enumerate(zip(models,predicted)):
            path=output/f'{name}-{i}.glb';model.export_vector(controls,path)
            rig=RigAsset.load(path);reader=AnimationSampler(rig.document,rig.binary,0)
            world=np.array([reader.sample(t) for t in times]);error=float(np.abs(world-expected).max())
            if error>2e-10:raise ValueError('Return batch and exported GLB differ')
            np.testing.assert_array_equal(world[(times<=native[0])|(times>=native[-1])],worlds[i][(times<=native[0])|(times>=native[-1])])
            actual.append(world);clips.append(dict(path=path.name,sha256=sha256(path),maximum_batch_error=error))
        record.update(exported=True,clips=clips,support=explain(payload(actual,ids),caps,labels),
            full_clock=explain(payload(actual,np.arange(len(times))),caps,labels))
        records.append(record)
    save(output/'returns.json',records)
    geometry=read(study/'geometry.json');attribution=[]
    queries=read(study/'source-queries.json')
    if [(q['sample'],q['source'],q['target']) for q in queries]!=[(s,a,1-a) for s in request['hand_samples'] for a in [0,1]]:
        raise ValueError('Complete ordered source query population required')
    if [r['sample'] for r in geometry]!=request['hand_samples']:raise ValueError('Complete candidate hand clock required')
    source_depth={(q['sample'],q['source']):q['maximum_depth_m'] for q in queries};comparison=[]
    for row in geometry:
        old=max(source_depth[row['sample'],actor] for actor in [0,1]);new=max(d['max_depth_m'] for d in row['directions'])
        comparison.append(dict(sample=row['sample'],time_s=row['time_s'],source_hand_peak_m=old,candidate_hand_peak_m=new,increase_m=new-old))
    save(output/'hand-comparison.json',dict(samples=comparison,
        source_peak_m=max(r['source_hand_peak_m'] for r in comparison),candidate_peak_m=max(r['candidate_hand_peak_m'] for r in comparison),
        source_failed_samples=[r['sample'] for r in comparison if r['source_hand_peak_m']>request['hand_tolerance_m']],
        candidate_failed_samples=[r['sample'] for r in comparison if r['candidate_hand_peak_m']>request['hand_tolerance_m']],
        maximum_sample_increase_m=max(r['increase_m'] for r in comparison)))
    for actor,rig in enumerate(sources):
        peak=max(geometry,key=lambda r:r['directions'][actor]['max_depth_m']);direction=peak['directions'][actor]
        vertex=direction['deepest_source_vertex'];weights={}
        if vertex is not None:
            if len(rig.primitives)!=1:raise ValueError('One primitive required for hand vertex attribution')
            primitive=rig.primitives[0]
            for palette,weight in zip(primitive['joints'][vertex],primitive['weights'][vertex]):
                if weight<=0:continue
                node=rig.joints[int(palette)];label=rig.document['nodes'][node]['name']
                weights[label]=weights.get(label,0.)+float(weight)
        attribution.append(dict(actor=actors[actor]['name'],sample=peak['sample'],time_s=peak['time_s'],
            hand_peak_m=direction['max_depth_m'],deepest_source_vertex=vertex,source_skin_weights=weights))
    save(output/'geometry-attribution.json',attribution)
    if warm_geometry is not None:save(output/'warm-start-comparison.json',compare(warm_geometry,geometry,request['hand_tolerance_m']))
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Return diagnosis input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Return diagnosis method changed')
    result=dict(at=now(),status='complete',candidates=len(records),request_sha256=sha256(output/'request.json'),
        returns_sha256=sha256(output/'returns.json'),geometry_attribution_sha256=sha256(output/'geometry-attribution.json'),
        hand_comparison_sha256=sha256(output/'hand-comparison.json'),
        accepted_for_publication=False,quality_approved=False)
    if warm_geometry is not None:result['warm_start_comparison_sha256']=sha256(output/'warm-start-comparison.json')
    save(output/'result.json',result);print(result,flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.study,args.output)
