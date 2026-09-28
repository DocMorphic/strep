"""Neutral grey mannequin using the original continuous skinned body.

Preserves original measured GLBs and every animation channel. This is a new
appearance variant; body skinning is preserved and the head is replaced.
"""
import copy
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb,write_glb,accessor,global_matrices,skin_vertices,append_accessor

FOLDER=ROOT/'reports/control-calibration-v1'


def make_human(document,binary):
    """Use the continuous weighted body, with one neutral material."""
    out=copy.deepcopy(document)
    out['materials']=[{
        'name':'Matte grey mannequin',
        'pbrMetallicRoughness':{
            'baseColorFactor':[.36,.38,.40,1],
            'metallicFactor':0,'roughnessFactor':.8
        }
    }]
    for mesh in out['meshes']:
        for primitive in mesh['primitives']:
            primitive['material']=0
            # Remove texture/tint inputs while retaining original skin weights,
            # normals, topology and all animation data.
            for name in list(primitive['attributes']):
                if name.startswith(('TEXCOORD_', 'COLOR_')):
                    del primitive['attributes'][name]
    for field in ['images','textures','samplers']:
        out.pop(field,None)
    # Replace the source character's oversized cylindrical head with a
    # featureless, naturally proportioned mannequin head. Keep body skinning.
    world=global_matrices(document)
    rest=skin_vertices(document,binary,world)
    buffer=bytearray(binary)
    primitive=out['meshes'][out['nodes'][2]['mesh']]['primitives'][0]
    triangles=accessor(document,binary,primitive['indices']).reshape(-1,3)
    kept=triangles[rest[triangles,1].max(axis=1)<1.166].astype('<u4').reshape(-1)
    while len(buffer)%4:buffer.append(0)
    offset=len(buffer);buffer.extend(kept.tobytes())
    view=len(out['bufferViews'])
    out['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':kept.nbytes,'target':34963})
    primitive['indices']=len(out['accessors'])
    out['accessors'].append({'bufferView':view,'componentType':5125,'count':len(kept),'type':'SCALAR','min':[int(kept.min())],'max':[int(kept.max())]})
    vertices=[]
    def point(i,j):
        phi=np.pi*i/24;theta=2*np.pi*j/40
        return [np.sin(phi)*np.cos(theta),np.cos(phi),np.sin(phi)*np.sin(theta)]
    for i in range(24):
        for j in range(40):
            a,b,c,d=[point(*ij) for ij in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]]
            if i:vertices.extend([a,d,b])
            if i<23:vertices.extend([d,c,b])
    unit=np.array(vertices,dtype=np.float32)
    pos=append_accessor(out,buffer,unit,'VEC3');normal=append_accessor(out,buffer,unit,'VEC3')
    out['accessors'][pos].update(min=unit.min(0).tolist(),max=unit.max(0).tolist())
    mesh=len(out['meshes'])
    out['meshes'].append({'name':'Mannequin head','primitives':[{'attributes':{'POSITION':pos,'NORMAL':normal},'material':0}]})
    transform=np.eye(4);transform[:3,:3]=np.diag([.063,.094,.069])
    transform[:3,3]=world[21,:3,3]+[0,.065,.003]
    local=np.linalg.inv(world[21])@transform
    head=len(out['nodes'])
    out['nodes'].append({'name':'Mannequin head','mesh':mesh,'matrix':local.T.reshape(-1).tolist()})
    out['nodes'][21].setdefault('children',[]).append(head)
    out['asset'].update(generator='strep grey mannequin v2',
        copyright='CesiumMan mesh and rig, Cesium © 2017, CC BY 4.0; neutral material by strep.')
    out.setdefault('extras',{})['appearance']={
        'id':'grey-mannequin-v2',
        'geometry':'Continuous skinned CesiumMan body; proportioned oval head; matte grey.',
        'surface_contact_status':'Body/foot geometry and skin weights preserved; head replaced.'
    }
    return out,buffer


def main(folder=FOLDER):
    results=[]
    for method in ['text','direct']:
        for trial in read(folder/method/'summary.json')['trials']:
            source=folder/method/'characters'/trial['id']/'motion.glb';target=source.with_name('human.glb')
            before=sha256(source);document,binary=read_glb(source);human,buffer=make_human(document,binary)
            assert human['animations']==document['animations']
            write_glb(target,human,buffer)
            decoded,payload=read_glb(target)
            for animation in document['animations']:
                for sampler in animation['samplers']:
                    for field in ['input','output']:
                        index=sampler[field];assert np.array_equal(accessor(document,binary,index),accessor(decoded,payload,index))
            assert sha256(source)==before
            results.append({'method':method,'id':trial['id'],'source_sha256':before,'human_sha256':sha256(target),'animation_arrays_unchanged':True})
    save(folder/'simple-human.json',{'created_at':now(),'implementation_sha256':sha256(Path(__file__)),'trials':results})
    print(f'Built {len(results)} grey mannequin GLBs; animations and original files unchanged.')


if __name__=='__main__':main()
