"""Publish an immutable local review package from an independently verified chain."""
import argparse
from pathlib import Path
import shutil
import zipfile
from strep import ROOT,read,save,sha256,now


def presentation(status):
    if status=='numerical_pass':return 'Numerical checks met · needs review',True
    if status=='already_passed':return 'Already within checks · no correction needed',False
    if status=='ineligible':return 'Contact checks failed · correction skipped',False
    return 'Correction unfinished · input retained',False


def checked_copy(source,target,digest=None):
    expected=digest or sha256(source)
    if sha256(source)!=expected:raise ValueError('Source artifact changed')
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    if sha256(target)!=expected:raise ValueError('Copied artifact differs')
    return expected


def build(study,audit,output,breadth):
    if output.exists():raise ValueError('Preserve prior review package')
    if output.parent!=ROOT/'reports/rig-jobs':raise ValueError('Review package must be a direct child of reports/rig-jobs')
    done=read(study/'completion.json');proof=read(audit);protocol=read(study/'protocol.json');population=read(breadth)
    if proof.get('all_chain_checks_passed') is not True or proof['chain_completion_sha256']!=sha256(study/'completion.json') or done['protocol_sha256']!=sha256(study/'protocol.json'):
        raise ValueError('Bound independent chain audit required')
    if [r['id'] for r in proof['rows']]!=[r['id'] for r in protocol['cases']]:raise ValueError('Review must retain full declared population')
    # Validate all outputs before publishing any catalogue entry.
    for item in proof['rows']:
        case=study/'cases'/item['id']/'completion.json'
        if sha256(case)!=item['case_completion_sha256']:raise ValueError('Case decision changed')
        result=read(case)
        for source in {Path(result['initial_source']),Path(result['final_source'])}:
            for name,digest in read(source/'completion.json')['files'].items():
                if sha256(source/name)!=digest:raise ValueError('Completed correction artifact changed')
        if sha256(Path(result['final_source'])/'take/candidate/character.glb')!=item['candidate_sha256']:raise ValueError('Final audited candidate changed')
    output.mkdir(parents=True);rows=[];prefix=f'/files/rig-jobs/{output.name}/'
    for item in proof['rows']:
        case_path=study/'cases'/item['id']/'completion.json';result=read(case_path);source=Path(result['initial_source']);final=Path(result['final_source']);request=read(source/'request.json');spec=read(source/'take/spec.json')
        original_case=next(c for c in population['cases'] if c['id']==Path(request['prior']).name)
        rig=next(r for r in population['rigs'] if r['id']==original_case['rig']);label=original_case['motion']['case'].replace('-',' ').replace('_',' ')
        folder=output/item['id'];status,corrected=presentation(result['status']);variants=[]
        raw_metrics=read(source/'take/verification.json')['metrics']['input'];source_metrics=read(source/'take/verification.json')['metrics']['candidate']
        choices=[('raw','Raw transfer',source/'take/input',raw_metrics),('input','Before angular correction',source/'take/candidate',source_metrics)]
        if corrected:choices.append(('corrected','Corrected candidate',final/'take/candidate',read(final/'take/verification.json')['metrics']['candidate']))
        for key,name,origin,metrics in choices:
            files={}
            for filename in ['character.glb','root-motion.json','contacts.json']:
                files[filename]=checked_copy(origin/filename,folder/key/filename)
            variants.append(dict(id=key,label=name,glb=prefix+f'{item["id"]}/{key}/character.glb',sha256=files['character.glb'],root_track=prefix+f'{item["id"]}/{key}/root-motion.json',contacts=prefix+f'{item["id"]}/{key}/contacts.json',metrics={name:metrics.get(name) for name in ['floor_depth_max_m','half_frame_floor_depth_max_m','root_acceleration_max_m_s2']},files=files))
        for name,digest in rig['files'].items():
            if name=='character.glb':continue
            checked_copy(Path(population['source'])/rig['directory']/name,folder/'attribution'/name,digest)
        checked_copy(case_path,folder/'chain-case.json');checked_copy(audit,folder/'chain-audit.json')
        checked_copy(final/'take/verification.json',folder/'measurements.json')
        if (final/'take/comparison.json').is_file():checked_copy(final/'take/comparison.json',folder/'comparisons.json')
        save(folder/'review.json',dict(case=item['id'],status=result['status'],quality_approved=False,chain_completion_sha256=sha256(study/'completion.json'),chain_audit_sha256=sha256(audit),variants=variants,
            notes='Raw transfer is the model motion transferred to this rig, before these corrections. Input includes earlier contact/root corrections. Predicted contacts are unconfirmed. Numerical peak constraints do not certify realism, balance, semantics or animator quality. No independent ratings or cleanup times supplied.'))
        members={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()}
        with zipfile.ZipFile(folder/'review-pack.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(members):archive.write(folder/name,name)
        with zipfile.ZipFile(folder/'review-pack.zip') as archive:
            import hashlib
            if {name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}!=members:raise ValueError('Review ZIP differs')
        rows.append(dict(id=item['id'],label=label+' · '+rig['label']+(' · passing control' if result['status']=='already_passed' else ''),status=result['status'],status_label=status,default_variant='input',frames=spec['frames'],fps=spec['fps'],root_node=spec['root_node'],variants=variants,
            prompt=original_case['motion']['prompt'],seed=original_case['motion']['seed'],failed_checks=result.get('assessment',{}).get('failed_checks',[]),blocks=len(result['history']),package=prefix+f'{item["id"]}/review-pack.zip',audit=prefix+f'{item["id"]}/chain-audit.json',measurements=prefix+f'{item["id"]}/measurements.json',license=prefix+f'{item["id"]}/attribution/LICENSE.md',quality_approved=False))
    save(output/'catalog.json',dict(schema='strep-correction-review-v1',at=now(),cases=rows,quality_approved=False,scope='Five retained development cases, including a duplicate no-op control. These are not new held-out samples or animator-approved assets.'))
    save(output/'package-verification.json',dict(at=now(),source_completion_sha256=sha256(study/'completion.json'),source_audit_sha256=sha256(audit),implementation_sha256=sha256(__file__),files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()},quality_approved=False))
    print(dict(cases=len(rows),variants=sum(len(r['variants']) for r in rows),catalog=prefix+'catalog.json'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('audit',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--breadth',type=Path,default=ROOT/'reports/whole-support-breadth-v1/protocol.json');args=parser.parse_args();build(args.study.resolve(),args.audit.resolve(),args.output.resolve(),args.breadth.resolve())
