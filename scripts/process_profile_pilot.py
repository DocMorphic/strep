"""Apply frozen loop and stance algorithms to every profile take, preserving failures."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now,source_check
from profile_inputs import DEFAULT_STUDY,validate_study
from correct_stance import load_motion,main as stance_main
from correct_loops import shortlist,evaluate_candidate,repeat_motion


def main(folder,study_path):
    from kimodo.skeleton import SOMASkeleton77
    folder=Path(folder).resolve();study=validate_study(read(study_path));skeleton=SOMASkeleton77()
    config=read(ROOT/'benchmarks/loop-correction-v1.json');targets=read(ROOT/'benchmarks/acceptance-v0.json')['targets']
    for profile in study['profiles']:
        loop_folder=folder/'loop'/profile['id'];stance_folder=folder/'stance'/profile['id']
        if (stance_folder/'summary.json').exists():
            previous=read(stance_folder/'summary.json')
            if previous.get('finished_at'):
                print('Already processed '+profile['id'],flush=True);continue
            raise RuntimeError('Incomplete stance output retained; inspect before retrying into a fresh directory')
        loop_folder.mkdir(parents=True,exist_ok=True)
        result={'started_at':now(),'source_commit':source_check(),'config':config,'study_sha256':sha256(study_path),
            'implementation_sha256':sha256(ROOT/'scripts/correct_loops.py'),'config_sha256':sha256(ROOT/'benchmarks/loop-correction-v1.json'),
            'acceptance_rubric_sha256':sha256(ROOT/'benchmarks/acceptance-v0.json'),'trials':[]}
        for seed in study['seeds']:
            out=loop_folder/f'seed-{seed}'
            if (out/'report.json').exists():
                winner=read(out/'report.json')
                if sha256(out/'corrected.npz')!=winner['corrected_sha256'] or sha256(winner['source'])!=winner['source_sha256']:raise RuntimeError('Existing loop output changed')
                result['trials'].append(winner);continue
            records=sorted((folder/'raw'/profile['id']/f'seed-{seed}').glob('attempt-*/record.json'))
            successful=[read(p) for p in records if read(p)['status']=='generated']
            if not successful:raise RuntimeError(f'Missing successful raw take: {profile["id"]}/{seed}')
            record=successful[-1]
            if record['study_sha256']!=sha256(study_path) or sha256(record['npz'])!=record['npz_sha256']:raise RuntimeError('Raw provenance differs')
            source=load_motion(record['npz']);candidates=[];best=None
            for blend in config['blend_frames']:
                for phase,start,length in shortlist(source,blend,config):
                    for mode in config['root_modes']:
                        candidate,corrected=evaluate_candidate(source,start,length,blend,mode,skeleton,config,targets,record['metrics'])
                        candidate['phase_match_score']=phase;candidates.append(candidate)
                        if best is None or candidate['selection_score']<best[0]['selection_score']:best=candidate,corrected
            winner,corrected=best;out.mkdir(exist_ok=False)
            np.savez(out/'corrected.npz',**corrected)
            winner.update(seed=seed,source=record['npz'],source_sha256=record['npz_sha256'],corrected_sha256=sha256(out/'corrected.npz'),full_raw_metrics=record['metrics'])
            save(out/'report.json',winner);save(out/'candidates.json',candidates);result['trials'].append(winner)
            save(loop_folder/'summary.json',result)
            print(f'Loop {profile["id"]}/{seed}: accepted={winner["numerically_accepted"]}',flush=True)
        result['finished_at']=now();save(loop_folder/'summary.json',result)
        stance_main(stance_folder,loop_folder)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--study',type=Path,default=DEFAULT_STUDY)
    a=p.parse_args();main(a.folder,a.study)
