"""Verify all-seed repeatability, frozen inputs, and correction invariants."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from correct_stance import load_motion


def main(study,reproduction):
    study,reproduction=Path(study).resolve(),Path(reproduction).resolve()
    first,second=read(study/'summary.json'),read(reproduction/'summary.json')
    for key in ('implementation_sha256','config_sha256','acceptance_sha256','baseline_summary_sha256','source_commit'):
        if first[key]!=second[key]:raise RuntimeError(f'Provenance differs: {key}')
    baseline=Path(first['baseline'])
    if sha256(baseline/'summary.json')!=first['baseline_summary_sha256']:
        raise RuntimeError('Frozen baseline summary changed')
    outcomes=[]
    for trial,other in zip(first['trials'],second['trials']):
        if trial!=other:raise RuntimeError('Trial metrics or selection differ')
        seed=trial['seed']
        a,b=load_motion(study/f'seed-{seed}/corrected.npz'),load_motion(reproduction/f'seed-{seed}/corrected.npz')
        if set(a)!=set(b) or not all(np.array_equal(a[k],b[k]) for k in a):raise RuntimeError('Output arrays differ')
        if read(study/f'seed-{seed}/candidates.json')!=read(reproduction/f'seed-{seed}/candidates.json'):raise RuntimeError('Candidate metrics differ')
        source=load_motion(trial['source'])
        if sha256(trial['source'])!=trial['source_sha256']:raise RuntimeError('Input modified')
        if not np.array_equal(a['foot_contacts'],source['foot_contacts']):raise RuntimeError('Contacts modified')
        if not np.array_equal(a['root_positions'][:,[0,2]],source['root_positions'][:,[0,2]]):raise RuntimeError('Horizontal root modified')
        outcomes.append({'seed':seed,'exact_reproduction':True,'contacts_unchanged':True,'horizontal_root_unchanged':True,'accepted':trial['accepted']})
    if len(outcomes)!=5 or [x['seed'] for x in outcomes]!=[11,22,33,44,55]:raise RuntimeError('Missing seeds')
    for trial in read(baseline/'summary.json')['trials']:
        raw=Path(trial['source'])
        record=read(raw.parent.parent/'record.json')
        if sha256(raw)!=record['source_motion_file_and_hash']['sha256']:raise RuntimeError('Original raw motion modified')
    result={'checked_at':now(),'status':'passed','scope':'Same machine/environment; exact arrays and all candidate metrics.',
        'frozen_baseline_summary_unchanged':True,'original_raw_hashes_preserved':True,'trials':outcomes}
    save(study/'reproducibility.json',result)
    print('PASS: all five outputs, candidate metrics, frozen sources, labels, and horizontal root paths verified.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',type=Path);parser.add_argument('reproduction',type=Path)
    args=parser.parse_args();main(args.study,args.reproduction)
