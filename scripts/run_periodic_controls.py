"""Evaluate the frozen cyclic editor against v1, including a newly reserved take."""
import argparse
from pathlib import Path
import shutil
import numpy as np
import torch
from strep import ROOT, read, save, sha256, now
from correct_stance import load_motion
from correct_loops import repeat_motion
from evaluate_grid import loop_screen
from combined_controls import combine as combine_old, screen
from periodic_motion_controls import combine_periodic as combine, cyclic_dynamics
from build_soma_preview import make_preview, ASSET
from gltf_tools import write_glb, read_glb, sample_animation


def main(output):
    from kimodo.skeleton import SOMASkeleton77
    from kimodo.exports.bvh import save_motion_bvh, bvh_to_kimodo_motion
    output=ROOT/output
    if (output/'summary.json').exists():raise ValueError('Existing experiment is preserved')
    protocol=read(output/'protocol.json')
    freeze=read(output/'implementation-freeze.json')
    for name,digest in freeze['files'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise RuntimeError('Frozen implementation changed: '+name)
    save(output/'evaluation-freeze.json',{'frozen_at':now(),'script_sha256':sha256(Path(__file__))})
    skeleton=SOMASkeleton77();skin=dict(np.load(ASSET,allow_pickle=False))
    source_folder=ROOT/'reports/control-calibration-v1/text'
    baseline=read(source_folder/'summary.json')
    thresholds=read(ROOT/'benchmarks/acceptance-v0.json')['targets']
    manifest={'id':protocol['id'],'created_at':now(),'protocol':protocol,'trials':[], 'baselines':[],
        'implementation_hashes':{name:sha256(ROOT/'scripts'/name) for name in ['combined_controls.py','run_combined_controls.py','motion_controls.py','build_soma_preview.py']},
        'asset_sha256':sha256(ASSET),'scope':protocol['scope']}
    manifest['implementation_hashes']['periodic_motion_controls.py']=sha256(ROOT/'scripts/periodic_motion_controls.py')
    def export(path,motion,delta):
        doc,binary,positions,rotations=make_preview(skin,motion,delta)
        write_glb(path,doc,binary);decoded,payload=read_glb(path)
        error=0.
        for frame in range(len(positions)):
            matrices=sample_animation(decoded,payload,0,frame)[1:78]
            error=max(error,float(np.linalg.norm(matrices[:,:3,3]-positions[frame],axis=-1).max()))
        if error>1e-5:raise RuntimeError('SOMA animation roundtrip error')
        return error
    for seed in protocol['seeds']:
        source_folder=(output/'holdout') if seed in protocol['held_out_seeds'] else ROOT/'reports/control-calibration-v1/text'
        baseline=read(source_folder/'summary.json')
        trial=next(t for t in baseline['trials'] if t['profile']=='neutral' and t['seed']==seed)
        source_path=source_folder/'stance/neutral'/f'seed-{seed}/corrected.npz'
        digest=sha256(source_path)
        if digest!=trial['stance_report']['corrected_sha256']:raise RuntimeError('Baseline hash mismatch')
        source=load_motion(source_path);delta=np.array(trial['processed_cycle_displacement_m'])
        neutral=output/'neutral'/f'seed-{seed}';neutral.mkdir(parents=True)
        export(neutral/'soma.glb',source,delta)
        manifest['baselines'].append({'seed':seed,'path':str(source_path),'sha256':digest,'accepted':trial['accepted_source']})
        for arm in protocol['arm_targets_degrees']:
            for lean in protocol['lean_targets_degrees']:
                name=f'arm-{arm}-lean-{lean}-seed-{seed}';folder=output/'takes'/name;folder.mkdir(parents=True)
                motion,diagnostics=combine(source,skeleton,arm,lean)
                previous,old_diagnostics=combine_old(source,skeleton,arm,lean)
                old_loop=loop_screen(repeat_motion(previous,delta,3),30,thresholds)
                old_dynamics=cyclic_dynamics(previous);new_dynamics=cyclic_dynamics(motion)
                loop=loop_screen(repeat_motion(motion,delta,3),30,thresholds)
                flags=screen(diagnostics,loop['screen_exceedances'],trial['accepted_source'],protocol)
                flags.extend('missing_'+key for key in loop['missing_screen_measures'])
                for key,old_value in old_dynamics.items():
                    if new_dynamics[key]>old_value*protocol['maximum_dynamics_ratio']+1e-6:flags.append(key+'_regression')
                # Independently repeat the composition and require exact determinism.
                repeated,_=combine(source,skeleton,arm,lean)
                for key in motion:np.testing.assert_array_equal(motion[key],repeated[key])
                np.savez(folder/'motion.npz',**motion)
                glb_error=export(folder/'soma.glb',motion,delta)
                before_error=export(folder/'before.glb',previous,delta)
                save_motion_bvh(folder/'motion.bvh',torch.from_numpy(motion['local_rot_mats']),torch.from_numpy(motion['root_positions']),skeleton=skeleton,fps=30,standard_tpose=True)
                restored,_=bvh_to_kimodo_motion(folder/'motion.bvh',skeleton=skeleton,standard_tpose=True)
                bvh_error=float(np.linalg.norm(restored['posed_joints'].numpy()-motion['posed_joints'],axis=-1).max())
                if bvh_error>1e-4:raise RuntimeError('BVH roundtrip error')
                record={'id':name,'seed':seed,'arm':arm,'lean':lean,'diagnostics':diagnostics,'loop':loop,
                    'old_loop':old_loop,'old_dynamics':old_dynamics,'new_dynamics':new_dynamics,'before_glb_joint_error_m':before_error,
                    'split':'held_out' if seed in protocol['held_out_seeds'] else 'development',
                    'old_passed':not screen(old_diagnostics,old_loop['screen_exceedances'],trial['accepted_source'],protocol),
                    'flags':flags,'passed':not flags,'source_sha256':digest,'glb_joint_error_m':glb_error,
                    'bvh_joint_error_m':bvh_error,'repeat_exact':True,'exports':{f:sha256(folder/f) for f in ['motion.npz','motion.bvh','soma.glb','before.glb']}}
                save(folder/'evidence.json',record);manifest['trials'].append(record)
                save(output/'summary.json',manifest)
                print(name+': '+(', '.join(flags) or 'source screens pass'),flush=True)
        if sha256(source_path)!=digest:raise RuntimeError('Source changed')
    manifest['pairs']=[{'arm':arm,'lean':lean,'enabled':all(t['passed'] for t in manifest['trials'] if t['arm']==arm and t['lean']==lean),
        'passed_takes':sum(t['passed'] for t in manifest['trials'] if t['arm']==arm and t['lean']==lean)}
        for arm in protocol['arm_targets_degrees'] for lean in protocol['lean_targets_degrees']]
    save(output/'summary.json',manifest)
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
    print(f"Finished {len(manifest['trials'])} combinations; {sum(p['enabled'] for p in manifest['pairs'])}/{len(manifest['pairs'])} pairs pass all seeds.")


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='reports/periodic-controls-v1')
    main(parser.parse_args().output)
