"""Independent dense exported-skin comparison for an object-contact fit."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from floor_contact import Surface
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from scene_constraints import pose,sample_object,transform_motion
from object_geometry import scene_geometry
from release_geometry import floor_gaps


def contact_mask(frames,contact):
    # Scene contact-window end events occur at end_frame + 1.
    return (frames>=contact['start_frame']) & (frames<contact['end_frame']+1)


def sample_scene(scene,base,skin,substeps=4):
    count=scene['frame_count'];frames=np.arange((count-1)*substeps+1)/substeps
    surface=Surface(skin);objects={};actors={}
    for name,obj in scene['objects'].items():
        p,r=sample_object(obj,count)
        objects[name]=(np.stack([np.interp(frames,np.arange(count),p[:,i]) for i in range(3)],1),
            Slerp(np.arange(count),Rotation.from_matrix(r))(frames).as_matrix(),scene_geometry(obj))
    for name,entry in scene['actors'].items():
        path=base/entry['preview_glb'];doc,binary=read_glb(path);sampler=AnimationSampler(doc,binary,0)
        joints=doc['skins'][0]['joints']
        if [doc['nodes'][i]['name'] for i in joints]!=surface.names:raise ValueError('Exported bone order mismatch')
        motion=dict(np.load(ROOT/entry['motion'],allow_pickle=False))
        if sha256(ROOT/entry['motion'])!=entry['source_sha256']:raise ValueError('Motion changed')
        expected=transform_motion(motion,entry['transform']);origin,placement=pose(entry['transform'])
        contacts=[c for c in scene['contacts'] if c['actor']==name]
        if any(c['target']['space']!='object' for c in contacts):raise ValueError('This audit requires object contact targets')
        faces={c['id']:skin['faces'][np.any(skin['faces']==c['effector']['surface_vertex'],axis=1)] for c in contacts}
        points={c['id']:[] for c in contacts};normals={c['id']:[] for c in contacts}
        floor=[];depths={obj:[] for obj in objects};positions=[];key_error=0.
        for sample,frame in enumerate(frames):
            matrices=sampler.sample(float(np.float32(frame/30)))[joints]
            r=placement@matrices[:,:3,:3];p=matrices[:,:3,3]@placement.T+origin
            if frame.is_integer():
                key_error=max(key_error,float(abs(p-expected['positions'][int(frame)]).max()),float(abs(r-expected['rotations'][int(frame)]).max()))
            vertices=surface.vertices(r,p);floor.append(max(0.,float(-vertices[:,1].min())));positions.append(p)
            for obj,(op,orr,geometry) in objects.items():depths[obj].append(float(geometry.penetration_depth(vertices,op[sample],orr[sample]).max()))
            for c in contacts:
                cid=c['id'];points[cid].append(vertices[c['effector']['surface_vertex']])
                triangles=vertices[faces[cid]];n=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]).sum(0)
                if np.linalg.norm(n)<1e-12:raise ValueError('Degenerate palm surface normal')
                normals[cid].append(n/np.linalg.norm(n))
        if key_error>1e-5:raise ValueError('Dense audit export keys differ from source motion')
        rows=[]
        for c in contacts:
            cid=c['id'];op,orr,geometry=objects[c['target']['object']];local=np.asarray(c['target']['point_m'])
            targets=op+np.einsum('fij,j->fi',orr,local);actual=np.array(points[cid]);errors=np.linalg.norm(actual-targets,axis=1)
            if c.get('normal_target'):raise ValueError('Explicit normal overrides require a separate audit')
            desired=np.einsum('fij,j->fi',orr,-geometry.local_surface_normal(local))
            angles=np.rad2deg(np.arccos(np.clip(np.sum(np.array(normals[cid])*desired,axis=1),-1,1)))
            active=contact_mask(frames,c);indices=np.flatnonzero(active)
            relative_speed=np.linalg.norm(np.diff(actual-targets,axis=0),axis=1)*30*substeps
            speed=np.linalg.norm(np.diff(actual,axis=0),axis=1)*30*substeps
            worst=indices[np.argmax(errors[active])];boundary={}
            for label,b in [('entry',c['start_frame']),('release',c['end_frame']+1)]:
                near=(frames[1:]>=b-1)&(frames[:-1]<=b+1)
                boundary[label]=dict(peak_palm_speed_m_s=float(speed[near].max()),peak_relative_speed_m_s=float(relative_speed[near].max()))
            rows.append(dict(id=cid,samples=int(active.sum()),maximum_error_m=float(errors[active].max()),worst_frame=float(frames[worst]),
                samples_within_30mm=int(np.sum(errors[active]<=.03)),samples_within_5mm=int(np.sum(errors[active]<=.005)),
                maximum_normal_error_degrees=float(angles[active].max()),samples_within_15degrees=int(np.sum(angles[active]<=15)),
                maximum_relative_speed_m_s=float(relative_speed[active[:-1]&active[1:]].max()),boundary=boundary,
                point_error_m=errors.tolist(),normal_error_degrees=angles.tolist()))
        position=np.array(positions);velocity=np.diff(position,axis=0)*30*substeps
        actors[name]=dict(glb_sha256=sha256(path),motion_sha256=sha256(ROOT/entry['motion']),key_matrix_error=key_error,
            maximum_floor_depth_m=max(floor),worst_floor_frame=float(frames[np.argmax(floor)]),samples_over_10mm_floor=int(np.sum(np.array(floor)>.01)),floor_depth_m=floor,
            objects={obj:dict(maximum_skin_vertex_depth_m=max(d),worst_frame=float(frames[np.argmax(d)]),samples_over_10mm=int(np.sum(np.array(d)>.01)),depth_m=d) for obj,d in depths.items()},
            contacts=rows,maximum_joint_speed_m_s=float(np.linalg.norm(velocity,axis=-1).max()),
            maximum_joint_acceleration_m_s2=float(np.linalg.norm(np.diff(velocity,axis=0)*30*substeps,axis=-1).max()))
    object_floor={}
    for name,(p,r,geometry) in objects.items():
        depths=np.maximum(0.,-floor_gaps(geometry,p,r))
        object_floor[name]=dict(maximum_depth_m=float(depths.max()),worst_frame=float(frames[np.argmax(depths)]),samples_over_10mm=int(np.sum(depths>.01)))
    return dict(frames=frames.tolist(),actors=actors,authored_object_floor=object_floor)


def run(study,output):
    study=Path(study).resolve();output=Path(output).resolve()
    if read(study/'pipeline.json')['status']!='complete':raise ValueError('Study is not complete')
    output.mkdir(parents=True,exist_ok=False);fit=study/'fit';summary=read(fit/'summary.json')
    if len(summary['trials'])!=1:raise ValueError('Single development scene expected')
    protocol=read(study/'protocol.json')
    for name,digest in protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Frozen input mismatch')
    scene_id=summary['trials'][0]['id'];scenes={variant:read(fit/scene_id/(variant+'.json'))['scene'] for variant in ['source','candidate']}
    for field in ['objects','contacts','fps','frame_count']:
        if scenes['source'][field]!=scenes['candidate'][field]:raise ValueError('Authored scene changed: '+field)
    if any(c.get('tolerance_m',.03)!=.03 for c in scenes['source']['contacts']):raise ValueError('This study declares a 30mm scene contact screen')
    skin=dict(np.load(ASSET,allow_pickle=False));rows={}
    save(output/'pipeline.json',dict(status='processing',quality_approved=False))
    with threadpool_limits(limits=1):
        for variant,scene in scenes.items():
            print('Dense audit '+variant,flush=True);rows[variant]=sample_scene(scene,fit,skin);save(output/(variant+'.json'),rows[variant])
    result=dict(at=now(),study_protocol_sha256=sha256(study/'protocol.json'),fit_summary_sha256=sha256(fit/'summary.json'),substeps=4,
        dense_samples_per_variant=len(rows['source']['frames']),authored_scene_preserved=True,quality_approved=False,authored_object_floor=rows['source']['authored_object_floor'],
        variants={v:{name:{k:value for k,value in a.items() if k not in ['floor_depth_m']} for name,a in row['actors'].items()} for v,row in rows.items()},
        scope='All skin vertices at exported 30fps keys and quarter-frame samples; contact interval [start,end+1) matches authored events. Signed analytic primitive distance, area-weighted palm normal, boundary speeds and joint derivatives. Discrete evidence only: no CCD, physical support classification, anatomy, balance or human approval.')
    for actors in result['variants'].values():
        for a in actors.values():
            for obj in a['objects'].values():obj.pop('depth_m')
            for c in a['contacts']:c.pop('point_error_m');c.pop('normal_error_degrees')
    implementation=['audit_primitive_grasp_fit.py','rig_clip_import.py','floor_contact.py','scene_constraints.py','object_geometry.py','release_geometry.py','gltf_tools.py']
    snapshot=output/'implementation';snapshot.mkdir()
    for name in implementation:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    result['implementation']={name:sha256(snapshot/name) for name in implementation};result['mesh_sha256']=sha256(ASSET)
    save(output/'verification.json',result);save(output/'pipeline.json',dict(status='complete',quality_approved=False))
    print({v:{a:dict(floor_mm=r['maximum_floor_depth_m']*1000,grip_mm=[c['maximum_error_m']*1000 for c in r['contacts']]) for a,r in actors.items()} for v,actors in result['variants'].items()},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.study,args.output)
