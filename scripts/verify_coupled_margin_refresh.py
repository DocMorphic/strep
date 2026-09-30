"""Replay every refreshed margin without calling the calibration functions."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import read,save,sha256,now


def run(calibration,audit,output):
    calibration,audit,output=map(lambda p:Path(p).resolve(),[calibration,audit,output])
    if output.exists():raise ValueError('Preserve previous margin verification')
    request,result=read(calibration/'request.json'),read(calibration/'result.json');proof=read(audit/'verification.json')
    if result['status']!='complete' or result['request_sha256']!=sha256(calibration/'request.json') or result['reserve_sha256']!=sha256(calibration/'reserve.npz'):
        raise ValueError('Completed bound refreshed margins required')
    inputs={**request['inputs'],**proof['inputs']}
    for path in [calibration/'request.json',calibration/'result.json',calibration/'reserve.npz',audit/'verification.json']:
        inputs[str(path)]=sha256(path)
    for name,digest in proof['artifacts'].items():inputs[str(audit/name)]=digest
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Margin verification input changed')
    with np.load(audit/'norms.npz',allow_pickle=False) as archive:norms=dict(archive)
    with np.load(calibration/'reserve.npz',allow_pickle=False) as archive:saved=dict(archive)
    with np.load(result['center_linearization_path'],allow_pickle=False) as archive:radii=archive['radii'];kinds=archive['kinds']
    np.testing.assert_array_equal(kinds,norms['kinds']);np.testing.assert_array_equal(kinds,saved['kinds'])
    expected=[]
    for row,kind in enumerate(kinds):
        error=max(0.,max(float(a[row])-float(b[row]) for a,b in zip(norms['exported'],norms['predicted'])))
        margin=0. if kind=='edit' else max(float(norms['previous_reserve'][row]),2*error)
        expected.append(margin)
    expected=np.array(expected)
    np.testing.assert_array_equal(saved['previous_reserve'],norms['previous_reserve'])
    np.testing.assert_allclose(expected,saved['reserve'],atol=1e-12,rtol=0)
    np.testing.assert_allclose(radii-expected,saved['tightened_radii'],atol=1e-12,rtol=0)
    if np.any(expected<norms['previous_reserve']) or np.any(expected>radii):raise ValueError('Margin weakened or silently clipped')
    original_controls=read(Path(result['checkpoint'])/'result.json')['total_controls']
    np.testing.assert_array_equal(result['center_controls'],original_controls)
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed during margin replay')
    output.mkdir();shutil.copyfile(__file__,output/'implementation.py')
    save(output/'verification.json',dict(at=now(),inputs=inputs,implementation_sha256=sha256(__file__),rows=len(expected),
        motion_observations=int((kinds!='edit').sum()*len(norms['exported'])),maximum_replay_error=float(np.abs(expected-saved['reserve']).max()),
        weakened_rows=0,native_edit_margins_changed=0,quality_approved=False,
        scope='Independent per-row arithmetic replay, previous-margin preservation and exact cumulative calibration center. No universal error-bound claim.'))
    print(dict(rows=len(expected),motion_observations=int((kinds!='edit').sum()*len(norms['exported'])),maximum_replay_error=float(np.abs(expected-saved['reserve']).max())),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['calibration','audit','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.calibration,a.audit,a.output)
