"""Source-bound Studio drafts and native-support jobs; no quality approval."""
import argparse
import copy
import os
from pathlib import Path
import re
import shutil
from strep import ROOT, read, save, sha256, now

NAMESPACE = 'native-support-jobs'
NAME = re.compile(r'[A-Za-z0-9_-]{1,100}')


def source(job, variant):
    if variant=='native_review':
        from native_review_support import source as native_source
        return native_source(job)
    from rig_contact_authoring import source as rig_source
    return rig_source(job,variant)


def folder_for(job):
    if not isinstance(job, str) or not NAME.fullmatch(job): raise ValueError('Invalid native support job')
    base=(ROOT/'reports'/NAMESPACE).resolve(); folder=(base/job).resolve()
    if folder.parent!=base: raise ValueError('Support job escapes its namespace')
    return folder


def metadata(job, variant):
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    _, result, _, report, glb = source(job, variant)
    digest = sha256(glb); rig = RigAsset.load(glb)
    if len(rig.document.get('animations', [])) != 1: raise ValueError('One chosen animation required')
    reader = NativeSupportSampler(rig.document, rig.binary, 0)
    from native_support_rigid_input import assessment
    preparation = assessment(rig,reader)
    clocks = []; ids = {}; tracks = {}
    for node, path, times, _, mode in reader.channels:
        if path != 'rotation': continue
        clock = tuple(float(t) for t in times)
        if clock not in ids:
            ids[clock] = str(len(clocks)); clocks.append(dict(id=ids[clock], times_s=list(clock)))
        tracks[node] = dict(rotation_clock=ids[clock], interpolation=mode)
    if sha256(glb) != digest: raise ValueError('Selected animation changed')
    return dict(source_job=job, variant=variant, label=result['label'], glb_sha256=digest,
        duration_s=reader.duration, animation_index=0, clocks=clocks,
        primitive_count=len(rig.primitives), rigid_preparation=preparation,
        joints=[dict(node=n, name=rig.document['nodes'][n].get('name'), parent=rig.parents[n], **tracks.get(n, {})) for n in rig.joints],
        root_node=report['root_node'], mapping={k:v for k,v in report['mapping'].items() if k in
            {s+n for s in ('Left','Right') for n in ('Leg','Shin','Foot')}},
        source_url=f'/files/native-correction-previews/{job}/candidate.glb' if variant=='native_review' else f'/files/rig-jobs/{job}/{variant}/character.glb',
        native_review_selection=result.get('native_review_selection'),quality_approved=False)


def validate_request(payload):
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    from native_support_spec import validate
    fields={'source_job','variant','spec'}
    if not isinstance(payload, dict) or not fields<=set(payload) or set(payload)-fields-{'prepare_rigid_input','sampled_support_repair','joint_source_rate_search'}:
        raise ValueError('Selected source job, version and native support draft required')
    if type(payload.get('prepare_rigid_input',False)) is not bool:raise ValueError('Explicit rig preparation choice required')
    if type(payload.get('sampled_support_repair',False)) is not bool:raise ValueError('Explicit sampled support choice required')
    if type(payload.get('joint_source_rate_search',False)) is not bool:raise ValueError('Explicit joint source-rate search choice required')
    if payload.get('sampled_support_repair',False) and payload.get('joint_source_rate_search',False):raise ValueError('Choose one support proposal method')
    _, _, _, report, glb = source(payload['source_job'], payload['variant'])
    spec = copy.deepcopy(payload['spec']); digest = sha256(glb); rig = RigAsset.load(glb)
    if len(rig.document.get('animations', [])) != 1: raise ValueError('One chosen animation required')
    reader = NativeSupportSampler(rig.document, rig.binary, 0)
    if not isinstance(spec, dict) or spec.get('root_node') != report['root_node']:
        raise ValueError('Use the selected clip mapped root')
    validate(spec, rig, reader, digest)
    if payload.get('prepare_rigid_input',False):
        from native_support_rigid_input import assessment
        eligibility=assessment(rig,reader)
        if not eligibility['eligible'] or not eligibility['static_node_changes']:
            raise ValueError('Selected rig has no eligible static scale roundoff to prepare')
    if sha256(glb) != digest: raise ValueError('Selected animation changed')
    return glb, spec


def prepare(payload, folder):
    glb, spec = validate_request(payload); folder = Path(folder).resolve()
    if folder != folder_for(folder.name).resolve() or folder.exists(): raise ValueError('Fresh Studio support job required')
    folder.mkdir(parents=True)
    shutil.copyfile(glb, folder/'source.glb'); save(folder/'draft.json', spec)
    if sha256(glb) != spec['glb_sha256'] or sha256(folder/'source.glb') != spec['glb_sha256']:
        save(folder/'pipeline.json', dict(status='failed',error='Source changed during snapshot'))
        raise ValueError('Source changed during snapshot')
    request = dict(at=now(), source_job=payload['source_job'], variant=payload['variant'],
        source_sha256=spec['glb_sha256'], draft_sha256=sha256(folder/'draft.json'),
        prepare_rigid_input=payload.get('prepare_rigid_input',False),
        sampled_support_repair=payload.get('sampled_support_repair',False),
        sampled_support_iterations=8 if payload.get('sampled_support_repair',False) else None,
        joint_source_rate_search=payload.get('joint_source_rate_search',False),
        joint_search_evaluations=160 if payload.get('joint_source_rate_search',False) else None,
        fit_folder='native-support-fit-'+folder.name, quality_approved=False)
    if payload['variant']=='native_review':
        from native_review_support import method_names
        _,native,_,_,_=source(payload['source_job'],payload['variant'])
        request['native_review_selection']=native['native_review_selection']
        request['native_review_methods']={name:sha256(Path(__file__).parent/name) for name in method_names()}
    save(folder/'request.json', request)
    archive=folder/'implementation';archive.mkdir()
    shutil.copyfile(__file__,archive/'studio_native_support.py')
    for name,digest in request.get('native_review_methods',{}).items():
        shutil.copyfile(Path(__file__).parent/name,archive/name)
        if sha256(archive/name)!=digest:raise ValueError('Native bridge method changed during snapshot')
    save(folder/'prepared.json', dict(request_sha256=sha256(folder/'request.json'),wrapper_sha256=sha256(archive/'studio_native_support.py')))
    save(folder/'pipeline.json', dict(status='starting'))
    return request


def frozen(folder):
    request = read(folder/'request.json'); prepared = read(folder/'prepared.json')
    if sha256(folder/'request.json') != prepared['request_sha256'] or request['quality_approved'] is not False:
        raise ValueError('Changed native support request')
    if request['fit_folder'] != 'native-support-fit-'+folder.name: raise ValueError('Invalid support output')
    if type(request.get('prepare_rigid_input',False)) is not bool:raise ValueError('Changed rig preparation choice')
    refinement=request.get('sampled_support_repair',False)
    if type(refinement) is not bool or request.get('sampled_support_iterations')!=(8 if refinement else None) or refinement and type(request.get('sampled_support_iterations')) is not int:raise ValueError('Changed sampled support choice or budget')
    joint=request.get('joint_source_rate_search',False)
    if type(joint) is not bool or request.get('joint_search_evaluations')!=(160 if joint else None) or joint and (type(request.get('joint_search_evaluations')) is not int or refinement):raise ValueError('Changed joint source-rate search choice or budget')
    if sha256(folder/'source.glb') != request['source_sha256'] or sha256(folder/'draft.json') != request['draft_sha256']:
        raise ValueError('Changed native support snapshot')
    if sha256(folder/'implementation/studio_native_support.py')!=prepared['wrapper_sha256']:
        raise ValueError('Changed support wrapper archive')
    if request['variant']=='native_review':
        from native_review_support import method_names
        if set(request.get('native_review_methods',{}))!=set(method_names()):raise ValueError('Native bridge method binding required')
        for name,digest in request['native_review_methods'].items():
            if sha256(folder/'implementation'/name)!=digest:raise ValueError('Changed native bridge method archive')
        _,native,_,_,glb=source(request['source_job'],request['variant'])
        if native['native_review_selection']!=request.get('native_review_selection') or sha256(glb)!=request['source_sha256']:
            raise ValueError('Changed native support parent selection')
    elif 'native_review_selection' in request or 'native_review_methods' in request:
        raise ValueError('Unexpected native support binding')
    return request


def fitting_binding(folder,request):
    """Separate original snapshot from explicitly prepared fitting input."""
    if not request.get('prepare_rigid_input',False):
        return folder/'source.glb',folder/'draft.json',None
    receipt=read(folder/'preparation-binding.json')
    expected='native-support-rigid-'+folder.name
    if receipt['folder']!=expected:raise ValueError('Invalid rig preparation folder')
    prepared=ROOT/'reports'/expected
    if sha256(prepared/'result.json')!=receipt['result_sha256'] or sha256(folder/'prepared-draft.json')!=receipt['draft_sha256']:
        raise ValueError('Changed rig preparation result or draft')
    q,r=read(prepared/'request.json'),read(prepared/'result.json')
    if r['status']!='complete' or r['quality_approved'] is not False or r['source_sha256']!=request['source_sha256'] or q['inputs']!={str(folder/'source.glb'):request['source_sha256']}:
        raise ValueError('Misbound rig preparation')
    for name,digest in r['outputs'].items():
        if Path(name).name!=name or '/' in name or '\\' in name or sha256(prepared/name)!=digest:raise ValueError('Changed rig preparation evidence')
    for name,digest in q['implementation'].items():
        if Path(name).name!=name or '/' in name or '\\' in name or sha256(prepared/'implementation'/name)!=digest:raise ValueError('Changed rig preparation method archive')
    from native_support_rigid_input import STATIC_SCALE_ROUNDOFF,GEOMETRY_CHANGE_LIMIT_M
    comparison=read(prepared/'comparison.json')
    if q['static_scale_roundoff_limit']!=STATIC_SCALE_ROUNDOFF or q['maximum_geometry_change_m']!=GEOMETRY_CHANGE_LIMIT_M or not 0<=r['maximum_vertex_distance_m']<=GEOMETRY_CHANGE_LIMIT_M or comparison['maximum_vertex_distance_m']!=r['maximum_vertex_distance_m'] or comparison['quality_approved'] is not False:
        raise ValueError('Changed rig preparation bounds')
    if not all(comparison[k] is True for k in ('inverse_binds_preserved','mesh_data_preserved','native_animation_bytes_preserved')) or len(comparison['changes'])!=r['changes']:
        raise ValueError('Changed rig preparation preservation evidence')
    source=prepared/'prepared.glb'
    if sha256(source)!=r['prepared_sha256'] or sha256(prepared/'input.glb')!=request['source_sha256']:raise ValueError('Changed prepared or original rig')
    expected_spec=read(folder/'draft.json');expected_spec['glb_sha256']=r['prepared_sha256']
    if read(folder/'prepared-draft.json')!=expected_spec:raise ValueError('Prepared draft changed authoring bounds')
    return source,folder/'prepared-draft.json',dict(folder=expected,original_sha256=request['source_sha256'],
        prepared_sha256=r['prepared_sha256'],result_sha256=receipt['result_sha256'],
        comparison_sha256=r['outputs']['comparison.json'],changes=r['changes'],
        maximum_vertex_distance_m=r['maximum_vertex_distance_m'],sampled_poses=r['sampled_poses'])


def run(folder):
    folder = Path(folder).resolve()
    if folder != folder_for(folder.name).resolve(): raise ValueError('Studio support folder required')
    try:
        import psutil
        save(folder/'worker.json', dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        request = frozen(folder); method=sha256(__file__)
        if method!=read(folder/'prepared.json')['wrapper_sha256']:raise ValueError('Support wrapper changed before fitting')
        for name,digest in request.get('native_review_methods',{}).items():
            if sha256(Path(__file__).parent/name)!=digest:raise ValueError('Native bridge method changed before fitting')
        save(folder/'pipeline.json', dict(status='processing'))
        from native_support_job import run as fit
        # Load numerical libraries before setting their limits. A context
        # entered before those DLLs load cannot constrain the new pools.
        from threadpoolctl import threadpool_limits,threadpool_info
        output = ROOT/'reports'/request['fit_folder']
        with threadpool_limits(limits=1):
            save(folder/'numerical-runtime.json',dict(configured_limit=1,
                pools=[dict(internal_api=p['internal_api'],num_threads=p['num_threads']) for p in threadpool_info()]))
            if request.get('prepare_rigid_input',False):
                from native_support_rigid_input import prepare as prepare_rig
                preparation=ROOT/'reports'/('native-support-rigid-'+folder.name)
                result=prepare_rig(folder/'source.glb',preparation)
                spec=read(folder/'draft.json');spec['glb_sha256']=result['prepared_sha256']
                save(folder/'prepared-draft.json',spec)
                save(folder/'preparation-binding.json',dict(folder=preparation.name,result_sha256=sha256(preparation/'result.json'),draft_sha256=sha256(folder/'prepared-draft.json')))
            source,draft,preparation=fitting_binding(folder,request)
            options=dict(sampled_support_repair=True,sampled_support_iterations=8) if request.get('sampled_support_repair',False) else {}
            if request.get('joint_source_rate_search',False):
                options=dict(joint_rates=True,joint_evaluations=160,joint_swivel=True,joint_foot_orientation=True)
            fit(source,draft,output,**options)
        if request['variant']=='native_review':
            from native_review_support import convert
            convert(folder,request,output)
        frozen(folder)
        fitting_binding(folder,request)
        for name,digest in request.get('native_review_methods',{}).items():
            if sha256(Path(__file__).parent/name)!=digest:raise ValueError('Native bridge method changed during fitting')
        if sha256(__file__)!=method:raise ValueError('Support wrapper changed during fitting')
        save(folder/'completion.json', dict(result_sha256=sha256(output/'result.json'),
            preparation_binding_sha256=sha256(folder/'preparation-binding.json') if preparation else None,
            numerical_runtime_sha256=sha256(folder/'numerical-runtime.json'),
            request_sha256=sha256(folder/'request.json'),
            native_conversion_sha256=sha256(folder/'native-conversion.json') if request['variant']=='native_review' else None,quality_approved=False))
        save(folder/'pipeline.json', dict(status='complete',finished_at=now()))
    except Exception as exc:
        save(folder/'pipeline.json', dict(status='failed',error=str(exc),finished_at=now())); raise


def manifest(job):
    folder = folder_for(job)
    if read(folder/'pipeline.json')['status'] != 'complete': raise ValueError('Support job is not complete')
    request = frozen(folder); completion = read(folder/'completion.json')
    source,draft,preparation=fitting_binding(folder,request)
    if completion.get('numerical_runtime_sha256'):
        if sha256(folder/'numerical-runtime.json')!=completion['numerical_runtime_sha256']:raise ValueError('Changed numerical runtime evidence')
        runtime=read(folder/'numerical-runtime.json')
        if runtime['configured_limit']!=1 or any(p['num_threads']!=1 for p in runtime['pools']):raise ValueError('Unbounded numerical runtime')
    if preparation and completion.get('preparation_binding_sha256')!=sha256(folder/'preparation-binding.json'):raise ValueError('Changed rig preparation binding')
    output = ROOT/'reports'/request['fit_folder']
    if completion['request_sha256'] != sha256(folder/'request.json') or completion['quality_approved'] is not False or sha256(output/'result.json') != completion['result_sha256']:
        raise ValueError('Changed support completion')
    result = read(output/'result.json')
    if result['status'] != 'complete' or result['quality_approved'] is not False: raise ValueError('Unapproved support result required')
    for name, digest in result['outputs'].items():
        if not isinstance(name, str) or Path(name).name != name or '/' in name or '\\' in name or sha256(output/name) != digest:
            raise ValueError('Changed support evidence')
    spec = read(draft); base = f'/files/{NAMESPACE}/{job}/'
    fit_request=read(output/'request.json');refined=request.get('sampled_support_repair',False);joint=request.get('joint_source_rate_search',False)
    if fit_request['spec']!=spec or fit_request['inputs']!={str(source):sha256(source),str(draft):sha256(draft)}:
        raise ValueError('Changed fitting source or authoring draft binding')
    expected_method='joint_support_source_rate_orientation_search' if joint else 'serialized_sampled_support_corridor_refinement' if refined else 'bounded_bend_smoothing'
    if fit_request['proposal_method']!=expected_method or fit_request.get('sampled_support_iterations')!=(8 if refined else None):
        raise ValueError('Changed fitting refinement mode')
    if joint and (fit_request.get('joint_search_maximum_evaluations')!=160 or type(fit_request.get('joint_search_maximum_evaluations')) is not int or fit_request.get('joint_swivel_limit_degrees')!=5. or fit_request.get('joint_foot_orientation_limit_degrees')!=1.):raise ValueError('Changed joint-search budget or motion freedom')
    for name,digest in fit_request['implementation'].items():
        if Path(name).name!=name or '/' in name or '\\' in name or sha256(output/'implementation'/name)!=digest:raise ValueError('Changed fitting method archive')
    def asset(name, label, **extra):
        digest = result['outputs'].get(name)
        if not digest: raise ValueError('Unbound support clip')
        return dict(id=name,url=base+name,sha256=digest,label=label,**extra)
    versions = [asset('input.glb','Prepared input' if preparation else 'Preserved input'), asset('candidate.glb',
        'Retained input' if result['retained_input'] else 'Bounded candidate')]
    if versions[0]['sha256'] != sha256(source) or versions[1]['sha256'] != result['candidate_sha256']:
        raise ValueError('Support candidate binding changed')
    if preparation:
        versions.insert(0,dict(id='original.glb',url=base+'original.glb',sha256=request['source_sha256'],label='Original input'))
        preparation.update(comparison_url=base+'rigid-comparison.json',result_url=base+'rigid-preparation.json')
    trial_screens=[]
    for trial in result['trials']:
        screen={k:trial[k] for k in ('trial','status','reason','supports','source_rates_pass','support_samples_pass','source_rate_failed_rows') if k in trial}
        if joint and trial['status']=='complete':
            evidence=trial['proposal'][0];control=evidence['controls_file'];index=trial['trial']
            if control!=f'trial-{index}.controls.json' or evidence['method']!=expected_method or evidence['maximum_evaluations']!=160 or evidence['orientation_limit_degrees']!=1. or result['outputs'].get(control)!=evidence['controls_sha256']:
                raise ValueError('Changed joint-search control binding')
            controls=read(output/control)
            if controls.get('schema')!='strep-native-support-orientation-controls-v1' or controls.get('proposal_sha256')!=result['outputs'][f'trial-{index}.glb'] or controls.get('orientation_limit_degrees')!=1. or controls.get('swivel_limit_degrees')!=5.:
                raise ValueError('Changed joint-search motion controls')
            screen['joint_search']=dict(evaluations=evidence['evaluations'],maximum_evaluations=160,
                initial_squared_residual=evidence['initial_squared_residual'],final_squared_residual=evidence['final_squared_residual'],
                maximum_native_orientation_edit_degrees=evidence['maximum_native_orientation_edit_degrees'],controls_url=base+control)
        if refined and trial['status']=='complete':
            evidence=trial['proposal'][0];index=trial['trial'];audit=f'trial-{index}-support-repair.json'
            if evidence['method']!='serialized_sampled_support_corridor_refinement' or evidence['iterations_limit']!=8 or evidence['quality_approved'] is not False or read(output/audit)!=evidence:
                raise ValueError('Changed decoded refinement evidence')
            seed=f'trial-{index}-support-seed.glb'
            if evidence['seed_file']!=seed or evidence['seed_sha256']!=result['outputs'][seed]:raise ValueError('Changed refinement seed binding')
            versions.append(asset(seed,f'Proposal {index+1} · before refinement'))
            screen['refinement']=dict(iterations=8,initial_score=evidence['initial_score'],final_score=evidence['final_score'],
                attempts=len(evidence['history']),accepted_steps=sum(h['status']=='accepted' for h in evidence['history']),
                audit_url=base+audit,seed_sha256=evidence['seed_sha256'],sampled_support_pass=evidence['sampled_support_pass'])
        trial_screens.append(screen)
        name = f"trial-{trial['trial']}.glb"
        if name not in result['outputs']: continue
        if trial.get('sha256') and result['outputs'][name] != trial['sha256']: raise ValueError('Changed proposal binding')
        versions.append(asset(name,f"Proposal {trial['trial']+1} · "+('screens met' if trial.get('source_rates_pass') and trial.get('support_samples_pass') else 'failed / rejected checks'), trial=screen))
    native_candidate=None
    if request['variant']=='native_review':
        if sha256(folder/'native-conversion.json')!=completion.get('native_conversion_sha256'):raise ValueError('Changed native conversion receipt')
        native_candidate=read(folder/'native-conversion.json')
        if native_candidate.get('schema')!='strep-native-support-conversion-v1' or native_candidate['selection']!=request['native_review_selection'] or any(native_candidate.get(k) is not False for k in ('quality_approved','training_admitted','release_approved')):
            raise ValueError('Changed native conversion selection or approval')
        for key,name in (('candidate_motion','native-candidate.npz'),('proposal','native-proposal.npz')):
            ref=native_candidate[key]
            if Path(ref['path']).resolve()!=folder/name or sha256(folder/name)!=ref['sha256']:raise ValueError('Changed native conversion pose tracks')
        from studio_correction_review import served_preview
        preview=native_candidate['preview'];path=served_preview(preview['preview_url'].removeprefix('/files/'))
        if path is None or sha256(path)!=preview['preview_sha256']:raise ValueError('Changed native support candidate preview')
        versions[1]['label']='Fitter output before native conversion'
        versions.insert(1,dict(id='native-selected',url=preview['preview_url'],sha256=preview['preview_sha256'],
            label='Native retained input' if native_candidate['retained_input'] else 'Native selected candidate'))
        events=native_candidate.get('selected_support_events')
        if events:
            if Path(events['path']).resolve()!=folder/'native-support-events.json' or sha256(events['path'])!=events['sha256']:
                raise ValueError('Changed native selected support markers')
            if read(events['path'])['target_clip_sha256']!=preview['preview_sha256']:
                raise ValueError('Native support markers belong to another selected clip')
    return dict(id=job, duration_s=spec['duration_s'], supports=spec['supports'], versions=versions,preparation=preparation,
        native_review_candidate=native_candidate,
        refinement=dict(iterations=8) if refined else None,
        joint_search=dict(maximum_evaluations=160,swivel_limit_degrees=5.,orientation_limit_degrees=1.) if joint else None,
        result_sha256=completion['result_sha256'], result_url=base+'result.json',
        native_conversion_url=base+'native-conversion.json' if native_candidate else None,
        events_url=base+('native-support-events.json' if native_candidate and native_candidate.get('selected_support_events') else 'support-events.json'), root_url=base+'root-motion.json',
        retained_input=native_candidate['retained_input'] if native_candidate else result['retained_input'],
        retention_reason=native_candidate['retention_reason'] if native_candidate else result['retention_reason'],
        output_support_samples_pass=native_candidate['selected_support_samples_pass'] if native_candidate else result['output_support_samples_pass'],
        fitted_retained_input=result['retained_input'],fitted_retention_reason=result['retention_reason'],
        fitted_output_support_samples_pass=result['output_support_samples_pass'],
        source_supports=result['source_supports'], trials=trial_screens, quality_approved=False,
        scope='Sampled foot-region height and source-relative rates; no whole-sole, physics, collision, engine or human approval')


def listing():
    from contact_edit_job import observed_state
    jobs = []
    for folder in sorted((ROOT/'reports'/NAMESPACE).glob('*'), reverse=True):
        if not (folder/'request.json').is_file(): continue
        try:
            request = frozen(folder); state = observed_state(folder)
            item = dict(id=folder.name, source_job=request['source_job'],variant=request['variant'],**state)
            if state['status'] == 'complete': item['review'] = manifest(folder.name)
        except (ValueError,OSError,KeyError,TypeError) as exc: item = dict(id=folder.name,status='failed',error=str(exc))
        jobs.append(item)
    return dict(jobs=jobs)


def served_file(relative):
    try:
        parts = relative.split('/')
        if len(parts) != 3 or parts[0] != NAMESPACE: return None
        _, job, name = parts; folder = folder_for(job)
        review = manifest(job); request = frozen(folder); output = ROOT/'reports'/request['fit_folder']
        result = read(output/'result.json')
        if name in ('native-support-events.json','native-conversion.json'):
            native=review['native_review_candidate']
            if native and (name=='native-conversion.json' or native.get('selected_support_events')):
                return folder/name
            return None
        if review['preparation'] and name in ('original.glb','rigid-comparison.json','rigid-preparation.json'):
            if name=='original.glb':return folder/'source.glb'
            prepared=ROOT/'reports'/review['preparation']['folder']
            return prepared/('comparison.json' if name=='rigid-comparison.json' else 'result.json')
        allowed = set(result['outputs']) | {'result.json'}
        if name not in allowed: return None
        target = output/name
        digest = review['result_sha256'] if name == 'result.json' else result['outputs'][name]
        return target if sha256(target) == digest else None
    except (ValueError,OSError,KeyError,TypeError): return None


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=1): run(args.folder)
