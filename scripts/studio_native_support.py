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


def folder_for(job):
    if not isinstance(job, str) or not NAME.fullmatch(job): raise ValueError('Invalid native support job')
    base=(ROOT/'reports'/NAMESPACE).resolve(); folder=(base/job).resolve()
    if folder.parent!=base: raise ValueError('Support job escapes its namespace')
    return folder


def metadata(job, variant):
    from rig_contact_authoring import source
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    _, result, _, report, glb = source(job, variant)
    digest = sha256(glb); rig = RigAsset.load(glb)
    if len(rig.document.get('animations', [])) != 1: raise ValueError('One chosen animation required')
    reader = NativeSupportSampler(rig.document, rig.binary, 0)
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
        joints=[dict(node=n, name=rig.document['nodes'][n].get('name'), parent=rig.parents[n], **tracks.get(n, {})) for n in rig.joints],
        root_node=report['root_node'], mapping={k:v for k,v in report['mapping'].items() if k in
            {s+n for s in ('Left','Right') for n in ('Leg','Shin','Foot')}},
        source_url=f'/files/rig-jobs/{job}/{variant}/character.glb', quality_approved=False)


def validate_request(payload):
    from rig_contact_authoring import source
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    from native_support_spec import validate
    if not isinstance(payload, dict) or set(payload) != {'source_job','variant','spec'}:
        raise ValueError('Selected source job, version and native support draft required')
    _, _, _, report, glb = source(payload['source_job'], payload['variant'])
    spec = copy.deepcopy(payload['spec']); digest = sha256(glb); rig = RigAsset.load(glb)
    if len(rig.document.get('animations', [])) != 1: raise ValueError('One chosen animation required')
    reader = NativeSupportSampler(rig.document, rig.binary, 0)
    if not isinstance(spec, dict) or spec.get('root_node') != report['root_node']:
        raise ValueError('Use the selected clip mapped root')
    validate(spec, rig, reader, digest)
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
        fit_folder='native-support-fit-'+folder.name, quality_approved=False)
    save(folder/'request.json', request)
    archive=folder/'implementation';archive.mkdir()
    shutil.copyfile(__file__,archive/'studio_native_support.py')
    save(folder/'prepared.json', dict(request_sha256=sha256(folder/'request.json'),wrapper_sha256=sha256(archive/'studio_native_support.py')))
    save(folder/'pipeline.json', dict(status='starting'))
    return request


def frozen(folder):
    request = read(folder/'request.json'); prepared = read(folder/'prepared.json')
    if sha256(folder/'request.json') != prepared['request_sha256'] or request['quality_approved'] is not False:
        raise ValueError('Changed native support request')
    if request['fit_folder'] != 'native-support-fit-'+folder.name: raise ValueError('Invalid support output')
    if sha256(folder/'source.glb') != request['source_sha256'] or sha256(folder/'draft.json') != request['draft_sha256']:
        raise ValueError('Changed native support snapshot')
    if sha256(folder/'implementation/studio_native_support.py')!=prepared['wrapper_sha256']:
        raise ValueError('Changed support wrapper archive')
    return request


def run(folder):
    folder = Path(folder).resolve()
    if folder != folder_for(folder.name).resolve(): raise ValueError('Studio support folder required')
    try:
        import psutil
        save(folder/'worker.json', dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        request = frozen(folder); method=sha256(__file__)
        if method!=read(folder/'prepared.json')['wrapper_sha256']:raise ValueError('Support wrapper changed before fitting')
        save(folder/'pipeline.json', dict(status='processing'))
        from native_support_job import run as fit
        output = ROOT/'reports'/request['fit_folder']
        fit(folder/'source.glb', folder/'draft.json', output)
        frozen(folder)
        if sha256(__file__)!=method:raise ValueError('Support wrapper changed during fitting')
        save(folder/'completion.json', dict(result_sha256=sha256(output/'result.json'),
            request_sha256=sha256(folder/'request.json'), quality_approved=False))
        save(folder/'pipeline.json', dict(status='complete',finished_at=now()))
    except Exception as exc:
        save(folder/'pipeline.json', dict(status='failed',error=str(exc),finished_at=now())); raise


def manifest(job):
    folder = folder_for(job)
    if read(folder/'pipeline.json')['status'] != 'complete': raise ValueError('Support job is not complete')
    request = frozen(folder); completion = read(folder/'completion.json')
    output = ROOT/'reports'/request['fit_folder']
    if completion['request_sha256'] != sha256(folder/'request.json') or completion['quality_approved'] is not False or sha256(output/'result.json') != completion['result_sha256']:
        raise ValueError('Changed support completion')
    result = read(output/'result.json')
    if result['status'] != 'complete' or result['quality_approved'] is not False: raise ValueError('Unapproved support result required')
    for name, digest in result['outputs'].items():
        if not isinstance(name, str) or Path(name).name != name or '/' in name or '\\' in name or sha256(output/name) != digest:
            raise ValueError('Changed support evidence')
    spec = read(folder/'draft.json'); base = f'/files/{NAMESPACE}/{job}/'
    def asset(name, label, **extra):
        digest = result['outputs'].get(name)
        if not digest: raise ValueError('Unbound support clip')
        return dict(id=name,url=base+name,sha256=digest,label=label,**extra)
    versions = [asset('input.glb','Preserved input'), asset('candidate.glb',
        'Retained input' if result['retained_input'] else 'Bounded candidate')]
    if versions[0]['sha256'] != request['source_sha256'] or versions[1]['sha256'] != result['candidate_sha256']:
        raise ValueError('Support candidate binding changed')
    trial_screens=[]
    for trial in result['trials']:
        screen={k:trial[k] for k in ('trial','status','reason','supports','source_rates_pass','support_samples_pass','source_rate_failed_rows') if k in trial}
        trial_screens.append(screen)
        name = f"trial-{trial['trial']}.glb"
        if name not in result['outputs']: continue
        if trial.get('sha256') and result['outputs'][name] != trial['sha256']: raise ValueError('Changed proposal binding')
        versions.append(asset(name,f"Proposal {trial['trial']+1} · "+('screens met' if trial.get('source_rates_pass') and trial.get('support_samples_pass') else 'failed / rejected checks'), trial=screen))
    return dict(id=job, duration_s=spec['duration_s'], supports=spec['supports'], versions=versions,
        result_sha256=completion['result_sha256'], result_url=base+'result.json',
        events_url=base+'support-events.json', root_url=base+'root-motion.json',
        retained_input=result['retained_input'], retention_reason=result['retention_reason'],
        output_support_samples_pass=result['output_support_samples_pass'],
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
