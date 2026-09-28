"""Export finite source clips without repeating or applying running corrections."""
import argparse
import shutil
import zipfile
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from build_soma_preview import make_preview,ASSET
from gltf_tools import write_glb,read_glb,accessor,sample_animation
from inspect_motion import validate_motion,metrics
from pace_controls import contact_intervals


def sequence_diagnostics(motion,schedule):
    root=motion['root_positions'];velocity=np.diff(root,axis=0)*30
    joint_steps=np.sqrt(np.mean(np.sum(np.diff(motion['posed_joints'],axis=0)**2,axis=-1),axis=1))
    joins=[]
    for segment in schedule[1:]:
        boundary=segment['start_frame'];indices=range(max(1,boundary-5),min(len(root)-1,boundary+2))
        joins.append({'requested_boundary_s':boundary/30,'requested_start_frame':boundary,
            'blend_frames':segment['blend_frames'],
            'samples':[{'arrival_frame':i,'joint_step_rms_m':float(joint_steps[i-1]),
                        'root_velocity_change_m_s':float(np.linalg.norm(velocity[i]-velocity[i-1]))} for i in indices]})
    # All values are diagnostics. A low join score cannot confirm a roll or standing finish.
    up=motion['global_rot_mats'][-15:,0,:,1]
    return {'joins':joins,'whole_clip_joint_step_p95_m':float(np.percentile(joint_steps,95)),
        'end_pelvis_height_m':float(np.mean(root[-15:,1])),
        'end_root_speed_m_s':float(np.mean(np.linalg.norm(velocity[-15:],axis=1))),
        'end_pelvis_up_angle_degrees':float(np.mean(np.degrees(np.arccos(np.clip(up[:,1],-1,1))))),
        'scope':'Requested boundaries with upstream five-frame blends. End-pelvis proxies are not standing/action correctness tests.'}


def main(folder):
    folder=Path(folder);batch=read(folder/'request.json');skin=dict(np.load(ASSET,allow_pickle=False));trials=[]
    license=ROOT/'vendor/kimodo/LICENSE';shutil.copyfile(license,folder/'SOMA-preview-LICENSE.txt')
    for request in batch['requests']:
        for seed in request['seeds']:
            records=sorted((folder/'raw'/request['id']/f'seed-{seed}').glob('attempt-*/record.json'))
            successful=[p for p in records if read(p)['status']=='generated']
            if not successful:raise ValueError('No generated source for '+request['id'])
            record_path=successful[-1];record=read(record_path);source=Path(record['npz'])
            if sha256(source)!=record['npz_sha256']:raise ValueError('Source changed')
            motion=dict(np.load(source,allow_pickle=False));names,_,feet=validate_motion(motion,30)
            id=f"{request['id']}-seed-{seed}";dest=folder/'takes'/id;dest.mkdir(parents=True,exist_ok=True)
            doc,binary,positions,rotations=make_preview(skin,motion,np.zeros(3),repeat=False)
            write_glb(dest/'soma.glb',doc,binary);decoded,payload=read_glb(dest/'soma.glb')
            max_error=0.;max_rotation_error=0.
            for f in range(len(positions)):
                matrices=sample_animation(decoded,payload,0,f)[1:78]
                max_error=max(max_error,float(np.linalg.norm(matrices[:,:3,3]-positions[f],axis=-1).max()))
                max_rotation_error=max(max_rotation_error,float(np.abs(matrices[:,:3,:3]-rotations[f]).max()))
            if max_error>1e-5 or max_rotation_error>1e-5:raise ValueError('SOMA export pose mismatch')
            for filename in ['motion.npz','motion.bvh']:shutil.copyfile(source.parent/filename,dest/filename)
            shutil.copyfile(record_path,dest/'generation-record.json')
            times=accessor(decoded,payload,decoded['animations'][0]['samplers'][0]['input'])
            q=Rotation.from_matrix(motion['global_rot_mats'][:,0]).as_quat()
            for i in range(1,len(q)):
                if np.dot(q[i-1],q[i])<0:q[i]*=-1
            save(dest/'root-motion.json',{'space':'SOMA Hips world transform, meters, Y up, +Z forward; not engine-specific root extraction.',
                'times_s':times.tolist(),'positions_m':motion['root_positions'].tolist(),'rotations_xyzw':q.tolist()})
            save(dest/'contacts.json',{'provenance':'Predicted foot contacts, not gameplay or confirmed contact events',
                'intervals':contact_intervals(motion['foot_contacts']>=.5,times,feet)})
            save(dest/'timeline.json',{'fps':30,'frame_count':len(times),'last_key_time_s':float(times[-1]),
                'sample_coverage_s':len(times)/30,'segments':record['timeline'],
                'scope':'Segment boundaries are conditioning requests, not detected action/event labels.'})
            measured=metrics(motion,names,feet,30);flags=[]
            if measured['max_joint_ground_penetration_m']>.01:flags.append('joint_ground_penetration_above_1cm')
            slide=measured['foot_horizontal_speed_predicted_contact_m_s']
            if slide and slide['p95']>.15:flags.append('predicted_contact_foot_speed_above_15cm_s')
            if not slide:flags.append('no_predicted_support_samples')
            if request.get('scene_requirements'):flags.append('scene_requirements_unsolved')
            constraint_audit=None
            if record.get('constraints'):
                from audit_generation_guides import audit
                constraint_audit=audit(motion,record['constraints'])
                save(dest/'constraint-audit.json',constraint_audit)
                if not constraint_audit['numerical_screen_passed']:flags.append('generation_constraint_screen_failed')
            trial={'id':id,'request_id':request['id'],'label':request['label'],'seed':seed,'request':request,
                'source_sha256':record['npz_sha256'],'generation_time_s':record['generation_time_s'],
                'frames':len(times),'duration_s':float(times[-1]),'metrics':measured,'sequence':sequence_diagnostics(motion,record['timeline']),
                'flags':flags,'review_status':'Unreviewed — action correctness and realism not established',
                'joint_roundtrip_max_error_m':max_error,'rotation_roundtrip_max_error':max_rotation_error,
                'processing':'Raw checkpoint output with upstream sequence blending; no running-specific correction',
                'human_approved':False,'engine_import':None}
            if constraint_audit is not None:trial['generation_constraints']=constraint_audit
            if record.get('motion_brief') is not None:
                trial['motion_brief']=record['motion_brief']
                flags.append('profile_response_unreviewed')
                save(dest/'motion-brief.json',record['motion_brief'])
            save(dest/'evidence.json',trial);save(dest/'request.json',request)
            files=['soma.glb','motion.npz','motion.bvh','root-motion.json','contacts.json','timeline.json','generation-record.json','evidence.json','request.json']
            if constraint_audit is not None:files.append('constraint-audit.json')
            if record.get('motion_brief') is not None:files.append('motion-brief.json')
            with zipfile.ZipFile(dest/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as z:
                for file in files:z.write(dest/file,file)
                z.write(license,'LICENSE.txt')
            trial['hashes']={file:sha256(dest/file) for file in files+['animation-pack.zip']}
            trials.append(trial)
    summary={'id':folder.name,'created_at':now(),'trials':trials,'request_count':len(batch['requests']),
        'scope':'An open-vocabulary input pipeline, not evidence of universal action coverage. Single humanoid SOMA; scene/partner contacts unsolved.',
        'exporter_sha256':sha256(Path(__file__)),'mesh_sha256':sha256(ASSET)}
    save(folder/'summary.json',summary)
    print(f'Exported {len(trials)} finite clips; verified every pose against raw motion.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);main(p.parse_args().folder)
