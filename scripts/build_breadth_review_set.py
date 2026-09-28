"""Complete all six raw breadth reviewer packets without quality selection."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import threading
import traceback
import zipfile
import psutil
from strep import ROOT,read,save,sha256,now
from build_breadth_review import prepare
from verify_portable_review import verify


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def run(output,relocated):
    output,relocated=output.resolve(),relocated.resolve()
    if output.exists() or relocated.exists():raise ValueError('Preserve previous packets and relocated copies')
    study=ROOT/'reports/breadth-baseline-v2';protocol=read(study/'protocol.json')
    if read(study/'pipeline.json')['status']!='complete':raise ValueError('Breadth baseline incomplete')
    expected={(c['id']+'-'+a['id'].lower(),seed) for c in protocol['cases'] for a in c['actors'] for seed in c['seeds']}
    if len(expected)!=390 or {c['round'] for c in protocol['cases']}!=set(range(1,7)):
        raise ValueError('Unexpected declared breadth population')
    output.mkdir(parents=True);relocated.mkdir(parents=True)
    for name in ['implementation','packets','private','archives','checks']:(output/name).mkdir()
    names=['build_breadth_review_set.py','build_breadth_review.py','portable_review_packet.py',
        'verify_portable_review.py','review_session.py','breadth_study.py','strep.py','gltf_tools.py',
        'human-review.html','soma-preview-skin.js','serve_review_packet.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    process=psutil.Process()
    first=ROOT/'reports/breadth-human-review-v2'
    input_paths=[study/'protocol.json',study/'freeze.json',study/'execution-freeze.json',
        study/'completion-verification.json',first/'private/round-01-key.json',first/'packet-v2/manifest.json',
        first/'reviewer-round-01-v2.zip',first/'build-v2.json']
    request=dict(at=now(),pid=process.pid,created=process.create_time(),rounds=list(range(1,7)),
        new_rounds=list(range(2,7)),randomization_seeds={str(n):94300+n for n in range(2,7)},
        expected_actor_clips=390,study=str(study),relocated=str(relocated),
        inputs={str(p):sha256(p) for p in input_paths},
        implementation={name:sha256(output/'implementation'/name) for name in names},
        scope='Complete raw development population. Existing corrected round01 packet reused byte-for-byte; rounds02–06 newly packaged. No ratings, cleanup records or release claims.')
    save(output/'request.json',request)
    def validate():
        for p,digest in request['inputs'].items():
            if sha256(p)!=digest:raise ValueError('Input changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
    def phase(status,**details):
        save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,details,flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(relocated)))
    server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    rows=[];seen=set()
    try:
        for number in range(1,7):
            validate();label=f'round-{number:02d}';phase('packaging',round=number)
            archive=output/'archives'/f'reviewer-{label}.zip'
            if number==1:
                packet=first/'packet-v2';key=first/'private/round-01-key.json'
                shutil.copyfile(first/'reviewer-round-01-v2.zip',archive)
                build=read(first/'build-v2.json')
                if sha256(archive)!=build['archive_sha256']:raise ValueError('Round01 bytes changed')
            else:
                packet=output/'packets'/label;key=output/'private'/f'{label}-key.json'
                build=prepare(study,number,packet,key,archive,request['randomization_seeds'][str(number)])
            save(output/'checks'/f'{label}-build.json',build)
            mapping=read(key);manifest=read(packet/'manifest.json')
            required={(c['id']+'-'+a['id'].lower(),seed) for c in protocol['cases'] if c['round']==number for a in c['actors'] for seed in c['seeds']}
            actual={(c['request_id'],c['seed']) for c in mapping['cases']}
            if actual!=required or len(actual)!=len(mapping['cases']) or seen.intersection(actual):raise ValueError('Incomplete, duplicate or filtered review population')
            seen.update(actual)
            cases_by_request={c['id']+'-'+a['id'].lower():c for c in protocol['cases'] for a in c['actors']}
            private_by_id={c['id']:c for c in mapping['cases']};missing=0
            for clip in manifest['cases']:
                source_case=cases_by_request[private_by_id[clip['id']]['request_id']]
                context=clip['review_context'];required_missing=source_case['scene_validation']=='missing_required_context_validation'
                if context['flat_floor_screen_applicable']!=source_case['flat_floor_screen_applicable']:
                    raise ValueError('Floor applicability changed')
                if bool(context['unavailable_categories'])!=required_missing:raise ValueError('Missing-context scoring changed')
                if required_missing and set(context['unavailable_categories'])!={'contacts_collisions'}:raise ValueError('Missing-context category differs')
                missing+=int(required_missing)
            dest=relocated/label;dest.mkdir()
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    target=(dest/info.filename).resolve()
                    if not target.is_relative_to(dest) or info.filename.startswith(('/', '\\')):raise ValueError('Unsafe archive path')
                z.extractall(dest)
            phase('verifying_relocated_packet',round=number)
            check=output/'checks'/f'{label}-verification.json'
            result=verify(dest,key,archive,f'http://127.0.0.1:{server.server_port}/{label}',check)
            if result['http_clips_verified']!=len(required):raise ValueError('Missing downloaded clips')
            rows.append(dict(round=number,packet_id=manifest['packet_id'],clips=len(required),
                missing_context_clips=missing,archive=str(archive),archive_sha256=sha256(archive),
                manifest_sha256=sha256(packet/'manifest.json'),key=str(key),key_sha256=sha256(key),
                relocated=str(dest),verification_sha256=sha256(check),build_sha256=sha256(output/'checks'/f'{label}-build.json')))
            save(output/'results.json',dict(rows=rows,human_reviews_collected=0,quality_approved=False))
        if seen!=expected:raise ValueError('Full390 population differs')
        validate()
        save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),
            results_sha256=sha256(output/'results.json'),rounds=len(rows),actor_clips=len(seen),
            cases=len(protocol['cases']),families=len({c['family'] for c in protocol['cases']}),
            human_reviews_collected=0,quality_approved=False,
            scope='All six model-free reviewer ZIPs retain the complete390-clip raw development population. Relocated inventories,ZIP contents,neutral motion payloads and all localHTTP assets checked. No new browser interaction or human evidence.'))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('relocated',type=Path);a=p.parse_args();run(a.output,a.relocated)
