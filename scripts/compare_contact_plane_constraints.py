"""Compare matched box/ball studies without interpreting fit cost as quality."""
import argparse
from pathlib import Path
import shutil
from strep import read, save, sha256, now


def run(box, ball, output):
    box, ball, output = Path(box).resolve(), Path(ball).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh comparison output required')
    studies = []; inputs = {}
    for folder, optimizer in [(box, 'slsqp_box'), (ball, 'slsqp_ball')]:
        result, request = read(folder/'result.json'), read(folder/'request.json')
        if result['status'] != 'complete' or request['optimizer'] != optimizer:
            raise ValueError('Completed, correctly labeled box and ball trials required')
        inputs[str(folder/'result.json')] = sha256(folder/'result.json')
        for name, digest in result['outputs'].items():
            path = (folder/name).resolve()
            if path.parent != folder or sha256(path) != digest: raise ValueError('Changed trial output')
            inputs[str(path)] = digest
        for path, digest in request['inputs'].items():
            if sha256(path) != digest: raise ValueError('Changed original input')
        for name, digest in request['implementation'].items():
            if sha256(folder/'implementation'/name) != digest: raise ValueError('Changed method archive')
        decoded = read(folder/'decoded.json'); fits = read(folder/'fits.json')
        studies.append(dict(request=request, summary=dict(folder=str(folder), optimizer=optimizer,
            contact=decoded['contact'], planes=decoded['planes'], motion_rates=decoded['motion_rates'],
            original_motion_caps_pass=result['original_motion_caps_pass'],
            selected_hand_plane_pass=result['selected_hand_plane_pass'],
            contact_proper_crossings=result['contact_proper_crossings'],
            contact_maximum_vertex_depth_m=result['contact_maximum_vertex_depth_m'],
            cost_per_actor=[f['cost'] for f in fits], optimizer_success_per_actor=[f['success'] for f in fits],
            residual_calls_per_actor=[f['residual_calls'] for f in fits])))
    first, second = [s['request'] for s in studies]
    # Only run identity and constraint shape may differ. Objective, population,
    # versioned methods, original limits and iteration budgets must be identical.
    ignored = {'at', 'optimizer'}
    if {k: v for k, v in first.items() if k not in ignored} != {k: v for k, v in second.items() if k not in ignored}:
        raise ValueError('Matched original inputs, objective implementation and budgets required')
    output.mkdir(); shutil.copyfile(__file__, output/Path(__file__).name)
    a, b = [s['summary'] for s in studies]
    save(output/'comparison.json', dict(at=now(), inputs=inputs, method_sha256=sha256(__file__),
        matched_input_and_method_check=True, box=a, ball=b,
        ball_minus_box=dict(contact_crossings=b['contact_proper_crossings']-a['contact_proper_crossings'],
            contact_maximum_depth_m=b['contact_maximum_vertex_depth_m']-a['contact_maximum_vertex_depth_m'],
            actor_costs=[y-x for x, y in zip(a['cost_per_actor'], b['cost_per_actor'])]),
        scope='One development pair at its authored meeting pose; no new full-interval geometry audit, anatomical review or held-out evaluation.',
        candidate_selected_for_studio=False, quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('box', type=Path); parser.add_argument('ball', type=Path)
    parser.add_argument('output', type=Path); args = parser.parse_args()
    run(args.box, args.ball, args.output)
