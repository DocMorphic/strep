"""Transfer every take, including flagged takes, to a separately measured character GLB."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from correct_stance import load_motion
from correct_loops import repeat_motion
from retarget_cesium import calibrate,transfer,MAPPING
from gltf_tools import read_glb,skin_vertices,append_accessor,write_glb,sample_animation


def repeated_with_terminal(data,displacement):
    repeated=repeat_motion(data,displacement,4)
    return {k:np.concatenate([v,(data[k][:1]+displacement*4) if k in ('posed_joints','root_positions') else data[k][:1]]) for k,v in repeated.items()}


def main(folder):
    from kimodo.skeleton import SOMASkeleton77
    folder=Path(folder).resolve();summary=read(folder/'summary.json');asset=ROOT/'assets/characters/cesium-man/CesiumMan.glb'
    original_hash=sha256(asset);document,binary=read_glb(asset);skeleton=SOMASkeleton77();calibration=calibrate(document,binary,skeleton)
    parents,base,bind,rest,offsets,scale=calibration
    all_reports=[]
    for trial in summary['trials']:
        destination=folder/'characters'/trial['id']
        if (destination/'report.json').exists():
            record=read(destination/'report.json')
            if sha256(destination/'motion.glb')!=record['glb_sha256'] or record['source_summary_sha256']!=sha256(folder/'summary.json'):raise RuntimeError('Character resume provenance differs')
            all_reports.append(record);continue
        destination.mkdir(parents=True,exist_ok=True)
        raw=load_motion(trial['source_path']);start=trial['source_start_frame'];length=trial['cycle_frames']
        crop={k:v[start:start+length].copy() for k,v in raw.items()}
        processed=load_motion(folder/'stance'/trial['profile']/f'seed-{trial["seed"]}/corrected.npz')
        motions={'raw_full':raw,'raw_cycle':repeated_with_terminal(crop,np.array(trial['raw_cycle_displacement_m'])),
            'processed_loop':repeated_with_terminal(processed,np.array(trial['processed_cycle_displacement_m']))}
        transfers={label:transfer(document,motion,skeleton,calibration) for label,motion in motions.items()}
        minima={label:min(float(skin_vertices(document,binary,matrix)[:,1].min()) for matrix in arrays[0]) for label,arrays in transfers.items()}
        lift=max(0,-min(minima.values()));root_lift=np.linalg.inv(base[parents[3],:3,:3])@[0,lift,0]
        output=copy.deepcopy(document);output['animations']=[];buffer=bytearray(binary)
        output['asset'].update(generator='strep profile pilot calibrated transfer',copyright='CesiumMan © 2017 Cesium, CC BY 4.0; modified animation by strep; logo terms retained.')
        for node,local in rest.items():
            target=output['nodes'][node];target.pop('matrix',None)
            target.update(translation=local[:3,3].tolist(),rotation=Rotation.from_matrix(local[:3,:3]).as_quat().tolist(),scale=[1,1,1])
        report={'id':trial['id'],'profile':trial['profile'],'seed':trial['seed'],'created_at':now(),
            'source_summary_sha256':sha256(folder/'summary.json'),'source_character_sha256':original_hash,
            'implementation_sha256':sha256(Path(__file__)),'retarget_implementation_sha256':sha256(ROOT/'scripts/retarget_cesium.py'),
            'scale':scale,'common_floor_lift_m':lift,'source_accepted':trial['accepted_source'],'conditions':{},
            'limitations':'Only ankle/toe-base contact proxies. Per-take common floor alignment does not solve target foot placement. No independent support, self-collision, or human approval.'}
        for label,(matrices,translations,rotations) in transfers.items():
            translations[3]+=root_lift;matrices[:,list(MAPPING),1,3]+=lift
            frames=len(matrices);time=append_accessor(output,buffer,np.arange(frames,dtype=np.float32)/30,'SCALAR')
            animation={'name':label,'channels':[],'samplers':[]}
            for node in MAPPING:
                for prop,values,kind in [('translation',translations[node],'VEC3'),('rotation',rotations[node],'VEC4')]:
                    index=append_accessor(output,buffer,values,kind);sampler=len(animation['samplers'])
                    animation['samplers'].append({'input':time,'output':index,'interpolation':'LINEAR'})
                    animation['channels'].append({'sampler':sampler,'target':{'node':node,'path':prop}})
            output['animations'].append(animation)
            feet=matrices[:,[10,11,6,7]][:,:,:3,3]
            velocity=np.linalg.norm(np.diff(feet[:,:,[0,2]],axis=0),axis=-1)*30
            contact=motions[label]['foot_contacts'][:,[0,1,3,4]];support=contact[:-1]&contact[1:];speeds=velocity[support]
            vertex_min=min(float(skin_vertices(document,binary,m)[:,1].min()) for m in matrices)
            root_travel=matrices[-1,3,:3,3]-matrices[0,3,:3,3]
            expected=(motions[label]['root_positions'][-1]-motions[label]['root_positions'][0])*scale
            travel_error=float(np.linalg.norm(root_travel-expected))
            if travel_error>1e-5:raise RuntimeError('Retarget root travel differs')
            report['conditions'][label]={'frames':frames,'duration_s':(frames-1)/30,'target_mean_speed_m_s':float(root_travel[2]*30/(frames-1)),
                'predicted_contact_speed_p95_m_s':float(np.percentile(speeds,95)) if len(speeds) else None,
                'keyframe_mesh_min_y_m':vertex_min,'root_travel_error_m':travel_error}
        output['extras']={'strep':{'study':summary['study']['id'],'id':trial['id'],'source_accepted':trial['accepted_source'],'scale':scale,
            'cycle_frames':length,'cycle_displacement_m':(np.array(trial['processed_cycle_displacement_m'])*scale).tolist(),
            'note':'Four cycles accumulate root displacement; playback resets only on explicit restart. Contact predictions are in sidecar.'}}
        path=destination/'motion.glb';write_glb(path,output,buffer)
        decoded,decoded_binary=read_glb(path)
        for index,(label,(expected,_,_)) in enumerate(transfers.items()):
            maximum=0.0
            for frame in range(len(expected)):
                actual=sample_animation(decoded,decoded_binary,index,frame)
                error=np.linalg.norm(skin_vertices(decoded,decoded_binary,actual)-skin_vertices(document,binary,expected[frame]),axis=-1).max()
                maximum=max(maximum,float(error))
            if maximum>1e-5:raise RuntimeError('GLB skin round-trip failed')
            report['conditions'][label]['roundtrip_max_vertex_error_m']=maximum
        report['glb_sha256']=sha256(path);save(destination/'report.json',report)
        save(destination/'contacts.json',{'fps':30,'labels':skeleton.foot_joint_names,'provenance':'Inherited predicted contacts, not support annotations.',
            'animations':{label:motion['foot_contacts'].astype(int).tolist() for label,motion in motions.items()}})
        all_reports.append(report);save(folder/'character-summary.json',all_reports)
        print(f'Exported and checked {trial["id"]}; source accepted={trial["accepted_source"]}',flush=True)
    for name in ('LICENSE.md','Cesium-logo-terms.txt','UPSTREAM-README.md'):
        shutil.copy2(asset.parent/name,folder/name)
    if sha256(asset)!=original_hash:raise RuntimeError('Original character modified')
    save(folder/'character-summary.json',all_reports)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);main(p.parse_args().folder)
