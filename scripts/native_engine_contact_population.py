"""Audit a frozen population of source/candidate contacts without selecting clips.

Every case uses the same fixed frame contract. Failed imports stay unavailable;
failed contact results stay failed. Metadata is an author label, not verification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from strep import ROOT,read,save,sha256,now
from native_engine_contacts import run as audit_engine
from native_review_support import method_names
from engine_contact_sampling import contract,contract_sha256


def methods():
    names=set(method_names())|{'native_engine_contact_population.py','native_engine_contacts.py',
        'engine_contact_sampling.py','native_contact_diagnostics.py','native_foot_plant.py',
        'godot_contact_audit.gd','strep.py'}
    return {str(ROOT/'scripts'/n):sha256(ROOT/'scripts'/n) for n in sorted(names)}


def resolve_manifest(path):
    path=Path(path).resolve();raw=path.read_bytes();spec=json.loads(raw)
    if (not isinstance(spec,dict) or set(spec)!={'schema','scope','cases'}
            or spec['schema']!='strep-native-engine-contact-population-v1'
            or not isinstance(spec['scope'],str) or not 1<=len(spec['scope'])<=2000
            or not isinstance(spec['cases'],list) or not 1<=len(spec['cases'])<=1024):
        raise ValueError('Explicit nonempty source-bound contact population required')
    cases=[];ids=set();inputs={str(path):hashlib.sha256(raw).hexdigest()}
    for case in spec['cases']:
        if (not isinstance(case,dict) or set(case)!={'id','source','candidate','base','draft','policy','metadata'}
                or not isinstance(case['id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',case['id'])
                or case['id'] in ids or not isinstance(case['metadata'],dict)
                or set(case['metadata'])-{'action','rig','candidate_role','original_selection'}
                or any(not isinstance(v,str) or not 1<=len(v)<=200 for v in case['metadata'].values())):
            raise ValueError('Distinct named cases and explicit label metadata required')
        ids.add(case['id']);resolved=dict(id=case['id'],metadata=dict(case['metadata']))
        for role in ('source','candidate','base','draft','policy'):
            ref=case[role]
            if (not isinstance(ref,dict) or set(ref)!={'path','sha256'} or not isinstance(ref['path'],str)
                    or not ref['path'] or not isinstance(ref['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',ref['sha256'])):
                raise ValueError('Every input needs an explicit path and SHA-256')
            file=(path.parent/ref['path']).resolve()
            if not file.is_file() or sha256(file)!=ref['sha256']:
                raise ValueError('Population input is missing or differs from its frozen hash')
            inputs[str(file)]=ref['sha256'];resolved[role]=str(file)
        cases.append(resolved)
    return spec,cases,inputs


def unchanged(bindings):
    if any(not Path(p).is_file() or sha256(p)!=h for p,h in bindings.items()):
        raise ValueError('Population inputs or implementation changed')


def run(manifest,output):
    manifest,output=Path(manifest).resolve(),Path(output).resolve()
    spec,cases,inputs=resolve_manifest(manifest);implementation=methods()
    output.mkdir(parents=True,exist_ok=False);archive=output/'implementation';archive.mkdir()
    for p in implementation:shutil.copyfile(p,archive/Path(p).name)
    shutil.copyfile(manifest,output/'manifest.json')
    save(output/'request.json',dict(at=now(),scope=spec['scope'],cases=cases,inputs_sha256=inputs,
        methods_sha256=implementation,frame_sampling_contract=contract(),frame_sampling_contract_sha256=contract_sha256()))
    save(output/'pipeline.json',dict(status='processing',at=now()))
    results=[]
    try:
        for case in cases:
            unchanged({**inputs,**implementation})
            print(dict(case=case['id'],metadata=case['metadata'],status='processing'),flush=True)
            try:
                report=audit_engine(case['source'],case['candidate'],case['draft'],case['policy'],
                    output/case['id'],base=case['base'],frame_sampling=True)
                if (report['status']!='complete' or report['frame_sampling_contract']!=contract()
                        or report['frame_sampling_contract_sha256']!=contract_sha256()
                        or report['original_contact_population_replaced'] is not False
                        or [c['id'] for c in report['cases']]!=['source','candidate']
                        or report['quality_approved'] is not False or report['release_approved'] is not False):
                    raise ValueError('Completed fixed-contract engine audit required')
                candidate=report['cases'][1]
                row=dict(id=case['id'],metadata=case['metadata'],status='complete',
                    result_sha256=sha256(output/case['id']/'result.json'),
                    engine_observations=sum(c['samples'] for c in report['cases']),
                    original_contact_pass=candidate['contact_samples_pass'],
                    frame_contact_pass=candidate['game_frame_contact_samples_pass'],
                    combined_contact_pass=candidate['all_contact_populations_pass'])
            except Exception as exc:
                row=dict(id=case['id'],metadata=case['metadata'],status='failed',error=str(exc),
                    engine_observations=0,original_contact_pass=None,frame_contact_pass=None,combined_contact_pass=False)
                save(output/(case['id']+'-failure.json'),row)
            unchanged({**inputs,**implementation})
            results.append(row);save(output/'progress.json',results);print(row,flush=True)
        for p,h in implementation.items():
            if sha256(archive/Path(p).name)!=h:raise ValueError('Population implementation archive changed')
        if sha256(output/'manifest.json')!=inputs[str(manifest)]:raise ValueError('Population manifest archive changed')
        report=dict(schema=spec['schema'],status='complete',at=now(),scope=spec['scope'],cases=results,
            manifest_sha256=inputs[str(manifest)],inputs_sha256=inputs,methods_sha256=implementation,
            frame_sampling_contract=contract(),frame_sampling_contract_sha256=contract_sha256(),
            engine_observations=sum(r['engine_observations'] for r in results),
            all_cases_completed=all(r['status']=='complete' for r in results),
            all_candidates_contact_pass=all(r['combined_contact_pass'] for r in results),
            selections_changed=False,quality_approved=False,training_admitted=False,release_approved=False)
        save(output/'result.json',report);save(output/'pipeline.json',dict(status='complete'));return report
    except Exception as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc)));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=1):
        result=run(args.manifest,args.output)
        print(dict(all_cases_completed=result['all_cases_completed'],all_candidates_contact_pass=result['all_candidates_contact_pass']))
