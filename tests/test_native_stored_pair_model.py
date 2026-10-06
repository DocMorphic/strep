"""Actual scene-model integration and rejection of changed scene contracts."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_stored_pair_model import centered_problem,model
from native_scene_contacts import SceneContacts
from native_scene_fit import SceneProblem
from native_scene_boundary_edit import BoundarySceneEdits,SCHEMA as BOUNDARY
from native_rotation_storage_repair import StorageAdjustedEdits,SCHEMA as STORAGE,authoring_digest
from native_scene_norms import rows
from native_surface_model import include_times
from test_native_partner_surface_rows import scene_fixture
from strep import read,save,sha256


def fixture(tmp_path):
    scene,policy,digest=scene_fixture(tmp_path);spec=read(tmp_path/'contacts.json')
    spec['objects']['box']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='box',size_m=[.2,.2,.2]),
        keyframes=[dict(time_s=0.,translation_m=[0.,3.,0.],rotation_xyzw=[0.,0.,0.,1.])])
    save(tmp_path/'contacts.json',spec);scene=SceneContacts(spec,tmp_path);digest=sha256(tmp_path/'contacts.json');policy['contacts_sha256']=digest
    permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors={'A':dict(window_s=[0.,2.],
        protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02)})
    request=dict(schema=BOUNDARY,permissions=permissions,boundary_keys={'A':dict(start='preserve',end='preserve')},acknowledge_changed_boundary_compatibility=False)
    base=BoundarySceneEdits(request,scene,digest,rotation_storage_policy='source-scale')
    storage=dict(schema=STORAGE,authoring_sha256=authoring_digest(base),maximum_component_steps=1,maximum_corrections=64,acknowledge_storage_adjustment=True)
    editor=StorageAdjustedEdits(base,storage,[]);problem=SceneProblem(scene,editor);include_times(problem,policy['clock']['times_s'])
    x=base.initial.copy();x[0]=.013;path=tmp_path/'anchor.glb';editor.export('A',x,path)
    guide=copy.deepcopy(spec);guide['actors']['A'].update(glb=str(path),sha256=sha256(path))
    return problem,x,{'A':path},spec,guide,policy


def arguments(tmp_path):
    problem,x,files,spec,guide,policy=fixture(tmp_path);guide_path=tmp_path/'guide.json';save(guide_path,guide)
    gp=copy.deepcopy(policy);gp['contacts_sha256']=sha256(guide_path)
    return [problem,x,files,SceneContacts(guide,tmp_path),gp,sha256(guide_path)],dict(source_policy=policy)


def test_actual_centering_keeps_original_problem_and_every_constraint(tmp_path):
    args,kw=arguments(tmp_path);original=args[0];editor=original.edits
    before={n:cap.caps for n,cap in original.caps.items()};worlds={n:w.copy() for n,w in original.source_world.items()}
    centered,decoded,report=centered_problem(*args,**kw)
    assert original.edits is editor and centered is not original and centered.edits.base is editor
    for n,w in worlds.items():np.testing.assert_array_equal(original.source_world[n],w)
    for n,caps in before.items():
        for a,b in zip(original.caps[n].caps,caps):np.testing.assert_array_equal(a,b)
    a,b=rows(original,args[1],decoded),rows(centered,args[1],decoded)
    for key in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(a,key),getattr(b,key))
    assert report['original_scene_and_acceptance_preserved'] and not report['quality_approved']
    assert report['geometry_samples']==3 and max(report['maximum_centered_world_difference'].values())<2e-12


def test_actual_complete_pair_model_uses_centered_curve_without_approving_asset(tmp_path):
    args,kw=arguments(tmp_path);centered,native,jac,guides,gaps,surface,report=model(*args,.02,**kw)
    assert guides.count>0 and len(gaps)==guides.count and surface.shape==(guides.count,centered.size)
    assert jac.shape==(native.vectors.size,centered.size) and len(report['surface_differences'])==centered.size
    assert report['derivative_proxy']=='verified-stored-anchor' and report['stored_pair_centering']['anchor_sha256']['A']==sha256(args[2]['A'])
    assert report['native_acceptance_unchanged'] and not report['quality_approved'] and not report['release_approved']


@pytest.mark.parametrize('fault',['limits','planes','clock','source-binding','contact','object-geometry','object-path','placement','edited-payload','unedited-payload','missing-actor'])
def test_changed_source_or_guide_contract_rejects_before_model(tmp_path,fault):
    problem,x,files,spec,guide,policy=fixture(tmp_path);source=copy.deepcopy(policy);gp=copy.deepcopy(policy)
    if fault=='limits':gp['limits']['penetration_m']=.006
    elif fault=='planes':gp['planes']['floor']=dict(normal_world=[0.,1.,0.],offset_m=0.)
    elif fault=='clock':gp['clock']['times_s']=[0.,.9,2.]
    elif fault=='source-binding':source['contacts_sha256']='a'*64
    elif fault=='contact':guide['contacts'][0]['limits']['position_m']+=.001
    elif fault=='object-geometry':guide['objects']['box']['geometry']['size_m'][0]=.3
    elif fault=='object-path':guide['objects']['box']['keyframes'][0]['translation_m'][1]=4.
    elif fault=='placement':guide['actors']['B']['placement']['translation_m'][0]+=.01
    elif fault=='edited-payload':guide['actors']['A']=copy.deepcopy(spec['actors']['A'])
    elif fault=='unedited-payload':guide['actors']['B'].update(glb=str(files['A']),sha256=sha256(files['A']))
    elif fault=='missing-actor':guide['actors'].pop('B')
    path=tmp_path/'guide.json';save(path,guide);gp['contacts_sha256']=sha256(path)
    with pytest.raises(ValueError):centered_problem(problem,x,files,SceneContacts(guide,tmp_path),gp,sha256(path),source_policy=source)


def test_missing_geometry_time_requires_original_problem_clock_extension(tmp_path):
    args,kw=arguments(tmp_path)
    for p in (args[4],kw['source_policy']):p['clock']['times_s']=[0.,1.003,2.]
    with pytest.raises(ValueError,match='every geometry time'):centered_problem(*args,**kw)


def test_unedited_actor_cannot_inherit_reference_worlds_as_actual_playback(tmp_path):
    args,kw=arguments(tmp_path)
    args[0].source_world['B']=args[0].source_world['B'].copy()
    args[0].source_world['B'][:,:,2,3]+=.01
    with pytest.raises(ValueError,match='Unedited actor'):
        centered_problem(*args,**kw)


def test_plain_or_missing_problem_cannot_bypass_storage_contract(tmp_path):
    args,kw=arguments(tmp_path);args[0].edits=args[0].edits.base
    with pytest.raises(ValueError,match='storage-adjusted'):centered_problem(*args,**kw)
    args[0]=None
    with pytest.raises(ValueError,match='storage-adjusted'):centered_problem(*args,**kw)
