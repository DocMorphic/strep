"""Engine-independent animated primitive nodes for a shared-clock scene package."""
import numpy as np
from scipy.spatial.transform import Rotation
from scene_constraints import sample_object
from gltf_tools import append_accessor,write_glb
from object_geometry import scene_geometry
from object_geometry_mesh import triangle_mesh


def export_objects(scene,path):
    doc=dict(asset=dict(version='2.0',generator='Strep object tracks'),scene=0,scenes=[dict(nodes=[])],nodes=[],
        meshes=[],materials=[dict(pbrMetallicRoughness=dict(baseColorFactor=[.44,.26,.12,1],metallicFactor=0,roughnessFactor=.85))],
        buffers=[],bufferViews=[],accessors=[],animations=[dict(name='Strep objects',channels=[],samplers=[])])
    binary=bytearray();times=append_accessor(doc,binary,np.arange(scene['frame_count'])/scene['fps'],'SCALAR')
    for name,obj in scene['objects'].items():
        p,r=sample_object(obj,scene['frame_count']);q=Rotation.from_matrix(r).as_quat()
        geometry=scene_geometry(obj)
        for f in range(1,len(q)):
            if q[f]@q[f-1]<0:q[f]*=-1
        vertices,normals,approximation=triangle_mesh(geometry)
        vertices=vertices.reshape(-1,3);normals=normals.reshape(-1,3)
        vertices=np.asarray(vertices);pos=append_accessor(doc,binary,vertices,'VEC3');doc['accessors'][pos].update(min=vertices.min(0).tolist(),max=vertices.max(0).tolist())
        normal=append_accessor(doc,binary,normals,'VEC3');mesh=len(doc['meshes']);node=len(doc['nodes'])
        doc['meshes'].append(dict(primitives=[dict(attributes=dict(POSITION=pos,NORMAL=normal),material=0,mode=4)]))
        doc['nodes'].append(dict(name='Object_'+name,mesh=mesh,translation=p[0].tolist(),rotation=q[0].tolist(),extras=dict(strep_object_id=name,strep_geometry=geometry.record(),strep_preview_mesh=approximation)))
        doc['scenes'][0]['nodes'].append(node)
        animation=doc['animations'][0]
        # Preserve a complete TRS track. Godot 4.7.2 otherwise converts animated
        # object quaternions through Euler angles near gimbal singularities.
        # Importers must retain this constant unit-scale track.
        for prop,values,kind in [('translation',p,'VEC3'),('rotation',q,'VEC4'),('scale',np.ones((len(p),3)),'VEC3')]:
            index=len(animation['samplers']);animation['samplers'].append(dict(input=times,output=append_accessor(doc,binary,values,kind),interpolation='LINEAR'))
            animation['channels'].append(dict(sampler=index,target=dict(node=node,path=prop)))
    doc['extras']=dict(strep_object_clock_fps=scene['fps'],scope='Object tracks in world metres; actor assets and placements are separate. No runtime physics required.')
    write_glb(path,doc,binary)
