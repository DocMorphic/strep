"""Local, non-blind review of all matched half-floor experiment outputs."""
import argparse
import hashlib
import zipfile
from pathlib import Path
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from package_correction_review import checked_copy
from study_half_floor_population import completed, pair_results, METHODS
from study_coupled_clip_sequence import verify_sequence


def review_note(pair):
    if pair['status']!='complete':
        raise ValueError('Both exported methods required for review')
    parts=[]
    for method,label in [('keys_only','Keys only'),('keys_and_halves','Keys plus halves')]:
        result=pair['methods'][method]
        accepted=result['status']=='accepted'
        parts.append(f'{label}: '+('numerical improvement accepted' if accepted else 'correction rejected')+
                     f'; {len(result["failing_centers"])} root-reference failures remain')
    return '. '.join(parts)+'. These are numerical outcomes, not motion-quality ratings.'


def build(study,output):
    if output.parent!=ROOT/'reports/rig-jobs' or output.exists():
        raise ValueError('Use a new local rig-jobs review directory')
    done=completed(study);request=read(study/'request.json');results=read(study/'results.json')
    check_files(study,read(study/'freeze.json'))
    if done['comparison_sha256']!=sha256(study/'comparison.json') or pair_results(results['rows'])!=read(study/'comparison.json'):
        raise ValueError('Matched comparison changed')
    breadth=read(ROOT/'reports/whole-support-breadth-v1/protocol.json')
    output.mkdir(parents=True)
    prefix=f'/files/rig-jobs/{output.name}/'
    rows=[]
    for pair in read(study/'comparison.json')['pairs']:
        identifier=pair['case'];note=review_note(pair)
        methods={r['method']:r for r in results['rows'] if r['case']==identifier}
        frozen={c['method']:c for c in request['cases'] if c['case']==identifier}
        folders={m:Path(methods[m]['selected_folder']) for m in METHODS}
        for m,folder in folders.items():
            verify_sequence(folder)
            if sha256(folder/'completion.json')!=methods[m]['completion_sha256']:
                raise ValueError('Selected result changed')
            check_files(folder,frozen[m]['files'])
            check_files(folder/'source',read(folder/'request.json')['source_files'])
        origin=Path(frozen['keys_only']['source'])
        verify_sequence(origin)
        if sha256(origin/'completion.json')!=frozen['keys_only']['source_completion_sha256'] or sha256(origin/'take/candidate/character.glb')!=sha256(folders['keys_only']/'starting.glb'):
            raise ValueError('Starting clip source changed')
        meta=next(c for c in breadth['cases'] if c['id']==identifier)
        raw=Path(meta['source'])
        check_files(raw,meta['files'])
        if sha256(raw/'character.glb')!=sha256(folders['keys_only']/'source/input/character.glb'):
            raise ValueError('Raw transfer differs from audited input')
        rig=next(r for r in breadth['rigs'] if r['id']==meta['rig'])
        spec=read(folders['keys_only']/'source/spec.json')
        folder=output/identifier
        choices=[('raw','Raw rig transfer',raw,None),
                 ('input','Before this comparison',origin/'take/candidate',methods['keys_only']['before']['peak_m_s2'])]
        for m,label in [('keys_only','Keys only'),('keys_and_halves','Keys plus halves')]:
            choices.append((m,label+(' · accepted numerical change' if methods[m]['status']=='accepted' else ' · rejected correction'),
                            folders[m]/'take/candidate',methods[m]['after']['peak_m_s2']))
        variants=[]
        for key,label,source,peak in choices:
            files={name:checked_copy(source/name,folder/key/name) for name in ['character.glb','root-motion.json','contacts.json']}
            variants.append(dict(id=key,label=label,glb=prefix+f'{identifier}/{key}/character.glb',sha256=files['character.glb'],
                root_track=prefix+f'{identifier}/{key}/root-motion.json',contacts=prefix+f'{identifier}/{key}/contacts.json',
                metrics=dict(root_acceleration_max_m_s2=peak),files=files))
        for name,digest in rig['files'].items():
            if name!='character.glb':
                checked_copy(Path(breadth['source'])/rig['directory']/name,folder/'attribution'/name,digest)
        for m in METHODS:
            for name in ['audit.json','comparison.json','completion.json']:
                checked_copy(folders[m]/name,folder/'evidence'/m/name)
            checked_copy(folders[m]/'engine/verification.json',folder/'evidence'/m/'engine.json')
        save(folder/'audit.json',dict(comparison=pair,source_completion_sha256=sha256(study/'completion.json'),quality_approved=False))
        save(folder/'review.json',dict(case=identifier,variants=variants,notes=note,quality_approved=False))
        (folder/'README.txt').write_text('Developer review, not blind or animator approval. Compare all four versions at normal speed, then at identical frames. '
            'Report action correctness, weight, balance, timing, contacts and start/end usability. Record the case, version and frame range with each issue. '
            'Both attempted outputs are retained, including rejected corrections; neither is automatically a recommended asset. Contact markers are unconfirmed predictions. '
            'Raw transfer precedes earlier contact/root corrections. Numerical preservation allows existing penetration. Licenses are in attribution/.\n'+note+'\n',encoding='utf8')
        members={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()}
        with zipfile.ZipFile(folder/'review-pack.zip','x',zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(members):archive.write(folder/name,name)
        with zipfile.ZipFile(folder/'review-pack.zip') as archive:
            if {n:hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()}!=members:
                raise ValueError('Review archive changed')
        center=read(folders['keys_only']/'request.json')['windows'][0]['center']
        landmarks=[dict(label='Correction window',frame=center)]
        added=sorted({f for values in pair['added_failures'].values() for f in values})
        landmarks += [dict(label='New root-reference failure',frame=f) for f in added if f!=center]
        rows.append(dict(id=identifier,label=meta['motion']['case'].replace('-',' ')+' · '+rig['label'],
            status='needs_review',status_label='Matched development comparison · needs review',default_variant='input',
            variants=variants,frames=spec['frames'],fps=spec['fps'],root_node=spec['root_node'],prompt=meta['motion']['prompt'],seed=meta['motion']['seed'],
            failed_checks=[],review_note=note,blocks=1,review_landmarks=landmarks,
            package=prefix+f'{identifier}/review-pack.zip',audit=prefix+f'{identifier}/audit.json',license=prefix+f'{identifier}/attribution/LICENSE.md',quality_approved=False))
    save(output/'catalog.json',dict(schema='strep-correction-review-v1',at=now(),cases=rows,quality_approved=False,
        developer_reviews_collected=0,independent_human_reviews_collected=0,
        scope='All nine diagnosed development cases and all four raw/start/attempt versions. Non-blind review, no ratings prefilled.'))
    save(output/'package-verification.json',dict(at=now(),source_completion_sha256=sha256(study/'completion.json'),
        implementation_sha256=sha256(__file__),cases=len(rows),variants=sum(len(r['variants']) for r in rows),
        files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()},quality_approved=False))
    print(dict(cases=len(rows),variants=sum(len(r['variants']) for r in rows),catalog=prefix+'catalog.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();build(a.study.resolve(),a.output.resolve())
