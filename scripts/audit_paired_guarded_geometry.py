"""Bind guarded exports and actual engine evidence to the existing surface audit."""
import argparse
import os
from pathlib import Path
import shutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from audit_paired_temporal_rates import validate_engine
from audit_paired_temporal_neighbor import run as audit


def run(study,engine,output):
    study,engine,output=map(lambda p:Path(p).resolve(),[study,engine,output])
    if output.exists():raise ValueError('Preserve earlier audit')
    request,result=read(study/'request.json'),read(study/'result.json');manifest=read(study/'manifest.json')
    if result['status']!='complete' or result['request_sha256']!=sha256(study/'request.json'):raise ValueError('Completed bound guarded study required')
    if request['seed']!=1301 or request['free_frames']!=[74,76]:raise ValueError('Declared contact-preserving fixture required')
    if len(result['rows'])!=2 or {r['actor'] for r in result['rows']}!={'A','B'}:raise ValueError('Complete distinct actor population required')
    if any(r['selected']['rate_failure_count'] for r in result['rows']):raise ValueError('Rate guards must pass before surface validation')
    if len(manifest['cases'])!=4 or {r['id'] for r in manifest['cases']}!={v+'-'+a for v in ['input','candidate'] for a in ['A','B']}:
        raise ValueError('Complete distinct input/candidate exports required')
    inputs={**request['inputs']};exports={v:{} for v in ['input','candidate']}
    for file in [study/'request.json',study/'result.json',study/'manifest.json',engine/'verification.json']:inputs[str(file)]=sha256(file)
    adapter=output/'adapter'
    for row in manifest['cases']:
        variant,actor=row['id'].split('-');path=study/row['path'];inputs[str(path)]=row['sha256']
        exports[variant][actor]=dict(path=Path(os.path.relpath(path,adapter)).as_posix(),sha256=row['sha256'])
    validate_engine(exports,read(engine/'verification.json')['checks'])
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input or export changed')
    prior=ROOT/'reports/paired-temporal-neighbor-v1/protocol.json'
    if str(prior) not in inputs:raise ValueError('Original scene provenance required')
    scene=read(prior)['source_scene']
    output.mkdir();adapter.mkdir();snapshot=adapter/'implementation';snapshot.mkdir()
    shutil.copyfile(__file__,snapshot/Path(__file__).name)
    protocol=dict(at=now(),first=73,event=75,last=77,variants=['input','candidate'],source_scene=scene,inputs=inputs,
        implementation={Path(__file__).name:sha256(__file__)},quality_approved=False,
        scope='Manifest adapter only; two changed keys affect interpolation on 73–77. Raw GLBs remain at their bound original paths. Geometry evidence is produced separately.')
    save(adapter/'protocol.json',protocol)
    save(adapter/'result.json',dict(status='complete',protocol_sha256=sha256(adapter/'protocol.json'),exports=exports,quality_approved=False))
    audit(adapter,output/'geometry')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','engine','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.study,a.engine,a.output)
