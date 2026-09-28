import sys
from pathlib import Path
import numpy as np
import trimesh
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from partner_surface_cuts import surface_cuts
import partner_surface_cuts as module
from strep import save,sha256


def test_cut_normal_pushes_an_interior_point_outward():
    mesh=trimesh.creation.box(extents=[2,2,2]);points=np.array([[.8,.1,.1],[1.2,0,0],[-.4,.2,.2]])
    cuts=surface_cuts(points,mesh.vertices,mesh.faces,max_cuts=1)
    assert len(cuts)==1
    c=cuts[0];assert c['vertex']==2
    p=np.array(c['point_m']);n=np.array(c['normal']);v=points[c['vertex']]
    assert np.dot(v-p,n)<0
    np.testing.assert_allclose(np.dot((v+c['reference_depth_m']*n)-p,n),0,atol=1e-10)
    assert len(surface_cuts(points[1:2],mesh.vertices,mesh.faces))==0


def test_cut_context_is_bound_to_its_hash_clock_and_placements(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    placements={'A':{'translation_m':[0,0,0],'rotation_xyzw':[0,0,0,1]}}
    p=tmp_path/'cuts.json'
    save(p,dict(schema_version=1,frame_count=4,placements=placements,reference_sources={'A':'fixture'},reference_scene_sha256='fixture',
        actors={'A':[dict(frame=1,vertex=0,point_m=[0,0,0],normal=[0,1,0])]}))
    scene=dict(frame_count=4,actors={'A':{'transform':placements['A']}},partner_cut_file='cuts.json',partner_cut_sha256=sha256(p))
    skin=dict(bind_vertices=np.zeros((1,3)))
    assert len(module.load_cuts(scene,'A',skin)[0])==1
    scene['actors']['A']['transform']={'translation_m':[0,0,1],'rotation_xyzw':[0,0,0,1]}
    with pytest.raises(ValueError,match='placements'):module.load_cuts(scene,'A',skin)
    scene['actors']['A']['transform']=placements['A'];scene['partner_cut_sha256']='wrong'
    with pytest.raises(ValueError,match='hash'):module.load_cuts(scene,'A',skin)
