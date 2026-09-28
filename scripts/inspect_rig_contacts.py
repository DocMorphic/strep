"""Inspect authored contacts on an exact exported mesh, without editing motion."""
import argparse
import copy
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now
from rig_asset import RigAsset
from gltf_tools import sample_animation
from target_rig_contact import validate


def inspect(glb,spec,mapping=None):
    glb=Path(glb);digest=sha256(glb)
    if digest!=spec['glb_sha256']:raise ValueError('Inspection draft belongs to a different mesh clip')
    rig=RigAsset.load(glb);validate(spec,rig)
    tracks={name:[] for name in spec['patches']};floor=[];worst=None
    for frame in range(spec['frames']):
        points=rig.vertices(sample_animation(rig.document,rig.binary,0,frame))
        vertex=int(np.argmin(points[:,1]));depth=max(0.,-float(points[vertex,1]));floor.append(depth)
        if worst is None or depth>worst['depth_m']:
            worst=dict(frame=frame,vertex=vertex,depth_m=depth,position_m=points[vertex].tolist())
        for name,patch in spec['patches'].items():tracks[name].append(points[patch['vertices']].mean(axis=0))
    roles={n:role for role,n in (mapping or {}).items()};offset=0;influences={}
    for primitive in rig.primitives:
        if offset<=worst['vertex']<offset+len(primitive['positions']):
            if primitive['joints'] is not None:
                index=worst['vertex']-offset
                for j,w in zip(primitive['joints'][index],primitive['weights'][index]):
                    node=rig.joints[j];influences[node]=influences.get(node,0.)+float(w)
            break
        offset+=len(primitive['positions'])
    worst['skin_influences']=[dict(node=n,label=roles.get(n,rig.document['nodes'][n].get('name',str(n))),weight=w)
        for n,w in sorted(influences.items(),key=lambda item:-item[1]) if w>1e-6]
    contacts=[];threshold=spec['screen']['contact_error_m']
    for index,contact in enumerate(spec['contacts']):
        a,b=contact['start_frame'],contact['end_frame_exclusive'];track=np.asarray(tracks[contact['patch']])[a:b]
        delta=track-contact['target_position_m'];error=np.linalg.norm(delta,axis=1);peak=int(np.argmax(error))
        speed=np.linalg.norm(np.diff(track,axis=0),axis=1)*spec['fps']
        contacts.append(dict(index=index,**contact,frames=b-a,error_max_m=float(error[peak]),error_p95_m=float(np.percentile(error,95)),
            failed_frames=int(np.sum(error>threshold)),worst_frame=a+peak,worst_position_m=track[peak].tolist(),
            worst_error_vector_m=delta[peak].tolist(),horizontal_error_max_m=float(np.linalg.norm(delta[:,[0,2]],axis=1).max()),
            vertical_error_max_m=float(np.abs(delta[:,1]).max()),speed_max_m_s=float(speed.max()) if len(speed) else None))
    return dict(schema='strep-mesh-contact-inspection-v1',created_at=now(),glb_sha256=digest,frames=spec['frames'],fps=spec['fps'],
        screen=copy.deepcopy(spec['screen']),contacts=contacts,worst_floor=worst,floor_frames_failed=int(np.sum(np.asarray(floor)>spec['screen']['floor_depth_m'])),
        failed_intervals=sum(c['failed_frames']>0 for c in contacts),implementation_sha256=sha256(__file__),
        scope='Sampled mesh vertices, authored centroid targets and intervals. Skin influences identify geometry, not anatomical support. Speed is within each interval; no continuous collision, force balance or semantic approval.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('glb',type=Path);parser.add_argument('spec',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();save(args.output,inspect(args.glb,read(args.spec)))
