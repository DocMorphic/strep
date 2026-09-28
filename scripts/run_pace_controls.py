"""Export exact pace variants with aligned GLB/BVH/NPZ clocks and event tracks."""
import argparse
import re
import shutil
import zipfile
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb,write_glb,accessor
from build_soma_preview import ASSET
from export_profile_characters import repeated_with_terminal
from profile_metrics import descriptors
from evaluate_grid import loop_screen
from pace_controls import retime_glb,contact_intervals,foot_surface_measurements


def main(output):
    from kimodo.skeleton import SOMASkeleton77
    from kimodo.exports.bvh import motion_to_bvh,bvh_to_kimodo_motion
    output=ROOT/output;output.mkdir(parents=True,exist_ok=False)
    protocol=read(ROOT/'benchmarks/pace-controls-v1.json');save(output/'protocol.json',protocol)
    parent=ROOT/'reports/periodic-controls-v1';source=read(parent/'summary.json')
    skin=dict(np.load(ASSET));skeleton=SOMASkeleton77();foot_names=[side+n for side in ['Left','Right'] for n in ['Foot','ToeBase','ToeEnd']]
    manifest={'id':protocol['id'],'created_at':now(),'protocol':protocol,'trials':[],
        'source_summary_sha256':sha256(parent/'summary.json'),
        'implementation_hashes':{p:sha256(ROOT/'scripts'/p) for p in ['pace_controls.py','run_pace_controls.py']}}
    save(output/'implementation-freeze.json',{'frozen_at':now(),**manifest['implementation_hashes']})
    shutil.copyfile(parent/'SOMA-preview-LICENSE.txt',output/'SOMA-preview-LICENSE.txt')
    thresholds=read(ROOT/'benchmarks/acceptance-v0.json')['targets']
    selected=[t for t in source['trials'] if t['arm'] in protocol['arm_targets_degrees'] and t['lean'] in protocol['lean_targets_degrees']]
    assert len(selected)==48 and all(t['passed'] for t in selected)
    for trial in selected:
        folder=parent/'takes'/trial['id'];doc,binary=read_glb(folder/'soma.glb')
        assert sha256(folder/'soma.glb')==trial['exports']['soma.glb'] and sha256(folder/'motion.npz')==trial['exports']['motion.npz']
        cycle=dict(np.load(folder/'motion.npz'));_,_,native=retime_glb(doc,binary,3)
        delta=np.array(native['cycle_displacement_m']);full=repeated_with_terminal(cycle,delta)
        foot=foot_surface_measurements(cycle,skin,delta,protocol)
        native_descriptors=descriptors(full,30)
        bvh=motion_to_bvh(torch.from_numpy(full['local_rot_mats']),torch.from_numpy(full['root_positions']),skeleton=skeleton,fps=30,standard_tpose=True)
        for speed in protocol['speeds_m_s']:
            name=trial['id']+f'-pace-{speed:.1f}';destination=output/'takes'/name;destination.mkdir(parents=True)
            changed,payload,timing=retime_glb(doc,binary,speed);write_glb(destination/'soma.glb',changed,payload)
            decoded,buffer=read_glb(destination/'soma.glb');animation=decoded['animations'][0]
            times=accessor(decoded,buffer,animation['samplers'][0]['input'])
            for old,new in zip(doc['animations'][0]['samplers'],animation['samplers']):
                np.testing.assert_array_equal(accessor(doc,binary,old['output']),accessor(decoded,buffer,new['output']))
            assert len(times)==len(full['posed_joints'])
            actual_speed=float((full['root_positions'][-1,2]-full['root_positions'][0,2])/(times[-1]-times[0]))
            assert abs(actual_speed-speed)<protocol['timing_speed_tolerance_m_s']
            np.savez(destination/'motion.npz',**full)
            clock={'effective_fps':timing['effective_fps'],'key_times_s':times.tolist(),'duration_s':float(times[-1]),
                'cycle_duration_s':float(times[-1]/4),'cycles':4,'cycle_displacement_m':delta.tolist(),
                'includes_terminal_pose':True,'npz_timing':'Use these times; the NPZ pose arrays do not imply 30 fps.'}
            save(destination/'timing.json',clock)
            # Keep the vendor pose serialization, but retain sufficient precision
            # in BVH Frame Time for exact requested pace.
            text=re.sub(r'Frame Time:\s*[^\r\n]+',f"Frame Time: {1/timing['effective_fps']:.12f}",bvh)
            (destination/'motion.bvh').write_text(text,encoding='utf-8')
            restored,bvh_fps=bvh_to_kimodo_motion(destination/'motion.bvh',skeleton=skeleton,standard_tpose=True)
            bvh_error=float(np.linalg.norm(restored['posed_joints'].numpy()-full['posed_joints'],axis=-1).max())
            assert bvh_error<1e-4 and abs((len(times)-1)/bvh_fps-float(times[-1]))<1e-5
            contacts=contact_intervals(full['foot_contacts'],times,foot_names)
            save(destination/'contacts.json',{'time_unit':'seconds','provenance':'Predicted bone-contact labels, not verified foot strikes. Intervals clipped by clip boundaries are marked.','intervals':contacts})
            quats=Rotation.from_matrix(full['global_rot_mats'][:,0]).as_quat()
            for i in range(1,len(quats)):
                if np.dot(quats[i-1],quats[i])<0:quats[i]*=-1
            save(destination/'root-motion.json',{'space':'SOMA Hips world transform in meters, Y up, +Z forward. Engine root extraction convention not selected.',
                'times_s':times.tolist(),'positions_m':full['root_positions'].tolist(),'rotations_xyzw':quats.tolist()})
            measured=descriptors(full,timing['effective_fps'])
            screening=loop_screen({k:v[:-1] for k,v in full.items()},timing['effective_fps'],thresholds)
            contact_flags=[];patch=foot['native_patch_speed_p95_m_s']
            current_patch=None if patch is None else patch*timing['time_scale']
            if current_patch is None:contact_flags.append('missing_support_patch_measurement')
            else:
                if current_patch>protocol['predicted_support_patch_speed_warning_m_s']:contact_flags.append('support_patch_sliding')
                if current_patch-patch>protocol['maximum_patch_speed_increase_m_s']:contact_flags.append('support_patch_regression')
            if foot['maximum_foot_penetration_m']>protocol['mesh_foot_penetration_warning_m']:contact_flags.append('foot_surface_penetration')
            flags=screening['screen_exceedances']+['missing_'+k for k in screening['missing_screen_measures']]+contact_flags
            recipe={'version':protocol['id'],'source_style':trial['id'],'source_sha256':trial['exports']['motion.npz'],
                'arm_range_degrees':trial['arm'],'torso_lean_degrees':trial['lean'],'seed':trial['seed'],'speed_m_s':speed,
                'effective_fps':timing['effective_fps'],'cadence_steps_min':measured['cadence_steps_min'],
                'method':'Uniform asset retiming, coupled speed/cadence, unchanged stride and pose sequence.',
                'contact_markers':'Model-predicted intervals, not independently annotated.','screen_flags':flags,'human_approved':False,'capability_mapping':None}
            save(destination/'recipe.json',recipe)
            record={'id':name,'source_style':trial['id'],'source_sha256':trial['exports']['motion.npz'],'seed':trial['seed'],
                'arm':trial['arm'],'lean':trial['lean'],'speed':speed,'timing':timing,'actual_speed_m_s':actual_speed,
                'native_descriptors':native_descriptors,'descriptors':measured,'foot_surface':foot,'patch_speed_p95_m_s':current_patch,
                'loop':screening,'contact_flags':contact_flags,'flags':flags,'passed':not flags,
                'bvh_joint_error_m':bvh_error,'pose_keys_unchanged':True,'contact_intervals':len(contacts)}
            save(destination/'evidence.json',record)
            files=['soma.glb','motion.bvh','motion.npz','timing.json','contacts.json','root-motion.json','recipe.json','evidence.json']
            with zipfile.ZipFile(destination/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as archive:
                for file in files:archive.write(destination/file,file)
                archive.write(output/'SOMA-preview-LICENSE.txt','LICENSE.txt')
            record['export_hashes']={file:sha256(destination/file) for file in files+['animation-pack.zip']}
            manifest['trials'].append(record);save(output/'summary.json',manifest)
        print(trial['id']+': all three pace exports verified',flush=True)
    manifest['counts']={'exports':len(manifest['trials']),'passes':sum(t['passed'] for t in manifest['trials'])}
    save(output/'summary.json',manifest);print(manifest['counts'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='reports/pace-controls-v1')
    main(parser.parse_args().output)
