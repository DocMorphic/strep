"""Audit an authored target and its exact model-representation roundtrip.

No inference or fitting. Separates target inconsistency from sampling error.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from kimodo.skeleton import SOMASkeleton30,SOMASkeleton77
from build_soma_preview import ASSET,make_preview
from gltf_tools import write_glb
from floor_contact import Surface
from convex_partner_surface import penetration
from verify_palm_region import measure


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier target audit')
    spec=read(study/'protocol.json');scene=read(study/'guide-scene.json')['scene'];event=spec['event_frame']
    if sha256(study/'guide-scene.json')!=spec['guide_scene_sha256']:raise ValueError('Changed guide scene')
    small,full=SOMASkeleton30(),SOMASkeleton77();skin=dict(np.load(ASSET,allow_pickle=False));surface=Surface(skin)
    patches_path=Path(spec['guide_export'])/'refinement/palm-region.json';patches=read(patches_path)
    output.mkdir();(output/'implementation').mkdir()
    for name in ['audit_paired_guide_target.py','convex_partner_surface.py','verify_palm_region.py','floor_contact.py']:
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),source_protocol_sha256=sha256(study/'protocol.json'),guide_scene_sha256=sha256(study/'guide-scene.json'),
        event=event,skin_sha256=sha256(ASSET),patch_sha256=sha256(patches_path),point_tolerance_m=.03,penetration_tolerance_m=.005,floor_tolerance_m=.005,
        region_tolerance_m=.003,region_area_m2=2.5e-5,opposing_region_normal_degrees=20,quality_approved=False,
        scope='Single frozen target frame before generation. Exact SOMA77-to30-to77 representation conversion; no fitting, inference, timing, whole-clip or anatomy approval.'))
    groups={'authored':{},'model_roundtrip':{}};conversion=[];manifest=dict(scenes=[],assets={})
    with threadpool_limits(limits=1):
        for name in ['A','B']:
            path=ROOT/spec['guides'][name]['path']
            if sha256(path)!=spec['guides'][name]['sha256']:raise ValueError('Changed guide motion')
            original=dict(np.load(path,allow_pickle=False));local=torch.tensor(original['local_rot_mats'],dtype=torch.float32)
            reduced=small.from_SOMASkeleton77(local);expanded=small.to_SOMASkeleton77(reduced);r,p,_=full.fk(expanded,torch.tensor(original['root_positions'],dtype=torch.float32))
            restored=copy.deepcopy(original);restored.update(local_rot_mats=expanded.numpy(),global_rot_mats=r.numpy(),posed_joints=p.numpy())
            wrist=full.bone_order_names.index('LeftHand');conversion.append(dict(actor=name,source_sha256=sha256(path),
                event_wrist_position_error_m=float(np.linalg.norm(restored['posed_joints'][event,wrist]-original['posed_joints'][event,wrist])),
                event_wrist_rotation_error_degrees=float(np.degrees(Rotation.from_matrix(restored['global_rot_mats'][event,wrist].T@original['global_rot_mats'][event,wrist]).magnitude()))))
            for variant,data in [('authored',original),('model_roundtrip',restored)]:
                folder=output/variant/name;folder.mkdir(parents=True);np.savez_compressed(folder/'motion.npz',**data)
                doc,binary,_,_=make_preview(skin,data,np.zeros(3),repeat=False);write_glb(folder/'character.glb',doc,binary)
                transform=scene['actors'][name]['transform'];rot=Rotation.from_quat(transform['rotation_xyzw']).as_matrix()
                groups[variant][name]=surface.vertices(data['global_rot_mats'][event],data['posed_joints'][event])@rot.T+transform['translation_m']
                manifest['assets'][f'{variant}/{name}/character.glb']=dict(sha256=sha256(folder/'character.glb'))
        results={};vertex=scene['contacts'][0]['effector']['surface_vertex']
        for variant,actors in groups.items():
            points=[actors[name] for name in ['A','B']];region=measure(points,[patches['A'],patches['B']],skin['faces'],.003)
            collision=[penetration(points[a],points[b],skin['faces']) for a,b in [(0,1),(1,0)]]
            gap=float(np.linalg.norm(points[0][vertex]-points[1][vertex]));floor=[max(0.,-float(p[:,1].min())) for p in points]
            passed=dict(point=gap<=.03,region=all(d['within_tolerance_count']>=3 and min(d['source_area_witness']['area_m2'],d['target_area_witness']['area_m2'])>=2.5e-5 for d in region['directions']),normal=region['opposing_normal_degrees']<=20,penetration=max(c['max_depth_m'] for c in collision)<=.005,floor=max(floor)<=.005)
            results[variant]=dict(palm_point_gap_m=gap,palm_A_minus_B_m=(points[0][vertex]-points[1][vertex]).tolist(),region=region,collision=collision,floor_depth_m=floor,screens=passed,target_screens_passed=all(passed.values()))
            current=copy.deepcopy(scene);current['id']='guide-target-'+variant
            for name,entry in current['actors'].items():
                entry.update(motion=(output/variant/name/'motion.npz').relative_to(ROOT).as_posix(),source_sha256=sha256(output/variant/name/'motion.npz'),preview_glb=f'{variant}/{name}/character.glb')
            save(output/(variant+'-scene.json'),dict(scene=current));manifest['scenes'].append(dict(id=current['id'],variants={'palm':variant+'-scene.json'}))
    save(output/'manifest.json',manifest);shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
    save(output/'verification.json',dict(at=now(),frame=event,variants=results,conversion=conversion,request_sha256=sha256(output/'request.json'),manifest_sha256=sha256(output/'manifest.json'),quality_approved=False,
        conclusion='Target feasibility is separate from generated adherence. Failed target screens cannot be attributed solely to model sampling error. No corrected or generated motion is produced by this audit.'))
    save(output/'pipeline.json',dict(status='complete',quality_approved=False));print({k:v['screens'] for k,v in results.items()},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
