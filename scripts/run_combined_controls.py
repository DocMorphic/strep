"""Build the frozen combination matrix from existing neutral loops, without inference."""
import argparse
import shutil
import numpy as np
import torch
from strep import ROOT, read, save, sha256, now
from correct_stance import load_motion
from correct_loops import repeat_motion
from evaluate_grid import loop_screen
from combined_controls import combine, screen
from build_soma_preview import make_preview, ASSET
from gltf_tools import write_glb, read_glb, sample_animation


def main(output):
    from kimodo.skeleton import SOMASkeleton77
    from kimodo.exports.bvh import save_motion_bvh, bvh_to_kimodo_motion
    output=ROOT/output
    output.mkdir(parents=True,exist_ok=False)
    protocol=read(ROOT/'benchmarks/combined-controls-v1.json')
    save(output/'protocol.json',protocol)
    skeleton=SOMASkeleton77();skin=dict(np.load(ASSET,allow_pickle=False))
    source_folder=ROOT/'reports/control-calibration-v1/text'
    baseline=read(source_folder/'summary.json')
    thresholds=read(ROOT/'benchmarks/acceptance-v0.json')['targets']
    manifest={'id':protocol['id'],'created_at':now(),'protocol':protocol,'trials':[], 'baselines':[],
        'implementation_hashes':{name:sha256(ROOT/'scripts'/name) for name in ['combined_controls.py','run_combined_controls.py','motion_controls.py','build_soma_preview.py']},
        'asset_sha256':sha256(ASSET),'scope':protocol['scope']}
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
                loop=loop_screen(repeat_motion(motion,delta,3),30,thresholds)
                flags=screen(diagnostics,loop['screen_exceedances'],trial['accepted_source'],protocol)
                # Independently repeat the composition and require exact determinism.
                repeated,_=combine(source,skeleton,arm,lean)
                for key in motion:np.testing.assert_array_equal(motion[key],repeated[key])
                np.savez(folder/'motion.npz',**motion)
                glb_error=export(folder/'soma.glb',motion,delta)
                save_motion_bvh(folder/'motion.bvh',torch.from_numpy(motion['local_rot_mats']),torch.from_numpy(motion['root_positions']),skeleton=skeleton,fps=30,standard_tpose=True)
                restored,_=bvh_to_kimodo_motion(folder/'motion.bvh',skeleton=skeleton,standard_tpose=True)
                bvh_error=float(np.linalg.norm(restored['posed_joints'].numpy()-motion['posed_joints'],axis=-1).max())
                if bvh_error>1e-4:raise RuntimeError('BVH roundtrip error')
                record={'id':name,'seed':seed,'arm':arm,'lean':lean,'diagnostics':diagnostics,'loop':loop,
                    'flags':flags,'passed':not flags,'source_sha256':digest,'glb_joint_error_m':glb_error,
                    'bvh_joint_error_m':bvh_error,'repeat_exact':True,'exports':{f:sha256(folder/f) for f in ['motion.npz','motion.bvh','soma.glb']}}
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
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='reports/combined-controls-v1')
    main(parser.parse_args().output)
