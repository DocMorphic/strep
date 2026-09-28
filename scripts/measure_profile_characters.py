"""Measure style and support after rig transfer, including midpoint floor samples."""
import argparse
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
from strep import read,save,sha256,now
from gltf_tools import read_glb,accessor,skin_vertices,sample_animation
from measure_character import interpolated_matrices


def rig_descriptors(matrices):
    p=matrices[:,:,:3,3];root=p[:,3];torso=p[:,20]-root
    arm=[];periods=[]
    for shoulder,hand,foot in [(17,19,10),(14,16,6)]:
        v=p[:,hand]-p[:,shoulder];angles=np.unwrap(np.arctan2(v[:,2],-v[:,1]))*180/np.pi
        arm.append(np.percentile(angles,95)-np.percentile(angles,5))
        peaks,_=find_peaks(p[:,foot,1],distance=9,prominence=.019)
        if len(peaks)>1:periods.extend((np.diff(peaks)/30).tolist())
    return {'torso_forward_lean_median_degrees':float(np.median(np.degrees(np.arctan2(torso[:,2],torso[:,1])))),
        'arm_swing_range_mean_degrees':float(np.mean(arm)),
        'pelvis_vertical_p95_p5_m':float(np.percentile(root[:,1],95)-np.percentile(root[:,1],5)),
        'cadence_steps_min':float(120/np.median(periods)) if periods else None}


def main(folder):
    folder=Path(folder);summary=read(folder/'summary.json');output={'checked_at':now(),'scope':'Exported GLB sampled at keys and midpoints; no continuous collision or independent support claim.','trials':[]}
    for trial in summary['trials']:
        target=folder/'characters'/trial['id'];document,binary=read_glb(target/'motion.glb');report=read(target/'report.json')
        contact=read(target/'contacts.json');conditions={}
        for index,label in enumerate(('raw_full','raw_cycle','processed_loop')):
            count=report['conditions'][label]['frames']
            matrices=np.array([sample_animation(document,binary,index,frame) for frame in range(count)])
            conditions[label]={'descriptors':rig_descriptors(matrices)}
            if label!='processed_loop':continue
            primitive=document['meshes'][0]['primitives'][0];skin=document['skins'][0]
            indices=accessor(document,binary,primitive['attributes']['JOINTS_0']).astype(int)
            weights=accessor(document,binary,primitive['attributes']['WEIGHTS_0'])
            masks=[(weights*np.isin(indices,[skin['joints'].index(n) for n in nodes])).sum(1)>.5 for nodes in ([10,11],[6,7])]
            min_y=1e9;heights=[[],[]]
            for frame in range(count):
                vertices=skin_vertices(document,binary,matrices[frame]);min_y=min(min_y,float(vertices[:,1].min()))
                for side,mask in enumerate(masks):heights[side].append(float(vertices[mask,1].min()))
                if frame<count-1:
                    mid=interpolated_matrices(document,binary,index,frame+.5)
                    min_y=min(min_y,float(skin_vertices(document,binary,mid)[:,1].min()))
            labels=np.array(contact['animations'][label],bool);support=[]
            for side,height in enumerate(heights):
                flags=labels[:,side*3:side*3+3].any(1);values=np.array(height)[flags]
                support.append({'side':['left','right'][side],'count':len(values),'median_m':float(np.median(values)) if len(values) else None,'max_m':float(values.max()) if len(values) else None})
            conditions[label].update(sampled_floor_penetration_m=max(0,-min_y),support_lowest_vertex_heights=support)
        record={'id':trial['id'],'glb_sha256':sha256(target/'motion.glb'),'conditions':conditions};save(target/'quality.json',record)
        output['trials'].append(record);save(folder/'character-quality.json',output)
        print('Measured '+trial['id'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);main(p.parse_args().folder)
