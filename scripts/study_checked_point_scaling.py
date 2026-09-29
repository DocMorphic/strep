"""Compare contact residual units on an immutable checked plan; no promotion."""
import argparse
import os
import time
from pathlib import Path

import psutil

from strep import ROOT, read, save, sha256, now
from checked_contact_job import prepare, verify
from run_contact_edit import run as edit


def run(check_id, output, control):
    output, control = Path(output).resolve(), Path(control).resolve()
    if output.parent != ROOT / 'reports/contact-jobs' or output.exists():
        raise ValueError('Fresh immediate contact-job folder required')
    check = ROOT / 'reports/contact-jobs' / check_id
    payload = dict(checked_plan=check_id, revision=sha256(check/'timing-result.json'))
    # The retained control must use the same selected clip, bound points and
    # original ceilings. Never substitute the failed candidate as initializer.
    files = ['source-take/motion.npz', 'source-take/soma.glb',
             'checked-plan/bound-contact-spec.json', 'checked-plan/rate-reference.json',
             'checked-plan/edit-request.json']
    control_hashes = {name: sha256(control/name) for name in files}
    prepare(payload, output)
    if any(sha256(output/name) != digest for name, digest in control_hashes.items()):
        raise ValueError('Comparison source or checked policy differs')
    save(output/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    protocol = dict(check=payload, control=control.relative_to(ROOT).as_posix(),
                    control_inputs=control_hashes, authored_point_scaling='tolerance',
                    outer_stages=2, iterations_per_stage=60, quality_approved=False,
                    scope='Development comparison: only explicit point residual scaling changes; '
                          'same targets, edit budgets, rates, initializer and iteration limits. '
                          'The default Studio fitter remains in metres.')
    save(output/'scaling-protocol.json', protocol)
    protocol_hash = sha256(output/'scaling-protocol.json')
    save(output/'pipeline.json', dict(status='processing', kind='checked_fit'))
    began = time.perf_counter()
    try:
        verify(output)
        edit(output/'source-take', output/'checked-plan/bound-contact-spec.json',
             output/'result', checked_plan=output/'checked-plan', authored_point_scaling='tolerance')
        verify(output)
        assert sha256(output/'scaling-protocol.json') == protocol_hash
        assert all(sha256(control/name) == h for name, h in control_hashes.items())
        save(output/'scaling-result.json', dict(status='complete', elapsed_s=time.perf_counter()-began,
             protocol_sha256=protocol_hash, summary_sha256=sha256(output/'result/summary.json'),
             quality_approved=False))
        save(output/'pipeline.json', dict(status='complete', kind='checked_fit', finished_at=now()))
    except Exception as exc:
        save(output/'pipeline.json', dict(status='failed', kind='checked_fit', error=str(exc)))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check_id')
    parser.add_argument('output')
    parser.add_argument('control')
    args = parser.parse_args()
    run(args.check_id, args.output, args.control)
