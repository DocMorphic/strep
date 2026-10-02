"""Every material participates in uniquely bound imported skin reconstruction."""
from pathlib import Path
import sys,numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_support_imported_surfaces import unique_correspondence, ImportedSupportSurfaces
from test_native_support_skin_geometry import multiprimitive
from test_native_support_skin import surface
from types import SimpleNamespace


def test_forced_unique_matching_allows_local_ambiguity():
    assert unique_correspondence([[1,1,0],[0,1,0],[0,1,1]])==[0,1,2]


@pytest.mark.parametrize('table',[[[1,1],[1,1]],[[1,0],[1,0]],[],[[1,0,0],[0,1,0]]])
def test_ambiguous_missing_or_incomplete_matching_rejected(table):
    with pytest.raises(ValueError):unique_correspondence(table)


def fixture(tmp_path):
    rig,reader=multiprimitive(tmp_path);data=[]
    for p in rig.primitives:
        mock=SimpleNamespace(primitives=[p],joints=rig.joints,document=rig.document,inverse=rig.inverse)
        data.append(surface(dict(id='test',path='test.glb'),mock)['surfaces'][0])
    return rig,reader,[data[2],data[0],data[1]]


def test_all_three_surfaces_keep_source_vertex_order_after_bind_and_surface_reordering(tmp_path):
    rig,reader,data=fixture(tmp_path);imported=ImportedSupportSurfaces(rig,data)
    assert imported.matching==[1,2,0] and imported.data_check['passed']
    assert imported.data_check['surfaces']==3 and imported.data_check['influences']==[4,8]
    names=[rig.document['nodes'][n]['name'] for n in rig.joints][::-1]
    for t in (0.,.853725,1.371,2.):
        world=reader.sample(t);bones=[np.vstack([world[n,:3,:3].T,world[n,:3,3]]).tolist() for n in rig.joints[::-1]]
        np.testing.assert_allclose(imported.vertices(bones,names),rig.vertices(world),atol=5e-15,rtol=0)


@pytest.mark.parametrize('fault',['missing','duplicate','weight','bind'])
def test_surface_loss_or_bad_correspondence_cannot_be_hidden(tmp_path,fault):
    rig,reader,data=fixture(tmp_path)
    if fault=='missing':data.pop()
    if fault=='duplicate':data[2]=data[0]
    if fault=='weight':data[2]['weights'][0]-=.01
    if fault=='bind':data[2]['binds'][0]['pose'][3][0]+=.05
    with pytest.raises(ValueError):ImportedSupportSurfaces(rig,data)


@pytest.mark.parametrize('offset',[0.,-.2])
def test_both_auditors_measure_the_full_surface_foot_region(tmp_path,offset):
    import run_native_support_engine as engine
    import audit_native_support_skin as skin
    from test_native_support_engine import observations
    rig,reader,data=fixture(tmp_path)
    times=[0.,.853725,1.371,2.]
    case=dict(id='test',path=str(tmp_path/'source.glb'),frames=len(times),sample_times_s=times)
    names=[rig.document['nodes'][n]['name'] for n in rig.joints]
    poses=observations(case,(rig,reader,names))
    rows=[dict(id='foot',chain=[1,2,3],stance_s=[0.,2.],up=[0,1,0],offset=offset,maximum_height=.01)]
    expected=[float(rig.vertices(reader.sample(t))[[0,1,2,3,4],1].min()+offset) for t in times]
    e,_,eh=engine.check_case(case,poses,(rig,reader,names),rows)
    s,_,sh=skin.check_skin(case,dict(id=case['id'],path=case['path'],surfaces=data),poses,rig,reader,rows)
    assert e['engine_pose_pass'] and s['skin_data_check']['passed']
    assert len(s['surface_checks'])==3
    np.testing.assert_allclose(eh[0]['engine_bone_lowest_heights_m'],expected,atol=5e-15,rtol=0)
    np.testing.assert_allclose(sh[0]['lowest_heights_m'],expected,atol=5e-15,rtol=0)
    passed=min(expected)>=-1e-8 and max(expected)<=.01
    assert e['engine_bones_original_skin_support_pass']==s['imported_skin_support_pass']==passed
