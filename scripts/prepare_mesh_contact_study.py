"""Freeze engineering contact fixtures before fitting; not human annotations."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_contact_authoring import source, empty_spec, validate_request
from rig_asset import RigAsset
from target_rig_contact import baseline


def weighted_region(rig, nodes):
    joints = [rig.joints.index(n) for n in nodes]
    weight = np.concatenate([np.zeros(len(p['positions'])) if p['joints'] is None else
        np.sum(np.where(np.isin(p['joints'], joints), p['weights'], 0), axis=1) for p in rig.primitives])
    indices = np.flatnonzero(weight >= .65)
    if not len(indices):
        raise ValueError('No sufficiently weighted vertices')
    return indices


def prepare(output):
    output = Path(output).resolve(); output.mkdir(exist_ok=False)
    manifest = dict(created_at=now(),scope='Engineering regression fixtures on previously seen seed-77 motion; not held-out or animator-annotated support. Frozen before fitting.',cases=[])
    for name, job in [('curved-sole-wave','rig-diversity-height-v1-11'),
                      ('upper-body-get-up','rig-diversity-height-v1-06')]:
        folder, result, request, report, glb = source(job,'transfer')
        rig = RigAsset.load(glb); world, _ = baseline(rig,report['frames'])
        vertices = np.array([rig.vertices(w) for w in world])
        spec = empty_spec(report); mapping = report['mapping']; selections = []
        if name == 'curved-sole-wave':
            points = rig.vertices(rig.reference)
            intervals = read(folder/'transfer/contacts.json')['intervals']
            for side in ('Left','Right'):
                ids = weighted_region(rig,[mapping[side+'Foot'],mapping[side+'ToeBase']])
                forward = rig.reference[mapping[side+'ToeBase'],:3,3]-rig.reference[mapping[side+'Foot'],:3,3]
                forward[1]=0; forward/=np.linalg.norm(forward)
                lateral=np.cross([0,1,0],forward)
                along=points[ids]@forward; across=points[ids]@lateral
                front=along>=np.quantile(along,.65); split=np.median(across[front])
                groups=[('heel',along<=np.quantile(along,.25),'Foot'),('fore-a',front & (across<=split),'ToeBase'),('fore-b',front & (across>split),'ToeBase')]
                for part,mask,role in groups:
                    region=ids[mask]; index=int(region[np.argmin(points[region,1])]); patch=side+'-'+part
                    spec['patches'][patch]=dict(vertices=[index])
                    selections.append(dict(patch=patch,vertex=index,reference_position_m=points[index].tolist(),rule='Lowest reference vertex in weighted foot/toe longitudinal/lateral partition; no flatness assumption'))
                    for interval in intervals:
                        if interval['joint']!=side+role:continue
                        a,b=interval['start_frame'],interval['end_frame_exclusive']
                        target=np.median(vertices[a:b,index],axis=0); target[1]=.0015
                        spec['contacts'].append(dict(patch=patch,start_frame=a,end_frame_exclusive=b,target_position_m=target.tolist()))
        else:
            # Diagnostic clearance target: not a claim that the head should bear weight.
            ids=weighted_region(rig,[mapping['Head']])
            f,i=np.unravel_index(np.argmin(vertices[:,ids,1]),(len(vertices),len(ids)))
            index=int(ids[i]); target=vertices[f,index].copy(); target[1]=.005
            spec['patches']['head-clearance']=dict(vertices=[index])
            spec['contacts'].append(dict(patch='head-clearance',start_frame=max(0,int(f)-3),end_frame_exclusive=min(len(vertices),int(f)+4),target_position_m=target.tolist()))
            for role in ('Spine2','Chest','Neck1','Head'):
                if role in mapping:spec['edit_joints'][role]=dict(node=mapping[role],limit_degrees=25)
            selections.append(dict(patch='head-clearance',vertex=index,frame=int(f),source_position_m=vertices[f,index].tolist(),rule='Lowest head-weighted vertex at worst head penetration; 7-frame fixed clearance target, not confirmed support'))
        spec['provenance']=manifest['scope']+' '+name+'; selections recorded separately; original source predictions are unconfirmed.'
        payload=dict(source_job=job,variant='transfer',spec=spec); validate_request(payload)
        save(output/(name+'.json'),payload);save(output/(name+'-selection.json'),selections)
        manifest['cases'].append(dict(id=name,source_job=job,request=name+'.json',request_sha256=sha256(output/(name+'.json')),selection=name+'-selection.json'))
    save(output/'request-manifest.json',manifest)
    print(manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    prepare(parser.parse_args().output)
