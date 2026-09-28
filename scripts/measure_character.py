"""Additional target-rig measurements, including interpolated mesh-ground clearance."""
import argparse
import copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from strep import read,save,sha256,now
from gltf_tools import read_glb,accessor,global_matrices,skin_vertices,hierarchy


def interpolated_matrices(document,binary,index,frame):
    nodes=copy.deepcopy(document['nodes'])
    animation=document['animations'][index]
    for channel in animation['channels']:
        sampler=animation['samplers'][channel['sampler']]
        values=accessor(document,binary,sampler['output'])
        a,b=int(np.floor(frame)),int(np.ceil(frame));alpha=frame-a
        path,node=channel['target']['path'],channel['target']['node']
        if a==b:
            value=values[a]
        elif path=='rotation':
            value=Slerp([0,1],Rotation.from_quat(values[[a,b]]))([alpha]).as_quat()[0]
        else:
            value=values[a]*(1-alpha)+values[b]*alpha
        nodes[node][path]=value.tolist()
    return global_matrices({**document,'nodes':nodes})


def main(folder):
    folder=Path(folder).resolve()
    report=read(folder/'report.json')
    doc,binary=read_glb(folder/'cesium-run-comparison.glb')
    skin=doc['skins'][0];joints=skin['joints'];parents=hierarchy(doc)
    primitive=doc['meshes'][0]['primitives'][0]
    joint_indices=accessor(doc,binary,primitive['attributes']['JOINTS_0']).astype(int)
    weights=accessor(doc,binary,primitive['attributes']['WEIGHTS_0'])
    contacts=np.array(read(folder/'contacts.json')['contacts'],bool)
    count=report['frames_per_cycle']*report['repeats']+1
    result={'checked_at':now(),'glb_sha256':sha256(folder/'cesium-run-comparison.glb'),
        'method':'CPU skinning of exported GLB, every keyframe and midpoint using linear TRS/quaternion slerp. Not a continuous-time collision proof.',
        'weight_sum_max_error':float(abs(weights.sum(1)-1).max()),'conditions':{}}
    for index,label in enumerate(('before','after')):
        matrices=np.array([interpolated_matrices(doc,binary,index,frame) for frame in range(count)])
        minimum=1e9
        for frame in np.arange(0,count-.5,.5):
            mesh=skin_vertices(doc,binary,interpolated_matrices(doc,binary,index,float(frame)))
            minimum=min(minimum,float(mesh[:,1].min()))
        all_vertices=np.array([skin_vertices(doc,binary,m) for m in matrices])
        lengths=np.array([np.linalg.norm(matrices[:,node,:3,3]-matrices[:,parents[node],:3,3],axis=1) for node in joints if node!=3])
        foot_height={}
        for side,nodes,channels in [('left',[10,11],[0,1,2]),('right',[6,7],[3,4,5])]:
            mask=(weights*np.isin(joint_indices,[joints.index(n) for n in nodes])).sum(1)>.5
            height=all_vertices[:,mask,1].min(1)
            stance=contacts[:,channels].any(1)
            foot_height[side]={'vertices_with_majority_foot_skin_weight':int(mask.sum()),
                'predicted_support_frames':int(stance.sum()),'min_m':float(height[stance].min()),
                'median_m':float(np.median(height[stance])),'max_m':float(height[stance].max())}
        positions=matrices[:,joints][:,:,:3,3]
        relative=positions-matrices[:,3,:3,3][:,None,:]
        seam_errors=[float(np.sqrt(np.mean(np.sum((2*relative[n-1]-relative[n-2]-relative[n])**2,axis=-1)))) for n in range(report['frames_per_cycle'],count,report['frames_per_cycle'])]
        travel=matrices[-1,3,:3,3]-matrices[0,3,:3,3]
        expected=np.array(report['cycle_displacement_target_m'])*report['repeats']
        travel_error=float(np.linalg.norm(travel-expected))
        if travel_error>1e-5 or np.ptp(lengths,axis=1).max()>1e-5:
            raise RuntimeError('Root travel or bone lengths changed in export')
        result['conditions'][label]={'sampled_mesh_min_y_m':minimum,'sampled_mesh_max_ground_penetration_m':max(0,-minimum),
            'support_foot_lowest_vertex_height':foot_height,'max_bone_length_variation_m':float(np.ptp(lengths,axis=1).max()),
            'root_travel_error_m':travel_error,'target_19_joint_loop_prediction_rms_m':seam_errors,
            'note':'19-joint seam diagnostic has different coverage from the 77-joint source gate. Floor clearance is not proof of appropriate support.'}
    save(folder/'quality.json',result)
    print(result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    main(parser.parse_args().folder)
