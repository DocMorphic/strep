"""Root-only scalar reduction and actual native export/readback contracts."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_rig_transfer import fixture
from rig_asset import RigAsset
from gltf_tools import append_accessor,write_glb
from native_support_clock import NativeSupportSampler
from rig_floor_comparison import compare
from engine_contact_sampling import frame_populations
from strep import save,read,sha256
import native_vertical_root as root
from native_vertical_storage import coordinates


def test_sparse_interpolation_matches_native_endpoint_and_key_arithmetic():
    clock=np.array([0,.008333334,.613725,2.0009999],dtype=np.float32)
    queries=np.unique(np.r_[clock.astype(float),[float(clock[-1])-1e-9,.03,.7]])
    values=np.random.default_rng(71).normal(size=(len(clock),3))
    expected=np.array([NativeSupportSampler.value('translation',clock,values,'LINEAR',t) for t in queries])
    np.testing.assert_allclose(root.basis(clock,queries)@values,expected,atol=5e-16,rtol=0)


def test_all_joint_norm_constraints_reduce_to_exact_vertical_interval():
    vectors=np.array([[[1,2,2],[0,-1,0]]],float);caps=np.array([[3,2.]])
    lo,hi,a,b=root.vertical_intervals(vectors,caps,tolerance=0)
    np.testing.assert_array_equal(lo,[-1]);np.testing.assert_array_equal(hi,[0]);assert a[0]==1 and b[0]==0
    for value in (-1,-.4,0):
        changed=vectors.copy();changed[:,:,1]+=value;assert np.all(np.linalg.norm(changed,axis=2)<=caps)
    for value in (-1.01,.01):
        changed=vectors.copy();changed[:,:,1]+=value;assert not np.all(np.linalg.norm(changed,axis=2)<=caps)


def test_unchanged_joint_is_checked_without_limiting_an_unrelated_root_derivative():
    vectors=np.array([[[0.,1.,0.],[0.,0.,0.]]]);caps=np.array([[1.,0.]])
    lo,hi,a,b=root.vertical_intervals(vectors,caps,tolerance=0,affected_joints=np.array([True,False]))
    assert lo[0]==-2 and hi[0]==0 and a[0]==b[0]==0
    changed=vectors.copy();changed[:,0,1]-=1
    assert np.all(np.linalg.norm(changed,axis=2)<=caps)
    with pytest.raises(ValueError,match='Unaffected original'):
        root.vertical_intervals(vectors+np.array([[[0,0,0],[0,1,0]]]),caps,tolerance=0,affected_joints=np.array([True,False]))


@pytest.fixture
def recipe(tmp_path):
    source,_=fixture(tmp_path/'input','root-source',animated=False,axes=13)
    rig=RigAsset.load(source);document=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    node=next(i for i,n in enumerate(document['nodes']) if n['name']=='root-source_Hips');parent=rig.parents[node]
    axis=np.linalg.solve(rig.reference[parent,:3,:3],np.array([0.,1.,0.]))
    initial=np.asarray(document['nodes'][node]['translation']);times=append_accessor(document,binary,np.array([0.,2.]),'SCALAR')
    values=append_accessor(document,binary,np.array([initial,initial+axis]),'VEC3')
    document['animations']=[dict(name='Generated upright translation fixture',channels=[dict(sampler=0,target=dict(node=node,path='translation'))],samplers=[dict(input=times,output=values,interpolation='LINEAR')])]
    write_glb(source,document,binary);rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    clock=np.unique(np.concatenate([p['times_s'] for p in frame_populations([0.,2.])]))
    floor_y=float(rig.vertices(reader.sample(0.))[:,1].min())+.04
    report=compare(source,source,clock,source_animation=0,target_animation=0,floor_y_m=floor_y,tolerance_m=.005)
    floor=tmp_path/'floor.json';save(floor,report)
    value=dict(schema=root.SCHEMA,source=dict(path=str(source),sha256=sha256(source),animation_index=0,root_node=node),
        floor_reference=dict(path=str(floor),sha256=sha256(floor),side='source'),maximum_displacement_m=.22,floor_reserve_m=.0005,frozen_keys=[1])
    path=tmp_path/'recipe.json';save(path,value);return path,value,source,floor


def test_real_scalar_correction_clears_floor_and_keeps_caps_end_and_other_tracks(recipe,tmp_path):
    path,value,source,floor=recipe;before=source.read_bytes();result=root.run(path,tmp_path/'proposal')
    assert result['solver_success'] and result['sampled_conditions_pass']
    assert result['rate_failures']==[0,0,0,0] and result['floor_failed_samples']==0
    assert result['maximum_joint_displacement_m']<.04 and result['maximum_horizontal_joint_drift_m']<=1e-7
    assert result['frozen_keys_and_other_tracks_preserved'] and source.read_bytes()==before
    assert result['original_selected'] and not result['quality_approved'] and not result['release_approved']
    assert result['output_animation_index']==1


def test_frozen_penetrating_start_retains_infeasible_proposal_without_export(recipe,tmp_path):
    path,value,source,floor=recipe;value['frozen_keys']=[0,1];save(path,value);output=tmp_path/'rejected'
    result=root.run(path,output)
    assert not result['solver_success'] and not result['sampled_conditions_pass'] and not (output/'character.glb').exists()
    assert 'not a global' in result['scope_failure'] and result['original_selected']


def test_nonunit_stored_inverse_bind_response_uses_full_positive_coefficient_bound(recipe,tmp_path):
    path,value,source,floor=recipe;rig=RigAsset.load(source)
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);inverse=rig.inverse.copy()
    inverse[:,3,3]+=np.where(np.arange(len(inverse))%2,1e-7,-1e-7)
    document['skins'][0]['inverseBindMatrices']=append_accessor(document,binary,inverse.transpose(0,2,1).reshape(-1,16),'MAT4')
    write_glb(source,document,binary);value['source']['sha256']=sha256(source)
    prior=read(floor);report=compare(source,source,prior['times_s'],floor_y_m=prior['floor_y_m'],tolerance_m=prior['tolerance_m'])
    save(floor,report);value['floor_reference']['sha256']=sha256(floor);save(path,value)
    prepared=root.prepare(value,path.parent);coefficients=prepared[5]
    assert coefficients.min()<1 and coefficients.max()>1
    result=root.run(path,tmp_path/'nonunit-proposal')
    assert result['sampled_conditions_pass'] and result['rate_failures']==[0,0,0,0] and result['floor_failed_samples']==0


def test_unweighted_skin_ancestor_keeps_all_original_caps_and_world_transforms(recipe,tmp_path):
    path,value,source,floor=recipe;rig=RigAsset.load(source)
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);ancestor=int(rig.parents[value['source']['root_node']])
    document['skins'][0]['joints'].append(ancestor)
    inverse=np.concatenate([rig.inverse,np.linalg.inv(rig.reference[ancestor])[None]])
    document['skins'][0]['inverseBindMatrices']=append_accessor(document,binary,inverse.transpose(0,2,1).reshape(-1,16),'MAT4')
    write_glb(source,document,binary);value['source']['sha256']=sha256(source)
    prior=read(floor);save(floor,compare(source,source,prior['times_s'],floor_y_m=prior['floor_y_m'],tolerance_m=prior['tolerance_m']))
    value['floor_reference']['sha256']=sha256(floor);save(path,value)
    result=root.run(path,tmp_path/'ancestor-proposal')
    assert result['sampled_conditions_pass'] and result['rate_failures']==[0,0,0,0]
    assert result['unaffected_skin_joints']==1 and result['affected_skin_joints']==len(rig.joints)
    assert result['unaffected_joint_world_transforms_preserved']
    assert result['full_original_rate_rows']>0 and result['frozen_keys_and_other_tracks_preserved']
    observations=np.load(tmp_path/'ancestor-proposal/reference.npz')
    assert not observations['affected_skin_joint_mask'][-1]


@pytest.fixture
def grid_recipe(recipe):
    path,value,source,floor=recipe;rig=RigAsset.load(source)
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    node=value['source']['root_node'];document['nodes'][rig.parents[node]]['rotation']=[0.,0.,0.,1.]
    channel=document['animations'][0]['channels'][0];sampler=document['animations'][0]['samplers'][channel['sampler']]
    start=np.asarray(document['nodes'][node]['translation'])
    sampler['output']=append_accessor(document,binary,np.array([start,start+[0.,1.,0.]]),'VEC3')
    write_glb(source,document,binary);rig=RigAsset.load(source);reader=NativeSupportSampler(rig.document,rig.binary,0)
    prior=read(floor);floor_y=float(rig.vertices(reader.sample(0.))[:,1].min())+.04
    save(floor,compare(source,source,prior['times_s'],floor_y_m=floor_y,tolerance_m=prior['tolerance_m']))
    value['source']['sha256']=sha256(source);value['floor_reference']['sha256']=sha256(floor)
    value['storage_mode']='float32-axis-grid';save(path,value);return path,value,source,floor


def test_float32_grid_export_clears_actual_fixture_without_changing_acceptance(grid_recipe,tmp_path):
    path,value,source,floor=grid_recipe
    result=root.run(path,tmp_path/'grid-proposal')
    assert result['sampled_conditions_pass'] and result['rate_failures']==[0,0,0,0]
    assert result['floor_failed_samples']==0 and result['frozen_keys_and_other_tracks_preserved']
    storage=read(tmp_path/'grid-proposal/storage.json')
    assert storage['integer_controls'] is not None and result['solver_method']=='scipy-highs-milp'
    assert result['horizontal_preservation_tolerance_m']==1e-7


def test_grid_coordinates_survive_exponent_crossings_and_keep_frozen_originals():
    values=np.array([[0.,0.,.49999997],[0.,0.,-.50000006],[0.,0.,.031234567]],np.float32).astype(float)
    spacing,base,lo,hi=coordinates(values,np.array([0.,0.,1.]),.22,[2])
    for integers in (lo,hi,np.floor((lo+hi)/2)):
        offsets=base+spacing*integers
        edited=values.copy();edited[:,2]+=offsets
        assert np.array_equal(edited,edited.astype(np.float32).astype(float))
        assert np.all(offsets>=0) and np.all(offsets<=.22)
        assert np.array_equal(edited[2],values[2])
    with pytest.raises(ValueError,match='unit root axis'):
        coordinates(values,np.array([0.,.6,.8]),.22,[2])


def test_float32_grid_frozen_penetration_retains_failed_attempt(grid_recipe,tmp_path):
    path,value,source,floor=grid_recipe;value['frozen_keys']=[0,1];save(path,value)
    result=root.run(path,tmp_path/'grid-rejected')
    assert not result['solver_success'] and not result['sampled_conditions_pass']
    assert not (tmp_path/'grid-rejected/character.glb').exists()
    assert 'not a global' in result['scope_failure']


@pytest.mark.parametrize('fault',['digest','index','root','bound','reserve','frozen','missing-clock','approval'])
def test_invalid_or_unbound_authoring_rejects_before_output(recipe,tmp_path,fault):
    path,value,source,floor=recipe
    if fault=='digest':value['source']['sha256']='0'*64
    elif fault=='index':value['source']['animation_index']=True
    elif fault=='root':value['source']['root_node']=999
    elif fault=='bound':value['maximum_displacement_m']=.221
    elif fault=='reserve':value['floor_reserve_m']=.005
    elif fault=='frozen':value['frozen_keys']=[True]
    else:
        report=read(floor)
        if fault=='approval':report['quality_approved']=True
        else:
            report['times_s'].pop(1);report['source']['minimum_y_m'].pop(1);report['samples']-=1
        save(floor,report);value['floor_reference']['sha256']=sha256(floor)
    save(path,value);output=tmp_path/'invalid'
    with pytest.raises((ValueError,IndexError)):root.run(path,output)
    assert not output.exists()
