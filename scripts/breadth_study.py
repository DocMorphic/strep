"""Resume frozen breadth batches without replacing completed or failed attempts."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import psutil
from strep import ROOT, read, save, sha256, now, offline_environment, source_check
from action_requests import request_digest

STUDY=ROOT/'reports/breadth-baseline-v2'


def validate_freeze(study):
    frozen=read(study/'freeze.json')
    if sha256(study/'protocol.json')!=frozen['protocol_sha256']:raise ValueError('Frozen protocol changed')
    if source_check()!=frozen['kimodo_commit']:raise ValueError('Pinned source changed')
    for file,key in [('benchmarks/sources.lock.json','source_lock_sha256'),('models/manifest.json','model_manifest_sha256')]:
        if sha256(ROOT/file)!=frozen[key]:raise ValueError('Frozen source/model acquisition changed')
    for name,digest in frozen['implementation_sha256'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Frozen implementation changed: '+name)
    for item in frozen['batches']:
        if sha256(ROOT/item['request'])!=item['request_sha256'] or request_digest(read(ROOT/item['request']))!=item['request_digest']:
            raise ValueError('Frozen request changed: '+item['id'])
    return frozen


def verify_complete(item):
    folder=ROOT/item['output'];batch=read(ROOT/item['request'])
    if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Batch is not complete')
    if request_digest(read(folder/'request.json'))!=item['request_digest']:raise ValueError('Saved request changed')
    expected={(r['id'],s):r for r in batch['requests'] for s in r['seeds']}
    trials=read(folder/'summary.json')['trials']
    if len(trials)!=len(expected) or {(t['request_id'],t['seed']) for t in trials}!=set(expected):raise ValueError('Missing or duplicate exported take')
    for trial in trials:
        if trial['request']!=expected[(trial['request_id'],trial['seed'])]:raise ValueError('Exported prompt changed')
        directory=folder/'takes'/trial['id']
        if not directory.resolve().is_relative_to((folder/'takes').resolve()):raise ValueError('Take path escapes output')
        for name,digest in trial['hashes'].items():
            path=(directory/name).resolve()
            if not path.is_relative_to(directory.resolve()) or sha256(path)!=digest:raise ValueError('Export changed: '+str(path))
        if read(directory/'evidence.json')!={k:v for k,v in trial.items() if k!='hashes'}:
            raise ValueError('Summary differs from its saved evidence')
    return trials


def summarize(spec, results, surfaces=None):
    """Keep every planned case/actor/seed in denominators, including missing outputs."""
    rows=[];surfaces=surfaces or {}
    for case in spec['cases']:
        for actor in case['actors']:
            for seed in case['seeds']:
                trial=results.get((case['id']+'-'+actor['id'].lower(),seed))
                metrics=trial.get('metrics',{}) if trial else {}
                depth=metrics.get('max_joint_ground_penetration_m')
                speed=(metrics.get('foot_horizontal_speed_predicted_contact_m_s') or {}).get('p95')
                eligible=case['flat_floor_screen_applicable']
                surface=surfaces.get((case['id']+'-'+actor['id'].lower(),seed))
                rows.append({'case':case['id'],'family':case['family'],'actor':actor['id'],'seed':seed,
                    'exported':trial is not None,'context':case['context'],'scene_validation':case['scene_validation'],
                    'flat_floor_screen_applicable':eligible,'joint_floor_depth_m':depth,'predicted_foot_speed_p95_m_s':speed,
                    'mesh_floor_depth_m':surface['mesh_max_depth_m'] if surface else None,
                    'mesh_floor_screen':surface['mesh_max_depth_m']<=.01 if surface and eligible else None,
                    'joint_floor_screen':depth<=spec['screens']['joint_floor_depth_m'] if eligible and depth is not None else None,
                    'predicted_foot_speed_screen':speed<=spec['screens']['predicted_foot_speed_p95_m_s'] if eligible and speed is not None else None,
                    'semantic_rating':None,'independent_human_review':False,'quality_approved':False,
                    'original_export_flags':trial.get('flags') if trial else None})
    families=[]
    for family in dict.fromkeys(c['family'] for c in spec['cases']):
        group=[r for r in rows if r['family']==family]
        families.append({'family':family,'planned_actor_clips':len(group),'exported':sum(r['exported'] for r in group),
                         'human_reviewed':0,'supported_actions_established':0,
                         'missing_scene_checks':sum(r['scene_validation']=='missing_required_context_validation' for r in group)})
    return {'planned_cases':len(spec['cases']),'planned_actor_clips':len(rows),'exported':sum(r['exported'] for r in rows),
            'families':families,'rows':rows,'quality_approved':False,
            'qualification':'Raw generation/export availability is not action support, scene validity, physical realism or release acceptance. Missing scores stay null.'}


def report(study):
    frozen=read(study/'freeze.json');spec=read(study/'protocol.json');results={};batches=[];surfaces={}
    for item in frozen['batches']:
        folder=ROOT/item['output'];status=read(folder/'pipeline.json')['status'] if (folder/'pipeline.json').exists() else 'pending'
        if status=='complete':
            for trial in verify_complete(item):results[(trial['request_id'],trial['seed'])]=trial
        audit=study/'surface'/f'{item["id"]}.json'
        if audit.exists():
            for entry in read(audit)['trials']:
                if entry['result'] is not None:surfaces[(entry['request_id'],entry['seed'])]=entry['result']
        generated=sum(read(p).get('status')=='generated' for p in folder.glob('raw/*/seed-*/attempt-*/record.json'))
        batches.append({'id':item['id'],'status':status,'generated_attempts':generated})
    result=summarize(spec,results,surfaces);result.update(at=now(),batches=batches)
    save(study/'coverage.json',result);return result


def surface_audit(study,identifier):
    import numpy as np
    from audit_body_ground import measure
    from build_soma_preview import ASSET
    item=next(i for i in read(study/'freeze.json')['batches'] if i['id']==identifier)
    cases={c['id']+'-'+a['id'].lower():c for c in read(study/'protocol.json')['cases'] for a in c['actors']}
    destination=study/'surface'/f'{identifier}.json'
    if destination.exists():raise ValueError('Preserve the existing surface audit')
    skin=dict(np.load(ASSET,allow_pickle=False));trials=[]
    for trial in verify_complete(item):
        result=None
        if cases[trial['request_id']]['flat_floor_screen_applicable']:
            path=ROOT/item['output']/'takes'/trial['id']/'motion.npz'
            if sha256(path)!=trial['source_sha256']:raise ValueError('Motion changed before surface audit')
            result=measure(dict(np.load(path,allow_pickle=False)),skin)
            print(trial['id']+f' / mesh-floor depth {result["mesh_max_depth_m"]:.5f} m',flush=True)
        trials.append({'request_id':trial['request_id'],'seed':trial['seed'],'source_sha256':trial['source_sha256'],'result':result})
    save(destination,{'at':now(),'trials':trials,'method_sha256':sha256(ROOT/'scripts/audit_body_ground.py'),
                      'mesh_sha256':sha256(ASSET),'scope':'All vertices and frames for declared flat-floor cases. Context-dependent cases are null, not passed.'})


def copy_cache(request,source,target):
    from action_worker_lock import worker_lock
    with worker_lock():
        from action_encoder import ActionEncoder
        from action_requests import conditioning_texts
        batch=read(request);original=read(source/'request.json');ActionEncoder(source/'conditioning',original)
        meta=copy.deepcopy(read(source/'conditioning/manifest.json'))
        if sorted(meta['entries'])!=conditioning_texts(batch):raise ValueError('Seed shard texts differ')
        if target.exists():
            ActionEncoder(target,batch);return
        target.mkdir()
        for item in meta['entries'].values():
            shutil.copyfile(source/'conditioning'/item['file'],target/item['file'])
            if sha256(target/item['file'])!=item['sha256']:raise ValueError('Copied tensor changed')
        meta.update(request_sha256=request_digest(batch),reuse_provenance={'source':str(source/'conditioning'),
            'source_manifest_sha256':sha256(source/'conditioning/manifest.json'),'copied_at':now(),
            'reason':'Same frozen prompts and validated encoder; only seeds differ. Tensor bytes unchanged.'})
        save(target/'manifest.json',meta);ActionEncoder(target,batch)


def run(study):
    frozen=validate_freeze(study)
    execution=study/'execution-freeze.json';current={'runner_sha256':sha256(Path(__file__)),
        'surface_method_sha256':sha256(ROOT/'scripts/audit_body_ground.py'),'surface_threshold_m':.01}
    if execution.exists() and read(execution)!=current:raise ValueError('Runner changed; preserve and explicitly revise execution protocol')
    save(execution,current)
    from action_worker_lock import worker_busy
    from process_monitor import kill_tree
    owner=psutil.Process()
    state={'status':'running','started_at':now(),'pid':owner.pid,'created_at':owner.create_time()}
    save(study/'runner.json',state)
    try:
        for item in frozen['batches']:
            folder=ROOT/item['output']
            if (folder/'pipeline.json').exists():
                previous=read(folder/'pipeline.json')['status']
                if previous=='complete':
                    verify_complete(item)
                    if not (study/'surface'/f'{item["id"]}.json').exists():
                        raise ValueError('Complete generation still needs its surface audit: '+item['id'])
                    continue
                raise ValueError('Existing non-complete batch requires investigation, not automatic retry: '+item['id'])
            while worker_busy():
                save(study/'pipeline.json',{'status':'waiting_for_local_worker','batch':item['id']});time.sleep(5)
            folder.mkdir(parents=True,exist_ok=False)
            commands=[]
            if item['reuse_from']:
                commands.append(('reuse-conditioning',[sys.executable,'-u',str(Path(__file__)),'cache',str(ROOT/item['request']),str(ROOT/item['reuse_from']),str(folder/'conditioning')]))
            commands.append(('pipeline',[sys.executable,'-u',str(ROOT/'scripts/run_actions.py'),str(ROOT/item['request']),'--output',str(folder)]))
            commands.append(('surface-audit',[sys.executable,'-u',str(Path(__file__)),'surface',item['id'],'--study',str(study)]))
            for stage,command in commands:
                save(study/'pipeline.json',{'status':'running','batch':item['id'],'stage':stage,'started_at':state['started_at']})
                print(item['id']+' / '+stage,flush=True)
                with (folder/(stage+'-supervisor.log')).open('a',encoding='utf-8') as log:
                    process=subprocess.Popen(command,cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                    save(study/'runner.json',{**state,'batch':item['id'],'stage':stage,'child_pid':process.pid,'child_created_at':psutil.Process(process.pid).create_time()})
                    try:code=process.wait()
                    finally:
                        if process.poll() is None:kill_tree(process.pid)
                    if code:raise RuntimeError(f'{item["id"]}/{stage} exited {code}; prior attempts retained')
            verify_complete(item);result=report(study)
            print(f'Exported {result["exported"]}/{result["planned_actor_clips"]} planned actor clips',flush=True)
        result=report(study)
        if result['exported']!=read(study/'protocol.json')['expected_actor_clips']:raise ValueError('Planned outputs missing')
        save(study/'pipeline.json',{'status':'complete','finished_at':now(),'scope':'Raw breadth baseline only; quality and scene acceptance unproven'})
    except BaseException as exc:
        save(study/'pipeline.json',{'status':'failed','finished_at':now(),'error':str(exc)})
        raise
    finally:
        save(study/'runner.json',{**state,'status':'stopped','finished_at':now()})


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    for command in ['run','report']:
        p=sub.add_parser(command);p.add_argument('--study',type=Path,default=STUDY)
    p=sub.add_parser('surface');p.add_argument('identifier');p.add_argument('--study',type=Path,default=STUDY)
    p=sub.add_parser('cache');p.add_argument('request',type=Path);p.add_argument('source',type=Path);p.add_argument('target',type=Path)
    args=parser.parse_args()
    if args.command=='run':run(args.study)
    elif args.command=='report':print(report(args.study)['exported'])
    elif args.command=='surface':surface_audit(args.study,args.identifier)
    else:copy_cache(args.request,args.source,args.target)
