"""Compare stricter adjacent-edit proposal margins without changing any animation or acceptance cap."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from study_conic_foot_release import problem_for
from conic_root_descent import direction


def run(folder, output):
    if output.exists(): raise ValueError('Preserve prior diagnostic')
    request = read(folder/'request.json')
    done = read(folder/'completion.json')
    for name, digest in done['files'].items():
        if sha256(folder/name) != digest: raise ValueError('Source output changed')
    rows = []
    with threadpool_limits(limits=1):
        p = problem_for(request, read(folder/'envelope.json'))
        x = p.initial[np.ix_(p.frames, p.free)].ravel()
        base = p.evaluate(x)
        for scale in [1e-6, 1e-7]:
            buffers = dict(request['proposal_buffers'], adjacent_edit=scale)
            delta, record = direction(p, x, 1e-4, buffers)
            row = dict(adjacent_edit_buffer=scale, proposal=record, trials=[])
            if delta is not None:
                row['proposed_delta'] = delta.tolist()
                for i in range(8):
                    alpha = .5**i
                    actual = p.evaluate(x+alpha*delta)
                    feasible = bool(np.isfinite(actual[2]).all() and actual[2].min() >= -1e-8)
                    geometry = p.geometric_guard(actual[5]) if feasible else None
                    row['trials'].append(dict(fraction=alpha, objective=actual[0],
                        minimum_constraint=float(actual[2].min()), geometry=geometry,
                        would_pass=bool(feasible and geometry and actual[0] < base[0]-1e-9)))
            rows.append(row)
    save(output, dict(at=now(), source=str(folder), completion_sha256=sha256(folder/'completion.json'),
        implementation_sha256=sha256(__file__), helper_sha256=sha256(Path(__file__).with_name('conic_root_descent.py')),
        initial_objective=base[0], rows=rows, quality_approved=False,
        scope='Two fixed additional adjacent-edit proposal margins at original source coordinates. Actual acceptance caps unchanged. No output clip, source mutation, or quality approval. Geometry null means not evaluated.'))
    print([{k:v for k,v in r.items() if k!='proposed_delta'} for r in rows])


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('folder',type=Path); p.add_argument('output',type=Path)
    a=p.parse_args(); run(a.folder.resolve(),a.output.resolve())
