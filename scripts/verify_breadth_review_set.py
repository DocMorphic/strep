"""Verify full reviewer-population coverage and create an organizer index."""
import argparse
from collections import Counter
from pathlib import Path
from strep import ROOT,read,save,sha256,now


def run(folder):
    folder=folder.resolve();output=folder/'independent-verification.json'
    if output.exists() or (folder/'README.md').exists():raise ValueError('Preserve previous set verification')
    if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Packet set still incomplete')
    done=read(folder/'completion.json');request=read(folder/'request.json');results=read(folder/'results.json')
    if sha256(folder/'request.json')!=done['request_sha256'] or sha256(folder/'results.json')!=done['results_sha256']:
        raise ValueError('Completion evidence changed')
    for path,digest in request['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Source input changed')
    for name,digest in request['implementation'].items():
        if sha256(folder/'implementation'/name)!=digest:raise ValueError('Builder snapshot changed')
    protocol=read(Path(request['study'])/'protocol.json')
    expected={(c['id']+'-'+a['id'].lower(),seed):(c['family'],c['round'],c['scene_validation']=='missing_required_context_validation')
              for c in protocol['cases'] for a in c['actors'] for seed in c['seeds']}
    observed=set();families=Counter();rows=[];files=0;runtime=0
    if len(results['rows'])!=6 or {r['round'] for r in results['rows']}!=set(range(1,7)):
        raise ValueError('Missing or duplicate review round')
    for row in results['rows']:
        number=row['round'];label=f'round-{number:02d}';packet=Path(row['relocated'])
        for path,digest in [(Path(row['archive']),row['archive_sha256']),
            (Path(row['key']),row['key_sha256']), (packet/'manifest.json',row['manifest_sha256']),
            (folder/'checks'/f'{label}-verification.json',row['verification_sha256']),
            (folder/'checks'/f'{label}-build.json',row['build_sha256'])]:
            if sha256(path)!=digest:raise ValueError('Packet evidence changed')
        manifest=read(packet/'manifest.json');private=read(row['key']);check=read(folder/'checks'/f'{label}-verification.json')
        if manifest['packet_id']!=row['packet_id'] or private['packet_id']!=row['packet_id'] or check['packet_id']!=row['packet_id']:
            raise ValueError('Packet identity differs')
        if private['manifest_sha256']!=row['manifest_sha256'] or check['archive_sha256']!=row['archive_sha256']:
            raise ValueError('Packet binding differs')
        if len(manifest['cases'])!=row['clips'] or len(private['cases'])!=row['clips'] or check['http_clips_verified']!=row['clips'] or check['source_motion_payloads_unchanged']!=row['clips']:
            raise ValueError('Clip population differs')
        mapping={c['id']:c for c in private['cases']}
        if len(mapping)!=row['clips'] or len({c['id'] for c in manifest['cases']})!=row['clips']:
            raise ValueError('Duplicate neutral clip IDs')
        missing=0;packet_families=set()
        for clip in manifest['cases']:
            key=mapping[clip['id']];identity=(key['request_id'],key['seed'])
            if identity not in expected or identity in observed:raise ValueError('Undeclared, duplicate or filtered take')
            family,declared_round,needs_context=expected[identity]
            if declared_round!=number:raise ValueError('Take assigned to wrong round')
            if sha256(packet/clip['path'])!=clip['sha256'] or key['review_sha256']!=clip['sha256']:
                raise ValueError('Review clip changed')
            categories=clip['review_context']['unavailable_categories']
            if set(categories)!=({'contacts_collisions'} if needs_context else set()):raise ValueError('Missing-context scoring changed')
            observed.add(identity);families[family]+=1;packet_families.add(family);missing+=int(needs_context)
        if len(packet_families)!=12 or missing!=row['missing_context_clips']:raise ValueError('Family/context population differs')
        if check['human_reviews_collected']!=0 or check['quality_approved']:raise ValueError('Build must not contain fabricated reviewer evidence')
        files+=check['files_verified'];runtime+=check['http_runtime_files_verified']
        rows.append(dict(round=number,clips=row['clips'],families=len(packet_families),missing_context_clips=missing,
                         archive_bytes=Path(row['archive']).stat().st_size,archive_sha256=row['archive_sha256']))
    if observed!=set(expected) or len(observed)!=390:raise ValueError('Full study population not represented')
    result=dict(at=now(),completion_sha256=sha256(folder/'completion.json'),implementation_sha256=sha256(__file__),
        actor_clips=len(observed),cases=len(protocol['cases']),family_clips=dict(sorted(families.items())),
        rows=rows,packaged_files_verified=files,http_runtime_downloads_verified=runtime,
        missing_context_clips=sum(r['missing_context_clips'] for r in rows),human_reviews_collected=0,
        quality_approved=False,scope='Independent aggregate390-take coverage, current ZIP/clip hashes and evidence linkage. Artifact/transport proof only; browser interaction and human ratings are separate.')
    save(output,result)
    lines=['# Complete breadth review set','',
        'Six portable packets contain all390 raw actor clips from72 cases across12 motion families. Each packet has65 clips: one case per family, five fixed seeds, with both actors retained for its partner case.',
        '', 'Every take is included. These are development diagnostics, not approved animation assets. No human ratings or cleanup records have been collected.', '',
        '| Packet | Clips | Missing scene/partner context | Download |','| --- | ---: | ---: | --- |']
    for row in rows:
        label=f"round-{row['round']:02d}"
        lines.append(f"| Round {row['round']} | {row['clips']} | {row['missing_context_clips']} | [ZIP](archives/reviewer-{label}.zip) |")
    lines += ['', 'Extract one complete ZIP and run `python serve.py` (Windows: `py -3 serve.py`). Open the printed local URL in a WebGL browser. Python3 is required; model weights and online accounts are unnecessary.',
        '', 'Reviewers use separate browser profiles and enter their own ratings. The viewer requires N/A with a reason for contact accuracy when required context is missing. Watching a clip is not animator cleanup time.',
        '', 'Share only the ZIPs through a separately agreed channel. The surrounding project folder contains organizer keys and must not accompany a blinded review. Nothing has been sent to anyone.',
        '', 'All390 neutral motion payloads, archive inventories and localHTTP clip downloads were verified in a separate folder. This verifies packaging and transport, not motion quality or independent reviewer participation.', '']
    (folder/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(dict(clips=len(observed),families=len(families),missing_context=result['missing_context_clips'],human_reviews=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();run(a.folder)
