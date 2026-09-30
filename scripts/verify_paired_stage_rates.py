"""Recompute staged rate rows from bound decoded tracks and summarize regressions."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now


def verify_rates(source,candidate,rates,names):
    """Separate direct-difference replay, including each joint's peak location."""
    comparisons=0;maximum_error=0.
    for metric in ['speed','acceleration']:
        arrays=[]
        for positions in [source,candidate]:
            values=(positions[1:]-positions[:-1])*120 if metric=='speed' else (positions[2:]-2*positions[1:-1]+positions[:-2])*14400
            arrays.append(np.sqrt((values*values).sum(-1)))
        times=(np.arange(len(arrays[0]))+(.5 if metric=='speed' else 1))/4
        for window in rates[metric]['windows']:
            mask=(times>=window['start_frame'])&(times<=window['end_frame']);clock=times[mask]
            if window['samples']!=len(clock) or [j['joint'] for j in window['joints']]!=names:raise ValueError('Changed sampled joint population')
            peaks=[a[mask].max(0) for a in arrays]
            if window['increased_joints_over_1e_5']!=int(np.sum(peaks[1]-peaks[0]>1e-5)):raise ValueError('Wrong increase count')
            for side,label in enumerate(['source','candidate']):
                np.testing.assert_allclose(window[label+'_peak'],peaks[side].max(),atol=1e-8,rtol=0)
                for joint,row in enumerate(window['joints']):
                    value=peaks[side][joint];delta=abs(value-row[label+'_peak']);maximum_error=max(maximum_error,float(delta))
                    if delta>1e-8 or row[label+'_peak_frame']!=clock[arrays[side][mask,joint].argmax()]:raise ValueError('Rate peak or clock mismatch')
            np.testing.assert_allclose([r['change'] for r in window['joints']],peaks[1]-peaks[0],atol=1e-8,rtol=0)
            comparisons+=2*len(names)
    return comparisons,maximum_error


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve();result,protocol=read(study/'result.json'),read(study/'protocol.json')
    if output.exists():raise ValueError('Preserve earlier verification')
    if result['status']!='complete' or result['protocol_sha256']!=sha256(study/'protocol.json'):raise ValueError('Completed unchanged audit required')
    for file,digest in protocol['inputs'].items():
        if sha256(file)!=digest:raise ValueError('Bound source changed')
    for name,digest in protocol['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Audit snapshot changed')
    expected={(s,a) for s in protocol['seeds'] for a in ['A','B']}
    if len(result['rows'])!=len(expected) or {(r['seed'],r['actor']) for r in result['rows']}!=expected:raise ValueError('Incomplete actor results')
    bindings={(r['seed'],r['actor'],r['method']) for r in result['bindings']}
    if bindings!={(s,a,m) for s,a in expected for m in protocol['methods']} or len(result['bindings'])!=len(bindings) or any(r['samples']!=597 for r in result['bindings']):raise ValueError('Incomplete clip/sample population')
    aggregates={};verified_rows=0;maximum_error=0.;case_rows=[]
    for actor in result['rows']:
        positions_path=study/f"seed-{actor['seed']}-{actor['actor']}-positions.npz"
        if sha256(positions_path)!=actor['positions_sha256']:raise ValueError('Decoded tracks changed')
        tracks=dict(np.load(positions_path,allow_pickle=False))
        if set(tracks)!=set(protocol['methods']) or any(v.shape!=(597,77,3) or not np.isfinite(v).all() for v in tracks.values()):raise ValueError('Bad decoded track layout')
        if len(actor['comparisons'])!=3 or {(r['before'],r['after']) for r in actor['comparisons']}!={tuple(e) for e in protocol['comparisons']}:raise ValueError('Incomplete stage comparisons')
        for comparison in actor['comparisons']:
            path=study/comparison['file']
            if sha256(path)!=comparison['sha256']:raise ValueError('Stage rate report changed')
            detail=read(path);rates=detail['rates'];before,after=comparison['before'],comparison['after']
            if (detail['seed'],detail['actor'],detail['before'],detail['after'])!=(actor['seed'],actor['actor'],before,after):raise ValueError('Stage identity mismatch')
            names=[j['joint'] for j in rates['speed']['windows'][0]['joints']]
            n,error=verify_rates(tracks[before],tracks[after],rates,names);verified_rows+=n;maximum_error=max(maximum_error,error)
            for metric in ['speed','acceleration']:
                for window in rates[metric]['windows']:
                    key=(before,after,metric,window['window'])
                    record=aggregates.setdefault(key,dict(before=before,after=after,metric=metric,window=window['window'],
                        actors=0,actors_with_joint_increase=0,actors_with_global_increase=0,masked_actor_increases=0,total_joint_increases=0,largest_increase=None))
                    record['actors']+=1;changed=window['increased_joints_over_1e_5'];global_up=window['candidate_peak']>window['source_peak']+1e-5
                    record['actors_with_joint_increase']+=bool(changed);record['actors_with_global_increase']+=bool(global_up)
                    record['masked_actor_increases']+=bool(changed and not global_up);record['total_joint_increases']+=changed
                    joint=max(window['joints'],key=lambda j:j['change'])
                    detail_row=dict(seed=actor['seed'],actor=actor['actor'],**joint)
                    if record['largest_increase'] is None or joint['change']>record['largest_increase']['change']:record['largest_increase']=detail_row
                    if metric=='acceleration' and window['window'] in ['whole_clip','event']:
                        case_rows.append(dict(seed=actor['seed'],actor=actor['actor'],before=before,after=after,window=window['window'],
                            source_peak=window['source_peak'],candidate_peak=window['candidate_peak'],increased_joints=changed,largest_increase=joint))
    output.mkdir();shutil.copyfile(__file__,output/Path(__file__).name)
    report=dict(at=now(),result_sha256=sha256(study/'result.json'),protocol_sha256=sha256(study/'protocol.json'),verifier_sha256=sha256(__file__),
        actor_clips=len(bindings),decoded_actor_samples=result['decoded_actor_samples'],verified_joint_peak_values=verified_rows,
        maximum_replay_error=maximum_error,comparisons=list(aggregates.values()),case_rows=case_rows,
        historical_geometry=result['historical_geometry'],historical_engine_actor_frames=result['historical_engine_actor_frames'],new_engine_actor_frames=0,
        quality_approved=False,scope='Hash-bound full-population stage attribution. Rate increases are diagnostics, not proof of unnaturalness. Prior geometry/engine results are reused, not rerun; no candidate changes or new motion generation.')
    save(output/'verification.json',report);print(dict(clips=len(bindings),samples=result['decoded_actor_samples'],peak_values=verified_rows,maximum_error=maximum_error),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.study,args.output)
