"""Export Kimodo's bundled SOMA preview mesh with the measured source motion.

All eight skin influences are retained. No retargeting, body approximation,
motion generation or modification of the frozen study assets is performed.
"""
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from gltf_tools import append_accessor, write_glb, read_glb, accessor, sample_animation

FOLDER = ROOT/'reports/control-calibration-v1'
ASSET = ROOT/'vendor/kimodo/kimodo/assets/skeletons/somaskel77/skin_standard.npz'


def make_preview(skin, motion, displacement, *, repeat=True, fps=30):
    positions=motion['posed_joints']; rotations=motion['global_rot_mats']
    if repeat:
        positions=np.concatenate([positions+displacement*i for i in range(4)]+[positions[:1]+displacement*4])
        rotations=np.concatenate([rotations]*4+[rotations[:1]])
    bind=skin['bind_rig_transform'].astype(float); names=skin['rig_joint_names']
    parents=np.full(len(names),-1,dtype=int)
    for parent,child in skin['rig_joint_connections']:parents[child]=parent
    doc={'asset':{'version':'2.0','generator':'strep SOMA preview v1',
        'copyright':'SOMA visualization asset from NVIDIA Kimodo, Apache-2.0. Motion study by strep.'},
        'scene':0,'scenes':[{'nodes':[0,1]}], 'nodes':[{'name':'SOMA body','mesh':0,'skin':0}],
        'bufferViews':[],'accessors':[], 'materials':[{'name':'Neutral grey',
        'pbrMetallicRoughness':{'baseColorFactor':[.38,.40,.42,1],'metallicFactor':0,'roughnessFactor':.78}}]}
    buffer=bytearray()
    def integer_accessor(values,kind,component,dtype):
        values=np.asarray(values,dtype=dtype)
        while len(buffer)%4:buffer.append(0)
        offset=len(buffer);buffer.extend(values.tobytes());view=len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':values.nbytes})
        index=len(doc['accessors']);doc['accessors'].append({'bufferView':view,'componentType':component,'count':len(values),'type':kind})
        return index
    verts=skin['bind_vertices'].astype(np.float32);faces=skin['faces']
    face_normals=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]])
    normals=np.zeros_like(verts)
    for column in range(3):np.add.at(normals,faces[:,column],face_normals)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    pos=append_accessor(doc,buffer,verts,'VEC3');doc['accessors'][pos].update(min=verts.min(0).tolist(),max=verts.max(0).tolist())
    attrs={'POSITION':pos,'NORMAL':append_accessor(doc,buffer,normals,'VEC3')}
    for group in range(2):
        attrs[f'JOINTS_{group}']=integer_accessor(skin['lbs_indices'][:,group*4:group*4+4],'VEC4',5123,'<u2')
        attrs[f'WEIGHTS_{group}']=append_accessor(doc,buffer,skin['lbs_weights'][:,group*4:group*4+4],'VEC4')
    indices=integer_accessor(faces.reshape(-1),'SCALAR',5125,'<u4')
    doc['meshes']=[{'name':'Kimodo SOMA standard body','primitives':[{'attributes':attrs,'indices':indices,'material':0}]}]
    inverse=append_accessor(doc,buffer,np.linalg.inv(bind).transpose(0,2,1).reshape(-1,16),'MAT4')
    doc['skins']=[{'inverseBindMatrices':inverse,'joints':list(range(1,78)),'skeleton':1}]
    times=append_accessor(doc,buffer,np.arange(len(positions),dtype=np.float32)/fps,'SCALAR')
    animation={'name':'processed_loop' if repeat else 'action','samplers':[],'channels':[]}
    for j,parent in enumerate(parents):
        rest=bind[j] if parent<0 else np.linalg.inv(bind[parent])@bind[j]
        node={'name':str(names[j]),'translation':rest[:3,3].tolist(),'rotation':Rotation.from_matrix(rest[:3,:3]).as_quat().tolist()}
        children=(np.flatnonzero(parents==j)+1).tolist()
        if children:node['children']=children
        doc['nodes'].append(node)
        if parent<0:local_r=rotations[:,j];local_p=positions[:,j]
        else:
            inv=rotations[:,parent].transpose(0,2,1)
            local_r=inv@rotations[:,j]
            local_p=np.einsum('fij,fj->fi',inv,positions[:,j]-positions[:,parent])
        q=Rotation.from_matrix(local_r).as_quat()
        for f in range(1,len(q)):
            if np.dot(q[f-1],q[f])<0:q[f]*=-1
        for prop,values,kind in [('translation',local_p,'VEC3'),('rotation',q,'VEC4')]:
            output=append_accessor(doc,buffer,values,kind);sampler=len(animation['samplers'])
            animation['samplers'].append({'input':times,'output':output,'interpolation':'LINEAR'})
            animation['channels'].append({'sampler':sampler,'target':{'node':j+1,'path':prop}})
    doc['animations']=[animation]
    doc['extras']={'appearance':'kimodo-soma-standard-grey-v1','space':'SOMA77 source motion','skin_influences':8}
    return doc,buffer,positions,rotations


def main(folder=FOLDER):
    skin=dict(np.load(ASSET,allow_pickle=False));results=[]
    for method in ['text','direct']:
        for trial in read(folder/method/'summary.json')['trials']:
            source=folder/method/'stance'/trial['profile']/f"seed-{trial['seed']}/corrected.npz"
            target=folder/method/'characters'/trial['id']/'soma.glb'
            before=sha256(source);motion=dict(np.load(source,allow_pickle=False))
            doc,binary,positions,rotations=make_preview(skin,motion,np.array(trial['processed_cycle_displacement_m']))
            write_glb(target,doc,binary);decoded,payload=read_glb(target)
            max_error=0.;max_rotation_error=0.
            for frame in range(len(positions)):
                matrices=sample_animation(decoded,payload,0,frame)[1:78]
                max_error=max(max_error,float(np.linalg.norm(matrices[:,:3,3]-positions[frame],axis=-1).max()))
                max_rotation_error=max(max_rotation_error,float(np.abs(matrices[:,:3,:3]-rotations[frame]).max()))
            assert max_error<1e-5 and max_rotation_error<1e-5
            attrs=decoded['meshes'][0]['primitives'][0]['attributes']
            weights=np.concatenate([accessor(decoded,payload,attrs[f'WEIGHTS_{i}']) for i in range(2)],axis=1)
            assert np.array_equal(weights,skin['lbs_weights']) and sha256(source)==before
            results.append({'method':method,'id':trial['id'],'source_sha256':before,'glb_sha256':sha256(target),
                'max_joint_roundtrip_error_m':max_error,'max_rotation_matrix_error':max_rotation_error,'all_eight_weights_preserved':True})
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',folder/'SOMA-preview-LICENSE.txt')
    save(folder/'soma-preview.json',{'created_at':now(),'asset':str(ASSET),'asset_sha256':sha256(ASSET),
        'implementation_sha256':sha256(Path(__file__)),'trials':results})
    print(f'Exported {len(results)} SOMA previews; all poses and eight skin weights verified.')


if __name__=='__main__':main()
