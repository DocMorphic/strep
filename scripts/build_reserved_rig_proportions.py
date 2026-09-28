"""Construct static proportion fixtures without using held-out motion prompts."""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import append_accessor,write_glb
from rig_asset import RigAsset,array
from rig_loop import encode
from strep import ROOT,now,read,save,sha256

RECIPES=[('rig-held-01','Superhero_Female_FullBody',[.90,1.10,.95]),
         ('rig-held-02','Superhero_Male_FullBody',[1.12,.90,1.08]),
         ('rig-held-03','Superhero_Female_FullBody',[1.15,1.,1.])]


def bake(rig,scale,path):
    scale=np.asarray(scale,float)
    if scale.shape!=(3,) or not np.isfinite(scale).all() or np.any(scale<=0):
        raise ValueError('Positive finite XYZ proportions required')
    if any(p['joints'] is None for p in rig.primitives):
        raise ValueError('Reserved fixture construction requires fully skinned primitives')
    old_points=rig.vertices(rig.reference)
    expected=old_points*scale;shift=np.array([0.,-expected[:,1].min(),0.]);expected+=shift
    world=rig.reference.copy();world[:,:3,3]=world[:,:3,3]*scale+shift
    doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary);doc.pop('animations',None)
    for n,parent in enumerate(rig.parents):
        local=world[n] if parent<0 else np.linalg.solve(world[parent],world[n])
        node=doc['nodes'][n]
        for key in ['matrix','translation','rotation','scale']:node.pop(key,None)
        node.update(translation=local[:3,3].tolist(),rotation=Rotation.from_matrix(local[:3,:3]).as_quat().tolist())
    doc['skins'][0]['inverseBindMatrices']=append_accessor(doc,binary,np.linalg.inv(world[rig.joints]).transpose(0,2,1),'MAT4')
    original_transforms=rig.reference[rig.joints]@rig.inverse
    offset=0
    for part in rig.primitives:
        primitive=doc['meshes'][doc['nodes'][part['node']]['mesh']]['primitives'][part['primitive']]
        attributes=primitive['attributes'];count=len(part['positions']);points=expected[offset:offset+count];offset+=count
        index=append_accessor(doc,binary,points,'VEC3');attributes['POSITION']=index
        doc['accessors'][index].update(min=points.min(0).tolist(),max=points.max(0).tolist())
        basis=np.einsum('nk,nkij->nij',part['weights'],original_transforms[part['joints'],:3,:3])
        if np.min(abs(np.linalg.det(basis)))<1e-8:raise ValueError('Singular source normal basis')
        if 'NORMAL' not in attributes:raise ValueError('Explicit source normals required')
        normals=array(rig.document,rig.binary,attributes['NORMAL'])
        normals=np.einsum('nij,nj->ni',np.linalg.inv(basis).transpose(0,2,1),normals)/scale
        lengths=np.linalg.norm(normals,axis=1)
        if np.min(lengths)<1e-8:raise ValueError('Degenerate normals')
        normals/=lengths[:,None];attributes['NORMAL']=append_accessor(doc,binary,normals,'VEC3')
        if 'TANGENT' in attributes:
            tangent=array(rig.document,rig.binary,attributes['TANGENT'])
            xyz=np.einsum('nij,nj->ni',basis,tangent[:,:3])*scale
            xyz-=np.sum(xyz*normals,axis=1)[:,None]*normals
            norm=np.linalg.norm(xyz,axis=1)
            if np.min(norm)<1e-8:raise ValueError('Degenerate tangents')
            attributes['TANGENT']=append_accessor(doc,binary,np.c_[xyz/norm[:,None],tangent[:,3]],'VEC4')
    doc.setdefault('extras',{})['strep_fixture']=dict(kind='reserved_proportions',world_axis_scale=scale.tolist(),
        construction='Default-pose mesh and joint positions scaled in world space; rigid node bases retained; mesh rebaked and inverse binds recomputed. Source animations removed.')
    write_glb(path,doc,binary);new=RigAsset.load(path);actual=new.vertices(new.reference)
    error=float(np.linalg.norm(actual-expected,axis=1).max())
    joint_error=float(abs(new.reference-world).max())
    if max(error,joint_error)>1e-5:raise ValueError('Proportion fixture roundtrip failed')
    if new.document.get('animations'):raise ValueError('Source animations must not survive changed bind geometry')
    for before,after in zip(rig.primitives,new.primitives):
        np.testing.assert_array_equal(before['joints'],after['joints'])
        np.testing.assert_array_equal(before['weights'],after['weights'])
    return new,dict(surface_roundtrip_max_m=error,joint_matrix_roundtrip_max=joint_error,
        original_dimensions_m=np.ptp(old_points,axis=0).tolist(),dimensions_m=np.ptp(actual,axis=0).tolist(),
        floor_min_y_m=float(actual[:,1].min()),ground_shift_m=shift.tolist(),
        original_joints=len(rig.joints),joints=len(new.joints),source_animations_removed=True)


def run(output):
    if output.exists():raise ValueError('Preserve reserved fixture versions')
    catalog=read(ROOT/'assets/characters/catalog.json')['characters']
    output.mkdir(parents=True);rows=[];manifest=[]
    for name,source_name,scale in RECIPES:
        entry=next(c for c in catalog if Path(c['file']).stem==source_name)
        source=ROOT/entry['file']
        if sha256(source)!=entry['sha256']:raise ValueError('Source character changed')
        folder=output/'rigs'/name;folder.mkdir(parents=True)
        rig=RigAsset.load(source);new,check=bake(rig,scale,folder/'character.glb')
        profile=copy.deepcopy(read(ROOT/entry['profile']));profile['character_sha256']=sha256(folder/'character.glb')
        profile['notes']='Reserved synthetic proportion fixture. Original neutral-pose role mapping and foot alignment retained. No motion-based tuning or quality approval.'
        save(folder/'rig-profile.json',profile)
        attachments={}
        for label,relative in entry['attachments'].items():
            dest=folder/label;shutil.copyfile(ROOT/relative,dest);attachments[label]=sha256(dest)
        # Two identical poses are solely an engine format/skinning check.
        animated=set(new.joints)
        _,pose_roundtrip=encode(new,np.repeat(new.reference[None],2,axis=0),animated,profile['mapping']['Hips'],folder/'static-import.glb','Fixture construction check')
        manifest.append(dict(id=name,path=str((folder/'static-import.glb').resolve()),sha256=sha256(folder/'static-import.glb'),frames=2,fps=30,sample_by_time=True))
        rows.append(dict(id=name,source=str(source),source_sha256=sha256(source),source_profile_sha256=sha256(ROOT/entry['profile']),
            scale_xyz=scale,character_sha256=sha256(folder/'character.glb'),profile_sha256=sha256(folder/'rig-profile.json'),
            attachments=attachments,checks=check,static_pose_roundtrip=pose_roundtrip,
            family='Quaternius Universal Base Characters',held_out_dimension='synthetic proportions; known topology and skinning family',
            release_quality_approved=False))
    save(output/'manifest.json',dict(cases=manifest))
    save(output/'construction.json',dict(at=now(),rows=rows,implementation_sha256=sha256(Path(__file__)),
        license_source='https://quaternius.com/packs/universalbasecharacters.html',license_checked='2026-09-28',license_page_label='CC0',
        source_licenses_copied=True,motion_trials_executed=0,quality_approved=False,
        scope='Three reserved proportion fixtures from two existing CC0 source meshes in one known rig family. Construction and static import checks do not validate retargeting, animation quality, new topologies or production characters. No reserved action prompt used.'))
    print([dict(id=r['id'],**r['checks']) for r in rows])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    run(parser.parse_args().output.resolve())
