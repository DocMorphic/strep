"""Load the hash-bound actor/control inputs of an existing partner-path trial."""
from pathlib import Path
import numpy as np
from strep import read,sha256
from rig_asset import RigAsset,array
from paired_palm_region import RegionActor
from unique_fractional_skin import UniqueBoundedPathFitter


def load(source):
    source=Path(source);recipe=read(source/'request.json');initial=read(source/'initial-parameters.json')
    if sha256(recipe['source_scene'])!=recipe['source_scene_sha256'] or sha256(source/'palm-region.json')!=recipe['palm_region_sha256']:
        raise ValueError('Contact scene or patch changed')
    scene=read(recipe['source_scene'])['scene'];patches=read(source/'palm-region.json');actors=[]
    for label in ['A','B']:
        item=recipe['sources'][label];path=Path(item['raw_glb']);local_path=source/(label+'-source-local.npz')
        if sha256(path)!=item['raw_glb_sha256'] or sha256(local_path)!=item['local_npz_sha256']:raise ValueError('Actor input changed')
        rig=RigAsset.load(path);local=np.load(local_path,allow_pickle=False)['authored_finger_local'];primitive=rig.document['meshes'][0]['primitives'][0]
        triangles=array(rig.document,rig.binary,primitive['indices']).reshape(-1,3)
        if actors and not np.array_equal(triangles,faces):raise ValueError('Actor topology differs')
        faces=triangles
        actors.append(RegionActor(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],faces,scene['actors'][label]['transform'],patch=patches[label]))
    fitter=UniqueBoundedPathFitter(actors)
    for name,value in [('basis',fitter.matrix),('control_bounds',fitter.bounds),('control_radii',fitter.control_radii)]:
        if not np.array_equal(np.asarray(initial[name]),value):raise ValueError('Control protocol differs')
    return recipe,fitter,faces,np.asarray(initial['controls'],float)
