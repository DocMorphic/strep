"""Immutable multi-action, three-rig mirror export and actual-engine study."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_mirror import draft_correspondence,write_clip,mirror,descendants
from rig_transition import localize


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    implementation=output/'implementation';implementation.mkdir()
    files=['study_rig_mirror.py','rig_mirror.py','rig_asset.py','rig_clip_import.py','rig_transition.py','rig_loop.py','gltf_tools.py','target_rig_contact.py','run_godot_rig_import.py','godot_import_audit.gd','strep.py']
    for name in files:shutil.copyfile(ROOT/'scripts'/name,implementation/name)
    cases=[]
    for motion in ['motion-026','motion-011','motion-006']:
        for rig_id in ['rig-01','rig-02','rig-03']:
            identity=motion+'-'+rig_id;source=ROOT/'reports/whole-support-breadth-v1/takes'/identity/'input'
            report=read(source/'report.json');rig=RigAsset.load(source/'character.glb');mapping=report['mapping'];root=report['root_node']
            normal=rig.reference[mapping['LeftLeg'],:3,3]-rig.reference[mapping['RightLeg'],:3,3];normal[1]=0;normal/=np.linalg.norm(normal)
            point=AnimationSampler(rig.document,rig.binary,0).sample(0)[root,:3,3]
            recipe=dict(schema='strep-rig-mirror-v1',source_sha256=sha256(source/'character.glb'),frames=report['frames'],fps=30,root_node=root,counterparts=draft_correspondence(rig,mapping),plane_normal=normal.tolist(),plane_point=point.tolist(),label='Mirror '+identity)
            cases.append(dict(id=identity,source=str(source),source_contacts_sha256=sha256(source/'contacts.json'),recipe=recipe))
    protocol=dict(created_at=now(),cases=cases,implementation={name:sha256(implementation/name) for name in files},
        scope='Development study, known clips: left beckon, grapevine dance, jab/cross/retreat on three rigs. Fixed vertical plane through starting pelvis, normal from reference left-minus-right thigh. No naturalness, action recognition or contact quality approval.',quality_approved=False,
        numerical_limits=dict(matrix_or_position_error=1e-5,engine_error=1e-4),sampling='All keys and temporal midpoints, maximum skin-floor depth reported; not continuous collision certification')
    save(output/'protocol.json',protocol);save(output/'pipeline.json',dict(status='processing',stage='Mirror exports'))
    checks=[];manifest=[]
    try:
        for case in cases:
            source=Path(case['source']);recipe=case['recipe'];dest=output/'takes'/case['id']
            if sha256(source/'contacts.json')!=case['source_contacts_sha256']:raise ValueError('Contact source changed')
            write_clip(source/'character.glb',recipe,dest,source/'contacts.json')
            input_rig=RigAsset.load(source/'character.glb');out_rig=RigAsset.load(dest/'character.glb')
            a=AnimationSampler(input_rig.document,input_rig.binary,0);b=AnimationSampler(out_rig.document,out_rig.binary,0)
            root=recipe['root_node'];normal=np.array(recipe['plane_normal']);point=np.array(recipe['plane_point']);F=np.eye(3)-2*np.outer(normal,normal)
            sample_times=np.arange(2*recipe['frames']-1)/(2*30)
            original=np.array([a.sample(float(t)) for t in sample_times]);found=np.array([b.sample(float(t)) for t in sample_times])
            recovered=mirror(input_rig,found,root,recipe['counterparts'],normal,point)
            outside=list(set(range(len(input_rig.parents)))-set(descendants(input_rig.parents,root)))
            root_error=float(np.max(np.abs(found[:,root,:3,3]-(point+(original[:,root,:3,3]-point)@F))))
            rotation_error=0
            for dst,src in recipe['counterparts'].items():
                dst=int(dst)
                # Compare deltas in the common world frame rather than calling mirror to build expected rotations.
                input_delta=original[:,src,:3,:3]@input_rig.reference[src,:3,:3].T
                output_delta=found[:,dst,:3,:3]@input_rig.reference[dst,:3,:3].T
                rotation_error=max(rotation_error,float(np.max(np.abs(output_delta-F@input_delta@F))))
            original_local=localize(original,input_rig.parents);new_local=localize(found,input_rig.parents)
            protected=[n for n in descendants(input_rig.parents,root) if n!=root]
            length_error=float(np.max(np.abs(np.linalg.norm(original_local[:,protected,:3,3],axis=-1)-np.linalg.norm(new_local[:,protected,:3,3],axis=-1))))
            outside_error=float(np.abs(found[:,outside]-original[:,outside]).max()) if outside else 0.
            inverse_error=float(np.abs(recovered-original).max())
            input_floor=max(max(0.,-float(input_rig.vertices(w)[:,1].min())) for w in original)
            output_floor=max(max(0.,-float(out_rig.vertices(w)[:,1].min())) for w in found)
            result=dict(id=case['id'],frames=recipe['frames'],samples=len(sample_times),root_reflection_error_m=root_error,paired_world_rotation_delta_error=rotation_error,
                unchanged_reference_bone_length_error_m=length_error,outside_subtree_error=outside_error,exported_inverse_max_matrix_error=inverse_error,
                input_skin_floor_depth_m=input_floor,output_skin_floor_depth_m=output_floor,quality_approved=False)
            if max(root_error,rotation_error,length_error,outside_error,inverse_error)>1e-5:raise ValueError('Mirror numerical check failed: '+case['id'])
            checks.append(result);save(dest/'study-check.json',result)
            manifest.append(dict(id=case['id'],path=(dest/'character.glb').relative_to(output).as_posix(),sha256=sha256(dest/'character.glb'),frames=recipe['frames'],fps=30,sample_by_time=True))
            save(output/'progress.json',dict(completed=len(checks),planned=len(cases),checks=checks))
        save(output/'manifest.json',dict(cases=manifest))
        from run_godot_rig_import import run as engine
        engine(output,output/'engine')
        save(output/'summary.json',dict(created_at=now(),protocol_sha256=sha256(output/'protocol.json'),checks=checks,engine_verification_sha256=sha256(output/'engine/verification.json'),quality_approved=False))
        save(output/'pipeline.json',dict(status='complete',cases=len(checks),engine_actor_frames=sum(c['frames'] for c in checks),quality_approved=False))
    except Exception as error:
        save(output/'pipeline.json',dict(status='failed',error=str(error),completed=len(checks),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);run(p.parse_args().output)
