import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,sha256
from actor_collision_proxies import compile_actor_proxies,fit_actor,DIRECTIONS
from build_soma_preview import ASSET,make_preview
from gltf_tools import write_glb,sample_animation


def test_mesh_fitted_actor_proxies_preserve_source_and_exported_clock(tmp_path):
    source=read(ROOT/'reports/object-release-v2/seed-22-original/palm.json')['scene']['actors']['A']
    motion=dict(np.load(ROOT/source['motion'],allow_pickle=False))
    short={k:v[:6].copy() if v.ndim and len(v)==180 else v.copy() for k,v in motion.items()}
    skin=dict(np.load(ASSET,allow_pickle=False));doc,binary,_,_=make_preview(skin,short,np.zeros(3),repeat=False)
    glb=tmp_path/'actor.glb';write_glb(glb,doc,binary);digest=sha256(glb)
    placement=Rotation.from_euler('y',.7).as_matrix();offset=np.array([2.,0,-1.])
    scene=dict(frame_count=6,actors=dict(A=dict(preview_glb='actor.glb',transform=dict(translation_m=offset.tolist(),rotation_xyzw=Rotation.from_matrix(placement).as_quat().tolist()))))
    colliders,report=compile_actor_proxies(scene,tmp_path,2,physics_fps=240,friction=.6,restitution=0)
    assert sha256(glb)==digest and len(colliders)==21
    parts=report['actors'][0]['parts_geometry']
    ids=[v for p in parts for v in p['vertex_ids']]
    assert sorted(ids)==list(range(len(skin['bind_vertices'])))
    assert report['actors'][0]['whole_half_frame_skin_outside_plane_max_m']<.001
    for c,part in zip(colliders,parts):
        assert c['id']=='actor:A:'+part['name'] and c['shape']=='convex'
        for frame in range(2,6):
            sample=sample_animation(doc,binary,0,frame)[part['node']];index=(frame-2)*8+1
            expected=placement@(sample[:3,3]+sample[:3,:3]@part['center_local_m'])+offset
            np.testing.assert_allclose(c['positions_m'][index],expected,atol=1e-6,rtol=0)
            np.testing.assert_allclose(Rotation.from_quat(c['rotations_xyzw'][index]).as_matrix(),placement@sample[:3,:3],atol=1e-6,rtol=0)
    with pytest.raises(ValueError,match='duration'):fit_actor(glb,7)
