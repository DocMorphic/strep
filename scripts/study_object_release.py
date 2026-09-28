"""Preserved original versus offline dynamic-release scenes, with failure audits."""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from object_release import release_request,simulate,bake,ENGINE

OUT=ROOT/'reports/object-release-v1'


def prepare():
    OUT.mkdir(exist_ok=False);cases=[]
    for seed in [11,22]:
        folder=ROOT/f'reports/object-attachment-v1/palm-attached-box-seed-{seed}'
        scene=read(folder/'scene.json');track=read(folder/'object-track.json');attachment=read(folder/'attachment.json')
        request=release_request(track,attachment['release_frame'])
        files={name:sha256(folder/name) for name in ['scene.json','object-track.json','attachment.json','events.json','palm.json','evaluation.json','orientation-audit.json','portable/scene.glb']}
        source=ROOT/scene['actors']['A']['motion'];asset=ROOT/'reports/object-attachment-v1'/scene['actors']['A']['preview_glb']
        cases.append(dict(id=f'seed-{seed}',source=folder.relative_to(ROOT).as_posix(),files=files,
            motion=source.relative_to(ROOT).as_posix(),motion_sha256=sha256(source),
            actor_glb=asset.relative_to(ROOT).as_posix(),actor_glb_sha256=sha256(asset),request=request))
    implementation={}
    for name in ['object_release.py','godot_object_release.gd','study_object_release.py','scene_constraints.py','object_geometry.py','audit_scene_orientation.py','export_attached_scene.py']:
        dest=OUT/'source-snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'scripts'/name,dest);implementation[name]=sha256(dest)
    save(OUT/'protocol.json',dict(at=now(),cases=cases,implementation=implementation,engine_sha256=sha256(ENGINE),
        gravity_m_s2=[0,-9.81,0],physics_fps=240,output_fps=30,mass_kg=5.,friction=.6,restitution=0.,
        assumptions='Hypothetical mass, uniform solid box, centered COM, infinite floor at Y=0, no actor collider. Explicit opt-in candidate. No learned model changes.',
        comparison='Keep original hand-followed/authored-tail output; change only object samples after release.',
        screens=dict(max_simulated_floor_depth_m=.01,max_final_floor_gap_m=.01,max_final_speed_m_s=.1),
        required_checks=['Preserved actor and pre-release object','unchanged events/contact targets','independent sampled body/object collisions',
            'all 240Hz floor samples','30fps and half-frame export floors','decoded and engine scene tracks','portable package and HTTP bytes'],
        held_out=False,human_approved=False))


def run():
    from scene_constraints import evaluate
    from audit_scene_orientation import audit
    from build_soma_preview import ASSET
    from export_attached_scene import export
    protocol=read(OUT/'protocol.json');assert sha256(ENGINE)==protocol['engine_sha256']
    for name,digest in protocol['implementation'].items():assert sha256(ROOT/'scripts'/name)==digest
    skin=dict(np.load(ASSET,allow_pickle=False));manifest=dict(created_at=now(),scenes=[],assets={});rows=[]
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',OUT/'SOMA-preview-LICENSE.txt')
    save(OUT/'pipeline.json',dict(status='processing'))
    for case in protocol['cases']:
        source=ROOT/case['source']
        for name,digest in case['files'].items():assert sha256(source/name)==digest
        assert sha256(ROOT/case['motion'])==case['motion_sha256'] and sha256(ROOT/case['actor_glb'])==case['actor_glb_sha256']
        original=read(source/'scene.json');preview=original['actors']['A']['preview_glb']
        dest=OUT/preview;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/case['actor_glb'],dest)
        manifest['assets'][preview]=dict(sha256=sha256(dest))
        original_folder=OUT/(case['id']+'-original');shutil.copytree(source,original_folder)
        simulation=simulate(case['request'],OUT/(case['id']+'-simulation'))
        track=read(source/'object-track.json');release=read(source/'attachment.json')['release_frame']
        candidate=bake(track,release,case['request'],simulation)
        folder=OUT/(case['id']+'-dynamic');folder.mkdir()
        scene=copy.deepcopy(original);scene['id']=case['id']+'-dynamic-release'
        scene['objects']['box']['keyframes']=[dict(frame=i,translation_m=p,rotation_xyzw=q) for i,(p,q) in enumerate(zip(candidate['positions_m'],candidate['rotations_xyzw']))]
        scene['objects']['box']['trajectory_provenance']=candidate['provenance']
        scene['review_note']='Offline simulated box release; actor unchanged. Floor-only physics, assumed 5 kg/.6 friction/zero restitution. Body/box collisions and existing grip failures remain; no animator approval.'
        evaluation=evaluate(scene,skin);orientation=audit(scene,skin)
        bundle=read(source/'palm.json');bundle.update(scene=scene,evaluation=evaluation)
        save(folder/'palm.json',bundle);save(folder/'scene.json',scene);save(folder/'object-track.json',candidate)
        save(folder/'evaluation.json',evaluation);save(folder/'orientation-audit.json',orientation)
        attachment=read(source/'attachment.json');attachment['tail_policy']=candidate['provenance']
        attachment['simulation_request']=case['request'];attachment['simulation_evidence']='../'+case['id']+'-simulation'
        save(folder/'attachment.json',attachment);shutil.copyfile(source/'events.json',folder/'events.json')
        observations=simulation['observations'];p=np.array([o['position_m'] for o in observations]);q=np.array([o['rotation_xyzw'] for o in observations])
        rotations=Rotation.from_quat(q).as_matrix();bottom=p[:,1]-np.abs(rotations[:,1,:])@(np.array(track['size_m'])/2)
        contacts=[o['tick'] for o in observations if o['contact_count']>0]
        depth=float(max(0,-bottom.min()));endgap=float(abs(bottom[-1]));endspeed=float(np.linalg.norm(observations[-1]['linear_velocity_m_s']))
        metrics=dict(id=case['id'],release_frame=release,simulation_ticks=len(observations),
            first_floor_contact_tick=contacts[0] if contacts else None,
            first_floor_contact_source_frame=release+contacts[0]/8 if contacts else None,
            simulated_floor_depth_max_m=depth,final_floor_gap_m=endgap,final_speed_m_s=endspeed,
            floor_screens_passed=depth<=.01 and endgap<=.01 and endspeed<=.1,
            original_floor_gap_m=float(read(ROOT/'reports/object-dynamics-v1/summary.json')['cases'][len(rows)]['released_bottom_height_min_m']),
            contact_metrics=evaluation['contacts'],body_box_collisions=evaluation['object_collisions'],human_approved=False)
        save(folder/'release-audit.json',metrics);rows.append(metrics)
        export(folder)
        # Exporter emits core scene content; include the simulation and its
        # audit in a separate report link until portable package verification.
        for label,variant_folder in [('Original authored release',original_folder),('Dynamic release candidate',folder)]:
            rel=variant_folder.relative_to(OUT).as_posix()
            manifest['scenes'].append(dict(id=rel,label=case['id']+' · '+label,variants=dict(palm=rel+'/palm.json'),
                orientation_file=rel+'/orientation-audit.json',review_note=scene['review_note'] if variant_folder==folder else original['review_note'],
                downloads=[dict(label='Scene pack · ZIP',path=rel+'/scene-pack.zip'),dict(label='Scene GLB',path=rel+'/portable/scene.glb'),dict(label='Grasp / release events',path=rel+'/events.json')]+([dict(label='Release audit',path=rel+'/release-audit.json')] if variant_folder==folder else [])))
        save(OUT/'manifest.json',manifest);save(OUT/'summary.json',dict(at=now(),cases=rows,quality_approved=False))
        print(case['id'],depth,endgap,endspeed,flush=True)
    save(OUT/'pipeline.json',dict(status='complete',at=now()))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args()
    OUT=args.output.resolve()
    prepare() if args.action=='prepare' else run()
