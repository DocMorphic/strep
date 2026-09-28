"""Calibrated SOMA77-to-CesiumMan rotation transfer and verified skinned GLB export."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from correct_stance import load_motion, swing
from correct_loops import repeat_motion
from gltf_tools import read_glb, accessor, hierarchy, global_matrices, skin_vertices, append_accessor, write_glb, sample_animation


MAPPING = {3:'Hips', 12:'Spine2', 13:'Chest', 20:'Neck1', 21:'Head',
           17:'LeftArm',18:'LeftForeArm',19:'LeftHand',14:'RightArm',15:'RightForeArm',16:'RightHand',
           8:'LeftLeg',9:'LeftShin',10:'LeftFoot',11:'LeftToeBase',4:'RightLeg',5:'RightShin',6:'RightFoot',7:'RightToeBase'}
PRIMARY_CHILD = {3:12,12:13,13:20,20:21,17:18,18:19,14:15,15:16,8:9,9:10,10:11,4:5,5:6,6:7}


def calibrate(document, binary, skeleton):
    parents = hierarchy(document)
    matrices = global_matrices(document)
    skin = document['skins'][0]
    inverse = accessor(document, binary, skin['inverseBindMatrices'])
    bind = matrices.copy()
    # Inverse bind matrices are in mesh coordinates, not scene coordinates.
    bind[skin['joints']] = matrices[2] @ np.linalg.inv(inverse)
    rest_local = {node: np.linalg.inv(bind[parents[node]]) @ bind[node] for node in skin['joints']}
    names = skeleton.bone_order_names
    if 'LeftShin' not in names:
        raise ValueError('SOMA joint mapping changed')
    neutral = skeleton.neutral_joints.numpy()
    calibration = {}
    for node, name in MAPPING.items():
        if node in PRIMARY_CHILD:
            a, b = node, PRIMARY_CHILD[node]
        else:
            a, b = parents[node], node
        target_direction = bind[b, :3, 3] - bind[a, :3, 3]
        source_direction = neutral[names.index(MAPPING[b])] - neutral[names.index(MAPPING[a])]
        calibration[node] = swing(target_direction, source_direction) @ Rotation.from_matrix(bind[node, :3, :3]).as_matrix()
    # Pelvis orientation uses bilateral hip and spine landmarks, not a single twist-ambiguous axis.
    source_landmarks = np.array([neutral[names.index(MAPPING[i])] - neutral[0] for i in (8,4,12)])
    target_landmarks = np.array([bind[i, :3, 3] - bind[3, :3, 3] for i in (8,4,12)])
    source_landmarks /= np.linalg.norm(source_landmarks, axis=1)[:, None]
    target_landmarks /= np.linalg.norm(target_landmarks, axis=1)[:, None]
    alignment, _ = Rotation.align_vectors(source_landmarks, target_landmarks)
    calibration[3] = alignment.as_matrix() @ Rotation.from_matrix(bind[3, :3, :3]).as_matrix()
    target_lengths, source_lengths = [], []
    for chain in ((8,9,10),(4,5,6)):
        target_lengths.append(sum(np.linalg.norm(bind[b,:3,3]-bind[a,:3,3]) for a,b in zip(chain,chain[1:])))
        source_lengths.append(sum(np.linalg.norm(neutral[names.index(MAPPING[b])]-neutral[names.index(MAPPING[a])]) for a,b in zip(chain,chain[1:])))
    scale = float(np.mean(np.array(target_lengths) / source_lengths))
    return parents, matrices, bind, rest_local, calibration, scale


def transfer(document, motion, skeleton, calibration_data):
    parents, base, bind, rest_local, calibration, scale = calibration_data
    names = skeleton.bone_order_names
    output, translations, rotations = [], {n:[] for n in MAPPING}, {n:[] for n in MAPPING}
    for frame in range(len(motion['root_positions'])):
        global_result, local_result = {}, {}
        def visit(node):
            if node in global_result:
                return global_result[node]
            parent = parents[node]
            parent_matrix = np.eye(4) if parent < 0 else visit(parent)
            if node in MAPPING:
                desired_rotation = motion['global_rot_mats'][frame, names.index(MAPPING[node])] @ calibration[node]
                local = np.eye(4)
                local[:3,:3] = Rotation.from_matrix(parent_matrix[:3,:3]).as_matrix().T @ desired_rotation
                local[:3,3] = rest_local[node][:3,3]
                if node == 3:
                    local[:3,3] = (np.linalg.inv(parent_matrix) @ np.r_[motion['root_positions'][frame] * scale, 1])[:3]
                local_result[node] = local
            else:
                from gltf_tools import local_matrix
                local = local_matrix(document['nodes'][node])
            global_result[node] = parent_matrix @ local
            return global_result[node]
        output.append(np.array([visit(node) for node in range(len(document['nodes']))]))
        for node in MAPPING:
            translations[node].append(local_result[node][:3,3])
            rotations[node].append(Rotation.from_matrix(local_result[node][:3,:3]).as_quat())
    rotations = {node: np.array(values) for node, values in rotations.items()}
    for values in rotations.values():
        for frame in range(1,len(values)):
            if values[frame] @ values[frame-1] < 0:
                values[frame] *= -1
    return np.array(output), {n:np.array(v) for n,v in translations.items()}, rotations


def main(study, output):
    from kimodo.skeleton import SOMASkeleton77
    study, folder = Path(study).resolve(), Path(output).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    summary = read(study/'summary.json')
    passing = [x for x in summary['trials'] if x['accepted']]
    if not passing:
        raise RuntimeError('No passing source motion to retarget')
    winner = min(passing, key=lambda x:x['after']['foot_horizontal_speed_predicted_contact_m_s']['p95'])
    seed = winner['seed']
    original_path = ROOT/'assets/characters/cesium-man/CesiumMan.glb'
    source_hash = sha256(original_path)
    document, binary = read_glb(original_path)
    skeleton = SOMASkeleton77()
    calibration_data = calibrate(document,binary,skeleton)
    parents, base, bind, rest_local, calibration, scale = calibration_data
    output_document = copy.deepcopy(document)
    output_document['animations'] = []
    output_document.setdefault('asset',{}).update(generator='strep calibrated transfer v1',copyright='CesiumMan © 2017 Cesium, CC BY 4.0; modified animation by strep. Logo terms retained.')
    for node, local in rest_local.items():
        target = output_document['nodes'][node]
        target.pop('matrix',None)
        target.update(translation=local[:3,3].tolist(),rotation=Rotation.from_matrix(local[:3,:3]).as_quat().tolist(),scale=[1,1,1])
    output_binary = bytearray(binary)
    displacement = np.array(winner['cycle_displacement_m'])
    motions, transfers = {}, {}
    for label,path in [('before',Path(winner['source'])),('after',study/f'seed-{seed}/corrected.npz')]:
        motion = load_motion(path)
        repeated = repeat_motion(motion,displacement,4)
        repeated = {key:np.concatenate([value, (motion[key][:1] + displacement*4) if key in ('root_positions','posed_joints') else motion[key][:1]]) for key,value in repeated.items()}
        motions[label] = repeated
        transfers[label] = transfer(document,repeated,skeleton,calibration_data)
    # Same constant mesh-ground offset for both conditions; report its magnitude.
    raw_min = {label:min(float(skin_vertices(document,binary,matrix)[:,1].min()) for matrix in values[0]) for label,values in transfers.items()}
    ground_lift = max(0,-min(raw_min.values()))
    parent_rotation = base[parents[3],:3,:3]
    root_local_lift = np.linalg.inv(parent_rotation) @ [0,ground_lift,0]
    report = {'created_at':now(),'seed':seed,'source_character':str(original_path),'character_sha256':source_hash,
              'implementation_sha256':sha256(Path(__file__)),'gltf_tools_sha256':sha256(ROOT/'scripts/gltf_tools.py'),
              'stance_summary_sha256':sha256(study/'summary.json'),'scale_from_mean_leg_length_ratio':scale,
              'mapping':{str(n):{'target':document['nodes'][n]['name'],'source':name} for n,name in MAPPING.items()},
              'cycle_displacement_target_m':(displacement*scale).tolist(),'common_mesh_ground_lift_m':ground_lift,
              'mesh_min_y_before_common_lift_m':raw_min,'frames_per_cycle':winner['cycle_frames'],'repeats':4,'fps':30,
              'conditions':{},'limitations':['Proportion-dependent rotation transfer; no target-rig foot IK.',
                'Only ankle and toe-base contact proxies transfer; toe-end and fingers absent.',
                'Vertex-floor distance is not mesh self-collision or independent support annotation.',
                'No animator approval or game-engine import.'],
              'specification':'https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html'}
    previews = {}
    for label,(matrices,translations,rotations) in transfers.items():
        translations[3] += root_local_lift
        matrices[:,list(MAPPING),1,3] += ground_lift
        frames = len(matrices)
        time_accessor = append_accessor(output_document,output_binary,np.arange(frames,dtype=np.float32)/30,'SCALAR')
        animation = {'name':f'run_seed_{seed}_{label}_four_cycles','channels':[],'samplers':[]}
        for node in MAPPING:
            for path,array,kind in [('translation',translations[node],'VEC3'),('rotation',rotations[node],'VEC4')]:
                index = append_accessor(output_document,output_binary,array,kind)
                sampler = len(animation['samplers'])
                animation['samplers'].append({'input':time_accessor,'output':index,'interpolation':'LINEAR'})
                animation['channels'].append({'sampler':sampler,'target':{'node':node,'path':path}})
        output_document['animations'].append(animation)
        vertices = np.array([skin_vertices(document,binary,matrix) for matrix in matrices])
        foot_nodes, channels = [10,11,6,7],[0,1,3,4]
        foot_positions = matrices[:,foot_nodes][:,:,:3,3]
        speed = np.linalg.norm(np.diff(foot_positions[:,:,[0,2]],axis=0),axis=-1)*30
        contact = motions[label]['foot_contacts'][:,channels]
        stance = contact[:-1]&contact[1:]
        values = speed[stance]
        np.savez(folder/f'{label}-validation.npz',global_matrices=matrices,skinned_vertices=vertices)
        report['conditions'][label] = {'mesh_min_y_m':float(vertices[:,:,1].min()),
            'predicted_contact_ankle_toebase_speed_p95_m_s':float(np.percentile(values,95)),
            'source_npz_sha256':sha256(Path(winner['source']) if label=='before' else study/f'seed-{seed}/corrected.npz'),
            'root_first_to_terminal_m':(matrices[-1,3,:3,3]-matrices[0,3,:3,3]).tolist(),
            'frames_including_terminal':frames}
        previews[label] = matrices
    output_document['extras']={'strep':{'seed':seed,'fps':30,'cycle_frames':winner['cycle_frames'],
        'cycles':4,'cycle_displacement_m':(displacement*scale).tolist(),'source_character_sha256':source_hash,
        'note':'Four accumulated cycles plus terminal sample. Stop at end; replay resets world position.',
        'contacts':'See contacts.json; inherited predictions, not independently annotated.'}}
    glb_path = folder/'cesium-run-comparison.glb'
    write_glb(glb_path,output_document,output_binary)
    exported,exported_binary = read_glb(glb_path)
    for index,label in enumerate(('before','after')):
        max_joint_error,max_vertex_error = 0.0,0.0
        for frame in range(len(previews[label])):
            actual = sample_animation(exported,exported_binary,index,frame)
            expected = previews[label][frame]
            max_joint_error=max(max_joint_error,float(np.abs(actual-expected).max()))
            vertex_error=np.linalg.norm(skin_vertices(exported,exported_binary,actual)-skin_vertices(document,binary,expected),axis=-1).max()
            max_vertex_error=max(max_vertex_error,float(vertex_error))
        if max_joint_error>1e-5 or max_vertex_error>1e-5:
            raise RuntimeError('GLB skin round-trip verification failed')
        report['conditions'][label].update(roundtrip_max_matrix_error=max_joint_error,roundtrip_max_vertex_error_m=max_vertex_error)
    report['glb_sha256']=sha256(glb_path)
    if source_hash!=sha256(original_path):
        raise RuntimeError('Source character modified')
    save(folder/'report.json',report)
    save(folder/'contacts.json',{'provenance':'Inherited model predictions unchanged by correction; source SOMA77 channels.',
         'fps':30,'labels':skeleton.foot_joint_names,'contacts':motions['after']['foot_contacts'].astype(int).tolist()})
    for name in ('LICENSE.md','Cesium-logo-terms.txt','UPSTREAM-README.md'):
        import shutil
        shutil.copy2(original_path.parent/name,folder/name)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    main(args.study,args.output)
