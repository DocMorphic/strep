"""Diagnostic constraint ablations on a saved local model; never accept edits."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def variant(model, omitted):
    if omitted not in ('none', 'motion', 'palm', 'old_witnesses'): raise ValueError('Unknown diagnostic group')
    base, jac = dict(model['base']), dict(model['jacobian'])
    if len(base['vectors']) <= 5: raise ValueError('Expected motion rows followed by five palm rows')
    if omitted in ('motion', 'palm'):
        selected = slice(-5, None) if omitted == 'motion' else slice(None, -5)
        for key in ('vectors', 'caps', 'scales'): base[key] = base[key][selected]
        jac['vectors'] = jac['vectors'][selected]
    elif omitted == 'old_witnesses':
        base['margins'] = np.ones_like(base['margins']); jac['margins'] = np.zeros_like(jac['margins'])
    return dict(model, base=base, jacobian=jac)


def run(study, output):
    from conic_root_descent import solver_module
    from hand_norm_proposal import direction, measurement
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh diagnostic output required')
    result, request = read(study/'result.json'), read(study/'request.json')
    if result['status'] != 'complete': raise ValueError('Completed saved finger study required')
    paths = ['request.json', 'iteration-01.npz']
    inputs = {str(study/'result.json'): sha256(study/'result.json')}
    for name in paths:
        digest = result['outputs'][name]
        if sha256(study/name) != digest: raise ValueError('Saved model changed')
        inputs[str(study/name)] = digest
    for name in ['hand_norm_proposal.py', 'conic_root_descent.py', 'conic_linear_screen.py', 'root_release_block.py']:
        if sha256(ROOT/'scripts'/name) != request['implementation'][name]: raise ValueError('Original proposal method required')
    with np.load(study/'iteration-01.npz', allow_pickle=False) as data:
        model = dict(point=data['point'], base={k:data[k] for k in ['vectors','caps','scales','margins','depths']},
            jacobian={k:data[k+'_jacobian'] for k in ['vectors','margins','depths']})
    if len(model['point']) != len(request['scale']): raise ValueError('Saved parameter population changed')
    # Explicitly identify the current five-row palm contract before slicing.
    expected = np.r_[np.repeat(request['point_drift_limit_m'], 3), np.repeat(request['normal_vector_drift_limit'], 2)]
    np.testing.assert_array_equal(model['base']['caps'][-5:], expected)
    solver = solver_module(); output.mkdir(); (output/'implementation').mkdir(); methods = {}
    for name in ['diagnose_finger_proposal.py', 'hand_norm_proposal.py', 'conic_root_descent.py', 'conic_linear_screen.py', 'root_release_block.py', 'sampled_motion_caps.py', 'strep.py']:
        path = ROOT/'scripts'/name; methods[name] = sha256(path); shutil.copyfile(path, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), inputs=inputs, implementation=methods, solver_version=solver.__version__,
        trust=.1, omitted_groups=['none','motion','palm','old_witnesses'], original=measurement(model['base']),
        quality_approved=False, scope='Local affine diagnostic only. Removing a group is not permitted for actual candidate acceptance. No motion evaluation, export, constraints update or feasibility certificate.'))
    records = []
    for omitted in ['none', 'motion', 'palm', 'old_witnesses']:
        delta, report = direction(variant(model, omitted), .1, solver)
        records.append(dict(omitted=omitted, **report)); save(output/'proposals.json', records)
        print(dict(omitted=omitted, status=report['status'], predicted=report.get('predicted')), flush=True)
    for path, digest in inputs.items():
        if sha256(path) != digest: raise ValueError('Diagnostic input changed')
    for name, digest in methods.items():
        if sha256(ROOT/'scripts'/name) != digest: raise ValueError('Diagnostic method changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        proposals_sha256=sha256(output/'proposals.json'), diagnostic_only=True, accepted_for_publication=False, quality_approved=False))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('study', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=1): run(args.study, args.output)
