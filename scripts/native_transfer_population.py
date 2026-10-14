"""Checksum-bound multi-action rig-transfer study; preserve every planned row."""
import argparse
import copy
import math
from pathlib import Path
import re
import shutil
import time
import os
import numpy as np
from threadpoolctl import threadpool_limits
import native_rig_transfer as bridge
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from rig_floor_comparison import compare
from engine_contact_sampling import frame_populations,contract_sha256
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-transfer-population-v1'
METHODS=tuple(dict.fromkeys(bridge.METHODS+('native_transfer_population.py','rig_floor_comparison.py','engine_contact_sampling.py')))
FLAGS=dict(original_selected=True,quality_approved=False,release_approved=False)


def require(value,message):
    if not value:raise ValueError(message)


def finite(value):return type(value) in (int,float) and math.isfinite(value)


def validate(value,base):
    require(isinstance(value,dict) and set(value)=={'schema','rate_hz','floor','scope','cases'} and value['schema']==SCHEMA,'Explicit population protocol required')
    require(type(value['rate_hz']) is int and value['rate_hz'] in (60,120,240),'Explicit native transfer rate required')
    floor=value['floor'];require(isinstance(floor,dict) and set(floor)=={'y_m','tolerance_m'} and all(finite(v) for v in floor.values()) and floor['tolerance_m']>0,'Explicit finite floor diagnostic required')
    require(isinstance(value['scope'],str) and 0<len(value['scope'])<=4000,'Explicit development scope required')
    cases=value['cases'];require(isinstance(cases,list) and 1<=len(cases)<=96,'Complete bounded case population required')
    result=copy.deepcopy(value);ids=set()
    for case in result['cases']:
        require(isinstance(case,dict) and set(case)=={'id','source','target','metadata'} and isinstance(case['id'],str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',case['id']) and case['id'] not in ids,'Distinct explicit case IDs required');ids.add(case['id'])
        require(isinstance(case['metadata'],dict) and all(isinstance(k,str) and isinstance(v,str) and len(v)<=256 for k,v in case['metadata'].items()),'Short metadata labels required; actions are not a whitelist')
        for side in ('source','target'):
            fields={'glb','profile','animation_index'} if side=='source' else {'glb','profile'}
            require(isinstance(case[side],dict) and set(case[side])==fields,'Explicit source/target bindings required')
            for name in ('glb','profile'):
                item=case[side][name];require(isinstance(item,dict) and set(item)=={'path','sha256'} and isinstance(item['path'],str) and isinstance(item['sha256'],str) and re.fullmatch('[a-f0-9]{64}',item['sha256']),'Exact artifact checksum required')
                path=(base/item['path']).resolve();require(path.is_file() and path.suffix==('.glb' if name=='glb' else '.json') and sha256(path)==item['sha256'],'Bound artifact missing or changed');item['path']=str(path)
        require(type(case['source']['animation_index']) is int and case['source']['animation_index']>=0,'Explicit source clip index required')
    return result


def unchanged(folder,protocol):
    freeze=read(folder/'freeze.json')
    require(sha256(folder/'protocol.json')==freeze['protocol_sha256'],'Study protocol changed')
    require(sha256(folder/'original-protocol.json')==freeze['original_protocol_sha256'] and contract_sha256()==freeze['frame_contract_sha256'],'Original protocol or frame contract changed')
    require(all(sha256(ROOT/'scripts'/n)==h==sha256(folder/'implementation'/n) for n,h in freeze['methods_sha256'].items()),'Study methods changed')
    for case in protocol['cases']:
        for side in ('source','target'):
            for name in ('glb','profile'):
                item=case[side][name];require(sha256(item['path'])==item['sha256'],'Original study input changed')


def prepare(protocol_path,digest,output):
    protocol_path,output=Path(protocol_path).resolve(),Path(output).resolve()
    require(not output.exists() and protocol_path.stat().st_size<=4*1024**2 and sha256(protocol_path)==digest,'Fresh output and explicit bounded protocol digest required')
    protocol=validate(read(protocol_path),protocol_path.parent)
    require(all(not Path(c[s][n]['path']).is_relative_to(output) for c in protocol['cases'] for s in ('source','target') for n in ('glb','profile')),'Inputs must remain outside output')
    output.mkdir(parents=True);shutil.copyfile(protocol_path,output/'original-protocol.json');save(output/'protocol.json',protocol)
    archive=output/'implementation';archive.mkdir();methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
    save(output/'freeze.json',dict(original_protocol_sha256=digest,protocol_sha256=sha256(output/'protocol.json'),methods_sha256=methods,frame_contract_sha256=contract_sha256()))
    save(output/'progress.json',dict(cases=[dict(id=c['id'],status='pending') for c in protocol['cases']],**FLAGS));save(output/'pipeline.json',dict(status='prepared',**FLAGS));unchanged(output,protocol)
    require(sha256(protocol_path)==digest,'Original protocol changed during preparation');return protocol


def checked_row(folder,row):
    require(row['status'] in ('complete','failed') and isinstance(row.get('artifacts'),dict),'Terminal row receipt required')
    attempt=(folder/row['attempt']).resolve();require(attempt.is_relative_to((folder/'cases'/row['id']).resolve()),'Contained case attempt required')
    actual={str(p.relative_to(folder)) for p in attempt.rglob('*') if p.is_file()}
    require(set(row['artifacts'])==actual and str((attempt/'case-receipt.json').relative_to(folder)) in actual,'Complete case artifact population required')
    for relative,digest in row['artifacts'].items():
        path=(folder/relative).resolve();require(path.is_relative_to(folder.resolve()) and sha256(path)==digest,'Recorded case artifact changed')
    require(read(attempt/'case-receipt.json')==dict({k:v for k,v in row.items() if k!='artifacts'},**FLAGS),'Recorded case summary changed')


def run(folder,*,resume=False,maximum_seconds=700):
    folder=Path(folder).resolve();require(finite(maximum_seconds) and 1<=maximum_seconds<=750,'Bounded phase-start time budget required')
    protocol=read(folder/'protocol.json');unchanged(folder,protocol);state=read(folder/'pipeline.json')
    require(not (folder/'result.json').exists(),'Completed population cannot be restarted')
    require(resume or state['status']=='prepared','Started population requires explicit resume')
    if resume and (folder/'runner.json').exists():
        import psutil
        identity=read(folder/'runner.json')
        try:
            process=psutil.Process(identity['pid']);live=process.is_running() and process.create_time()==identity['created_at']
        except psutil.NoSuchProcess:live=False
        require(not live,'Previous population worker is still live')
    import psutil
    save(folder/'runner.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
    rows=read(folder/'progress.json')['cases'];require([r['id'] for r in rows]==[c['id'] for c in protocol['cases']],'Complete planned row population required')
    for row in rows:
        if row['status']!='pending':checked_row(folder,row)
    deadline=time.monotonic()+maximum_seconds
    save(folder/'pipeline.json',dict(status='processing',**FLAGS))
    for case,row in zip(protocol['cases'],rows):
        if row['status']!='pending':continue
        if time.monotonic()>=deadline:save(folder/'pipeline.json',dict(status='deferred',reason='phase_start_budget',**FLAGS));return
        unchanged(folder,protocol);home=folder/'cases'/case['id'];home.mkdir(parents=True,exist_ok=True)
        attempts=list(home.glob('attempt-*'));attempt=home/f'attempt-{len(attempts):04d}';attempt.mkdir()
        save(folder/'pipeline.json',dict(status='processing',case=case['id'],attempt=str(attempt.relative_to(folder)),**FLAGS))
        try:
            inputs=[]
            for side in ('source','target'):
                for name in ('glb','profile'):
                    source=case[side][name];target=attempt/(side+('-profile.json' if name=='profile' else '.glb'));shutil.copyfile(source['path'],target)
                    require(sha256(target)==source['sha256'],'Input snapshot changed');inputs.append(target)
            try:report=bridge.export(*inputs,case['source']['animation_index'],attempt/'transfer',protocol['rate_hz'])
            except ValueError as error:
                # A measured fidelity failure still has a diagnostic export.
                if not (attempt/'transfer/report.json').is_file():raise
                report=read(attempt/'transfer/report.json')
                require(report['schema']=='strep-native-rig-transfer-v1' and report['status']=='failed'
                    and sha256(attempt/'transfer/character.glb')==report['glb_sha256'],'Bound rejected transfer required')
                row['transfer_error']=str(error)
            with worker_lock(),threadpool_limits(limits=1):
                samplers=[NativeSupportSampler(r.document,r.binary,i) for r,i in [(RigAsset.load(inputs[0]),case['source']['animation_index']),(RigAsset.load(attempt/'transfer/character.glb'),report['output_animation_index'])]]
                require(samplers[0].duration==samplers[1].duration,'Transfer extended the source duration')
                duration=samplers[0].duration;groups=[np.array([0.,duration])]+[p['times_s'] for p in frame_populations([0.,duration])]
                for sampler in samplers:
                    for c in sampler.channels:groups.extend([c[2],(c[2][:-1].astype(float)+c[2][1:].astype(float))/2])
                times=np.unique(np.concatenate(groups));require(len(times)<=20000,'Complete comparison clock exceeds capacity; no decimation')
                floor=compare(inputs[0],attempt/'transfer/character.glb',times,source_animation=case['source']['animation_index'],target_animation=report['output_animation_index'],floor_y_m=protocol['floor']['y_m'],tolerance_m=protocol['floor']['tolerance_m'])
                save(attempt/'floor-comparison.json',floor)
            row.update(status='complete',transfer_fidelity_pass=report['fidelity']['passed'],scale=report['scale_from_mean_leg_lengths'],samples=floor['samples'],
                source_floor_pass=floor['source']['sampled_floor_pass'],target_floor_pass=floor['target']['sampled_floor_pass'],
                source_peak_depth_m=floor['source']['maximum_depth_m'],target_peak_depth_m=floor['target']['maximum_depth_m'],
                source_failed_samples=floor['source']['failed_samples'],target_failed_samples=floor['target']['failed_samples'])
        except Exception as error:row.update(status='failed',error_type=type(error).__name__,error=str(error))
        row['attempt']=str(attempt.relative_to(folder));save(attempt/'case-receipt.json',dict(row,**FLAGS))
        row['artifacts']={str(p.relative_to(folder)):sha256(p) for p in attempt.rglob('*') if p.is_file()}
        unchanged(folder,protocol);save(folder/'progress.json',dict(cases=rows,**FLAGS))
    for row in rows:checked_row(folder,row)
    unchanged(folder,protocol)
    save(folder/'result.json',dict(schema=SCHEMA,status='complete',at=now(),protocol_sha256=sha256(folder/'protocol.json'),cases=rows,
        planned=len(rows),completed=sum(r['status']=='complete' for r in rows),failed=sum(r['status']=='failed' for r in rows),
        fidelity_passes=sum(r.get('transfer_fidelity_pass') is True for r in rows),target_floor_passes=sum(r.get('target_floor_pass') is True for r in rows),
        frame_contract_sha256=contract_sha256(),engine_executed=False,contact_verified=False,continuous_collision_certified=False,human_reviewed=False,
        scope='All declared source/target cases retained. Native transfer fidelity and complete sampled floor comparison only; no semantic, support, physics, engine or human approval.',**FLAGS))
    save(folder/'pipeline.json',dict(status='complete',**FLAGS))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('protocol',type=Path);p.add_argument('output',type=Path);p.add_argument('--protocol-sha256',required=True)
    p=sub.add_parser('run');p.add_argument('folder',type=Path);p.add_argument('--resume',action='store_true');p.add_argument('--maximum-seconds',type=float,default=700)
    a=parser.parse_args()
    if a.command=='prepare':prepare(a.protocol,a.protocol_sha256,a.output)
    else:run(a.folder,resume=a.resume,maximum_seconds=a.maximum_seconds)
