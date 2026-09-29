"""Independent decoded quarter-frame audit of a regional scene-fit candidate."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from floor_contact import Surface
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from scene_constraints import pose,sample_object
from scene_region_contact import compile_region,measure_frame
from object_geometry import scene_geometry
from inspect_motion import skeleton_metadata,validate_motion


def native_fk_error(source,candidate,parents):
    rotations=[];positions=[]
    for joint,parent in enumerate(parents):
        local=candidate['local_rot_mats'][:,joint]
        if parent<0:
            rotations.append(local);positions.append(candidate['root_positions'])
        else:
            offset=np.einsum('fji,fj->fi',source['global_rot_mats'][:,parent],source['posed_joints'][:,joint]-source['posed_joints'][:,parent])
            rotations.append(rotations[parent]@local)
            positions.append(positions[parent]+np.einsum('fij,fj->fi',rotations[parent],offset))
    return max(float(np.max(np.abs(np.stack(rotations,1)-candidate['global_rot_mats']))),
               float(np.max(np.abs(np.stack(positions,1)-candidate['posed_joints']))))


def edit_bounds(source,candidate,names,config):
    """Independent V14 control policy; never trust the candidate's recipe caps."""
    frames=len(source['root_positions'])
    if any(candidate[k].shape!=source[k].shape for k in source):raise ValueError('Motion shape changed')
    delta=source['local_rot_mats'].transpose(0,1,3,2)@candidate['local_rot_mats']
    angles=np.rad2deg(np.linalg.norm(Rotation.from_matrix(delta.reshape(-1,3,3)).as_rotvec(),axis=1)).reshape(frames,-1)
    limits=np.zeros(len(names))
    body=['Spine1','Spine2','Chest','Neck1','Neck2','Head']+[side+part for side in ['Left','Right'] for part in ['Shoulder','Arm','ForeArm','Hand','Leg','Shin','Foot']]
    for name in body:limits[names.index(name)]=config['max_rotation_degrees']
    for side in ['Left','Right']:
        for finger in ['Thumb','Index','Middle','Ring','Pinky']:
            for joint in range(1,4 if finger=='Thumb' else 5):
                limits[names.index(side+'Hand'+finger+str(joint))]=(8 if finger=='Thumb' else 5) if joint==1 else 12
    lift=candidate['root_positions'][:,1]-source['root_positions'][:,1]
    passed=bool(np.all(angles<=limits+1e-4) and lift.min()>=-1e-7 and lift.max()<=config['max_root_lift_m']+1e-7
                and np.allclose(source['root_positions'][:,[0,2]],candidate['root_positions'][:,[0,2]],atol=1e-7,rtol=0)
                and np.array_equal(source['foot_contacts'],candidate['foot_contacts']))
    return passed,angles,lift


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    protocol,result=read(study/'protocol.json'),read(study/'result.json')
    if result['status']!='complete' or sha256(study/'protocol.json')!=result['protocol_sha256']:
        raise ValueError('Completed unchanged fitting run required')
    if sha256(study/'motion.npz')!=result['candidate_sha256'] or sha256(study/'candidate.glb')!=result['candidate_glb_sha256']:
        raise ValueError('Candidate changed')
    for name,key in [('source.glb','source_glb_sha256'),('recipe.json','recipe_sha256'),('authored-scene.json','authored_scene_sha256')]:
        if sha256(study/name)!=result[key]:raise ValueError('Saved artifact changed: '+name)
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Source input changed')
    for name,digest in protocol['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Implementation snapshot changed')
    scene=read(study/'authored-scene.json');actor=protocol['actor'];skin=dict(np.load(ASSET,allow_pickle=False))
    source=dict(np.load(study/'source-motion.npz',allow_pickle=False));candidate=dict(np.load(study/'motion.npz',allow_pickle=False))
    validate_motion(source,30);validate_motion(candidate,30)
    _,parents,_=skeleton_metadata(77)
    reconstruction_error=native_fk_error(source,candidate,parents)
    if reconstruction_error>3e-6:raise ValueError('Candidate changed source bone offsets or has inconsistent native FK')
    if sha256(study/'source-motion.npz')!=sha256(ROOT/scene['actors'][actor]['motion']):raise ValueError('Copied source changed')
    frames=scene['frame_count'];times=np.arange((frames-1)*4+1)/4
    origin,placement=pose(scene['actors'][actor]['transform']);surface=Surface(skin)
    objects={}
    for name,obj in scene['objects'].items():
        p,r=sample_object(obj,frames)
        positions=np.stack([np.interp(times,np.arange(frames),p[:,i]) for i in range(3)],1)
        rotations=Slerp(np.arange(frames),Rotation.from_matrix(r))(times).as_matrix()
        objects[name]=(scene_geometry(obj),positions,rotations)
    contacts=[c for c in scene['contacts'] if c['id'] in protocol['contact_ids']]
    region_data={c['id']:compile_region(c,scene,skin) for c in contacts}
    variants={}
    for label in ['source','candidate']:
        doc,binary=read_glb(study/(label+'.glb'));sampler=AnimationSampler(doc,binary,0);joints=doc['skins'][0]['joints']
        if [doc['nodes'][j]['name'] for j in joints]!=list(map(str,skin['rig_joint_names'])):raise ValueError('Export rig mismatch')
        if abs(sampler.duration-(frames-1)/30)>1e-5:raise ValueError('Export duration mismatch')
        rows=[];positions=[];key_error=0.;native=source if label=='source' else candidate
        for i,frame in enumerate(times):
            matrices=sampler.sample(frame/30)[joints]
            if frame==int(frame):
                f=int(frame)
                key_error=max(key_error,float(np.max(np.abs(matrices[:,:3,3]-native['posed_joints'][f]))),
                              float(np.max(np.abs(matrices[:,:3,:3]-native['global_rot_mats'][f]))))
            rotation=placement@matrices[:,:3,:3];position=matrices[:,:3,3]@placement.T+origin
            vertices=surface.vertices(rotation,position);positions.append(position)
            region_rows=[]
            for c in contacts:
                if not c['start_frame']<=frame<=c['end_frame']:continue
                ids,faces,geometry,local_normal=region_data[c['id']]
                _,op,orr=objects[c['target']['object']];target=orr[i]@c['target']['point_m']+op[i]
                measured=measure_frame(vertices,ids,faces,target,orr[i]@local_normal,geometry,op[i],orr[i],c['region_contact']['limits'])
                error=float(np.linalg.norm(vertices[c['effector']['surface_vertex']]-target))
                region_rows.append(dict(contact_id=c['id'],anchor_error_m=error,**measured,
                    all_conditions_passed=measured['passed'] and error<=c.get('tolerance_m',.03)))
            clearances={name:float(g.distance_gradient(vertices,p[i],r[i])[0].min()) for name,(g,p,r) in objects.items()}
            floor=float(vertices[:,1].min())
            rows.append(dict(frame=float(frame),contacts=region_rows,minimum_floor_m=floor,object_clearances_m=clearances,
                geometry_passed=floor>=protocol['config']['clearance_m']-1e-6 and all(v>=protocol['config']['object_clearance_m']-1e-6 for v in clearances.values())))
        positions=np.asarray(positions)
        if key_error>3e-6:raise ValueError('Decoded export differs from recorded native motion')
        variants[label]=dict(glb_sha256=sha256(study/(label+'.glb')),native_key_error=key_error,rows=rows,
            contact_samples=sum(len(r['contacts']) for r in rows),contact_failures=sum(not c['all_conditions_passed'] for r in rows for c in r['contacts']),
            geometry_failures=sum(not r['geometry_passed'] for r in rows),
            peak_joint_speed_m_s=float(np.linalg.norm(np.diff(positions,axis=0)*120,axis=-1).max()),
            peak_joint_acceleration_m_s2=float(np.linalg.norm(np.diff(positions,n=2,axis=0)*120**2,axis=-1).max()))
    bounds,angles,lift=edit_bounds(source,candidate,list(map(str,skin['rig_joint_names'])),protocol['config'])
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/Path(__file__).name)
    save(output/'verification.json',dict(at=now(),study=study.relative_to(ROOT).as_posix(),result_sha256=sha256(study/'result.json'),
        protocol_sha256=sha256(study/'protocol.json'),auditor_sha256=sha256(__file__),variants=variants,
        hard_edit_bounds_passed=bounds,native_fk_error=reconstruction_error,maximum_rotation_edit_degrees=float(angles.max()),root_lift_range_m=[float(lift.min()),float(lift.max())],
        quality_approved=False,scope='Decoded quarter-frame full skin and region checks; native source-relative edit budgets. No continuous collision, self-collision, anatomy, force, semantic or human approval.'))
    print(dict(bounds=bounds,variants={k:{f:v[f] for f in ['contact_samples','contact_failures','geometry_failures','peak_joint_speed_m_s','peak_joint_acceleration_m_s2']} for k,v in variants.items()}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.study,a.output)
