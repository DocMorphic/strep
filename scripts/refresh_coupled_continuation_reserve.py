"""Refresh local fitting margins from a completed exhausted-direction audit."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from coupled_pair_reserve import conservative_refresh,tightened_radii


def run(study,audit,output):
    study,audit,output=map(lambda p:Path(p).resolve(),[study,audit,output])
    if output.exists():raise ValueError('Preserve prior local calibration')
    request,result=read(study/'request.json'),read(study/'result.json');proof=read(audit/'verification.json')
    if result['status']!='complete' or result['termination']!='exported_line_search_exhausted' or result['request_sha256']!=sha256(study/'request.json'):
        raise ValueError('Completed exhausted continuation required')
    if proof['inputs'].get(str(study/'result.json'))!=sha256(study/'result.json'):raise ValueError('Audit belongs to another continuation')
    center=study/f"iteration-{proof['iteration']:02d}";solver=read(center/'solver.json')
    np.testing.assert_array_equal(result['total_controls'],solver['base_controls'])
    inputs={**request['inputs'],**proof['inputs']}
    for path in [study/'request.json',study/'result.json',audit/'verification.json',center/'solver.json',center/'linearization.npz']:
        inputs[str(path)]=sha256(path)
    for name,digest in proof['artifacts'].items():inputs[str(audit/name)]=digest
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Local calibration input changed')
    with np.load(center/'linearization.npz',allow_pickle=False) as archive:linear=dict(archive)
    with np.load(audit/'norms.npz',allow_pickle=False) as archive:norms=dict(archive)
    np.testing.assert_array_equal(norms['kinds'],linear['kinds'])
    updated,error=conservative_refresh(norms['previous_reserve'],norms['predicted'],norms['exported'],norms['kinds'])
    radii=tightened_radii(linear['radii'],updated,norms['kinds'])
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    for name in ['refresh_coupled_continuation_reserve.py','coupled_pair_reserve.py','strep.py']:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    np.savez_compressed(output/'reserve.npz',reserve=updated,previous_reserve=norms['previous_reserve'],positive_error=error,tightened_radii=radii,kinds=norms['kinds'])
    protocol=dict(at=now(),inputs=inputs,multiplier=2.,implementation={p.name:sha256(p) for p in snapshot.iterdir()},
        scope='Per motion row, retain the larger of the previous margin and twice the largest positive exported-minus-affine norm error observed in the exhausted local direction. Native edit margins remain zero. No cap clipping or final acceptance change; these remain empirical local margins.')
    save(output/'request.json',protocol)
    stats={}
    for kind in ['edit','speed','acceleration']:
        mask=norms['kinds']==kind
        stats[kind]=dict(rows=int(mask.sum()),increased_rows=int((updated[mask]>norms['previous_reserve'][mask]).sum()),
                         maximum_previous=float(norms['previous_reserve'][mask].max()),maximum_updated=float(updated[mask].max()))
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed during margin refresh')
    save(output/'result.json',dict(at=now(),status='complete',request_sha256=sha256(output/'request.json'),reserve_sha256=sha256(output/'reserve.npz'),
         checkpoint=str(study),center_controls=result['total_controls'],center_linearization_path=str(center/'linearization.npz'),
         center_linearization_sha256=sha256(center/'linearization.npz'),statistics=stats,quality_approved=False))
    print(stats,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','audit','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.study,a.audit,a.output)
