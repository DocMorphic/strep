"""Inspect actual imported primitive meshes and all authored transforms in Godot."""
import argparse
import shutil
import subprocess
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from scene_constraints import sample_object,target_track
from scene_object_export import export_objects
from object_geometry import scene_geometry
from gltf_tools import read_glb,accessor


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    frames=31
    keys=[dict(frame=0,translation_m=[-.4,.7,.3],rotation_xyzw=Rotation.from_euler('xyz',[.2,.6,-.3]).as_quat().tolist()),
          dict(frame=frames-1,translation_m=[.8,1.1,-.4],rotation_xyzw=Rotation.from_euler('xyz',[1.3,-.5,.8]).as_quat().tolist())]
    scene=dict(id='primitive-import-development',fps=30,frame_count=frames,objects={
        'ball':dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.3),keyframes=keys),
        'crate':dict(shape='box',size_m=[.4,.6,.8],keyframes=keys)})
    save(output/'scene.json',scene);export_objects(scene,output/'objects.glb')
    project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    request=dict(scenes=[dict(id=scene['id'],frames=frames,actors={},objects_glb=str(output/'objects.glb'),object_names=list(scene['objects']),audit_object_meshes=True)])
    save(output/'request.json',request)
    sources=['verify_primitive_scene.py','object_geometry.py','object_geometry_mesh.py','scene_constraints.py','scene_object_export.py','godot_scene_import_audit.gd']
    (output/'implementation').mkdir()
    for name in sources:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'pipeline.json',dict(status='importing',at=now()))
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    with (output/'engine.log').open('w') as log:
        result=subprocess.run([str(engine),'--headless','--path',str(project),'--script',str(ROOT/'scripts/godot_scene_import_audit.gd'),'--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
    if result.returncode:raise RuntimeError('Godot primitive import failed; inspect retained engine.log')
    report=read(output/'engine-output.json');actual=report['scenes'][0]
    if len(report['scenes'])!=1 or actual['id']!=scene['id'] or len(actual['object_frames'])!=frames:
        raise ValueError('Engine scene/clock mismatch')
    doc,binary=read_glb(output/'objects.glb');checks=[]
    for name,obj in scene['objects'].items():
        geometry=scene_geometry(obj);p,r=sample_object(obj,frames)
        values=np.array([frame[name] for frame in actual['object_frames']]);positions=values[:,3];rotations=values[:,:3].transpose(0,2,1)
        pe=float(abs(positions-p).max());re=float(abs(rotations-r).max())
        node=next(n for n in doc['nodes'] if n.get('extras',{}).get('strep_object_id')==name)
        if node['extras']['strep_geometry']!=geometry.record():raise ValueError('Exported geometry identity mismatch')
        primitive=doc['meshes'][node['mesh']]['primitives'][0]
        source=accessor(doc,binary,primitive['attributes']['POSITION'])
        surfaces=actual['object_meshes'][name]
        if len(surfaces)!=1:raise ValueError('Unexpected primitive surface count')
        vertices=np.asarray(surfaces[0]['positions']);normals=np.asarray(surfaces[0]['normals'])
        mesh_error=max(float(cKDTree(source).query(vertices)[0].max()),float(cKDTree(vertices).query(source)[0].max()))
        normal_unit_error=float(abs(np.linalg.norm(normals,axis=1)-1).max())
        surface_error=float(abs(geometry.distance_gradient(vertices,np.zeros(3),np.eye(3))[0]).max())
        # A material point on the sphere must rotate with it even though its
        # silhouette and inertia are rotation invariant.
        point=[geometry.dimensions[0],0,0] if geometry.shape=='sphere' else [geometry.dimensions[0]/2,0,0]
        target=target_track(dict(space='object',object=name,point_m=point),{},{name:(p,r)},frames)
        engine_grip=positions+np.einsum('fij,j->fi',rotations,point)
        grip_error=float(np.linalg.norm(engine_grip-target,axis=1).max())
        passed=max(pe,re,mesh_error,surface_error,grip_error)<1e-5 and normal_unit_error<.002
        checks.append(dict(object=name,shape=geometry.shape,frames=frames,engine_vertices=len(vertices),position_error_m=pe,rotation_element_error=re,
            mesh_hausdorff_vertex_error_m=mesh_error,analytic_vertex_surface_error_m=surface_error,normal_unit_error=normal_unit_error,
            attached_material_point_error_m=grip_error,preview_mesh=node['extras']['strep_preview_mesh'],passed=passed))
    verification=dict(at=now(),engine=report['engine'],checks=checks,all_passed=all(row['passed'] for row in checks),quality_approved=False,
        implementation={name:sha256(output/'implementation'/name) for name in sources},scene_sha256=sha256(output/'scene.json'),glb_sha256=sha256(output/'objects.glb'),
        scope='Two authored primitive tracks, 62 object-frame observations, actual imported meshes and material-point transforms. No actor fitting, generated interaction, physics release, browser rendering or human quality approval.')
    save(output/'verification.json',verification);save(output/'pipeline.json',dict(status='complete',all_checks_passed=verification['all_passed'],quality_approved=False))
    print(checks,flush=True)
    if not verification['all_passed']:raise RuntimeError('Primitive engine import checks failed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.output)
