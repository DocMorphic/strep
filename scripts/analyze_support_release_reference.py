"""Measure the reference-target change at every completed release ablation."""
import argparse
from pathlib import Path
import numpy as np
from strep import read, save, sha256, now


def run(study, output):
    study, output = study.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Preserve prior diagnostic')
    population = read(study/'results.json')['rows']
    rows, hashes = [], {}
    for item in population:
        if item['status'] != 'complete':
            continue
        folder = study/'takes'/item['id']
        for name, digest in item['files'].items():
            if sha256(folder/name) != digest:
                raise ValueError('Completed artifact changed')
        dynamics = read(folder/'release-dynamics.json')
        request = read(folder/'request.json')
        fps = read(folder/'spec.json')['fps']
        for name in ['release-dynamics.json','request.json','spec.json']:
            hashes[str(folder/name)] = sha256(folder/name)
        for side, guide in request['support']['guides'].items():
            weights = np.asarray(guide['weights'])
            anchor = np.asarray(guide['anchors_xz_m'])
            tracks = {key: np.asarray(value['feet'][side]['centroids_m']) for key,value in dynamics.items()}
            if any(len(track) != len(weights) for track in tracks.values()):
                raise ValueError('Track/weight clock differs')
            for release in dynamics['candidate']['feet'][side]['releases']:
                b = release['release_frame']
                if b < 1 or b >= len(weights):
                    raise ValueError('Invalid release frame')
                prior, raw, candidate = tracks['prior'], tracks['input'], tracks['candidate']
                frames = release['acceleration_frames']
                acceleration = {key: np.diff(track,n=2,axis=0)*fps**2 for key,track in tracks.items()}
                peaks = {key: max(frames,key=lambda f: np.linalg.norm(values[f-1])) for key,values in acceleration.items()}
                maxima = {key: float(np.linalg.norm(values[peaks[key]-1])) for key,values in acceleration.items()}
                if abs(maxima['candidate']-release['acceleration_max_m_s2'])>1e-9:
                    raise ValueError('Decoded release metric differs')
                rows.append(dict(case=item['id'],side=side,release_frame=b,
                    support_weight_before=float(weights[b-1]),support_weight_after=float(weights[b]),
                    horizontal_reference_weight_before=float(30*np.sqrt(1-weights[b-1])),
                    horizontal_reference_weight_after=float(30*np.sqrt(1-weights[b])),
                    last_support_anchor_xz_m=anchor[b-1].tolist(),
                    raw_to_anchor_offset_before_m=float(np.linalg.norm(raw[b-1,[0,2]]-anchor[b-1])),
                    corrected_to_raw_offset_before_m=float(np.linalg.norm(candidate[b-1,[0,2]]-raw[b-1,[0,2]])),
                    raw_to_anchor_reference_change_m=float(np.linalg.norm(raw[b,[0,2]]-anchor[b-1])),
                    candidate_to_raw_swing_target_m=float(np.linalg.norm(raw[b,[0,2]]-candidate[b-1,[0,2]])),
                    raw_horizontal_step_m=float(np.linalg.norm(raw[b,[0,2]]-raw[b-1,[0,2]])),
                    candidate_horizontal_step_m=float(np.linalg.norm(candidate[b,[0,2]]-candidate[b-1,[0,2]])),
                    acceleration_peak_frames=peaks,acceleration_peak_m_s2=maxima,
                    acceleration_regresses=maxima['candidate']>max(maxima['input'],maxima['prior'])+1e-5))
    output.mkdir(parents=True)
    save(output/'summary.json',dict(at=now(),study=str(study),implementation_sha256=sha256(__file__),inputs=hashes,
         completed_cases=[r['id'] for r in population if r['status']=='complete'],
         unfinished_cases=[r['id'] for r in population if r['status']!='complete'],
         releases=len(rows),regressing_releases=sum(r['acceleration_regresses'] for r in rows),rows=rows,
         quality_approved=False,scope='Read-only target/centroid release diagnostic. Reference weights are before per-patch normalization. '
         'Target changes are evidence of objective discontinuity, not proof of sole causation, physical correctness or improved motion.'))
    print(dict(releases=len(rows),regressing_releases=sum(r['acceleration_regresses'] for r in rows)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.study,args.output)
